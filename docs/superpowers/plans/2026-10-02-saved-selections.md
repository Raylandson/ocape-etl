# Saved Selections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the rule-based filter builder with named sets of hand-picked map features that can be annotated, shown on their own on the map, and exported to KML.

**Architecture:** A member is remembered by a locator (layer, attribute fingerprint, anchor point), never by a `search_index` id, and is resolved in PostGIS on demand. A new FastAPI router (`/selections`) owns CRUD, geometry for drawing and KML export. On the Angular side a root `SelectionService` holds the active set; a new panel replaces the builder, add buttons live in the Sobreposições rows and the detail popup, and an isolation service draws the set's full boundaries after hiding the data layers.

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy + PostGIS 3.5 (`uv run`), pytest; Angular 20 standalone components + signals, MapLibre GL JS.

**Spec:** [`docs/specs/2026-10-02-saved-selections.md`](../../specs/2026-10-02-saved-selections.md)

## Global Constraints

- Commits: **never run `git commit`** unless the user explicitly asks (global and `AGENTS.md` rule). Each task ends with a checkpoint, not a commit.
- Spatial data stays EPSG:4326; new tables have no geometry column (Martin ignores them).
- Tables use `CREATE TABLE IF NOT EXISTS`, never `DROP`: these hold user data no pipeline can regenerate.
- Cap: **500 members per selection**.
- UI: minimalist institutional design, no decorative emojis, pt-BR strings, SVG stroke icons, `@if` / `@for … track` control flow, standalone components. Panels are 320 px wide (the left stack sets the width; components use `width: 100%`).
- The API container has **no auto-reload**: run `docker compose restart search` after every backend change before testing against `localhost:7055`.
- Python tests import only modules that do not connect to a database at import time; DB-backed tests skip themselves when no database is reachable.
- Run everything from the repo root `/home/raylenda/github/personal/ocape-etl`. Python via `uv run`; frontend dev server is already on `http://localhost:4200` (`ng serve` hot-reloads).
- `AGENTS.md` doc protocol: read `docs/` before changing, update `docs/CHANGELOG.md` and `README.md` on completion (Task 11).

## Spec adjustments made by this plan

The spec is the source of intent; three details change here and Task 11 edits the spec to match:

