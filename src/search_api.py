"""
Unified Search API: Free-text and code search over every displayed map layer, backed by
the `search_index` table built by `src/build_search_index.py`.

Started by `docker compose up -d` (service `search`), or locally with:
    uv run uvicorn src.search_api:app --port 7055
"""

import sys
import json
import re
import unicodedata
from pathlib import Path
from typing import List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import logging

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from src.build_search_index import NON_SEARCHABLE_LAYERS
from src.database import get_engine
from src.export_api import router as export_router
from src.saved_selections import ensure_saved_selections_tables
from src.selections_api import router as selections_router

logger = logging.getLogger(__name__)

MIN_QUERY_LENGTH = 3
MAX_TOKENS = 6


def _unaccent(text: str) -> str:
    """Strip accents/diacritics from a string for uniform text search."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


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

app.include_router(export_router)
app.include_router(selections_router)


@app.on_event("startup")
def _ensure_schema() -> None:
    """`docker compose up -d` alone must yield a working feature. A cold database must not
    stop the API booting, so this is advisory only."""
    try:
        ensure_saved_selections_tables(engine)
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Could not ensure the saved_selections tables: {exc}")


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
    elif NON_SEARCHABLE_LAYERS:
        # Indexed for filtering/export only; naming them in `layers` still works.
        where += " AND NOT (s.layer_id = ANY(:non_searchable))"
        params["non_searchable"] = NON_SEARCHABLE_LAYERS

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


@app.get("/ppcac/areas")
def get_ppcac_areas(
    situacao: Optional[str] = Query(None, description="Filter by ATIVO, ARQUIVADO, or ALL"),
    q: Optional[str] = Query(None, description="Search term for area, municipality, or movement"),
    municipio: Optional[str] = Query(None, description="Filter by municipality name"),
):
    """Returns the list of PPCAC conflict areas with procedural metadata, coordinates, and statistics."""
    with engine.connect() as conn:
        # Check if table exists
        has_table = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'ppcac_conflitos_pe'
            )
        """)).scalar()
        if not has_table:
            return {
                "total": 0,
                "stats": {
                    "ativos": 0, "arquivados": 0, "com_geometria_exata": 0,
                    "total_processos_judiciais": 0, "total_procedimentos_mppe": 0, "total_processos_sei": 0
                },
                "areas": []
            }

        # Calculate overall stats
        stats_row = conn.execute(text("""
            SELECT
                count(*) FILTER (WHERE situacao = 'ATIVO') AS ativos,
                count(*) FILTER (WHERE situacao = 'ARQUIVADO') AS arquivados,
                count(*) FILTER (WHERE tem_geometria_exata IS TRUE) AS com_geometria_exata,
                count(*) FILTER (WHERE tipo_geometria = 'POLYGON') AS com_poligono,
                count(*) FILTER (WHERE fonte_geometria LIKE 'SIGEF%') AS com_poligono_sigef,
                count(*) FILTER (WHERE cardinality(car_codigos) > 0) AS com_car,
                COALESCE(sum(cardinality(processos_judiciais)), 0) AS total_judiciais,
                COALESCE(sum(cardinality(processos_mppe)), 0) AS total_mppe,
                COALESCE(sum(cardinality(processos_sei)), 0) AS total_sei
            FROM public.ppcac_conflitos_pe;
        """)).mappings().first()

        stats = {
            "ativos": int(stats_row["ativos"] or 0),
            "arquivados": int(stats_row["arquivados"] or 0),
            "com_geometria_exata": int(stats_row["com_geometria_exata"] or 0),
            "com_poligono": int(stats_row["com_poligono"] or 0),
            "com_poligono_sigef": int(stats_row["com_poligono_sigef"] or 0),
            "com_car": int(stats_row["com_car"] or 0),
            "total_processos_judiciais": int(stats_row["total_judiciais"] or 0),
            "total_procedimentos_mppe": int(stats_row["total_mppe"] or 0),
            "total_processos_sei": int(stats_row["total_sei"] or 0),
        }

        # Build filter query
        where_clauses = ["1=1"]
        params = {}

        if situacao and situacao.upper() != "ALL":
            where_clauses.append("situacao = :situacao")
            params["situacao"] = situacao.upper()

        if q and q.strip():
            where_clauses.append("""
                (
                    lower(unaccent(nome_area)) LIKE :q
                    OR lower(unaccent(municipio)) LIKE :q
                    OR lower(unaccent(COALESCE(proprietario, ''))) LIKE :q
                    OR lower(unaccent(COALESCE(movimento_social, ''))) LIKE :q
                    OR array_to_string(processos_judiciais, ' ') LIKE :q_raw
                    OR array_to_string(processos_mppe, ' ') LIKE :q_raw
                    OR array_to_string(processos_sei, ' ') LIKE :q_raw
                    OR array_to_string(car_codigos, ' ') LIKE :q_raw
                    OR array_to_string(sigef_codigos, ' ') LIKE :q_raw
                    OR array_to_string(iterpe_nomes, ' ') LIKE :q_raw
                    OR array_to_string(incra_projetos, ' ') LIKE :q_raw
                )
            """)
            q_clean = q.strip()
            params["q"] = f"%{_unaccent(q_clean).lower()}%"
            params["q_raw"] = f"%{q_clean}%"

        if municipio and municipio.strip():
            where_clauses.append("lower(unaccent(municipio)) LIKE :mun")
            params["mun"] = f"%{_unaccent(municipio.strip()).lower()}%"

        sql = f"""
            SELECT
                id, nome_area, municipio, municipio_ibge, proprietario, movimento_social,
                processos_judiciais, processos_mppe, processos_sei,
                ano_referencia, situacao, observacoes,
                datajud_processos, despejo_zero_ids, sigef_codigos,
                car_codigos, iterpe_nomes, incra_projetos, total_car_imoveis,
                fonte_geometria, tipo_geometria, tem_geometria_exata,
                centroid_lat, centroid_lon, bbox,
                ST_AsGeoJSON(geometry, 7) AS geometry_json
            FROM public.ppcac_conflitos_pe
            WHERE {' AND '.join(where_clauses)}
            ORDER BY nome_area;
        """

        rows = conn.execute(text(sql), params).mappings().all()

        areas = [
            {
                "id": r["id"],
                "nome_area": r["nome_area"],
                "municipio": r["municipio"],
                "municipio_ibge": r["municipio_ibge"],
                "proprietario": r["proprietario"],
                "movimento_social": r["movimento_social"],
                "processos_judiciais": r["processos_judiciais"] or [],
                "processos_mppe": r["processos_mppe"] or [],
                "processos_sei": r["processos_sei"] or [],
                "ano_referencia": r["ano_referencia"],
                "situacao": r["situacao"],
                "observacoes": r["observacoes"],
                "datajud_processos": r["datajud_processos"] or [],
                "despejo_zero_ids": r["despejo_zero_ids"] or [],
                "sigef_codigos": r["sigef_codigos"] or [],
                "car_codigos": r["car_codigos"] or [],
                "iterpe_nomes": r["iterpe_nomes"] or [],
                "incra_projetos": r["incra_projetos"] or [],
                "total_car_imoveis": r["total_car_imoveis"] or 0,
                "fonte_geometria": r["fonte_geometria"],
                "tipo_geometria": r["tipo_geometria"],
                "tem_geometria_exata": r["tem_geometria_exata"],
                "centroid_lat": r["centroid_lat"],
                "centroid_lon": r["centroid_lon"],
                "bbox": r["bbox"],
                "geometry": json.loads(r["geometry_json"]) if r["geometry_json"] else None,
            }
            for r in rows
        ]

    return {
        "total": len(areas),
        "stats": stats,
        "areas": areas,
    }


@app.get("/ppcac/filter-keys")
def get_ppcac_filter_keys():
    """Returns compiled lists of feature identifiers (DataJud and Despejo Zero)
    for constructing MapLibre layer filter expressions."""
    with engine.connect() as conn:
        has_table = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'ppcac_conflitos_pe'
            )
        """)).scalar()
        if not has_table:
            return {"processos_conflitos_judiciais": [], "despejo_zero_pe": []}

        dj_rows = conn.execute(text("""
            SELECT DISTINCT unnest(datajud_processos) AS p 
            FROM public.ppcac_conflitos_pe
            WHERE datajud_processos IS NOT NULL;
        """)).fetchall()
        dj_keys = [r[0] for r in dj_rows if r[0]]

        dz_rows = conn.execute(text("""
            SELECT DISTINCT unnest(despejo_zero_ids) AS d 
            FROM public.ppcac_conflitos_pe
            WHERE despejo_zero_ids IS NOT NULL;
        """)).fetchall()
        dz_keys = [r[0] for r in dz_rows if r[0]]

    return {
        "processos_conflitos_judiciais": dj_keys,
        "despejo_zero_pe": dz_keys,
    }

