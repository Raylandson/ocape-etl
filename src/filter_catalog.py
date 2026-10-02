"""
Builds the field catalog the filter builder and the compiler both need.

Uses `information_schema.columns` rather than `jsonb_object_keys(props)`. Both would yield the
same names, since `search_index.props` is `to_jsonb(t) - 'geometry'`, but information_schema
also carries `data_type` — which the UI needs to offer the right operators and the compiler
needs to pick the numeric, date or text accessor. It is also one query for every layer.
"""

from __future__ import annotations

import re
import time
from typing import Any

from sqlalchemy import text

from src.build_search_index import SEARCH_SOURCES
from src.filter_compiler import field_kind

#: The catalog only changes when the pipeline reruns, so a short TTL is plenty.
_CACHE_TTL_SECONDS = 300
_cache: dict[str, Any] = {"at": 0.0, "catalog": None, "fields": None}

_DDMMYYYY = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def _filterable_tables() -> set[str]:
    """Only layers present in the search index can be filtered, since every query reads it."""
    return {source["table"] for source in SEARCH_SOURCES}


def _load(engine) -> tuple[dict, dict]:
    tables = _filterable_tables()
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT table_name, column_name, data_type "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND column_name <> 'geometry' "
            "ORDER BY table_name, ordinal_position"
        )).fetchall()

        indexed = {r[0] for r in conn.execute(text(
            "SELECT DISTINCT layer_id FROM search_index")).fetchall()}

    catalog: dict[str, dict[str, str]] = {}
    for table, column, data_type in rows:
        if table in tables and table in indexed:
            catalog.setdefault(table, {})[column] = data_type

    # A text column holding dd/mm/yyyy should offer date operators, not text ones.
    fields: dict[str, list[dict[str, str]]] = {}
    with engine.connect() as conn:
        for layer, columns in catalog.items():
            sample = conn.execute(text(
                "SELECT props FROM search_index WHERE layer_id = :layer LIMIT 1"
            ), {"layer": layer}).scalar() or {}
            entries = []
            for name, data_type in columns.items():
                kind = field_kind(data_type)
                value = sample.get(name)
                if kind == "text" and isinstance(value, str) and _DDMMYYYY.match(value):
                    kind = "date"
                entries.append({"name": name, "data_type": data_type, "kind": kind})
            fields[layer] = entries

    return catalog, fields


def get_catalog(engine, force: bool = False) -> dict[str, dict[str, str]]:
    _refresh(engine, force)
    return _cache["catalog"]


def get_fields(engine, force: bool = False) -> dict[str, list[dict[str, str]]]:
    _refresh(engine, force)
    return _cache["fields"]


def _refresh(engine, force: bool) -> None:
    fresh = _cache["catalog"] is not None and (time.monotonic() - _cache["at"]) < _CACHE_TTL_SECONDS
    if fresh and not force:
        return
    catalog, fields = _load(engine)
    _cache.update({"at": time.monotonic(), "catalog": catalog, "fields": fields})
