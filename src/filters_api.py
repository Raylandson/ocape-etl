"""
Saved-filter CRUD, the field catalog and the match preview.

Mounted into `src/search_api.py`; see that module for how it is served.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, Mapping

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from src import saved_filters as store
from src.database import get_engine
from src.filter_catalog import get_catalog, get_fields
from src.filter_compiler import FilterError, compile_filter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/filters", tags=["filters"])
engine = get_engine()

#: A preview runs against 624k rows; an unconstrained one must not pin a connection forever.
PREVIEW_TIMEOUT = "20s"


class FilterPayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    definition: dict[str, Any]


class FilterPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    definition: dict[str, Any] | None = None


class PreviewRequest(BaseModel):
    definition: dict[str, Any] | None = None
    saved_filter_id: str | None = None


def resolve_definition(definition: Mapping[str, Any] | None,
                       saved_filter_id: str | None) -> dict[str, Any]:
    """Accepts either an inline definition or the id of a stored one."""
    if definition is not None:
        return dict(definition)
    if saved_filter_id:
        record = store.get_filter(engine, saved_filter_id)
        if not record:
            raise HTTPException(status_code=404, detail="Filtro não encontrado.")
        return record["definition"]
    raise HTTPException(status_code=400, detail="Informe 'definition' ou 'saved_filter_id'.")


def compile_or_400(definition: Mapping[str, Any], **kwargs):
    try:
        return compile_filter(definition, get_catalog(engine), **kwargs)
    except FilterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ------------------------------------------------------------------ catalog
# Declared before /{filter_id} so "catalog" is not swallowed as an id.

@router.get("/catalog")
def catalog():
    fields = get_fields(engine)
    return {"layers": [{"id": layer, "fields": entries} for layer, entries in sorted(fields.items())]}


@router.get("/catalog/{layer}/fields/{field}/values")
def field_values(layer: str, field: str, limit: int = Query(200, ge=1, le=1000)):
    """Distinct values for a dropdown. Reports `truncated` so the UI can fall back to free
    text: `municipio` on CAR has 184 distinct values, but `cod_imovel` has 433,069."""
    catalog_map = get_catalog(engine)
    if layer not in catalog_map:
        raise HTTPException(status_code=404, detail=f"Camada '{layer}' não é filtrável.")
    if field not in catalog_map[layer]:
        raise HTTPException(status_code=404, detail=f"Campo '{field}' não existe em '{layer}'.")

    with engine.connect() as conn:
        conn.execute(text(f"SET LOCAL statement_timeout = '{PREVIEW_TIMEOUT}'"))
        rows = conn.execute(text(
            "SELECT props ->> :field AS value, count(*) AS total "
            "FROM search_index WHERE layer_id = :layer AND props ->> :field IS NOT NULL "
            "GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT :limit"
        ), {"field": field, "layer": layer, "limit": limit + 1}).mappings().all()

    truncated = len(rows) > limit
    return {"values": [{"value": r["value"], "count": r["total"]} for r in rows[:limit]],
            "truncated": truncated}


# ------------------------------------------------------------------ preview

@router.post("/preview")
def preview(payload: PreviewRequest):
    definition = resolve_definition(payload.definition, payload.saved_filter_id)
    compiled = compile_or_400(definition, select="count_by_layer")

    with engine.connect() as conn:
        conn.execute(text(f"SET LOCAL statement_timeout = '{PREVIEW_TIMEOUT}'"))
        rows = conn.execute(text(compiled.sql), compiled.params).mappings().all()

    by_layer = {r["layer_id"]: r["total"] for r in rows}
    return {"total": sum(by_layer.values()), "by_layer": by_layer, "layers": list(compiled.layers)}


# ------------------------------------------------------------------ CRUD

@router.get("")
def list_all():
    return store.list_filters(engine)


@router.post("", status_code=201)
def create(payload: FilterPayload):
    compile_or_400(payload.definition)          # reject definitions that cannot run
    try:
        return store.create_filter(engine, payload.name, payload.definition, payload.description)
    except store.DuplicateFilterName as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/import")
def import_many(records: list[dict[str, Any]]):
    return store.import_filters(engine, records)


@router.get("/{filter_id}")
def get_one(filter_id: str):
    record = store.get_filter(engine, filter_id)
    if not record:
        raise HTTPException(status_code=404, detail="Filtro não encontrado.")
    return record


@router.put("/{filter_id}")
def update(filter_id: str, payload: FilterPatch):
    if payload.definition is not None:
        compile_or_400(payload.definition)
    try:
        record = store.update_filter(engine, filter_id, name=payload.name,
                                     definition=payload.definition,
                                     description=payload.description)
    except store.DuplicateFilterName as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not record:
        raise HTTPException(status_code=404, detail="Filtro não encontrado.")
    return record


@router.delete("/{filter_id}", status_code=204)
def delete(filter_id: str):
    if not store.delete_filter(engine, filter_id):
        raise HTTPException(status_code=404, detail="Filtro não encontrado.")
