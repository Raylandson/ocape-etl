"""
Storage for named, globally shared filter definitions.

Unlike every other table in this project, `saved_filters` holds data a user created rather than
data an ETL step can regenerate, so it is created with `CREATE TABLE IF NOT EXISTS` instead of
the usual `DROP TABLE ... CREATE TABLE` full-rebuild idiom. That difference is deliberate.

It is also the only table `run_all_pipelines.py` cannot rebuild: `docker compose down -v`
destroys the volume and the filters with it. `GET /filters` plus `POST /filters/import` exist
as the backup path, and the README documents a `pg_dump -t saved_filters` one-liner.

The table carries no geometry column, so Martin's auto-discovery ignores it.

Run standalone to create or repair the table:
    uv run python -m src.saved_filters
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

TABLE = "saved_filters"

#: `name_norm` deliberately uses only lower()/btrim(), which are IMMUTABLE. `unaccent()` is
#: merely STABLE, so PostgreSQL rejects it in a generated column or an index expression.
DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL CHECK (btrim(name) <> ''),
    name_norm   text GENERATED ALWAYS AS (lower(btrim(name))) STORED,
    description text,
    definition  jsonb NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
"""

INDEXES = (
    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{TABLE}_name_norm ON {TABLE} (name_norm);",
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_updated_at ON {TABLE} (updated_at DESC);",
)

_COLUMNS = "id, name, description, definition, created_at, updated_at"


class DuplicateFilterName(ValueError):
    """Raised when a name collides case- and whitespace-insensitively with an existing one."""


def ensure_saved_filters_table(engine=None) -> None:
    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.execute(text(DDL))
        for statement in INDEXES:
            conn.execute(text(statement))
    logger.info(f"Table '{TABLE}' is present.")


def _row_to_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "description": row["description"],
        "definition": row["definition"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def list_filters(engine) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(text(
            f"SELECT {_COLUMNS} FROM {TABLE} ORDER BY updated_at DESC"
        )).mappings().all()
    return [_row_to_dict(r) for r in rows]


def get_filter(engine, filter_id: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        row = conn.execute(text(
            f"SELECT {_COLUMNS} FROM {TABLE} WHERE id = CAST(:id AS uuid)"
        ), {"id": filter_id}).mappings().first()
    return _row_to_dict(row) if row else None


def create_filter(engine, name: str, definition: Mapping[str, Any],
                  description: str | None = None) -> dict[str, Any]:
    try:
        with engine.begin() as conn:
            row = conn.execute(text(
                f"INSERT INTO {TABLE} (name, description, definition) "
                f"VALUES (:name, :description, CAST(:definition AS jsonb)) "
                f"RETURNING {_COLUMNS}"
            ), {"name": name, "description": description,
                "definition": json.dumps(definition)}).mappings().first()
    except IntegrityError as exc:
        raise DuplicateFilterName(f"Já existe um filtro chamado '{name}'.") from exc
    return _row_to_dict(row)


def update_filter(engine, filter_id: str, *, name: str | None = None,
                  definition: Mapping[str, Any] | None = None,
                  description: str | None = None) -> dict[str, Any] | None:
    assignments = ["updated_at = now()"]
    params: dict[str, Any] = {"id": filter_id}
    if name is not None:
        assignments.append("name = :name")
        params["name"] = name
    if description is not None:
        assignments.append("description = :description")
        params["description"] = description
    if definition is not None:
        assignments.append("definition = CAST(:definition AS jsonb)")
        params["definition"] = json.dumps(definition)

    try:
        with engine.begin() as conn:
            row = conn.execute(text(
                f"UPDATE {TABLE} SET {', '.join(assignments)} "
                f"WHERE id = CAST(:id AS uuid) RETURNING {_COLUMNS}"
            ), params).mappings().first()
    except IntegrityError as exc:
        raise DuplicateFilterName(f"Já existe um filtro chamado '{name}'.") from exc
    return _row_to_dict(row) if row else None


def delete_filter(engine, filter_id: str) -> bool:
    with engine.begin() as conn:
        result = conn.execute(text(
            f"DELETE FROM {TABLE} WHERE id = CAST(:id AS uuid)"
        ), {"id": filter_id})
    return result.rowcount > 0


def import_filters(engine, records: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Upserts by `name_norm`, so re-importing a backup updates rather than duplicating."""
    imported = skipped = 0
    with engine.begin() as conn:
        for record in records:
            name = (record or {}).get("name")
            definition = (record or {}).get("definition")
            if not name or definition is None:
                skipped += 1
                continue
            conn.execute(text(
                f"INSERT INTO {TABLE} (name, description, definition) "
                f"VALUES (:name, :description, CAST(:definition AS jsonb)) "
                f"ON CONFLICT (name_norm) DO UPDATE SET "
                f"  description = EXCLUDED.description, "
                f"  definition = EXCLUDED.definition, "
                f"  updated_at = now()"
            ), {"name": name, "description": record.get("description"),
                "definition": json.dumps(definition)})
            imported += 1
    return {"imported": imported, "skipped": skipped}


if __name__ == "__main__":
    ensure_saved_filters_table()
