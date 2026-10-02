"""
Storage for saved selections: named sets of hand-picked map features.

A member is remembered by a locator (layer, attribute fingerprint, anchor point) rather than by
`search_index.id`, because `build_search_index.py` drops and recreates that table and the
`bigserial` ids restart: a stale id would silently point at a different feature. Members are
resolved in PostGIS on demand, see `resolve_member`.

Like `saved_filters` before it, this module owns tables no pipeline can regenerate, so it uses
`CREATE TABLE IF NOT EXISTS` and must never DROP. `docker compose down -v` destroys them; the
JSON backup (`export_backup` / `import_backup`) is the mitigation.

Run standalone to create or repair the tables:
    uv run python -m src.saved_selections
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.database import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

T_SELECTIONS = "saved_selections"
T_MEMBERS = "saved_selection_members"

#: Keeps one set cheap to draw and export in a single request.
MEMBER_CAP = 500
#: ~0.1 m. The anchor is ST_PointOnSurface so it lies inside polygons at distance 0; one
#: tolerance also serves lines and points.
ANCHOR_TOLERANCE = 1e-6

HINT_MAX_KEYS = 20
HINT_MAX_VALUE_LEN = 200

DDL = (
    f"""
    CREATE TABLE IF NOT EXISTS {T_SELECTIONS} (
        id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name        text NOT NULL CHECK (btrim(name) <> ''),
        name_norm   text GENERATED ALWAYS AS (lower(btrim(name))) STORED,
        description text,
        created_at  timestamptz NOT NULL DEFAULT now(),
        updated_at  timestamptz NOT NULL DEFAULT now()
    )
    """,
    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{T_SELECTIONS}_name_norm ON {T_SELECTIONS} (name_norm)",
    f"""
    CREATE TABLE IF NOT EXISTS {T_MEMBERS} (
        id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        selection_id uuid NOT NULL REFERENCES {T_SELECTIONS}(id) ON DELETE CASCADE,
        layer_id     text NOT NULL,
        label        text NOT NULL,
        fingerprint  text NOT NULL,
        anchor_lng   double precision NOT NULL,
        anchor_lat   double precision NOT NULL,
        hint         jsonb NOT NULL DEFAULT '{{}}'::jsonb,
        note         text,
        added_at     timestamptz NOT NULL DEFAULT now(),
        UNIQUE (selection_id, layer_id, fingerprint, anchor_lng, anchor_lat)
    )
    """,
    f"CREATE INDEX IF NOT EXISTS idx_{T_MEMBERS}_selection ON {T_MEMBERS} (selection_id, added_at)",
)

#: Geometry expressions for `resolve_member`, selected as the `geom` column.
NO_GEOM_SQL = "NULL"
GEOJSON_SQL = "ST_AsGeoJSON(ST_SimplifyPreserveTopology(geometry, :simp), 6)::json"
KML_SQL = ("ST_AsKML(CASE WHEN GeometryType(geometry) = 'GEOMETRYCOLLECTION' "
           "THEN ST_CollectionExtract(geometry) ELSE geometry END, 7)")

_MEMBER_COLUMNS = ("id, selection_id, layer_id, label, fingerprint, anchor_lng, anchor_lat, "
                   "hint, note, added_at")


class DuplicateSelectionName(ValueError):
    """The name collides, ignoring case and surrounding whitespace, with an existing set."""


class SelectionFull(ValueError):
    """The set already holds MEMBER_CAP members."""


# --------------------------------------------------------------------------- pure helpers

def normalize_name(name: str) -> str:
    """Mirrors the generated `name_norm` column: lower() and btrim() only."""
    return (name or "").strip().lower()


def hint_from_props(props: Mapping[str, Any] | None) -> dict[str, str]:
    """String-valued properties only (MVT rounds numbers and omits nulls, so only strings
    compare reliably), bounded so one verbose feature cannot bloat the table."""
    hint: dict[str, str] = {}
    for key, value in (props or {}).items():
        if isinstance(value, str) and value and len(value) <= HINT_MAX_VALUE_LEN:
            hint[key] = value
        if len(hint) >= HINT_MAX_KEYS:
            break
    return hint


def member_key(member: Mapping[str, Any]) -> tuple:
    """What makes two members the same feature; the note and ids are not part of it."""
    return (member["layer_id"], member["fingerprint"],
            member["anchor_lng"], member["anchor_lat"])


# --------------------------------------------------------------------------- schema

def ensure_saved_selections_tables(engine=None) -> None:
    engine = engine or get_engine()
    with engine.begin() as conn:
        for statement in DDL:
            conn.execute(text(statement))
    logger.info(f"Tables '{T_SELECTIONS}' and '{T_MEMBERS}' are present.")


# --------------------------------------------------------------------------- selections

def _row(row: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key, value in out.items():
        if key in ("id", "selection_id"):
            out[key] = str(value)
        elif hasattr(value, "isoformat"):
            out[key] = value.isoformat()
    return out


def list_selections(engine) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(text(
            f"SELECT s.id, s.name, s.description, s.updated_at, "
            f"       (SELECT count(*) FROM {T_MEMBERS} m WHERE m.selection_id = s.id) AS member_count "
            f"FROM {T_SELECTIONS} s ORDER BY s.updated_at DESC")).mappings().all()
    return [_row(r) for r in rows]


def get_selection(engine, selection_id: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        row = conn.execute(text(
            f"SELECT s.id, s.name, s.description, s.updated_at, "
            f"       (SELECT count(*) FROM {T_MEMBERS} m WHERE m.selection_id = s.id) AS member_count "
            f"FROM {T_SELECTIONS} s WHERE s.id = CAST(:id AS uuid)"), {"id": selection_id}).mappings().first()
    return _row(row) if row else None


def create_selection(engine, name: str, description: str | None = None) -> dict[str, Any]:
    try:
        with engine.begin() as conn:
            row = conn.execute(text(
                f"INSERT INTO {T_SELECTIONS} (name, description) VALUES (btrim(:name), :description) "
                f"RETURNING id"), {"name": name, "description": description}).first()
    except IntegrityError as exc:
        raise DuplicateSelectionName(f"Já existe um conjunto chamado '{name.strip()}'.") from exc
    return get_selection(engine, str(row[0]))


def update_selection(engine, selection_id: str, *, name: str | None = None,
                     description: str | None = None) -> dict[str, Any] | None:
    sets, params = ["updated_at = now()"], {"id": selection_id}
    if name is not None:
        sets.append("name = btrim(:name)")
        params["name"] = name
    if description is not None:
        sets.append("description = :description")
        params["description"] = description
    try:
        with engine.begin() as conn:
            result = conn.execute(text(
                f"UPDATE {T_SELECTIONS} SET {', '.join(sets)} WHERE id = CAST(:id AS uuid)"), params)
    except IntegrityError as exc:
        raise DuplicateSelectionName(f"Já existe um conjunto chamado '{(name or '').strip()}'.") from exc
    return get_selection(engine, selection_id) if result.rowcount else None


def delete_selection(engine, selection_id: str) -> bool:
    with engine.begin() as conn:
        return conn.execute(text(f"DELETE FROM {T_SELECTIONS} WHERE id = CAST(:id AS uuid)"),
                            {"id": selection_id}).rowcount > 0


# --------------------------------------------------------------------------- members

def list_members(engine, selection_id: str) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(text(
            f"SELECT {_MEMBER_COLUMNS} FROM {T_MEMBERS} "
            f"WHERE selection_id = CAST(:id AS uuid) ORDER BY added_at, id"),
            {"id": selection_id}).mappings().all()
    return [_row(r) for r in rows]


def _get_member(conn, selection_id: str, member_id: str) -> dict[str, Any] | None:
    row = conn.execute(text(
        f"SELECT {_MEMBER_COLUMNS} FROM {T_MEMBERS} "
        f"WHERE selection_id = CAST(:s AS uuid) AND id = CAST(:m AS uuid)"),
        {"s": selection_id, "m": member_id}).mappings().first()
    return _row(row) if row else None


def add_member(engine, selection_id: str, *, layer_id: str, label: str, fingerprint: str,
               lng: float, lat: float, hint: Mapping[str, str], note: str | None = None
               ) -> tuple[dict[str, Any], bool]:
    """Idempotent: adding a feature already in the set returns the existing member."""
    params = {"s": selection_id, "layer": layer_id, "label": label, "fp": fingerprint,
              "lng": lng, "lat": lat, "hint": json.dumps(dict(hint)), "note": note}
    with engine.begin() as conn:
        # Serialise adds per set: without the row lock two simultaneous requests both pass the
        # "already there?" and cap checks, so a double click raised IntegrityError (HTTP 500)
        # and the cap could be exceeded.
        conn.execute(text(f"SELECT 1 FROM {T_SELECTIONS} WHERE id = CAST(:s AS uuid) FOR UPDATE"), params)
        existing = conn.execute(text(
            f"SELECT {_MEMBER_COLUMNS} FROM {T_MEMBERS} WHERE selection_id = CAST(:s AS uuid) "
            f"AND layer_id = :layer AND fingerprint = :fp AND anchor_lng = :lng AND anchor_lat = :lat"),
            params).mappings().first()
        if existing:
            return _row(existing), False

        count = conn.execute(text(
            f"SELECT count(*) FROM {T_MEMBERS} WHERE selection_id = CAST(:s AS uuid)"), params).scalar()
        if count >= MEMBER_CAP:
            raise SelectionFull(f"Um conjunto aceita no máximo {MEMBER_CAP} áreas.")

        row = conn.execute(text(
            f"INSERT INTO {T_MEMBERS} (selection_id, layer_id, label, fingerprint, anchor_lng, "
            f"anchor_lat, hint, note) VALUES (CAST(:s AS uuid), :layer, :label, :fp, :lng, :lat, "
            f"CAST(:hint AS jsonb), :note) RETURNING {_MEMBER_COLUMNS}"), params).mappings().first()
        conn.execute(text(f"UPDATE {T_SELECTIONS} SET updated_at = now() WHERE id = CAST(:s AS uuid)"), params)
        return _row(row), True


def update_member_note(engine, selection_id: str, member_id: str, note: str | None) -> dict[str, Any] | None:
    with engine.begin() as conn:
        result = conn.execute(text(
            f"UPDATE {T_MEMBERS} SET note = :note "
            f"WHERE selection_id = CAST(:s AS uuid) AND id = CAST(:m AS uuid)"),
            {"s": selection_id, "m": member_id, "note": (note or None)})
        if not result.rowcount:
            return None
        conn.execute(text(f"UPDATE {T_SELECTIONS} SET updated_at = now() WHERE id = CAST(:s AS uuid)"),
                     {"s": selection_id})
        return _get_member(conn, selection_id, member_id)


def remove_member(engine, selection_id: str, member_id: str) -> bool:
    with engine.begin() as conn:
        removed = conn.execute(text(
            f"DELETE FROM {T_MEMBERS} WHERE selection_id = CAST(:s AS uuid) AND id = CAST(:m AS uuid)"),
            {"s": selection_id, "m": member_id}).rowcount > 0
        if removed:
            conn.execute(text(f"UPDATE {T_SELECTIONS} SET updated_at = now() WHERE id = CAST(:s AS uuid)"),
                         {"s": selection_id})
        return removed


# --------------------------------------------------------------------------- resolution

def resolve_member(engine_or_conn, member: Mapping[str, Any], geom_sql: str = NO_GEOM_SQL,
                   simplify: float = 0.0) -> dict[str, Any]:
    """Finds the `search_index` row a member refers to.

    Narrowed by position through the GIST index first, so the md5 of `props` is computed for a
    handful of rows. Ranks exact fingerprint, then string-attribute hint, then distance, then
    smallest area. `status` is `exact` (same attributes), `approximate` (found at the anchor
    with the same label but changed attributes) or `missing` (no row of that layer near the
    anchor matches by attributes or label). A different feature that merely covers the anchor
    is `missing`, never `approximate`: otherwise a removed CAR parcel would hand its note to
    whichever neighbour overlaps it.
    """
    point = "ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)"
    sql = text(
        f"SELECT id, layer_id, label, props, md5(props::text) = :fp AS exact, {geom_sql} AS geom "
        f"FROM search_index "
        f"WHERE layer_id = :layer AND ST_DWithin(geometry, {point}, :tol) "
        f"  AND (md5(props::text) = :fp OR label = :label) "
        f"ORDER BY exact DESC, (props @> CAST(:hint AS jsonb)) DESC, "
        f"         ST_Distance(geometry, {point}) ASC, ST_Area(geometry) ASC "
        f"LIMIT 1")
    params = {"layer": member["layer_id"], "fp": member["fingerprint"], "label": member["label"],
              "lng": member["anchor_lng"], "lat": member["anchor_lat"],
              "tol": ANCHOR_TOLERANCE, "hint": json.dumps(member.get("hint") or {})}
    if ":simp" in geom_sql:
        params["simp"] = simplify

    if hasattr(engine_or_conn, "connect"):
        with engine_or_conn.connect() as conn:
            row = conn.execute(sql, params).mappings().first()
    else:
        row = engine_or_conn.execute(sql, params).mappings().first()

    if row is None:
        return {"status": "missing", "row": None}
    return {"status": "exact" if row["exact"] else "approximate", "row": row}


# --------------------------------------------------------------------------- backup

def export_backup(engine) -> list[dict[str, Any]]:
    """Locators only, no geometry, so a backup stays valid across index rebuilds."""
    out = []
    for selection in list_selections(engine):
        members = [{k: m[k] for k in ("layer_id", "label", "fingerprint", "anchor_lng",
                                      "anchor_lat", "hint", "note")}
                   for m in list_members(engine, selection["id"])]
        out.append({"name": selection["name"], "description": selection["description"],
                    "members": members})
    return out


def import_backup(engine, records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Upserts sets by name and merges members by locator, so re-importing never duplicates."""
    selections = members_added = skipped = 0
    existing = {normalize_name(s["name"]): s["id"] for s in list_selections(engine)}
    for record in records:
        name = (record or {}).get("name")
        if not isinstance(name, str) or not name.strip():
            skipped += 1
            continue
        selection_id = existing.get(normalize_name(name))
        if selection_id is None:
            selection_id = create_selection(engine, name, record.get("description"))["id"]
            existing[normalize_name(name)] = selection_id
            selections += 1
        for member in record.get("members") or []:
            try:
                _, created = add_member(
                    engine, selection_id,
                    layer_id=member["layer_id"], label=member["label"],
                    fingerprint=member["fingerprint"], lng=member["anchor_lng"],
                    lat=member["anchor_lat"], hint=member.get("hint") or {}, note=member.get("note"))
            except (KeyError, SelectionFull):
                skipped += 1
                continue
            members_added += int(created)
    return {"selections": selections, "members_added": members_added, "skipped": skipped}


if __name__ == "__main__":
    ensure_saved_selections_tables()
