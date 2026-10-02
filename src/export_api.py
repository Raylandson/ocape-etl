"""
Single-feature endpoints shared by the map popup and saved selections: locate a clicked
feature in `search_index` (`_locate_feature`), return its full boundary for the highlight
(`/feature/geometry`) and export it as KML (`/export/kml/feature`). Set/ZIP exports live in
`selections_api.py`.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.database import get_engine
from src.kml_writer import KmlItem, build_document, sanitize_filename

logger = logging.getLogger(__name__)

router = APIRouter(tags=["export"])
engine = get_engine()


class LayerStyle(BaseModel):
    name: str | None = None
    fill: str | None = None
    border: str | None = None


class FeatureExportRequest(BaseModel):
    layer: str
    lng: float
    lat: float
    zoom: float = 12
    tolerance_px: float = 6
    props: dict[str, Any] = Field(default_factory=dict)
    search_index_id: int | None = None
    style: LayerStyle = Field(default_factory=LayerStyle)


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