1. **Resolution tolerance is uniform `1e-6` degrees** (≈0.1 m), not `0` for polygons. The anchor is `ST_PointOnSurface`, so it lies inside the polygon at distance 0 either way; one tolerance keeps lines and points working with no geometry-type branch.
2. **Pressing "add" on a feature already in the set does not toggle it off.** The member is not duplicated, the panel shows "Já está no conjunto", and removal happens from the panel. (Spec acceptance criterion 2's "pressing it again removes it" is dropped: the client cannot compute the server-side fingerprint, so it cannot know a row is already a member without an extra lookup endpoint.)
3. **`_locate_feature` in `export_api.py` is not modified.** The add-member endpoint calls it with a `geometry_sql` that returns a small JSON object (`lng`, `lat`, fingerprint) in the existing `geom` column.

## Review Focus

1. **Note with markup** (`<script>`, `]]>`, `&`, quotes) must not break the KML or inject HTML into the balloon. Pinned in Task 1.
2. **A member whose source row vanished or moved** (index rebuilt, ETL re-ingest) must resolve to `missing`, keep its note, be skipped by geometry and export, and be listed in `LEIAME.txt` rather than producing an empty placemark. Pinned in Tasks 2 and 4.
3. **The same feature added twice** (double click, or row button then popup button) must yield one member and a 200; the 501st member must yield 409. Pinned in Task 2.
4. **An empty set, or a set whose members are all `missing`**: Isolar must not hide any layer, export must be disabled/refuse, and neither may produce an empty file. Pinned in Tasks 4 and 8.
5. **Deleting or switching the active set while isolated, or toggling layers during isolation, then leaving isolation**: the layer snapshot taken on entry is restored exactly and no overlay or hidden layer is left behind. Pinned in Task 8.

---

## File Structure

| File | Responsibility |
| :--- | :--- |
| `src/saved_selections.py` (new) | DDL, pure helpers (`normalize_name`, `hint_from_props`, `member_key`), and all SQL for sets, members, resolution and backup. No FastAPI. |
| `src/selections_api.py` (new) | FastAPI router for `/selections*`. Thin: validation, HTTP errors, response shaping. |
| `src/kml_writer.py` (modify) | `KmlItem.note`; `html_description(..., note=None)` renders an **Observação** block. |
| `src/search_api.py` (modify) | Include the router; ensure tables on startup (replaces `saved_filters` wiring in Task 10). |
| `src/run_all_pipelines.py` (modify) | Step `8b` ensures the selection tables. |
| `tests/test_kml_writer.py` (modify) | Note rendering tests. |
| `tests/test_saved_selections.py` (new) | Pure helper tests. |
| `tests/test_saved_selections_db.py` (new) | DB-backed lifecycle/resolution tests (skip without DB). |
| `frontend/src/app/services/selection.service.ts` (new) | HTTP + shared state: sets, active set, members, notices, panel open flag. |
| `frontend/src/app/services/selection-isolation.service.ts` (new) | "Isolar": layer snapshot/restore, overlay source and layers, fit bounds. |
| `frontend/src/app/selections-panel/` (new) | The Filtros panel UI. |
| `frontend/src/app/overlap-stack-panel/*` (modify) | Add button on each row. |
| `frontend/src/app/app.ts`, `app.html`, `app.css` (modify) | Wiring: panel, add handlers, popup button, isolation host, hit-test of the overlay. |
| `frontend/src/app/services/export.service.ts` (modify) | `exportSelection`; later drop `exportFilter`. |
| Removed in Task 10 | `filter-builder/`, `filter.service.ts`, `src/filters_api.py`, `filter_compiler.py`, `filter_catalog.py`, `saved_filters.py`, `tests/test_filter_compiler.py`, `POST /export/kml` |

---

### Task 1: KML note support

**Files:**
- Modify: `src/kml_writer.py:47-60` (`KmlItem`), `:184-215` (`html_description`), `:228-241` (`build_placemark`)
- Test: `tests/test_kml_writer.py`

**Interfaces:**
- Consumes: existing `KmlItem`, `html_description(title, layer_name, properties)`, `build_placemark`, `build_document`.
- Produces: `KmlItem.note: str | None = None`; `html_description(title, layer_name, properties, note=None)`. Tasks 4 uses `KmlItem(note=...)`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_kml_writer.py`:

```python
# --- member notes ("Observação") -----------------------------------------------------

def test_note_renders_as_observacao_block():
    desc = html_description("CAR PE-1", "CAR", {"cod_imovel": "PE-1"}, note="Visitar em março")
    assert "Observação" in desc
    assert "Visitar em março" in desc


def test_no_note_means_no_observacao_block():
    assert "Observação" not in html_description("t", "l", {"a": 1})
    assert "Observação" not in html_description("t", "l", {"a": 1}, note="   ")
    assert "Observação" not in html_description("t", "l", {"a": 1}, note=None)


def test_note_markup_is_escaped_and_cdata_survives():
    hostile = "<script>alert(1)</script> ]]> & \"q\" 'a'"
    desc = html_description("t", "l", {"a": 1}, note=hostile)
    assert "<script>" not in desc
    assert desc.count("]]>") == 1          # only the real CDATA terminator at the end
    assert "&lt;script&gt;" in desc


def test_placemark_with_hostile_note_is_well_formed_xml():
    item = KmlItem(geometry_kml=POLY, properties={"cod_imovel": "PE-1"},
                   layer_id="area_imovel_1", layer_name="CAR",
                   note="<b>x</b> ]]> & <![CDATA[ nested")
    ET.fromstring(build_document("doc", [item]))   # raises ParseError if malformed
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_kml_writer.py -k "note" -v`
Expected: FAIL (`html_description() got an unexpected keyword argument 'note'`, `KmlItem` has no `note`).

- [ ] **Step 3: Implement.** In `src/kml_writer.py`:

Add the field to `KmlItem` after `border_color`:

```python
    border_color: str | None = None
    #: Free text a user attached to this feature in a saved selection; rendered as "Observação".
    note: str | None = None
```

Change the `html_description` signature and add the note block. Replace the function header and the line `<table style="width: 100%; border-collapse: collapse;">` region:

```python
def html_description(title: str, layer_name: str, properties: dict[str, Any],
                     note: str | None = None) -> str:
```

Immediately before the `return f"""<![CDATA[` statement add:

```python
    note_html = ""
    if note and note.strip():
        note_html = (
            '<div style="margin-bottom: 8px; padding: 6px 8px; background: #fffbeb; '
            'border: 1px solid #fde68a; border-radius: 4px; font-size: 11px; color: #78350f;">'
            f'<strong>Observação:</strong> {escape_xml(note.strip())}</div>'
        )
```

and inside the returned template, put `{note_html}` directly before `<table style="width: 100%; border-collapse: collapse;">`:

```python
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-top: none; border-radius: 0 0 6px 6px; padding: 8px;">
          {note_html}
          <table style="width: 100%; border-collapse: collapse;">
```

In `build_placemark` change the description call:

```python
      <description>{html_description(title, layer_name, properties, item.note)}</description>
```

- [ ] **Step 4: Run all KML tests**

Run: `uv run pytest tests/test_kml_writer.py tests/test_kml_archive.py -v`
Expected: all PASS (existing tests unchanged, 4 new ones pass).

- [ ] **Step 5: Checkpoint** — `uv run pytest` fully green. Do not commit.

---

### Task 2: `saved_selections` storage module

**Files:**
- Create: `src/saved_selections.py`
- Test: `tests/test_saved_selections.py` (pure), `tests/test_saved_selections_db.py` (DB)

**Interfaces:**
- Consumes: `src.database.get_engine`.
- Produces (used by Tasks 3–5), all taking a SQLAlchemy `engine` first:
  - constants `MEMBER_CAP = 500`, `ANCHOR_TOLERANCE = 1e-6`, `GEOJSON_SQL`, `KML_SQL`, `NO_GEOM_SQL`
  - exceptions `DuplicateSelectionName`, `SelectionFull`
  - pure: `normalize_name(name) -> str`, `hint_from_props(props) -> dict[str, str]`, `member_key(member) -> tuple`
  - `ensure_saved_selections_tables(engine=None)`
  - `list_selections(engine) -> list[dict]`, `get_selection(engine, id) -> dict | None`, `create_selection(engine, name, description=None) -> dict`, `update_selection(engine, id, *, name=None, description=None) -> dict | None`, `delete_selection(engine, id) -> bool`
  - `list_members(engine, selection_id) -> list[dict]` (keys: `id, selection_id, layer_id, label, fingerprint, anchor_lng, anchor_lat, hint, note, added_at`)
  - `add_member(engine, selection_id, *, layer_id, label, fingerprint, lng, lat, hint, note=None) -> tuple[dict, bool]` (member, created)
  - `update_member_note(engine, selection_id, member_id, note) -> dict | None`, `remove_member(engine, selection_id, member_id) -> bool`
  - `resolve_member(engine_or_conn, member, geom_sql=NO_GEOM_SQL, simplify=0.0) -> dict` with keys `status` (`"exact" | "approximate" | "missing"`), `row` (mapping with `layer_id, label, props, geom` or `None`)
  - `export_backup(engine) -> list[dict]`, `import_backup(engine, records) -> dict` (`{"selections": int, "members_added": int, "skipped": int}`)

- [ ] **Step 1: Write the failing pure tests** — create `tests/test_saved_selections.py`:

```python
from src.saved_selections import MEMBER_CAP, hint_from_props, member_key, normalize_name


def test_normalize_name_matches_the_generated_column():
    assert normalize_name("  Fazenda X ") == "fazenda x"
    assert normalize_name("FAZENDA X") == normalize_name("fazenda x")


def test_hint_keeps_only_short_string_values():
    props = {"cod": "PE-1", "area": 12.5, "n": None, "empty": "", "long": "x" * 500, "ok": "a"}
    assert hint_from_props(props) == {"cod": "PE-1", "ok": "a"}


def test_hint_is_bounded_in_key_count():
    props = {f"k{i}": "v" for i in range(100)}
    assert len(hint_from_props(props)) <= 20


def test_member_key_identifies_a_feature_not_a_row():
    a = {"layer_id": "l", "fingerprint": "f", "anchor_lng": 1.0, "anchor_lat": 2.0, "note": "x"}
    b = {**a, "note": "different note", "id": "other"}
    assert member_key(a) == member_key(b)
    assert member_key(a) != member_key({**a, "anchor_lng": 1.5})


def test_cap_is_five_hundred():
    assert MEMBER_CAP == 500
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_saved_selections.py -v`
Expected: FAIL (`ModuleNotFoundError: src.saved_selections`).

- [ ] **Step 3: Write the DB tests** — create `tests/test_saved_selections_db.py`:

```python
"""Lifecycle and resolution against the real database. Skips when it is not reachable."""
import uuid

import pytest
from sqlalchemy import text

from src import saved_selections as store


@pytest.fixture(scope="module")
def engine():
    try:
        from src.database import get_engine
        eng = get_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1 FROM search_index LIMIT 1"))
    except Exception:
        pytest.skip("database with search_index is not reachable")
    store.ensure_saved_selections_tables(eng)
    return eng


@pytest.fixture
def selection(engine):
    created = store.create_selection(engine, f"pytest-{uuid.uuid4()}")
    yield created
    store.delete_selection(engine, created["id"])


def _sample_feature(engine, layer="tis_poligonais"):
    """A real indexed feature, described the way the add-member endpoint stores it."""
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT label, props, md5(props::text) AS fp, "
            "       ST_X(ST_PointOnSurface(geometry)) AS lng, ST_Y(ST_PointOnSurface(geometry)) AS lat "
            "FROM search_index WHERE layer_id = :l LIMIT 1"), {"l": layer}).mappings().first()
    assert row is not None, f"no rows indexed for {layer}"
    return dict(layer_id=layer, label=row["label"], fingerprint=row["fp"],
                lng=row["lng"], lat=row["lat"], hint=store.hint_from_props(row["props"]))


def test_duplicate_names_are_rejected_case_and_space_insensitively(engine, selection):
    with pytest.raises(store.DuplicateSelectionName):
        store.create_selection(engine, f"  {selection['name'].upper()}  ")


def test_adding_the_same_feature_twice_is_idempotent(engine, selection):
    feature = _sample_feature(engine)
    first, created_first = store.add_member(engine, selection["id"], **feature)
    second, created_second = store.add_member(engine, selection["id"], **feature)
    assert created_first is True and created_second is False
    assert first["id"] == second["id"]
    assert len(store.list_members(engine, selection["id"])) == 1


def test_cap_blocks_the_501st_member(engine, selection, monkeypatch):
    monkeypatch.setattr(store, "MEMBER_CAP", 1)
    store.add_member(engine, selection["id"], **_sample_feature(engine))
    other = {**_sample_feature(engine), "fingerprint": "different", "lng": 0.0, "lat": 0.0}
    with pytest.raises(store.SelectionFull):
        store.add_member(engine, selection["id"], **other)


def test_resolution_is_exact_approximate_or_missing(engine, selection):
    feature = _sample_feature(engine)
    member, _ = store.add_member(engine, selection["id"], **feature)

    assert store.resolve_member(engine, member)["status"] == "exact"

    # Attributes drifted since the member was saved (an ETL re-ingest): still found, flagged.
    drifted = {**member, "fingerprint": "stale"}
    result = store.resolve_member(engine, drifted)
    assert result["status"] == "approximate" and result["row"] is not None

    # The source feature is gone / moved: nothing near the anchor in that layer.
    gone = {**member, "anchor_lng": 0.0, "anchor_lat": 0.0}
    result = store.resolve_member(engine, gone)
    assert result["status"] == "missing" and result["row"] is None


def test_note_survives_and_missing_member_keeps_it(engine, selection):
    member, _ = store.add_member(engine, selection["id"], **_sample_feature(engine))
    updated = store.update_member_note(engine, selection["id"], member["id"], "verificar divisa")
    assert updated["note"] == "verificar divisa"
    assert store.list_members(engine, selection["id"])[0]["note"] == "verificar divisa"


def test_deleting_a_selection_removes_its_members(engine):
    created = store.create_selection(engine, f"pytest-{uuid.uuid4()}")
    store.add_member(engine, created["id"], **_sample_feature(engine))
    assert store.delete_selection(engine, created["id"]) is True
    with engine.connect() as conn:
        left = conn.execute(text("SELECT count(*) FROM saved_selection_members WHERE selection_id = :i"),
                            {"i": created["id"]}).scalar()
    assert left == 0


def test_backup_round_trip_merges_instead_of_duplicating(engine, selection):
    member, _ = store.add_member(engine, selection["id"], **_sample_feature(engine))
    store.update_member_note(engine, selection["id"], member["id"], "nota")
    backup = [s for s in store.export_backup(engine) if s["name"] == selection["name"]]
    assert len(backup) == 1 and backup[0]["members"][0]["note"] == "nota"

    result = store.import_backup(engine, backup)          # same name -> merge, no duplicate
    assert result["members_added"] == 0
    assert len(store.list_members(engine, selection["id"])) == 1

    store.delete_selection(engine, selection["id"])
    result = store.import_backup(engine, backup)          # gone -> recreated with notes
    assert result["selections"] == 1 and result["members_added"] == 1
    recreated = [s for s in store.list_selections(engine) if s["name"] == selection["name"]][0]
    assert store.list_members(engine, recreated["id"])[0]["note"] == "nota"
    store.delete_selection(engine, recreated["id"])
```

- [ ] **Step 4: Implement `src/saved_selections.py`:**

```python
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
    but attributes changed) or `missing` (nothing of that layer near the anchor).
    """
    point = "ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)"
    sql = text(
        f"SELECT id, layer_id, label, props, md5(props::text) = :fp AS exact, {geom_sql} AS geom "
        f"FROM search_index "
        f"WHERE layer_id = :layer AND ST_DWithin(geometry, {point}, :tol) "
        f"ORDER BY exact DESC, (props @> CAST(:hint AS jsonb)) DESC, "
        f"         ST_Distance(geometry, {point}) ASC, ST_Area(geometry) ASC "
        f"LIMIT 1")
    params = {"layer": member["layer_id"], "fp": member["fingerprint"],
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
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_saved_selections.py tests/test_saved_selections_db.py -v`
Expected: all PASS (DB tests skip with a clear reason if the database is down; the database is up in this environment, so they should run, not skip).

- [ ] **Step 6: Checkpoint** — `uv run pytest` fully green; confirm `docker exec conflitos_agrarios_db psql -U postgres -d conflitos_agrarios -c "\dt saved_selection*"` lists both tables and `saved_filters` still exists. Do not commit.

---

### Task 3: Selections API — CRUD and members

**Files:**
- Create: `src/selections_api.py`
- Modify: `src/search_api.py` (include router, ensure tables on startup)

**Interfaces:**
- Consumes: Task 2 functions; `src.export_api._locate_feature(payload, geometry_sql)` and `FeatureExportRequest` (fields `layer, lng, lat, zoom, tolerance_px, props, search_index_id, style`).
- Produces: `router` with
  - `GET /selections`, `POST /selections` (201; 409 duplicate), `PUT /selections/{id}`, `DELETE /selections/{id}` (204)
  - `GET /selections/{id}` → `{id, name, description, member_count, updated_at, members: [{id, layer_id, label, note, anchor: {lng, lat}, resolved}]}`
  - `POST /selections/{id}/members` (body = `FeatureExportRequest`) → `{member, created}`, 404 if feature not found or set missing, 409 at cap
  - `PUT /selections/{id}/members/{member_id}` (`{note}`), `DELETE …/{member_id}` (204)

- [ ] **Step 1: Implement `src/selections_api.py`:**

```python
"""
HTTP surface for saved selections: named sets of hand-picked map features.

Thin on purpose. SQL lives in `src.saved_selections`; geometry drawing and KML export are in
the same router further down (see the geometry and export endpoints).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src import saved_selections as store
from src.database import get_engine
from src.export_api import FeatureExportRequest, _locate_feature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/selections", tags=["selections"])
engine = get_engine()

#: Returned in `geom` by `_locate_feature`: what a member needs besides the label.
LOCATOR_SQL = ("json_build_object("
               "'lng', ST_X(ST_PointOnSurface(geometry)), "
               "'lat', ST_Y(ST_PointOnSurface(geometry)), "
               "'fp', md5(props::text))")


class SelectionCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None


class SelectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class NoteUpdate(BaseModel):
    note: str | None = None


def _require(selection_id: str) -> dict[str, Any]:
    try:
        selection = store.get_selection(engine, selection_id)
    except Exception:  # malformed uuid
        selection = None
    if selection is None:
        raise HTTPException(status_code=404, detail="Conjunto não encontrado.")
    return selection


def _public_member(member: dict[str, Any], status: str) -> dict[str, Any]:
    return {"id": member["id"], "layer_id": member["layer_id"], "label": member["label"],
            "note": member["note"],
            "anchor": {"lng": member["anchor_lng"], "lat": member["anchor_lat"]},
            "resolved": status}


def _resolved_members(selection_id: str) -> list[dict[str, Any]]:
    members = store.list_members(engine, selection_id)
    with engine.connect() as conn:
        return [_public_member(m, store.resolve_member(conn, m)["status"]) for m in members]


@router.get("")
def list_all():
    return store.list_selections(engine)


@router.post("", status_code=201)
def create(payload: SelectionCreate):
    try:
        return store.create_selection(engine, payload.name, payload.description)
    except store.DuplicateSelectionName as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{selection_id}")
def detail(selection_id: str):
    selection = _require(selection_id)
    return {**selection, "members": _resolved_members(selection_id)}


@router.put("/{selection_id}")
def update(selection_id: str, payload: SelectionUpdate):
    _require(selection_id)
    if payload.name is not None and not payload.name.strip():
        raise HTTPException(status_code=422, detail="O nome não pode ser vazio.")
    try:
        return store.update_selection(engine, selection_id, name=payload.name,
                                      description=payload.description)
    except store.DuplicateSelectionName as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{selection_id}", status_code=204)
def delete(selection_id: str):
    _require(selection_id)
    store.delete_selection(engine, selection_id)


@router.post("/{selection_id}/members")
def add_member(selection_id: str, payload: FeatureExportRequest):
    """Resolves the clicked feature and stores what the database says it is, not what the
    tile said: canonical label, fingerprint, anchor and string attributes."""
    _require(selection_id)
    row = _locate_feature(payload, LOCATOR_SQL)          # 404 when nothing is there
    locator = row["geom"]
    try:
        member, created = store.add_member(
            engine, selection_id, layer_id=row["layer_id"], label=row["label"],
            fingerprint=locator["fp"], lng=locator["lng"], lat=locator["lat"],
            hint=store.hint_from_props(row["props"]))
    except store.SelectionFull as exc:
        raise HTTPException(status_code=409, detail={"cap": store.MEMBER_CAP, "message": str(exc)}) from exc
    return {"member": _public_member(member, "exact"), "created": created}


@router.put("/{selection_id}/members/{member_id}")
def update_note(selection_id: str, member_id: str, payload: NoteUpdate):
    _require(selection_id)
    member = store.update_member_note(engine, selection_id, member_id, payload.note)
    if member is None:
        raise HTTPException(status_code=404, detail="Área não encontrada no conjunto.")
    return _public_member(member, "exact")


@router.delete("/{selection_id}/members/{member_id}", status_code=204)
def remove(selection_id: str, member_id: str):
    _require(selection_id)
    if not store.remove_member(engine, selection_id, member_id):
        raise HTTPException(status_code=404, detail="Área não encontrada no conjunto.")
```

- [ ] **Step 2: Wire it into `src/search_api.py`.** Add the import next to the others and include the router; extend the startup hook (the old `saved_filters` wiring is removed in Task 10):

```python
from src.saved_selections import ensure_saved_selections_tables
from src.selections_api import router as selections_router
```

```python
app.include_router(selections_router)
```

and inside `_ensure_schema` add a second guarded call:

```python
    try:
        ensure_saved_selections_tables(engine)
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Could not ensure the saved_selections tables: {exc}")
```

- [ ] **Step 3: Restart and exercise it**

```bash
docker compose restart search && sleep 14
J='Content-Type: application/json'
curl -s -w " %{http_code}\n" -X POST localhost:7055/selections -H "$J" -d '{"name":"plan smoke"}'
curl -s -w " %{http_code}\n" -X POST localhost:7055/selections -H "$J" -d '{"name":"  PLAN SMOKE "}'
```
Expected: first returns the new set with `"member_count":0` and `201`; second returns `{"detail":"Já existe um conjunto chamado 'PLAN SMOKE'."}` with `409`.

Pick a real CAR point (any known one, e.g. the Afogados da Ingazeira parcel `-37.642696 -7.842596`), then:

```bash
SID=$(curl -s localhost:7055/selections | python3 -c "import json,sys;print([s['id'] for s in json.load(sys.stdin) if s['name']=='plan smoke'][0])")
BODY='{"layer":"area_imovel_1","lng":-37.642696,"lat":-7.842596,"zoom":14,"tolerance_px":0,"props":{}}'
curl -s -X POST localhost:7055/selections/$SID/members -H "$J" -d "$BODY"; echo
curl -s -X POST localhost:7055/selections/$SID/members -H "$J" -d "$BODY"; echo
curl -s -w " %{http_code}\n" -X POST localhost:7055/selections/$SID/members -H "$J" -d '{"layer":"area_imovel_1","lng":0,"lat":0,"zoom":14,"tolerance_px":0,"props":{}}'
curl -s localhost:7055/selections/$SID | python3 -m json.tool | head -20
```
Expected: first call `"created": true`, second `"created": false` with the same member id, third `404`; detail shows one member with `"resolved": "exact"`.

- [ ] **Step 4: Clean up the smoke set**

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X DELETE localhost:7055/selections/$SID
```
Expected: `204`.

- [ ] **Step 5: Checkpoint** — `uv run pytest` green. Do not commit.

---

### Task 4: Geometry for drawing and KML export

**Files:**
- Modify: `src/selections_api.py`

**Interfaces:**
- Consumes: `store.resolve_member`, `GEOJSON_SQL`, `KML_SQL`; `kml_writer.KmlItem/LayerGroup/build_document/stream_archive/sanitize_filename`; `export_api.LayerStyle`.
- Produces:
  - `GET /selections/{id}/geometry?zoom=12` → `{"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {...}, "properties": {...props, "__member", "__layer", "__label", "__note", "__resolved"}}], "missing": [member ids]}`
  - `POST /selections/{id}/export/kml` body `{grouping: "set" | "feature", style: {layer_id: {name, fill, border}}}` → `.kml` or `.zip`; 404 when the set is empty or nothing resolves.

- [ ] **Step 1: Append to `src/selections_api.py`** (add the imports at the top with the others):

```python
import json
from datetime import date
from itertools import groupby
from typing import Literal

from fastapi import Query
from fastapi.responses import StreamingResponse

from src.export_api import LayerStyle
from src.kml_writer import KmlItem, LayerGroup, build_document, sanitize_filename, stream_archive
```

```python
class SelectionExport(BaseModel):
    grouping: Literal["set", "feature"] = "set"
    #: Layer colours and pt-BR names live only in the frontend registry.
    style: dict[str, LayerStyle] = Field(default_factory=dict)


def _resolve_all(selection_id: str, geom_sql: str, simplify: float = 0.0):
    """(member, result) pairs in the order added, using one connection."""
    members = store.list_members(engine, selection_id)
    with engine.connect() as conn:
        return [(m, store.resolve_member(conn, m, geom_sql, simplify)) for m in members]


@router.get("/{selection_id}/geometry")
def geometry(selection_id: str, zoom: float = Query(12, ge=0, le=24)):
    """Every resolved member with its full boundary, for the map's "Isolar" overlay.

    Simplified to about half a pixel at `zoom`. Layer colours are the client's job.
    """
    _require(selection_id)
    simplify = 360.0 / (512.0 * (2 ** zoom)) * 0.5
    features, missing = [], []
    for member, result in _resolve_all(selection_id, store.GEOJSON_SQL, simplify):
        row = result["row"]
        if row is None:
            missing.append(member["id"])
            continue
        features.append({
            "type": "Feature",
            "geometry": row["geom"],
            "properties": {**(row["props"] or {}), "__member": member["id"],
                           "__layer": member["layer_id"], "__label": member["label"],
                           "__note": member["note"], "__resolved": result["status"]},
        })
    return {"type": "FeatureCollection", "features": features, "missing": missing}


def _style_for(styles: dict[str, LayerStyle], layer_id: str) -> LayerStyle:
    return styles.get(layer_id) or LayerStyle()


def _kml_item(member: dict[str, Any], row, styles: dict[str, LayerStyle]) -> KmlItem:
    style = _style_for(styles, member["layer_id"])
    return KmlItem(geometry_kml=row["geom"] or "", properties=dict(row["props"] or {}),
                   title=row["label"], layer_id=member["layer_id"],
                   layer_name=style.name or member["layer_id"],
                   fill_color=style.fill, border_color=style.border, note=member["note"])


@router.post("/{selection_id}/export/kml")
def export_kml(selection_id: str, payload: SelectionExport):
    selection = _require(selection_id)
    pairs = _resolve_all(selection_id, store.KML_SQL)
    resolved = [(m, r["row"]) for m, r in pairs if r["row"] is not None]
    missing = [m for m, r in pairs if r["row"] is None]
    if not resolved:
        raise HTTPException(status_code=404, detail="Este conjunto não tem áreas para exportar.")

    slug = sanitize_filename(selection["name"])
    stamp = f"{date.today():%Y%m%d}"
    items = [_kml_item(m, row, payload.style) for m, row in resolved]

    if payload.grouping == "set":
        document = build_document(selection["name"], items)
        return StreamingResponse(
            iter([document.encode("utf-8")]),
            media_type="application/vnd.google-earth.kml+xml",
            headers={"Content-Disposition":
                     f'attachment; filename="conflitos_pe_{slug}_{stamp}.kml"'})

    items.sort(key=lambda i: i.layer_id or "")
    groups = []
    for layer_id, group_items in groupby(items, key=lambda i: i.layer_id):
        group_items = list(group_items)
        style = _style_for(payload.style, layer_id)
        groups.append(LayerGroup(layer_id=layer_id, layer_name=style.name or layer_id,
                                 count=len(group_items), items=group_items,
                                 fill_color=style.fill, border_color=style.border))

    lines = [f"Conjunto: {selection['name']}", f"Gerado em: {date.today().isoformat()}",
             f"Áreas exportadas: {len(items)}"]
    if missing:
        lines += ["", f"Áreas não encontradas ({len(missing)}), não exportadas:"]
        lines += [f"- {m['label']} ({m['layer_id']})" + (f" — {m['note']}" if m["note"] else "")
                  for m in missing]
    stream = stream_archive(groups, grouping="feature", readme_text="\n".join(lines))
    return StreamingResponse(
        stream, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="conflitos_pe_{slug}_{stamp}.zip"'})
```

- [ ] **Step 2: Restart and exercise**

```bash
docker compose restart search && sleep 14
J='Content-Type: application/json'
SID=$(curl -s -X POST localhost:7055/selections -H "$J" -d '{"name":"plan geo"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
echo empty-export; curl -s -w " %{http_code}\n" -X POST localhost:7055/selections/$SID/export/kml -H "$J" -d '{"grouping":"set"}'
# a CAR parcel crossing tile seams (large) and a Terra Indígena point
curl -s -o /dev/null -X POST localhost:7055/selections/$SID/members -H "$J" -d '{"layer":"area_imovel_1","lng":-37.642696,"lat":-7.842596,"zoom":14,"tolerance_px":0,"props":{}}'
MID=$(curl -s localhost:7055/selections/$SID | python3 -c "import json,sys;print(json.load(sys.stdin)['members'][0]['id'])")
curl -s -X PUT localhost:7055/selections/$SID/members/$MID -H "$J" -d '{"note":"<b>divisa</b> ]]> & teste"}' >/dev/null
echo geometry; curl -s "localhost:7055/selections/$SID/geometry?zoom=14" | python3 -c "
import json,sys
d=json.load(sys.stdin);f=d['features'][0]
xs=[];ys=[]
def w(c):
    (xs.append(c[0]),ys.append(c[1])) if isinstance(c[0],float) else [w(i) for i in c]
w(f['geometry']['coordinates'])
print(len(d['features']),d['missing'],f['properties']['__resolved'],round(min(xs),4),round(max(xs),4))"
echo kml-set; curl -s -X POST localhost:7055/selections/$SID/export/kml -H "$J" -d '{"grouping":"set","style":{"area_imovel_1":{"name":"CAR","fill":"#84cc16","border":"#4d7c0f"}}}' -o /tmp/set.kml -D - | grep -i "content-disp"; python3 -c "
import xml.etree.ElementTree as ET;ET.parse('/tmp/set.kml');t=open('/tmp/set.kml').read();print('well-formed; has Observação:', 'Observação' in t, '| raw <b> leaked:', '<b>divisa' in t)"
echo kml-zip; curl -s -X POST localhost:7055/selections/$SID/export/kml -H "$J" -d '{"grouping":"feature"}' -o /tmp/set.zip; unzip -l /tmp/set.zip | tail -4
```
Expected: empty set → `404`; geometry → `1 [] exact -37.6621 -37.6252` (the full parcel, not the clipped sliver); KML header shows `conflitos_pe_plan-geo_<date>.kml`, `well-formed; has Observação: True | raw <b> leaked: False`; zip lists `area_imovel_1/…_1.kml` and `LEIAME.txt`.

- [ ] **Step 3: Pin the "missing" behaviour** (Review Focus 2). Make the member unresolvable and re-check:

```bash
docker exec conflitos_agrarios_db psql -U postgres -d conflitos_agrarios -c "UPDATE saved_selection_members SET anchor_lng = 0, anchor_lat = 0 WHERE selection_id = '$SID'"
curl -s "localhost:7055/selections/$SID/geometry" | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d['features']),len(d['missing']))"
curl -s -w " %{http_code}\n" -X POST localhost:7055/selections/$SID/export/kml -H "$J" -d '{"grouping":"set"}'
curl -s localhost:7055/selections/$SID | python3 -c "import json,sys;m=json.load(sys.stdin)['members'][0];print(m['resolved'],m['note'])"
```
Expected: `0 1`; export `404` with "Este conjunto não tem áreas para exportar."; member shows `missing` and still has its note.

- [ ] **Step 4: Clean up** — `curl -s -o /dev/null -X DELETE localhost:7055/selections/$SID`. Checkpoint: `uv run pytest` green. Do not commit.

---

### Task 5: Backup endpoints and pipeline step

**Files:**
- Modify: `src/selections_api.py`, `src/run_all_pipelines.py`

**Interfaces:**
- Consumes: `store.export_backup`, `store.import_backup`, `ensure_saved_selections_tables`.
- Produces: `GET /selections/backup` → `[{name, description, members: [...]}]`; `POST /selections/backup` (list body) → `{selections, members_added, skipped}`; pipeline step `8b` (`--step saved_selections`).

- [ ] **Step 1: Add the endpoints to `src/selections_api.py` — they MUST be defined before the `/{selection_id}` routes** (otherwise `backup` is parsed as an id). Insert directly after `create`:

```python
@router.get("/backup")
def backup_export():
    return store.export_backup(engine)


@router.post("/backup")
def backup_import(records: list[dict[str, Any]]):
    return store.import_backup(engine, records)
```

- [ ] **Step 2: Replace the pipeline step in `src/run_all_pipelines.py`.** In the `choices=[…]` list change `"saved_filters"` to `"saved_selections"`, and replace the 8b block:

```python
    # Step 8b: Saved selections tables. User data, so this only creates them if missing; they
    # are the only tables in the database this pipeline cannot regenerate.
    if not args.step or args.step == "saved_selections":
        from src.saved_selections import ensure_saved_selections_tables
        results.append(run_pipeline_step("8b. Saved Selections Tables", ensure_saved_selections_tables))
```

- [ ] **Step 3: Verify**

```bash
docker compose restart search && sleep 14
J='Content-Type: application/json'
SID=$(curl -s -X POST localhost:7055/selections -H "$J" -d '{"name":"plan backup"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
curl -s -o /dev/null -X POST localhost:7055/selections/$SID/members -H "$J" -d '{"layer":"area_imovel_1","lng":-37.642696,"lat":-7.842596,"zoom":14,"tolerance_px":0,"props":{}}'
curl -s localhost:7055/selections/backup > /tmp/backup.json; python3 -c "import json;d=json.load(open('/tmp/backup.json'));print([ (s['name'],len(s['members'])) for s in d if s['name']=='plan backup'])"
curl -s -X DELETE localhost:7055/selections/$SID
curl -s -X POST localhost:7055/selections/backup -H "$J" -d @/tmp/backup.json
PYTHONPATH=. uv run python src/run_all_pipelines.py --step saved_selections 2>&1 | tail -4
```
Expected: `[('plan backup', 1)]`; import returns `{"selections":N,"members_added":M,"skipped":0}` with `N >= 1`; pipeline summary shows `8b. Saved Selections Tables | SUCCESS`. Then delete the restored `plan backup` set via the API.

- [ ] **Step 4: Checkpoint** — `uv run pytest` green. Do not commit.

---

### Task 6: `SelectionService` and the Filtros panel

**Files:**
- Create: `frontend/src/app/services/selection.service.ts`
- Create: `frontend/src/app/selections-panel/selections-panel.component.{ts,html,css}`
- Modify: `frontend/src/app/services/export.service.ts` (add `exportSelection`), `frontend/src/app/app.ts` (imports), `frontend/src/app/app.html` (replace the builder)

**Interfaces:**
- Consumes: `SEARCH_API_URL`, `ActiveFeatureRef` (`export.service.ts`), Task 3–5 endpoints.
- Produces (used by Tasks 7–9):
  - `SelectionService`: signals `panelOpen`, `selections`, `activeId`, `members`, `notice`, `changed`; methods `refresh()`, `open(id | null)`, `create(name)`, `rename(id, name)`, `remove(id)`, `add(ref)`, `removeMember(memberId)`, `setNote(memberId, note)`, `geometry(zoom)`, `say(text)`, `exportBackup()`, `importBackup(file)`.
  - Types `SelectionSummary`, `SelectionMember`, `SelectionGeometry`.
  - `ExportService.exportSelection(id, grouping, style, fallbackName): Observable<void>`.
  - Component selector `app-selections-panel`, input `layers`.

- [ ] **Step 1: Add `exportSelection` to `ExportService`** (keep `exportFilter` for now; Task 10 removes it). Insert after `exportFilter`:

```ts
  /** Exports the active selection: one KML for the set, or a ZIP with one KML per area. */
  exportSelection(id: string, grouping: 'set' | 'feature',
                  style: Record<string, LayerStyle>, fallbackName: string): Observable<void> {
    return this.http
      .post(`${SEARCH_API_URL}/selections/${id}/export/kml`, { grouping, style },
            { responseType: 'blob', observe: 'response' })
      .pipe(map(response => this.save(response, fallbackName)));
  }
```

- [ ] **Step 2: Create `selection.service.ts`:**

```ts
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { SEARCH_API_URL } from './search.service';
import { ActiveFeatureRef } from './export.service';

export type Resolved = 'exact' | 'approximate' | 'missing';

export interface SelectionSummary {
  id: string;
  name: string;
  description: string | null;
  member_count: number;
  updated_at: string;
}

export interface SelectionMember {
  id: string;
  layer_id: string;
  label: string;
  note: string | null;
  anchor: { lng: number; lat: number };
  resolved: Resolved;
}

export interface SelectionGeometry {
  type: 'FeatureCollection';
  features: { type: 'Feature'; geometry: any; properties: Record<string, any> }[];
  missing: string[];
}

const BASE = `${SEARCH_API_URL}/selections`;

/**
 * Shared state for saved selections. Three places need the active set (the Filtros panel, the
 * Sobreposições rows and the detail popup), so it lives in a root service.
 */
@Injectable({ providedIn: 'root' })
export class SelectionService {
  private http = inject(HttpClient);

  readonly panelOpen = signal(false);
  readonly selections = signal<SelectionSummary[]>([]);
  readonly activeId = signal<string | null>(null);
  readonly members = signal<SelectionMember[]>([]);
  readonly notice = signal('');
  /** Bumped whenever the active set's members change, so the map overlay can redraw. */
  readonly changed = signal(0);

  private noticeTimer?: ReturnType<typeof setTimeout>;

  say(text: string) {
    this.notice.set(text);
    clearTimeout(this.noticeTimer);
    this.noticeTimer = setTimeout(() => this.notice.set(''), 4000);
  }

  async refresh(): Promise<void> {
    try {
      this.selections.set(await firstValueFrom(this.http.get<SelectionSummary[]>(BASE)));
    } catch {
      this.selections.set([]);
      this.say('Não foi possível carregar os conjuntos. A API de busca está no ar?');
    }
  }

  /** Makes a set active (or none) and loads its members. */
  async open(id: string | null): Promise<void> {
    this.activeId.set(id);
    await this.loadMembers();
  }

  private async loadMembers(): Promise<void> {
    const id = this.activeId();
    if (!id) {
      this.members.set([]);
    } else {
      try {
        const detail = await firstValueFrom(
          this.http.get<SelectionSummary & { members: SelectionMember[] }>(`${BASE}/${id}`));
        this.members.set(detail.members);
      } catch {
        this.members.set([]);
        this.say('Não foi possível carregar o conjunto.');
      }
    }
    this.changed.update(n => n + 1);
  }

  async create(name: string): Promise<string | null> {
    try {
      const created = await firstValueFrom(this.http.post<SelectionSummary>(BASE, { name }));
      await this.refresh();
      await this.open(created.id);
      return null;
    } catch (err: any) {
      return err?.error?.detail ?? 'Não foi possível criar o conjunto.';
    }
  }

  async rename(id: string, name: string): Promise<string | null> {
    try {
      await firstValueFrom(this.http.put(`${BASE}/${id}`, { name }));
      await this.refresh();
      return null;
    } catch (err: any) {
      return err?.status === 409 ? err.error.detail : 'Não foi possível renomear.';
    }
  }

  async remove(id: string): Promise<void> {
    await firstValueFrom(this.http.delete(`${BASE}/${id}`));
    if (this.activeId() === id) await this.open(null);
    await this.refresh();
  }

  /** Adds the feature to the active set. A feature already there is not duplicated. */
  async add(ref: ActiveFeatureRef): Promise<void> {
    const id = this.activeId();
    if (!id) {
      this.panelOpen.set(true);
      this.say('Escolha ou crie um conjunto em Filtros.');
      return;
    }
    const body = {
      layer: ref.layerId, lng: ref.lng, lat: ref.lat, zoom: ref.zoom,
      tolerance_px: ref.tolerancePx ?? 6, props: ref.props ?? {},
      search_index_id: ref.searchIndexId ?? null,
    };
    try {
      const res = await firstValueFrom(
        this.http.post<{ member: SelectionMember; created: boolean }>(`${BASE}/${id}/members`, body));
      await this.loadMembers();
      await this.refresh();
      this.panelOpen.set(true);
      this.say(res.created ? `Adicionada: ${res.member.label}` : 'Já está no conjunto.');
    } catch (err: any) {
      this.say(err?.status === 404 ? 'Feição não encontrada nesta posição.'
             : err?.status === 409 ? 'O conjunto atingiu o limite de 500 áreas.'
             : 'Não foi possível adicionar a área.');
    }
  }

  async removeMember(memberId: string): Promise<void> {
    const id = this.activeId();
    if (!id) return;
    await firstValueFrom(this.http.delete(`${BASE}/${id}/members/${memberId}`));
    await this.loadMembers();
    await this.refresh();
  }

  async setNote(memberId: string, note: string): Promise<void> {
    const id = this.activeId();
    if (!id) return;
    await firstValueFrom(this.http.put(`${BASE}/${id}/members/${memberId}`, { note }));
    this.members.update(list => list.map(m => m.id === memberId ? { ...m, note: note || null } : m));
  }

  geometry(zoom: number): Promise<SelectionGeometry> {
    return firstValueFrom(
      this.http.get<SelectionGeometry>(`${BASE}/${this.activeId()}/geometry?zoom=${zoom}`));
  }

  async exportBackup(): Promise<void> {
    const data = await firstValueFrom(this.http.get<unknown[]>(`${BASE}/backup`));
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `conjuntos_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  async importBackup(file: File): Promise<void> {
    try {
      const parsed = JSON.parse(await file.text());
      if (!Array.isArray(parsed)) throw new Error('formato');
      const result = await firstValueFrom(
        this.http.post<{ selections: number; members_added: number; skipped: number }>(`${BASE}/backup`, parsed));
      await this.refresh();
      await this.loadMembers();
      this.say(`${result.selections} conjunto(s) novo(s), ${result.members_added} área(s) adicionada(s), ${result.skipped} ignorada(s).`);
    } catch {
      this.say('Arquivo inválido: esperado uma lista de conjuntos em JSON.');
    }
  }
}
```

- [ ] **Step 3: Create the panel.** Copy the old styles as the base, then add the new rules:

```bash
cp frontend/src/app/filter-builder/filter-builder.component.css frontend/src/app/selections-panel/selections-panel.component.css
```
(create the `selections-panel/` directory first). Append to the copied CSS:

```css
/* ---------- selections panel ---------- */
.legend-panel.left-panel.selections-panel {
  position: relative;
  top: auto;
  right: auto;
  left: auto;
  max-height: 62vh;
}

.selections-panel .legend-body {
  max-height: none;
  flex: 1 1 auto;
  min-height: 0;
  gap: 8px;
}

.set-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 7px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.15s ease;
}

.set-row:hover { background: #f1f5f9; border-color: #cbd5e1; }
.set-row.active { border-color: #0f172a; background: #f1f5f9; }

.set-row-text { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.set-row-name { font-size: 0.78rem; font-weight: 500; color: #1e293b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.set-row-meta { font-size: 0.65rem; color: #94a3b8; }

.member-row {
  border: 1px solid #e2e8f0;
  border-radius: 7px;
  background: #f8fafc;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.member-head { display: flex; align-items: center; gap: 6px; min-width: 0; }
.member-text { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.member-layer { font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.04em; color: #64748b; }
.member-label { font-size: 0.74rem; font-weight: 500; color: #1e293b; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.member-badge {
  font-size: 0.6rem;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 4px;
  background: #fef3c7;
  color: #92400e;
}
.member-badge.missing { background: #fee2e2; color: #991b1b; }

.member-note {
  width: 100%;
  box-sizing: border-box;
  font-family: inherit;
  font-size: 0.72rem;
  color: #1e293b;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 5px;
  padding: 4px 6px;
  resize: vertical;
  min-height: 44px;
  outline: none;
}
.member-note:focus { border-color: #94a3b8; }

.panel-notice {
  font-size: 0.72rem;
  color: #334155;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 6px 8px;
}

.builder-primary-btn.secondary { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; }
```

Create `selections-panel.component.ts`:

```ts
import { Component, Input, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SelectionService, SelectionMember } from '../services/selection.service';
import { ExportService, LayerStyle } from '../services/export.service';
import { SelectionIsolationService } from '../services/selection-isolation.service';

interface LayerMetaItem {
  id: string;
  name: string;
  fillColor: string;
  borderColor: string;
}

@Component({
  selector: 'app-selections-panel',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './selections-panel.component.html',
  styleUrl: './selections-panel.component.css',
})
export class SelectionsPanelComponent {
  readonly sel = inject(SelectionService);
  readonly isolation = inject(SelectionIsolationService);
  private exporter = inject(ExportService);

  /** The frontend layer registry: the only place layer colours and pt-BR names live. */
  @Input() layers: LayerMetaItem[] = [];

  newName = '';
  createError = '';
  renamingId: string | null = null;
  renameValue = '';
  renameError = '';
  grouping: 'set' | 'feature' = 'set';
  exporting = false;
  exportError = '';

  constructor() {
    void this.sel.refresh();
  }

  toggleOpen() { this.sel.panelOpen.update(v => !v); }

  layerName(id: string): string { return this.layers.find(l => l.id === id)?.name ?? id; }
  layerColor(id: string): string { return this.layers.find(l => l.id === id)?.fillColor ?? '#64748b'; }
  layerBorder(id: string): string { return this.layers.find(l => l.id === id)?.borderColor ?? '#475569'; }

  get activeName(): string {
    return this.sel.selections().find(s => s.id === this.sel.activeId())?.name ?? '';
  }

  /** Nothing resolvable to draw or export. */
  get usable(): number {
    return this.sel.members().filter(m => m.resolved !== 'missing').length;
  }

  async create() {
    const name = this.newName.trim();
    if (!name) return;
    this.createError = (await this.sel.create(name)) ?? '';
    if (!this.createError) this.newName = '';
  }

  async pick(id: string) {
    if (this.sel.activeId() === id) return;
    await this.sel.open(id);
  }

  startRename(id: string, current: string, event: Event) {
    event.stopPropagation();
    this.renamingId = id;
    this.renameValue = current;
    this.renameError = '';
  }

  async commitRename() {
    if (!this.renamingId) return;
    const name = this.renameValue.trim();
    if (!name) { this.renamingId = null; return; }
    this.renameError = (await this.sel.rename(this.renamingId, name)) ?? '';
    if (!this.renameError) this.renamingId = null;
  }

  async removeSet(id: string, event: Event) {
    event.stopPropagation();
    await this.sel.remove(id);
  }

  zoomTo(member: SelectionMember) {
    this.isolation.flyTo(member.anchor.lng, member.anchor.lat);
  }

  async saveNote(member: SelectionMember, value: string) {
    if ((member.note ?? '') === value.trim()) return;
    await this.sel.setNote(member.id, value.trim());
  }

  async toggleIsolation() {
    if (this.isolation.active()) this.isolation.exit();
    else await this.isolation.enter();
  }

  exportNow() {
    const id = this.sel.activeId();
    if (!id || !this.usable) return;
    this.exporting = true;
    this.exportError = '';
    const style: Record<string, LayerStyle> = {};
    for (const layer of this.layers) {
      style[layer.id] = { name: layer.name, fill: layer.fillColor, border: layer.borderColor };
    }
    const fallback = this.grouping === 'set' ? 'conjunto.kml' : 'conjunto.zip';
    this.exporter.exportSelection(id, this.grouping, style, fallback).subscribe({
      next: () => this.exporting = false,
      error: () => { this.exporting = false; this.exportError = 'Falha ao exportar.'; },
    });
  }

  async onImport(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (file) await this.sel.importBackup(file);
  }
}
```

Create `selections-panel.component.html`:

```html
@if (!sel.panelOpen()) {
  <button class="panel-toggle-badge left-toggle" (click)="toggleOpen()" title="Abrir conjuntos de áreas">
    <svg class="toggle-badge-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18l-7 8v6l-4 2v-8z" />
    </svg>
    <span class="toggle-badge-text">Filtros</span>
    @if (sel.activeId()) { <span class="toggle-badge-count">{{ sel.members().length }}</span> }
  </button>
} @else {
  <div class="legend-panel left-panel selections-panel">
    <div class="legend-header">
      <div class="legend-header-text">
        <h3>Filtros</h3>
        <p>Conjuntos de áreas selecionadas</p>
      </div>
      <button class="close-panel-btn" (click)="toggleOpen()" title="Ocultar painel">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="legend-body">
      @if (sel.notice()) { <div class="panel-notice">{{ sel.notice() }}</div> }

      <div class="builder-section-title">Conjuntos ({{ sel.selections().length }})</div>
      @for (item of sel.selections(); track item.id) {
        <div class="set-row" [class.active]="item.id === sel.activeId()" (click)="pick(item.id)">
          <div class="set-row-text">
            @if (renamingId === item.id) {
              <input class="builder-input" [(ngModel)]="renameValue" (click)="$event.stopPropagation()"
                     (keydown.enter)="commitRename()" (blur)="commitRename()" />
            } @else {
              <span class="set-row-name">{{ item.name }}</span>
              <span class="set-row-meta">{{ item.member_count }} área(s)</span>
            }
          </div>
          <button class="builder-icon-btn" (click)="startRename(item.id, item.name, $event)" title="Renomear">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4z" />
            </svg>
          </button>
          <button class="builder-icon-btn" (click)="removeSet(item.id, $event)" title="Excluir conjunto">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />
            </svg>
          </button>
        </div>
      }
      @if (renameError) { <div class="builder-error inline">{{ renameError }}</div> }

      <div class="builder-save">
        <input class="builder-input grow" [(ngModel)]="newName" (keydown.enter)="create()" placeholder="Nome do novo conjunto" />
        <button class="builder-primary-btn" [disabled]="!newName.trim()" (click)="create()">Criar</button>
      </div>
      @if (createError) { <div class="builder-error inline">{{ createError }}</div> }

      <div class="builder-block-actions">
        <button class="builder-text-btn" (click)="sel.exportBackup()">Exportar JSON</button>
        <button class="builder-text-btn" (click)="importInput.click()">Importar JSON</button>
        <input #importInput type="file" accept="application/json,.json" hidden (change)="onImport($event)" />
      </div>

      @if (sel.activeId()) {
        <div class="builder-section-title">{{ activeName }} · {{ sel.members().length }} área(s)</div>

        @if (!sel.members().length) {
          <div class="set-row-meta">Clique no mapa e use o botão de adicionar nas linhas de Sobreposições ou no popup.</div>
        }

        @for (member of sel.members(); track member.id) {
          <div class="member-row">
            <div class="member-head">
              <span class="color-indicator" [style.background-color]="layerColor(member.layer_id)"
                    [style.border-color]="layerBorder(member.layer_id)"></span>
              <div class="member-text">
                <span class="member-layer">{{ layerName(member.layer_id) }}</span>
                <span class="member-label">{{ member.label }}</span>
              </div>
              @if (member.resolved === 'approximate') { <span class="member-badge" title="Os atributos mudaram desde que a área foi adicionada">aproximada</span> }
              @if (member.resolved === 'missing') { <span class="member-badge missing" title="A feição não existe mais nesta posição">não encontrada</span> }
              <button class="builder-icon-btn" [disabled]="member.resolved === 'missing'" (click)="zoomTo(member)" title="Ir para a área">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3" /><path stroke-linecap="round" d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                </svg>
              </button>
              <button class="builder-icon-btn" (click)="sel.removeMember(member.id)" title="Remover do conjunto">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <textarea class="member-note" placeholder="Observação (opcional)"
                      [value]="member.note ?? ''" (blur)="saveNote(member, $any($event.target).value)"></textarea>
          </div>
        }

        <button class="builder-primary-btn full secondary" [disabled]="!usable && !isolation.active()"
                (click)="toggleIsolation()">
          {{ isolation.active() ? 'Sair do isolamento' : 'Isolar no mapa' }}
        </button>

        <div class="builder-section-title">Exportar KML</div>
        <label class="builder-radio">
          <input type="radio" value="set" [(ngModel)]="grouping" /> <span>Um KML para o conjunto</span>
        </label>
        <label class="builder-radio">
          <input type="radio" value="feature" [(ngModel)]="grouping" /> <span>Um KML por área (ZIP)</span>
        </label>
        <button class="builder-primary-btn full" [disabled]="exporting || !usable" (click)="exportNow()">
          {{ exporting ? 'Gerando…' : 'Baixar' }}
        </button>
        @if (exportError) { <div class="builder-error inline">{{ exportError }}</div> }
      }
    </div>
  </div>
}
```

- [ ] **Step 4: Stub the isolation service** so the panel compiles now (Task 8 fills it in). Create `frontend/src/app/services/selection-isolation.service.ts`:

```ts
import { Injectable, signal } from '@angular/core';

/** Filled in by Task 8. */
@Injectable({ providedIn: 'root' })
export class SelectionIsolationService {
  readonly active = signal(false);
  readonly count = signal(0);
  flyTo(_lng: number, _lat: number): void {}
  async enter(): Promise<void> {}
  exit(): void {}
}
```

- [ ] **Step 5: Swap the panel into the app.** In `app.html` replace `<app-filter-builder [layers]="layers"></app-filter-builder>` with `<app-selections-panel [layers]="layers"></app-selections-panel>`. In `app.ts` replace the `FilterBuilderComponent` import (`import { FilterBuilderComponent } from './filter-builder/filter-builder.component';`) with `import { SelectionsPanelComponent } from './selections-panel/selections-panel.component';` and replace `FilterBuilderComponent` with `SelectionsPanelComponent` in the `imports: [...]` array.

- [ ] **Step 6: Verify in the browser** (dev server hot-reloads; wait ~6 s). With headless Chrome at `http://localhost:4200/`, press **Filtros**, create a set named `Fazenda X`, create `fazenda x ` and confirm the duplicate message, rename the first, delete it. Concretely (adapt the CDP pattern used earlier in this session, `ng.getComponent(document.querySelector('app-selections-panel'))`): after `create()` the component's `sel.activeId()` is non-null and `sel.selections().length === 1`; a second `create()` with a different-case name sets `createError` to "Já existe um conjunto chamado …". Expected: both hold; no console errors.

- [ ] **Step 7: Checkpoint** — `ng serve` shows no compile errors in its terminal; `uv run pytest` green. Do not commit.

---

### Task 7: Add buttons (Sobreposições rows and the detail popup)

**Files:**
- Modify: `frontend/src/app/overlap-stack-panel/overlap-stack-panel.component.{ts,html}`, `frontend/src/app/app.html`, `frontend/src/app/app.ts`, `frontend/src/app/app.css`

**Interfaces:**
- Consumes: `SelectionService.add(ref)`, `App.buildFeatureRef(layerInfo, renderedLayerId, props, lngLat)`, `StackEntry` fields `baseLayerId, layerName, fillColor, borderColor, renderedLayerId, feature.properties, lngLat`.
- Produces: `OverlapStackPanelComponent.featureAddRequested: EventEmitter<StackEntry>`; popup button `data-action="add-to-selection"`; `App.onStackFeatureAdd(entry)`.

- [ ] **Step 1: Row button.** In `overlap-stack-panel.component.ts` add next to the other outputs:

```ts
  @Output() featureAddRequested = new EventEmitter<StackEntry>();
```

and a handler near `onSelect`:

```ts
  onAdd(entry: StackEntry, event: Event) {
    event.stopPropagation();
    this.featureAddRequested.emit(entry);
  }
```

In the `.html`, inside `<div class="stack-row-actions">` insert **before** the first `<button class="stack-icon-btn" [disabled]="isEntryHidden(entry)" …>`:

```html
              <button class="stack-icon-btn" (click)="onAdd(entry, $event)"
                      title="Adicionar ao conjunto ativo (Filtros)">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14M5 12h14" />
                </svg>
              </button>
```

- [ ] **Step 2: Wire it in `app.html`**: add `(featureAddRequested)="onStackFeatureAdd($event)"` to the `<app-overlap-stack-panel …>` element.

- [ ] **Step 3: `app.ts`.** Inject the service next to the others at the top of the class:

```ts
  readonly selection = inject(SelectionService);
```

with `import { SelectionService } from './services/selection.service';`. Add the handler near `onStackFeatureHidden`:

```ts
  onStackFeatureAdd(entry: StackEntry) {
    const ref = this.buildFeatureRef(
      { id: entry.baseLayerId, name: entry.layerName,
        fillColor: entry.fillColor, borderColor: entry.borderColor },
      entry.renderedLayerId, entry.feature.properties, entry.lngLat);
    void this.selection.add(ref);
  }
```

In `openCustomPopup`, add the button before the KML one. Replace `const enhancedHtml = …` input so both buttons are appended: define next to `kmlBtnHtml`

```ts
        const addBtnHtml = `
          <button type="button" class="popup-btn popup-btn-add" data-action="add-to-selection" title="Adicionar esta feição ao conjunto ativo (Filtros)">
            Adicionar ao conjunto
          </button>
        `;
```

and change the two uses of `${kmlBtnHtml}` in `enhancedHtml` to `${addBtnHtml}${kmlBtnHtml}`.

In the document click handler in `ngAfterViewInit` (the one with `export-single-kml`), add right after the `kmlBtn` block:

```ts
      const addBtn = (e.target as HTMLElement).closest('[data-action="add-to-selection"]');
      if (addBtn && this.activeFeatureRef) {
        e.preventDefault();
        e.stopPropagation();
        void this.selection.add(this.activeFeatureRef);
        return;
      }
```

- [ ] **Step 4: CSS.** Add to `app.css` after `.popup-btn:hover`:

```css
.popup-btn-add {
  width: 100%;
  cursor: pointer;
}
```

- [ ] **Step 5: Verify** (headless Chrome, same technique as the highlight fix). Create and activate a set through the panel's component (`ng.getComponent(document.querySelector('app-selections-panel')).sel.create('Teste')`), toggle `area_imovel_1` visible, jump to `[-37.642696, -7.842596]` zoom 14, `map.fire('click', …)` then click the row's first button. Expected: `sel.members().length === 1` with `label` equal to the CAR code, `sel.notice()` starts with "Adicionada:"; pressing it again leaves `members().length === 1` and the notice becomes "Já está no conjunto."; with no active set the notice is "Escolha ou crie um conjunto em Filtros." and the panel opens. Then `map.fire('contextmenu', …)` and click `[data-action="add-to-selection"]` in the popup: still one member (same feature).

- [ ] **Step 6: Checkpoint** — no compile errors, `uv run pytest` green. Do not commit.

---

### Task 8: Isolate on the map

**Files:**
- Modify (replace the stub): `frontend/src/app/services/selection-isolation.service.ts`
- Modify: `frontend/src/app/app.ts`, `frontend/src/app/app.html`, `frontend/src/app/app.css`

**Interfaces:**
- Consumes: `SelectionService` (`geometry`, `activeId`, `changed`, `say`), MapLibre `Map`, the registry (`id, visible, fillColor, borderColor`), the layer host from `App`.
- Produces: `SelectionIsolationService` with `attach(map, host)`, `enter()`, `exit()`, `flyTo(lng, lat)`, signals `active`, `count`, and `layerIds` (`['selection-members-fill', 'selection-members-line', 'selection-members-circle']`). `LayerHost = { layers: {id; visible; fillColor; borderColor}[]; setLayerVisible(id: string, visible: boolean): void }`.

- [ ] **Step 1: Replace `selection-isolation.service.ts`:**

```ts
import { Injectable, effect, inject, signal, untracked } from '@angular/core';
import type { Map as MapLibreMap, GeoJSONSource } from 'maplibre-gl';
import { SelectionService, SelectionGeometry } from './selection.service';

export interface LayerHost {
  layers: { id: string; visible: boolean; fillColor: string; borderColor: string }[];
  setLayerVisible(id: string, visible: boolean): void;
}

const SOURCE = 'selection-members-source';
const FILL = 'selection-members-fill';
const LINE = 'selection-members-line';
const CIRCLE = 'selection-members-circle';
/** Registered below this layer so the invariant satellite < data < highlight < labels holds. */
const ANCHOR = 'hover-feature-fill';

/**
 * "Isolar": hides every data layer and draws only the active set's full boundaries.
 *
 * Entering snapshots each layer's visibility; leaving restores exactly that snapshot, so
 * toggling layers while isolated can never leave the map in a different state afterwards.
 */
@Injectable({ providedIn: 'root' })
export class SelectionIsolationService {
  private selection = inject(SelectionService);

  private map?: MapLibreMap;
  private host?: LayerHost;
  private snapshot: { id: string; visible: boolean }[] = [];
  private busy = false;

  readonly active = signal(false);
  readonly count = signal(0);
  readonly layerIds = [FILL, LINE, CIRCLE];

  constructor() {
    // Switching or deleting the active set, or editing its members, while isolated.
    effect(() => {
      this.selection.changed();
      this.selection.activeId();
      untracked(() => { if (this.active()) void this.refresh(); });
    });
  }

  /** Registers the overlay once the highlight layers exist. */
  attach(map: MapLibreMap, host: LayerHost) {
    this.map = map;
    this.host = host;

    map.addSource(SOURCE, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    map.addLayer({
      id: FILL, type: 'fill', source: SOURCE, filter: ['==', '$type', 'Polygon'],
      paint: { 'fill-color': ['get', '__fill'], 'fill-opacity': 0.45 },
    }, ANCHOR);
    map.addLayer({
      id: LINE, type: 'line', source: SOURCE,
      filter: ['any', ['==', '$type', 'Polygon'], ['==', '$type', 'LineString']],
      paint: { 'line-color': ['get', '__border'], 'line-width': 2 },
    }, ANCHOR);
    map.addLayer({
      id: CIRCLE, type: 'circle', source: SOURCE, filter: ['==', '$type', 'Point'],
      paint: {
        'circle-radius': 7, 'circle-color': ['get', '__fill'],
        'circle-stroke-color': ['get', '__border'], 'circle-stroke-width': 2,
      },
    }, ANCHOR);
  }

  flyTo(lng: number, lat: number) {
    this.map?.flyTo({ center: [lng, lat], zoom: Math.max(this.map.getZoom(), 15), essential: true });
  }

  async enter(): Promise<void> {
    if (this.busy || this.active() || !this.map || !this.host) return;
    this.busy = true;
    try {
      const collection = await this.selection.geometry(this.map.getZoom());
      if (!collection.features.length) {
        this.selection.say('Nenhuma área encontrada neste conjunto para isolar.');
        return;
      }
      this.snapshot = this.host.layers.map(l => ({ id: l.id, visible: l.visible }));
      for (const layer of this.host.layers) {
        if (layer.visible) this.host.setLayerVisible(layer.id, false);
      }
      this.draw(collection);
      this.active.set(true);
      this.fit(collection);
    } catch {
      this.selection.say('Não foi possível carregar as áreas do conjunto.');
    } finally {
      this.busy = false;
    }
  }

  exit(): void {
    if (!this.active() || !this.host) return;
    for (const saved of this.snapshot) {
      const layer = this.host.layers.find(l => l.id === saved.id);
      if (layer && layer.visible !== saved.visible) this.host.setLayerVisible(saved.id, saved.visible);
    }
    this.snapshot = [];
    (this.map?.getSource(SOURCE) as GeoJSONSource | undefined)
      ?.setData({ type: 'FeatureCollection', features: [] });
    this.count.set(0);
    this.active.set(false);
  }

  /** Redraws after the set changed; leaves isolation when there is nothing left to show. */
  private async refresh(): Promise<void> {
    if (!this.selection.activeId()) { this.exit(); return; }
    try {
      const collection = await this.selection.geometry(this.map?.getZoom() ?? 12);
      if (!collection.features.length) { this.exit(); return; }
      this.draw(collection);
    } catch {
      this.exit();
    }
  }

  private draw(collection: SelectionGeometry) {
    for (const feature of collection.features) {
      const layer = this.host?.layers.find(l => l.id === feature.properties['__layer']);
      feature.properties['__fill'] = layer?.fillColor ?? '#64748b';
      feature.properties['__border'] = layer?.borderColor ?? '#475569';
    }
    (this.map?.getSource(SOURCE) as GeoJSONSource | undefined)?.setData(collection as any);
    this.count.set(collection.features.length);
  }

  private fit(collection: SelectionGeometry) {
    let [minX, minY, maxX, maxY] = [Infinity, Infinity, -Infinity, -Infinity];
    const walk = (c: any): void => {
      if (typeof c[0] === 'number') {
        minX = Math.min(minX, c[0]); maxX = Math.max(maxX, c[0]);
        minY = Math.min(minY, c[1]); maxY = Math.max(maxY, c[1]);
      } else {
        c.forEach(walk);
      }
    };
    collection.features.forEach(f => walk(f.geometry.coordinates));
    this.map?.fitBounds([[minX, minY], [maxX, maxY]], { padding: 80, maxZoom: 16, essential: true });
  }
}
```

- [ ] **Step 2: Attach it from `app.ts`.** Inject next to `selection`:

```ts
  readonly isolation = inject(SelectionIsolationService);
```

with `import { SelectionIsolationService } from './services/selection-isolation.service';`. Immediately after the existing line `this.visibility.attach(this.map, firstLabelId);` that follows the highlight layers (around line 671, the one marked "The highlight layers are now registered") add:

```ts
      this.isolation.attach(this.map, {
        layers: this.layers,
        setLayerVisible: (id, visible) => {
          const layer = this.layers.find(l => l.id === id);
          if (layer && layer.visible !== visible) this.toggleLayer(layer);
        },
      });
```

- [ ] **Step 3: Make the overlay clickable.** In `queryStackAt` (around `const activeLayers = …`), replace the early return and the query call so the overlay layers are queried while isolated, and its features are converted back into the shape the rest of the pipeline expects:

```ts
        const overlayLayers = this.isolation.active() ? this.isolation.layerIds : [];
        if (activeLayers.length === 0 && overlayLayers.length === 0) return null;

        const hits = this.map.queryRenderedFeatures(e.point, { layers: [...activeLayers, ...overlayLayers] });
        if (!hits || hits.length === 0) return null;
        const rendered = hits.map(f => this.fromSelectionOverlay(f));
```

(remove the old `if (activeLayers.length === 0) return null;`, the old `const rendered = this.map.queryRenderedFeatures(...)` line and the old `if (!rendered || rendered.length === 0) return null;`). Add the converter next to `toStackEntry`:

```ts
  /**
   * Overlay features carry the original properties plus `__layer`; rebuild the shape a tile
   * feature has so popups, the overlap stack and highlighting need no special case.
   */
  private fromSelectionOverlay(feature: any): any {
    if (!this.isolation.layerIds.includes(feature.layer.id)) return feature;
    const props = feature.properties ?? {};
    const baseId: string = props['__layer'];
    const renderedId = this.priorityOrder.find(id =>
      ['_fill', '_circle', '_line', '_symbol'].some(suffix => id === baseId + suffix)) ?? `${baseId}_fill`;
    const clean = Object.fromEntries(Object.entries(props).filter(([k]) => !k.startsWith('__')));
    return { layer: { id: renderedId }, properties: clean, geometry: feature.geometry };
  }
```

- [ ] **Step 4: Banner.** In `app.html`, inside the main `legend-panel` element immediately after `<div class="legend-header">…</div>` closes (before `<div class="legend-body">`), add:

```html
  @if (isolation.active()) {
    <div class="isolation-note">
      <span>Isolamento ativo — {{ isolation.count() }} área(s)</span>
      <button type="button" class="isolation-exit" (click)="isolation.exit()">Sair</button>
    </div>
  }
```

and to `app.css`:

```css
.isolation-note {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  padding: 6px 10px;
  font-size: 0.74rem;
  color: #334155;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 7px;
  flex-shrink: 0;
}

.isolation-exit {
  font-family: inherit;
  font-size: 0.72rem;
  font-weight: 600;
  color: #0f172a;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}
```

- [ ] **Step 5: Verify** (headless Chrome). Create a set, add the large CAR parcel at `[-37.642696, -7.842596]` and a Terra Indígenas feature, enable two other layers, record every `layer.visible`, then:
  1. `isolation.enter()` → `isolation.active()` true, every `layer.visible` false, source holds both features, the CAR feature's bounds are the full `-37.6621 … -37.6252` (not the clipped tile fragment).
  2. While isolated, toggle `sigef_privado_pe` on, then `isolation.exit()` → every layer's `visible` equals the recorded snapshot (including `sigef_privado_pe` back to its original value) and the overlay source is empty.
  3. Right-click a member while isolated (`map.fire('contextmenu', …)` at its anchor) → a popup opens.
  4. **Review Focus 4:** a set with zero members and a set whose only member is `missing`: `enter()` leaves every layer visible and `isolation.active()` false.
  5. **Review Focus 5:** enter, then `sel.remove(activeId)` (delete the set) → isolation exits on its own, layers restored; enter, then `sel.open(otherSetId)` → the overlay redraws with the other set's areas.
  Expected: all five hold.

- [ ] **Step 6: Checkpoint** — no compile errors, `uv run pytest` green. Do not commit.

---

### Task 9: Export and backup in the browser

The export and JSON backup UI shipped with the panel in Task 6; this task only verifies them end to end so neither is left untested.

**Files:** none (verification only; fix defects in the files from Task 6 if found).

- [ ] **Step 1: Export.** With a set holding the large CAR parcel (note: `<b>divisa</b> & teste`) and one other feature: call `ExportService.exportSelection` through the panel (`ng.getComponent(document.querySelector('app-selections-panel')).exportNow()` once with `grouping = 'set'`, once with `'feature'`) and intercept the blob (override `URL.createObjectURL` in the page to capture the blob and its type before the download link is clicked). Expected: `'set'` yields `application/vnd.google-earth.kml+xml` with a `Observação` block and no raw `<b>`; `'feature'` yields a ZIP with one KML per area and `LEIAME.txt`.

- [ ] **Step 2: Export disabled when unusable.** Make every member `missing` (SQL as in Task 4 step 3) and reload the set in the panel. Expected: the **Baixar** and **Isolar** buttons are disabled; no request is sent.

- [ ] **Step 3: Backup round trip.** `await sel.exportBackup()` (capture the blob), delete the set, then `await sel.importBackup(new File([blobText], 'b.json'))`. Expected: the set reappears with its members and notes; the notice reads "1 conjunto(s) novo(s), N área(s) adicionada(s), 0 ignorada(s)."; importing a non-array file shows "Arquivo inválido: esperado uma lista de conjuntos em JSON."

- [ ] **Step 4: Checkpoint** — clean up test sets via the API. Do not commit.

---

### Task 10: Remove the rule-based builder

Done last so the app keeps working while the replacement was built.

**Files:**
- Delete: `frontend/src/app/filter-builder/`, `frontend/src/app/services/filter.service.ts`, `src/filters_api.py`, `src/filter_compiler.py`, `src/filter_catalog.py`, `src/saved_filters.py`, `tests/test_filter_compiler.py`
- Modify: `src/search_api.py`, `src/export_api.py`, `frontend/src/app/services/export.service.ts`, `tests/conftest.py`

**Interfaces:**
- Consumes: nothing from earlier tasks beyond confirming they replaced the removed pieces.
- Produces: a tree with no references to the removed modules. The `saved_filters` database table is **not** dropped.

- [ ] **Step 1: Find every reference first**

Run: `grep -rn "filters_api\|filter_compiler\|filter_catalog\|saved_filters\|FilterService\|filter-builder\|FilterBuilder\|exportFilter\|compile_or_400\|resolve_definition" src tests frontend/src docker-compose.yml README.md AGENTS.md | grep -v "docs/"`
Expected: a list limited to the files named above plus doc mentions (docs are updated in Task 11).

- [ ] **Step 2: Delete the files**

```bash
git rm -r frontend/src/app/filter-builder frontend/src/app/services/filter.service.ts \
  src/filters_api.py src/filter_compiler.py src/filter_catalog.py src/saved_filters.py \
  tests/test_filter_compiler.py
```
(Some of these are untracked in git; use plain `rm -r` for those that `git rm` refuses.)

- [ ] **Step 3: Clean `src/search_api.py`** — remove `from src.filters_api import router as filters_router`, `from src.saved_filters import ensure_saved_filters_table`, `app.include_router(filters_router)`, and the `ensure_saved_filters_table(engine)` try/except block in `_ensure_schema`.

- [ ] **Step 4: Clean `src/export_api.py`** — remove the rule-based bulk export: the `from src.filters_api import compile_or_400, resolve_definition` import, `ExportRequest`, `_counts`, `_readme`, `_to_item`, `_groups`, the `export_kml` endpoint and the now-unused imports and constants (`groupby`, `stream_archive`, `LayerGroup`, `CAP_BY_LAYER`, `CAP_BY_FEATURE`, `SPLIT_AT`, `Literal`). **Keep** `LayerStyle`, `FeatureExportRequest`, `_style_for` only if still referenced, `_locate_feature`, `feature_geometry`, and `export_feature`, which the selections router and popup still use.

- [ ] **Step 5: Clean the frontend** — in `export.service.ts` remove `exportFilter` and the `import { FilterDefinition } from './filter.service';` line. In `tests/conftest.py` delete the file if nothing else uses `FAKE_CATALOG` (the compiler tests were its only consumer); otherwise keep only what is used.

- [ ] **Step 6: Verify**

```bash
uv run pytest
docker compose restart search && sleep 14
curl -s -o /dev/null -w "%{http_code} filters\n" localhost:7055/filters
curl -s -o /dev/null -w "%{http_code} bulk export\n" -X POST localhost:7055/export/kml -H 'Content-Type: application/json' -d '{}'
curl -s -o /dev/null -w "%{http_code} selections\n" localhost:7055/selections
curl -s -o /dev/null -w "%{http_code} feature geometry\n" -X POST localhost:7055/feature/geometry -H 'Content-Type: application/json' -d '{"layer":"area_imovel_1","lng":-37.642696,"lat":-7.842596,"zoom":14,"tolerance_px":0}'
docker exec conflitos_agrarios_db psql -U postgres -d conflitos_agrarios -Atc "select to_regclass('saved_filters')"
```
Expected: pytest green; `/filters` → `404`; `/export/kml` → `404`/`405`; `/selections` → `200`; `/feature/geometry` → `200`; the last command prints `saved_filters` (table untouched). The Angular dev server shows no compile errors, and the page loads with the Filtros panel from Task 6.

- [ ] **Step 7: Checkpoint** — `grep -rn "filters_api\|filter_compiler\|FilterService" src tests frontend/src` returns nothing. Do not commit.

---

### Task 11: Documentation

**Files:**
- Modify: `README.md`, `AGENTS.md`, `docs/CHANGELOG.md`, `docs/specs/2026-10-02-saved-selections.md`, `docs/specs/2026-10-01-feature-visibility-and-saved-filters.md`

- [ ] **Step 1: `README.md`** — replace the "Saved Filters & KML Export" section with:

```markdown
#### Saved Selections & KML Export
The **Filtros** panel (top left) keeps named **sets of areas you pick by hand**. Create a set, make it active, then add features from the **Sobreposições** panel (the **+** button on each row) or from a feature's detail popup (**Adicionar ao conjunto**). The same feature is never added twice. Each area can carry a note.

**Isolar no mapa** hides every data layer and draws only the set's areas with their full boundaries; leaving isolation restores your layer visibility exactly. **Baixar** exports the set as one KML (folder per layer) or as a ZIP with one KML per area; notes appear in the balloons. An area whose source feature no longer exists is shown as *não encontrada*, keeps its note and is skipped on export.

Areas are remembered by layer, attribute fingerprint and a point inside them, so they survive a search-index rebuild. The CAR sub-layers (`apps_1`, `reserva_legal_1`, `vegetacao_nativa_1`) can be added like any other layer but are excluded from the search bar.

> **Backup warning:** `saved_selections` and `saved_selection_members` are the only tables the pipelines cannot regenerate, and `docker compose down -v` destroys them. Use **Exportar JSON** / **Importar JSON** in the panel, or `docker exec conflitos_agrarios_db pg_dump -U postgres -t saved_selections -t saved_selection_members conflitos_agrarios > selections.sql` (`*.sql` is git-ignored). `uv run python -m src.saved_selections` recreates empty tables. The old `saved_filters` table is no longer used and can be dropped manually.
```

Also change the `docker compose down -v` comment to `# also destroys the saved selections: export them first`.

- [ ] **Step 2: `AGENTS.md`** — in the pipelines list, replace the line mentioning `filters_api.py, saved_filters.py, filter_compiler.py` with: `` `src/search_api.py` (port `7055`, Docker service `search`, **no auto-reload**: `docker compose restart search` after backend edits): search, saved selections (`selections_api.py`, `saved_selections.py`), KML export and feature geometry (`export_api.py`, `kml_writer.py`). `` Replace the "`saved_filters` is user data" bullet with: `**`saved_selections` / `saved_selection_members` are user data**: the only tables the pipelines cannot regenerate. Never drop them, and warn before `docker compose down -v`.` Keep the tests bullet, changing the pure-modules list to `kml_writer`, `saved_selections`.

- [ ] **Step 3: `docs/CHANGELOG.md`** — add above the newest entry:

```markdown
### October 2026: Saved Selections (Replaces the Rule-Based Filter Builder)
- **Why**: The rule-based builder (layer blocks, conditions, spatial crossings) did not match the intent, which was named sets of hand-picked areas. Specification: [`docs/specs/2026-10-02-saved-selections.md`](specs/2026-10-02-saved-selections.md).
- **Model**: `saved_selections` and `saved_selection_members` ([`src/saved_selections.py`](../src/saved_selections.py)). A member is a locator (layer, `md5(props::text)` fingerprint, `ST_PointOnSurface` anchor, string-attribute hint, note), not a `search_index.id`, because the index is rebuilt and its ids restart. Resolution is `exact`, `approximate` (attributes changed) or `missing` (kept, flagged, skipped on export). 500 areas per set.
- **API** ([`src/selections_api.py`](../src/selections_api.py)): CRUD, idempotent add-member (the server stores what the database says the feature is), `/geometry` (full simplified boundaries for drawing), `/export/kml` (one KML or a ZIP per area; notes become an *Observação* block), `/backup` import/export.
- **Frontend**: `SelectionService` (shared active set), the Filtros panel, a **+** button on each Sobreposições row and in the popup, and **Isolar no mapa** (`SelectionIsolationService`: layer snapshot and exact restore, overlay drawn with full boundaries and still clickable).
- **Removed**: the builder UI, `/filters`, the SQL compiler and catalog, `POST /export/kml`, `saved_filters.py` and their tests. The `saved_filters` table is left in place, unused.
- **Pipeline**: step `8b` (`--step saved_selections`) creates the tables if missing.
```

- [ ] **Step 4: Specs.** In `docs/specs/2026-10-02-saved-selections.md`: change §2.1's "`:tol` is `0` for polygons and `1e-6` degrees for points and lines" to "`:tol` is `1e-6` degrees (≈0.1 m) for every geometry type"; change §5.3 to say pressing add on a feature already in the set shows "Já está no conjunto" and does not toggle it off (removal is from the panel), and acceptance criterion 2 to "…Pressing it again leaves one member and shows 'Já está no conjunto'"; change §4.1 to say `_locate_feature` is reused unmodified, with the locator values returned through its `geometry_sql`. At the top of `docs/specs/2026-10-01-feature-visibility-and-saved-filters.md` add a line under the title: `> **Feature B (§5) was superseded by [`2026-10-02-saved-selections.md`](2026-10-02-saved-selections.md).** Feature A is unchanged.`

- [ ] **Step 5: Verify** — `grep -n "saved_filters\|Saved Filters" README.md AGENTS.md` shows only the "no longer used" mention; links in the new CHANGELOG entry resolve to existing files.

- [ ] **Step 6: Checkpoint** — `uv run pytest` green. Do not commit.

---

## Self-Review

**Spec coverage**

| Spec section | Task |
| :--- | :--- |
| §2 locator, exact/approximate/missing | 2 (resolve + tests), 4 (missing behaviour) |
| §3 data model, cap, ensure on startup/pipeline/`__main__` | 2, 3, 5 |
| §4 API (CRUD, members, geometry, export, backup) | 3, 4, 5 |
| §4.3 KML note / `LEIAME.txt` for missing | 1, 4 |
| §5.1–5.2 service and panel (sets, members, notes, hint when no set) | 6 |
| §5.3 add buttons (row, popup) | 7 |
| §5.4 JSON backup | 5, 6, 9 |
| §5.5 Isolar (snapshot, overlay, clickable, refresh) | 8 |
| §6 removal | 10 |
| §7 testing, §8 acceptance 1–11 | 1, 2 (unit/DB), 3–9 (verification steps map to criteria: 1→6, 2–3→7, 4→6/3, 5–6→8, 7→4/9, 8→2/4, 9→5/9, 10→2/3, 11→10) |
| §9 docs | 11 |

Gaps: none. Criterion 2's toggle behaviour is a documented deviation (see "Spec adjustments").

**Placeholder scan:** none; every code step carries the code. Task 9 and the verification steps describe checks rather than files, by design (no frontend test framework exists in the repo).

**Type consistency:** `resolve_member(...)` returns `{"status", "row"}` and is used that way in Tasks 3 and 4; `add_member` returns `(member, created)` in Tasks 2, 3 and the backup; `SelectionMember`/`SelectionGeometry` shapes in `selection.service.ts` match the API responses of Tasks 3 and 4 (`anchor: {lng, lat}`, `resolved`, `missing`); `LayerHost` and `layerIds` are defined in Task 8 and consumed by `app.ts` in the same task; the stub in Task 6 exposes exactly the members the panel calls (`active`, `count`, `flyTo`, `enter`, `exit`).

**Review Focus coverage:** 1 → Task 1; 2 → Tasks 2, 4; 3 → Tasks 2, 3, 7; 4 → Tasks 4, 8, 9; 5 → Task 8.
