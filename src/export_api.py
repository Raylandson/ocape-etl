"""
KML export: bulk (from a filter) and single feature (from a map click).

Everything streams. The `search` container mounts only `./src` read-only and has no writable
data directory, so writing a temp archive is not an option — and streaming is what keeps a
50,000-feature export from materialising in memory anyway.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from itertools import groupby
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.database import get_engine
from src.filters_api import compile_or_400, resolve_definition
from src.kml_writer import KmlItem, LayerGroup, build_document, sanitize_filename, stream_archive

logger = logging.getLogger(__name__)

router = APIRouter(tags=["export"])
engine = get_engine()

#: ~3 kB per placemark, so 50k is roughly 150 MB raw / 15 MB deflated.
CAP_BY_LAYER = 50_000
#: Each entry repeats the document envelope and costs a central-directory record.
CAP_BY_FEATURE = 2_000
#: Google Earth becomes unusable well before this many placemarks in one file.
SPLIT_AT = 25_000


class LayerStyle(BaseModel):
    name: str | None = None
    fill: str | None = None
    border: str | None = None


class ExportRequest(BaseModel):
    definition: dict[str, Any] | None = None
    saved_filter_id: str | None = None
    grouping: Literal["layer", "feature"] = "layer"
    #: Layer colours and pt-BR names live only in the frontend registry; mirroring 43 entries
    #: server-side would drift the first time a layer is recoloured.
    style: dict[str, LayerStyle] = Field(default_factory=dict)
    filename: str | None = None


class FeatureExportRequest(BaseModel):
    layer: str
    lng: float
    lat: float
    zoom: float = 12
    tolerance_px: float = 6
    props: dict[str, Any] = Field(default_factory=dict)
    search_index_id: int | None = None
    style: LayerStyle = Field(default_factory=LayerStyle)


def _style_for(styles: dict[str, LayerStyle], layer_id: str) -> LayerStyle:
    return styles.get(layer_id) or LayerStyle()


def _counts(definition: dict[str, Any]) -> dict[str, int]:
    compiled = compile_or_400(definition, select="count_by_layer")
    with engine.connect() as conn:
        conn.execute(text("SET LOCAL statement_timeout = '60s'"))
        rows = conn.execute(text(compiled.sql), compiled.params).mappings().all()
    return {r["layer_id"]: r["total"] for r in rows}


def _readme(definition: dict[str, Any], counts: dict[str, int], grouping: str) -> str:
    lines = [
        "Exportação KML — Plataforma de Mapeamento de Conflitos Agrários de Pernambuco",
        f"Gerado em: {datetime.now().isoformat(timespec='seconds')}",
        f"Agrupamento: {'um arquivo por camada' if grouping == 'layer' else 'um arquivo por feição'}",
        f"Total de feições: {sum(counts.values())}",
        "",
        "Feições por camada:",
    ]
    lines += [f"  {layer}: {total}" for layer, total in sorted(counts.items())]
    lines += ["", "Definição do filtro:", json.dumps(definition, ensure_ascii=False, indent=2)]
    return "\n".join(lines)


def _to_item(row, styles: dict[str, LayerStyle]) -> KmlItem:
    style = _style_for(styles, row["layer_id"])
    return KmlItem(
        geometry_kml=row["geom_kml"] or "",
        properties=dict(row["props"] or {}),
        title=row["label"],
        layer_id=row["layer_id"],
        layer_name=style.name or row["layer_id"],
        fill_color=style.fill,
        border_color=style.border,
    )


def _groups(definition: dict[str, Any], counts: dict[str, int],
            styles: dict[str, LayerStyle], limit: int):
    """Streams rows ordered by layer and hands `stream_archive` one group per layer."""
    compiled = compile_or_400(definition, select="features", limit=limit)
    connection = engine.connect().execution_options(stream_results=True, yield_per=1000)
    try:
        result = connection.execute(text(compiled.sql), compiled.params).mappings()
        for layer_id, rows in groupby(result, key=lambda r: r["layer_id"]):
            style = _style_for(styles, layer_id)
            yield LayerGroup(
                layer_id=layer_id,
                layer_name=style.name or layer_id,
                count=counts.get(layer_id, 0),
                items=(_to_item(r, styles) for r in rows),
                fill_color=style.fill,
                border_color=style.border,
            )
    finally:
        connection.close()


@router.post("/export/kml")
def export_kml(payload: ExportRequest):
    definition = resolve_definition(payload.definition, payload.saved_filter_id)
    counts = _counts(definition)
    total = sum(counts.values())

    cap = CAP_BY_LAYER if payload.grouping == "layer" else CAP_BY_FEATURE
    if total > cap:
        raise HTTPException(status_code=413, detail={
            "total": total, "cap": cap, "grouping": payload.grouping,
            "message": (f"{total:,} feições excedem o limite de {cap:,} para este agrupamento. "
                        "Use o agrupamento por camada ou refine o filtro.").replace(",", "."),
        })
    if total == 0:
        raise HTTPException(status_code=404, detail="Nenhuma feição corresponde ao filtro.")

    slug = sanitize_filename(payload.filename or "filtro")
    name = f"conflitos_pe_{slug}_{date.today():%Y%m%d}.zip"

    stream = stream_archive(
        _groups(definition, counts, payload.style, cap),
        grouping=payload.grouping,
        readme_text=_readme(definition, counts, payload.grouping),
        max_per_file=SPLIT_AT,
    )
    return StreamingResponse(stream, media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


def _locate_feature(payload: FeatureExportRequest, geometry_sql: str) -> Any:
    """Finds the one search_index row a clicked feature refers to, or raises 404.

    There is no MVT feature id and most tables have no primary key, so the feature is located
    by point-in-polygon: 0.25 ms through the GIST index, against 248 ms for a natural-key
    lookup that would also need a hand-curated key per layer.
    """
    point = "ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)"

    if payload.search_index_id is not None:
        # Search-bar selections already carry the exact row id, so skip the spatial lookup.
        sql = (f"SELECT id, layer_id, label, props, {geometry_sql} AS geom FROM search_index "
               f"WHERE id = :row_id AND layer_id = :layer")
        params: dict[str, Any] = {"row_id": payload.search_index_id, "layer": payload.layer}
    else:
        sql = params = None

    with engine.connect() as conn:
        row = None
        if sql:
            row = conn.execute(text(sql), params).mappings().first()
        if row is None:
            # Degrees of tolerance: 0 for polygons (still index-accelerated), a pixel-derived
            # box for points and lines.
            tolerance = 0.0 if payload.tolerance_px <= 0 else (
                360.0 / (512.0 * (2 ** payload.zoom)) * payload.tolerance_px)
            # A string-only hint: MVT rounds numbers and omits nulls, so numeric props cannot
            # be compared reliably. It only ranks, never filters, so a mismatch degrades to
            # "nearest, smallest" rather than returning nothing.
            hint = {k: v for k, v in (payload.props or {}).items() if isinstance(v, str)}
            row = conn.execute(text(
                f"SELECT id, layer_id, label, props, {geometry_sql} AS geom "
                f"FROM search_index "
                f"WHERE layer_id = :layer AND ST_DWithin(geometry, {point}, :tol) "
                f"ORDER BY (props @> CAST(:hint AS jsonb)) DESC, "
                f"         ST_Distance(geometry, {point}) ASC, "
                f"         ST_Area(geometry) ASC "
                f"LIMIT 1"
            ), {"layer": payload.layer, "lng": payload.lng, "lat": payload.lat,
                "tol": tolerance, "hint": json.dumps(hint)}).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="Feição não encontrada nesta posição.")
    return row


@router.post("/feature/geometry")
def feature_geometry(payload: FeatureExportRequest):
    """Full geometry of a clicked feature, for the map highlight.

    `queryRenderedFeatures` at a point only returns the fragment inside the tile under the
    cursor, so a parcel crossing tile seams was highlighted as a clipped sliver. This returns
    the whole boundary, simplified to about half a pixel at the caller's zoom.
    """
    tolerance = 360.0 / (512.0 * (2 ** payload.zoom)) * 0.5
    geometry = (f"ST_AsGeoJSON(ST_SimplifyPreserveTopology(geometry, {tolerance!r}), 6)::json")
    row = _locate_feature(payload, geometry)
    return {"geometry": row["geom"]}


@router.post("/export/kml/feature")
def export_feature(payload: FeatureExportRequest):
    """Exports one clicked feature with its exact PostGIS geometry."""
    geometry = ("ST_AsKML(CASE WHEN GeometryType(geometry) = 'GEOMETRYCOLLECTION' "
                "THEN ST_CollectionExtract(geometry) ELSE geometry END, 7)")
    row = _locate_feature(payload, geometry)

    style = payload.style
    item = KmlItem(geometry_kml=row["geom"] or "", properties=dict(row["props"] or {}),
                   title=row["label"], layer_id=row["layer_id"],
                   layer_name=style.name or row["layer_id"],
                   fill_color=style.fill, border_color=style.border)
    title = row["label"] or row["layer_id"]
    document = build_document(f"{style.name or row['layer_id']} - {title}", [item])
    filename = f"{sanitize_filename(title)}.kml"

    return StreamingResponse(
        iter([document.encode("utf-8")]),
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
