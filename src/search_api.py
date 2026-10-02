"""
Unified Search API: Free-text and code search over every displayed map layer, backed by
the `search_index` table built by `src/build_search_index.py`.

Started by `docker compose up -d` (service `search`), or locally with:
    uv run uvicorn src.search_api:app --port 7055
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import logging

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from src.database import get_engine
from src.export_api import router as export_router
from src.filters_api import router as filters_router
from src.saved_filters import ensure_saved_filters_table

logger = logging.getLogger(__name__)

MIN_QUERY_LENGTH = 3
MAX_TOKENS = 6

app = FastAPI(title="Land Conflict Mapping — Search API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    # Without this the browser hides the header from a blob response and the downloaded
    # archive gets a random name.
    expose_headers=["Content-Disposition"],
)

engine = get_engine()

app.include_router(filters_router)
app.include_router(export_router)


@app.on_event("startup")
def _ensure_schema() -> None:
    """`docker compose up -d` alone must yield a working feature. A cold database must not
    stop the API booting, so this is advisory only."""
    try:
        ensure_saved_filters_table(engine)
    except Exception as exc:  # pragma: no cover - depends on container start order
        logger.warning(f"Could not ensure the saved_filters table: {exc}")


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@app.get("/search")
def search(
    q: str = Query(..., description="Code, name, case number, CPF/CNPJ or municipality"),
    layers: Optional[str] = Query(None, description="Comma-separated layer ids to restrict the search"),
    limit: int = Query(20, ge=1, le=100),
):
    q = q.strip()
    if len(re.sub(r"[\W_]", "", q)) < MIN_QUERY_LENGTH:
        return {"query": q, "results": []}

    tokens = [t for t in re.split(r"\s+", q) if t][:MAX_TOKENS]
    params = {"q": q, "limit": limit}

    # Every token must appear in the accent/case-folded text; alternatively the whole
    # query matches an identifier with punctuation stripped (CNJ, CPF, CAR, SIGEF codes).
    token_clauses = []
    for i, token in enumerate(tokens):
        params[f"t{i}"] = _escape_like(token)
        token_clauses.append(f"s.search_text LIKE '%' || lower(unaccent(:t{i})) || '%'")

    where = f"(({' AND '.join(token_clauses)}) OR (length(qn.qc) >= {MIN_QUERY_LENGTH} AND s.codes LIKE '%' || qn.qc || '%'))"

    layer_ids: List[str] = [l for l in (layers or "").split(",") if l]
    if layer_ids:
        where += " AND s.layer_id = ANY(:layer_ids)"
        params["layer_ids"] = layer_ids

    sql = f"""
        WITH qn AS (
            SELECT lower(unaccent(:q)) AS qt,
                   regexp_replace(lower(unaccent(:q)), '[^a-z0-9]', '', 'g') AS qc
        ),
        hits AS (
            SELECT s.*,
                CASE
                    WHEN length(qn.qc) >= {MIN_QUERY_LENGTH} AND (' ' || s.codes || ' ') LIKE '% ' || qn.qc || ' %' THEN 0
                    WHEN length(qn.qc) >= {MIN_QUERY_LENGTH} AND (' ' || s.codes) LIKE '% ' || qn.qc || '%' THEN 1
                    WHEN s.label_norm = qn.qt THEN 2
                    WHEN s.label_norm LIKE qn.qt || '%' THEN 3
                    WHEN s.label_norm LIKE '%' || qn.qt || '%' THEN 4
                    ELSE 5
                END AS match_rank,
                similarity(s.label_norm, qn.qt) AS score
            FROM search_index s, qn
            WHERE {where}
            ORDER BY match_rank, round(similarity(s.label_norm, qn.qt)::numeric, 1) DESC, s.layer_rank, s.id
            LIMIT :limit
        )
        SELECT
            id, layer_id, label, code, place, match_rank, score, props,
            ST_AsGeoJSON(geometry, 7) AS geometry,
            ST_AsGeoJSON(ST_PointOnSurface(geometry), 7) AS anchor,
            ST_XMin(geometry) AS xmin, ST_YMin(geometry) AS ymin,
            ST_XMax(geometry) AS xmax, ST_YMax(geometry) AS ymax
        FROM hits
        ORDER BY match_rank, round(score::numeric, 1) DESC, layer_rank, id
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    results = [
        {
            "id": r["id"],
            "layer_id": r["layer_id"],
            "label": r["label"],
            "code": r["code"],
            "place": r["place"],
            "match_rank": r["match_rank"],
            "props": r["props"],
            "geometry": json.loads(r["geometry"]),
            "anchor": json.loads(r["anchor"])["coordinates"],
            "bbox": [r["xmin"], r["ymin"], r["xmax"], r["ymax"]],
        }
        for r in rows
    ]
    return {"query": q, "results": results}
