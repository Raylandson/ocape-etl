"""
HTTP surface for saved selections: named sets of hand-picked map features.

Thin on purpose. SQL lives in `src.saved_selections`; geometry drawing and KML export are in
the same router further down (see the geometry and export endpoints).
"""

from __future__ import annotations

import logging
from datetime import date
from itertools import groupby
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src import saved_selections as store
from src.database import get_engine
from src.export_api import FeatureExportRequest, LayerStyle, _locate_feature
from src.kml_writer import KmlItem, LayerGroup, build_document, sanitize_filename, stream_archive

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


@router.get("/backup")
def backup_export():
    return store.export_backup(engine)


@router.post("/backup")
def backup_import(records: list[dict[str, Any]]):
    return store.import_backup(engine, records)


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
