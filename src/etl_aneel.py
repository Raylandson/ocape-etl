"""
ANEEL / SIGEL & EPE Energy Infrastructure ETL.

Extracts the electric-sector geospatial layers that affect land tenure in
Pernambuco and loads them into PostGIS:

  * ANEEL SIGEL (ArcGIS REST, https://sigel.aneel.gov.br/arcgis/rest/services):
    DUP polygons (servidão administrativa / desapropriação), wind farms, wind
    turbines and interference regions, solar plants, parks, panels and
    substations, restricted-interest lines, thermal plants, hydro sites and
    reservoirs.
  * EPE WebMap (ArcGIS REST, https://gisepeprd2.epe.gov.br/arcgis/rest/services):
    transmission lines and substations of the National Interconnected System
    (in operation and planned). SIGEL only republishes these from an ONS KML
    without structured attributes, so the EPE copy is used instead.
  * ANEEL Dados Abertos (CKAN): SIGA generation registry CSV, kept as a
    non-spatial enrichment table joined by the CEG nucleus.

Every API response is cached under data/raw/aneel/ so the load can be replayed
with --offline. Features are requested inside the Pernambuco bounding box and
then kept only if they intersect the official PE boundary.

Usage:
    uv run python src/etl_aneel.py              # fetch + load everything
    uv run python src/etl_aneel.py --offline    # reload from data/raw/aneel/
    uv run python src/etl_aneel.py --only aneel_dup_pe epe_linhas_transmissao_pe
"""

import re
import sys
import json
import time
import logging
import argparse
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import shapely
import geopandas as gpd
from shapely.geometry import (
    shape, Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon, GeometryCollection
)
from sqlalchemy import text
from src.database import get_engine
from src.config import RAW_DATA_DIR
from src.overlaps import calculate_energy_overlaps

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SIGEL = "https://sigel.aneel.gov.br/arcgis/rest/services"
EPE = "https://gisepeprd2.epe.gov.br/arcgis/rest/services"
CKAN = "https://dadosabertos.aneel.gov.br/api/3/action"
SIGA_PACKAGE = "siga-sistema-de-informacoes-de-geracao-da-aneel"
SIGA_RESOURCE_NAME = "siga-empreendimentos-geracao.csv"

RAW_DIR = RAW_DATA_DIR / "aneel"
PE_BOUNDARY = BASE_DIR / "src" / "pe_boundary.geojson"
PE_BBOX = "-41.36,-9.49,-34.80,-7.15"

USER_AGENT = "ocape-etl/1.0 (land-conflict mapping; +https://sigel.aneel.gov.br)"
HTTP_TIMEOUT = 300
PAGE_SIZE = 1000

# Placeholder strings SIGEL stores instead of NULL
NULL_SENTINELS = {"", "<null>", "null", "-"}

# ArcGIS geometry-statistics columns that are recomputed in PostGIS (area_ha / comprimento_km)
DROP_COLUMN_PATTERN = re.compile(r"^(shape|shape_length|shape_area|shape__area|shape__length)$|\.st(area|length)\(\)$", re.I)


@dataclass(frozen=True)
class LayerSpec:
    key: str          # cache file name (data/raw/aneel/<key>.geojson)
    base: str         # ArcGIS REST root
    service: str      # e.g. "DadosAbertos/DUP/MapServer"
    layer_id: int
    table: str        # target PostGIS table (several specs may share one table)
    kind: str         # "polygon" | "line" | "point"
    extra: Dict[str, str] = field(default_factory=dict)  # constant columns added to every row
    page_size: int = PAGE_SIZE  # features per request (lower for layers with very heavy geometries)


LAYERS: List[LayerSpec] = [
    # --- Servidões administrativas e desapropriações ---
    LayerSpec("sigel_dup", SIGEL, "DadosAbertos/DUP/MapServer", 0, "aneel_dup_pe", "polygon"),

    # --- Eólicas (EOL) ---
    LayerSpec("sigel_eol_usinas", SIGEL, "PORTAL/Camadas_Downloads/MapServer", 0, "aneel_eol_usinas_pe", "point"),
    LayerSpec("sigel_eol_parques", SIGEL, "PORTAL/Camadas_Downloads/MapServer", 7, "aneel_eol_parques_pe", "polygon"),
    LayerSpec("sigel_eol_aerogeradores", SIGEL, "PORTAL/Camadas_Downloads/MapServer", 8, "aneel_eol_aerogeradores_pe", "point"),
    LayerSpec("sigel_eol_interferencia", SIGEL, "PORTAL/Camadas_Downloads/MapServer", 11, "aneel_eol_interferencia_pe", "polygon"),

    # --- Linhas de interesse restrito (conexão de parques à rede) ---
    LayerSpec("sigel_lt_interesse_restrito_eol", SIGEL, "PORTAL/Camadas_Downloads/MapServer", 5,
              "aneel_lt_interesse_restrito_pe", "line", {"fonte_geracao": "EOL"}),
    LayerSpec("sigel_lt_interesse_restrito_ufv", SIGEL, "PORTAL/UFV/MapServer", 1,
              "aneel_lt_interesse_restrito_pe", "line", {"fonte_geracao": "UFV"}),

    # --- Solares fotovoltaicas (UFV) ---
    LayerSpec("sigel_ufv_usinas", SIGEL, "PORTAL/Camadas_Downloads/MapServer", 21, "aneel_ufv_usinas_pe", "point"),
    LayerSpec("sigel_ufv_parques", SIGEL, "PORTAL/UFV/MapServer", 2, "aneel_ufv_parques_pe", "polygon"),
    LayerSpec("sigel_ufv_paineis", SIGEL, "PORTAL/UFV/MapServer", 3, "aneel_ufv_paineis_pe", "polygon"),
    LayerSpec("sigel_ufv_subestacoes", SIGEL, "PORTAL/UFV/MapServer", 4, "aneel_ufv_subestacoes_pe", "polygon"),

    # --- Termelétricas (UTE) ---
    LayerSpec("sigel_ute_usinas", SIGEL, "PORTAL/Camadas_Downloads/MapServer", 18, "aneel_ute_usinas_pe", "point"),

    # --- Hidrelétricas (UHE / PCH / CGH e eixos inventariados) ---
    LayerSpec("sigel_hidro_aproveitamentos", SIGEL, "PORTAL/Camadas_Downloads/MapServer", 1,
              "aneel_hidro_aproveitamentos_pe", "point"),
    # Reservoir outlines are extremely detailed (Xingó alone has ~374k vertices, ~15 MB of GeoJSON);
    # SIGEL returns HTTP 500 for pages of more than a couple of them.
    LayerSpec("sigel_hidro_reservatorios", SIGEL, "PORTAL/Camadas_Downloads/MapServer", 27,
              "aneel_hidro_reservatorios_pe", "polygon", page_size=1),

    # --- Rede básica de transmissão (EPE WebMap) ---
    LayerSpec("epe_lt_operacao", EPE, "WMS_Webmap_EPE_Data/MapServer", 23,
              "epe_linhas_transmissao_pe", "line", {"situacao": "Em operação"}),
    LayerSpec("epe_lt_planejada", EPE, "WMS_Webmap_EPE_Data/MapServer", 10,
              "epe_linhas_transmissao_pe", "line", {"situacao": "Planejada"}),
    LayerSpec("epe_se_operacao", EPE, "WMS_Webmap_EPE_Data/MapServer", 22,
              "epe_subestacoes_pe", "point", {"situacao": "Em operação"}),
    LayerSpec("epe_se_planejada", EPE, "WMS_Webmap_EPE_Data/MapServer", 9,
              "epe_subestacoes_pe", "point", {"situacao": "Planejada"}),
]

SIGA_TABLE = "aneel_siga_empreendimentos_pe"

# DUP records whose polygon is a copy of another DUP's polygon (verified against the project names:
# both works are outside Pernambuco). Keyed by ato_legal because SIGEL reassigns OBJECTIDs on reloads.
# The flag is only applied while the geometry is still shared, so it clears itself once ANEEL fixes it.
DUP_SOURCE_ERRORS = {
    "REA 4797/2014": "Geometria idêntica à da LT 230 kV SE Elevadora Santa Brígida VII – SE Garanhuns II "
                     "(REA 4888/2014); o empreendimento (LD 72,5 kV Complexo Industrial do Pecém – Cumbuco) "
                     "fica no Ceará.",
    "REA 5716/2016": "Geometria idêntica à da LT 138 kV SE Elevadora UFV São Pedro e Paulo I – SE Flores "
                     "(REA 5699/2016); o empreendimento (LD 69 kV Santa Rosa – Três de Maio) fica no Rio "
                     "Grande do Sul.",
}

# Metric CRS for widths: SIRGAS 2000 / UTM 24S west of -36° and UTM 25S east of it (by centroid)
UTM_SRID_SQL = "CASE WHEN ST_X(ST_Centroid({g})) < -36 THEN 31984 ELSE 31985 END"


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def http_get(url: str, params: Optional[Dict[str, Any]] = None, retries: int = 4) -> bytes:
    """GET with retries and exponential backoff (SIGEL occasionally drops connections).

    HTTP 500 is raised immediately: ArcGIS returns it when a page is too heavy to serialize,
    which fetch_layer() handles by shrinking the page instead of repeating the same request.
    """
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code == 500 or attempt == retries:
                raise
            wait = 2 ** attempt
            logger.warning(f"Request failed ({e}); retry {attempt}/{retries - 1} in {wait}s: {full[:160]}")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def http_json(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = json.loads(http_get(url, params))
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"ArcGIS error for {url}: {data['error']}")
    return data


def layer_url(spec: LayerSpec) -> str:
    return f"{spec.base}/{urllib.parse.quote(spec.service)}/{spec.layer_id}"


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def fetch_layer(spec: LayerSpec) -> Dict[str, Any]:
    """Downloads every feature of a layer intersecting the PE bounding box as GeoJSON (EPSG:4326)."""
    url = layer_url(spec)
    meta = http_json(url, {"f": "json"})
    oid_field = meta.get("objectIdField") or next(
        (f["name"] for f in meta.get("fields", []) if f.get("type") == "esriFieldTypeOID"), "OBJECTID"
    )
    page_size = min(int(meta.get("maxRecordCount") or PAGE_SIZE), spec.page_size)

    features: List[Dict[str, Any]] = []
    offset = 0
    single_failures = 0
    while True:
        params = {
            "where": "1=1",
            "geometry": PE_BBOX,
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "outSR": 4326,
            "orderByFields": oid_field,
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "f": "geojson",
        }
        try:
            page = http_json(f"{url}/query", params)
        except urllib.error.HTTPError as e:
            if e.code != 500:
                raise
            if page_size > 1:
                page_size = max(1, page_size // 2)
                logger.warning(f"  {spec.key}: HTTP 500 at offset {offset}; retrying with pages of {page_size}")
                continue
            single_failures += 1
            if single_failures > 3:
                raise
            time.sleep(2 ** single_failures)
            continue
        batch = page.get("features", [])
        features.extend(batch)
        exceeded = page.get("exceededTransferLimit") or page.get("properties", {}).get("exceededTransferLimit")
        if not batch or (len(batch) < page_size and not exceeded):
            break
        offset += len(batch)

    logger.info(f"  {spec.key}: {len(features)} features in PE bbox ({meta.get('name')})")
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source_url": url,
            "layer_name": meta.get("name"),
            "geometry_type": meta.get("geometryType"),
            "source_wkid": (meta.get("extent") or {}).get("spatialReference", {}).get("wkid"),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "bbox": PE_BBOX,
            "fields": [{"name": f["name"], "type": f.get("type"), "alias": f.get("alias")}
                       for f in meta.get("fields", [])],
        },
    }


def load_or_fetch(spec: LayerSpec, offline: bool) -> Dict[str, Any]:
    cache = RAW_DIR / f"{spec.key}.geojson"
    if offline:
        if not cache.exists():
            raise FileNotFoundError(f"--offline requested but cache is missing: {cache}")
        return json.loads(cache.read_text(encoding="utf-8"))
    fc = fetch_layer(spec)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(".geojson.tmp")
    tmp.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    tmp.replace(cache)
    return fc


# ---------------------------------------------------------------------------
# Transformation
# ---------------------------------------------------------------------------

def coerce_geometry(geom: Any, kind: str) -> Any:
    """Validates, flattens to 2D and coerces to MultiPolygon / MultiLineString / Point."""
    if geom is None or geom.is_empty:
        return None
    geom = shapely.force_2d(shapely.make_valid(geom))
    if kind == "point":
        if isinstance(geom, Point):
            return geom
        if isinstance(geom, MultiPoint) and len(geom.geoms) > 0:
            return geom.geoms[0]
        return None

    target, single, multi = {
        "polygon": (MultiPolygon, Polygon, MultiPolygon),
        "line": (MultiLineString, LineString, MultiLineString),
    }[kind]
    if isinstance(geom, multi):
        return geom
    if isinstance(geom, single):
        return target([geom])
    if isinstance(geom, GeometryCollection):
        parts = []
        for g in geom.geoms:
            if isinstance(g, single):
                parts.append(g)
            elif isinstance(g, multi):
                parts.extend(g.geoms)
        return target(parts) if parts else None
    return None


def normalize_ceg_nucleus(ceg: Any) -> Optional[str]:
    """Extracts the 6-digit CEG nucleus shared by SIGEL (EOLCVBA031519-2-01) and SIGA (UHE.PH.PE.001174-6.1)."""
    if not isinstance(ceg, str):
        return None
    m = re.match(r"^[A-Z]{7}(\d{6})", re.sub(r"[^A-Z0-9]", "", ceg.upper()))
    return m.group(1) if m else None


def to_snake(name: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^0-9a-zA-Z]+", "_", name)).strip("_").lower()


def build_frame(fc: Dict[str, Any], spec: LayerSpec, pe_geom: Any) -> gpd.GeoDataFrame:
    meta = fc.get("metadata", {})
    field_types = {f["name"]: f.get("type") for f in meta.get("fields", [])}

    rows, geoms = [], []
    for feat in fc.get("features", []):
        g = feat.get("geometry")
        geoms.append(coerce_geometry(shape(g), spec.kind) if g else None)
        rows.append(feat.get("properties") or {})

    df = pd.DataFrame(rows)
    df = df[[c for c in df.columns if not DROP_COLUMN_PATTERN.search(c)]]

    for col in df.columns:
        ftype = field_types.get(col)
        if ftype == "esriFieldTypeDate":
            df[col] = pd.to_datetime(pd.to_numeric(df[col], errors="coerce"), unit="ms", utc=True).dt.tz_localize(None)
        elif ftype == "esriFieldTypeString" or df[col].dtype == object:
            df[col] = df[col].map(lambda v: (None if v.strip().lower() in NULL_SENTINELS else v.strip())
                                  if isinstance(v, str) else v)

    renamed = {c: to_snake(c) for c in df.columns}
    df = df.rename(columns=renamed)
    if "objectid" in df.columns:
        df = df.rename(columns={"objectid": "source_objectid"})

    for k, v in spec.extra.items():
        df[k] = v
    df["fonte_orgao"] = "EPE / WebMap" if spec.base == EPE else "ANEEL / SIGEL"
    df["fonte_camada"] = f"{spec.service}/{spec.layer_id} — {meta.get('layer_name', '')}".strip(" —")
    df["fonte_url"] = meta.get("source_url")
    df["data_coleta"] = pd.to_datetime(meta.get("fetched_at")).tz_localize(None) if meta.get("fetched_at") else pd.NaT
    if "ceg" in df.columns:
        df["ceg_nucleo"] = df["ceg"].map(normalize_ceg_nucleus)

    gdf = gpd.GeoDataFrame(df, geometry=geoms, crs="EPSG:4326")
    gdf = gdf[gdf.geometry.notna()]
    gdf = gdf[gdf.geometry.intersects(pe_geom)]
    return gdf


def drop_exact_duplicates(gdf: gpd.GeoDataFrame, table: str) -> gpd.GeoDataFrame:
    """Removes records republished under a new OBJECTID with identical geometry and attributes.

    SIGEL's reservoir layer, for example, lists every PE reservoir twice: the original record and a
    2025 bulk reload that only differs in OBJECTID and DATA_ATUALIZACAO. The most recently updated
    copy is kept. Rows sharing a geometry but differing in any other attribute (e.g. two REAs over
    the same DUP polygon) are preserved.
    """
    ignored = {"geometry", "source_objectid", "data_atualizacao"}
    if "data_atualizacao" in gdf.columns:
        gdf = gdf.sort_values("data_atualizacao", ascending=False, na_position="last")
    attrs = [c for c in gdf.columns if c not in ignored]
    key = pd.Series([repr(row) for row in gdf[attrs].itertuples(index=False, name=None)], index=gdf.index)
    dup = (key + "|" + gdf.geometry.to_wkb(hex=True)).duplicated()
    if dup.any():
        logger.info(f"  {table}: dropped {int(dup.sum())} duplicate record(s) (same geometry and attributes).")
    return gdf[~dup].sort_index()


def load_pe_boundary() -> Any:
    pe = gpd.read_file(PE_BOUNDARY).to_crs("EPSG:4326")
    geom = shapely.make_valid(pe.geometry.union_all())
    shapely.prepare(geom)
    return geom


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def finalize_table(engine, table: str, kind: str) -> int:
    """Adds PK, metric columns, GIST/attribute indexes and municipality attribution."""
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;"))
        if kind == "polygon":
            conn.execute(text(f"""
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS area_ha NUMERIC;
                UPDATE {table} SET area_ha = ROUND((ST_Area(geometry::geography) / 10000.0)::numeric, 4);
            """))
        elif kind == "line":
            conn.execute(text(f"""
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS comprimento_km NUMERIC;
                UPDATE {table} SET comprimento_km = ROUND((ST_Length(geometry::geography) / 1000.0)::numeric, 3);
            """))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_geometry ON {table} USING GIST (geometry);"))

        cols = {r[0] for r in conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:t"
        ), {"t": table})}
        if "ceg_nucleo" in cols:
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_ceg_nucleo ON {table} (ceg_nucleo);"))

        # Municipality attribution from IBGE 2022 census tracts (optional dependency)
        has_setores = conn.execute(text("SELECT to_regclass('public.pe_setores_cd2022') IS NOT NULL")).scalar()
        if has_setores:
            conn.execute(text(f"""
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS municipios_ibge INTEGER[];
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS municipios TEXT;
                UPDATE {table} t SET municipios_ibge = m.ibge, municipios = m.nomes
                FROM (
                    SELECT a.id,
                           array_agg(DISTINCT s.cd_mun::int ORDER BY s.cd_mun::int) AS ibge,
                           string_agg(DISTINCT s.nm_mun, ', ' ORDER BY s.nm_mun) AS nomes
                    FROM {table} a
                    JOIN pe_setores_cd2022 s ON ST_Intersects(a.geometry, s.geometry)
                    GROUP BY a.id
                ) m
                WHERE m.id = t.id;
            """))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table}_municipios ON {table} USING GIN (municipios_ibge);"))
        else:
            logger.warning(f"  pe_setores_cd2022 not found; skipping municipality attribution for {table}.")

        return conn.execute(text(f"SELECT COUNT(*) FROM {table};")).scalar()


def enrich_dup(engine) -> None:
    """Adds shape and data-quality columns to aneel_dup_pe.

    * largura_m: diameter of the maximum inscribed circle (the servitude strip width for corridors).
    * forma: 'faixa' for line servitudes (LT, LD, interesse restrito), 'area' for substations and APPs.
      Rows without objeto_text fall back to elongation (area / largura² >= 12).
    * extensao_km: corridor length (area / largura) for 'faixa' rows.
    * grupo_geometria / geometria_compartilhada / atos_mesma_geometria: DUPs sharing an identical polygon
      (the same strip declared by more than one REA, or a copied geometry).
    * erro_origem: curated source errors from DUP_SOURCE_ERRORS, applied only while the polygon is shared.
    """
    utm = UTM_SRID_SQL.format(g="geometry")
    with engine.begin() as conn:
        conn.execute(text(f"""
            ALTER TABLE aneel_dup_pe
                ADD COLUMN IF NOT EXISTS largura_m NUMERIC,
                ADD COLUMN IF NOT EXISTS forma TEXT,
                ADD COLUMN IF NOT EXISTS extensao_km NUMERIC,
                ADD COLUMN IF NOT EXISTS grupo_geometria INTEGER,
                ADD COLUMN IF NOT EXISTS geometria_compartilhada BOOLEAN,
                ADD COLUMN IF NOT EXISTS atos_mesma_geometria TEXT,
                ADD COLUMN IF NOT EXISTS erro_origem TEXT;

            UPDATE aneel_dup_pe SET largura_m = ROUND(
                ((ST_MaximumInscribedCircle(ST_Transform(geometry, {utm}))).radius * 2)::numeric, 1);

            UPDATE aneel_dup_pe SET forma = CASE
                WHEN objeto_text LIKE 'Linhas%' THEN 'faixa'
                WHEN objeto_text IS NULL AND largura_m > 0 AND area_ha * 10000 / (largura_m ^ 2) >= 12 THEN 'faixa'
                ELSE 'area' END;

            UPDATE aneel_dup_pe SET extensao_km = CASE
                WHEN forma = 'faixa' AND largura_m > 0 THEN ROUND((area_ha * 10000 / largura_m / 1000)::numeric, 2)
                END;

            UPDATE aneel_dup_pe d SET
                grupo_geometria = g.grupo,
                geometria_compartilhada = g.n > 1,
                atos_mesma_geometria = CASE WHEN g.n > 1 THEN g.atos END
            FROM (
                SELECT md5(ST_AsBinary(geometry)) AS h, MIN(id) AS grupo, COUNT(*) AS n,
                       string_agg(ato_legal, ' | ' ORDER BY ano_dup, ato_legal) AS atos
                FROM aneel_dup_pe GROUP BY 1
            ) g
            WHERE md5(ST_AsBinary(d.geometry)) = g.h;

            UPDATE aneel_dup_pe SET erro_origem = NULL;
            CREATE INDEX IF NOT EXISTS idx_aneel_dup_pe_grupo ON aneel_dup_pe (grupo_geometria);
        """))
        for ato, reason in DUP_SOURCE_ERRORS.items():
            conn.execute(text(
                "UPDATE aneel_dup_pe SET erro_origem = :reason WHERE ato_legal = :ato AND geometria_compartilhada"
            ), {"ato": ato, "reason": reason})

        stats = conn.execute(text("""
            SELECT COUNT(*) FILTER (WHERE forma = 'faixa'), COUNT(*) FILTER (WHERE forma = 'area'),
                   COUNT(*) FILTER (WHERE geometria_compartilhada), COUNT(*) FILTER (WHERE erro_origem IS NOT NULL)
            FROM aneel_dup_pe
        """)).one()
    logger.info(f"  aneel_dup_pe: {stats[0]} faixas, {stats[1]} áreas, {stats[2]} com geometria compartilhada, "
                f"{stats[3]} marcadas com erro de origem.")


def ingest_layers(offline: bool = False, only: Optional[List[str]] = None) -> Dict[str, int]:
    engine = get_engine()
    pe_geom = load_pe_boundary()

    tables: Dict[str, List[LayerSpec]] = {}
    for spec in LAYERS:
        if only and spec.table not in only:
            continue
        tables.setdefault(spec.table, []).append(spec)

    counts: Dict[str, int] = {}
    for table, specs in tables.items():
        logger.info(f"Building '{table}' from {len(specs)} source layer(s)...")
        frames = [build_frame(load_or_fetch(s, offline), s, pe_geom) for s in specs]
        frames = [f for f in frames if not f.empty]
        if not frames:
            logger.warning(f"  No features intersect Pernambuco for '{table}'; table not written.")
            continue
        gdf = drop_exact_duplicates(
            gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs="EPSG:4326"), table
        )
        gdf.to_postgis(table, engine, if_exists="replace", index=False)
        counts[table] = finalize_table(engine, table, specs[0].kind)
        if table == "aneel_dup_pe":
            enrich_dup(engine)
        logger.info(f"  Table '{table}' ready with {counts[table]} rows.")
    return counts


# ---------------------------------------------------------------------------
# SIGA (tabular enrichment)
# ---------------------------------------------------------------------------

SIGA_NUMERIC = ["MdaPotenciaOutorgadaKw", "MdaPotenciaFiscalizadaKw", "MdaGarantiaFisicaKw",
                "NumCoordNEmpreendimento", "NumCoordEEmpreendimento"]
SIGA_DATES = ["DatGeracaoConjuntoDados", "DatEntradaOperacao", "DatInicioVigencia", "DatFimVigencia"]


def siga_csv_url() -> str:
    pkg = http_json(f"{CKAN}/package_show", {"id": SIGA_PACKAGE})["result"]
    for res in pkg["resources"]:
        if res.get("name") == SIGA_RESOURCE_NAME:
            return res["url"]
    raise RuntimeError(f"Resource '{SIGA_RESOURCE_NAME}' not found in CKAN package '{SIGA_PACKAGE}'")


def ingest_siga(offline: bool = False) -> int:
    """Loads SIGA generation units located (fully or partly) in PE as a non-spatial table."""
    cache = RAW_DIR / SIGA_RESOURCE_NAME
    if not offline:
        url = siga_csv_url()
        logger.info(f"Downloading SIGA registry: {url}")
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".csv.tmp")
        tmp.write_bytes(http_get(url))
        tmp.replace(cache)
    elif not cache.exists():
        raise FileNotFoundError(f"--offline requested but cache is missing: {cache}")

    df = pd.read_csv(cache, sep=";", dtype=str, encoding="utf-8", keep_default_na=False)
    df = df.apply(lambda s: s.str.strip()).replace({"": None})
    in_pe = (df["SigUFPrincipal"] == "PE") | df["DscMuninicpios"].fillna("").str.contains(r"- PE\b", regex=True)
    df = df[in_pe].copy()

    for col in SIGA_NUMERIC:
        df[col] = pd.to_numeric(df[col].str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
                                errors="coerce")
    for col in SIGA_DATES:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    df = df.rename(columns={
        "DatGeracaoConjuntoDados": "data_geracao_conjunto",
        "NomEmpreendimento": "nome",
        "IdeNucleoCEG": "ceg_nucleo",
        "CodCEG": "ceg",
        "SigUFPrincipal": "uf_principal",
        "SigTipoGeracao": "tipo_geracao",
        "DscFaseUsina": "fase",
        "DscOrigemCombustivel": "origem_combustivel",
        "DscFonteCombustivel": "fonte_combustivel",
        "DscTipoOutorga": "tipo_outorga",
        "NomFonteCombustivel": "nome_fonte_combustivel",
        "DatEntradaOperacao": "data_entrada_operacao",
        "MdaPotenciaOutorgadaKw": "potencia_outorgada_kw",
        "MdaPotenciaFiscalizadaKw": "potencia_fiscalizada_kw",
        "MdaGarantiaFisicaKw": "garantia_fisica_kw",
        "IdcGeracaoQualificada": "geracao_qualificada",
        "NumCoordNEmpreendimento": "latitude",
        "NumCoordEEmpreendimento": "longitude",
        "DatInicioVigencia": "data_inicio_vigencia",
        "DatFimVigencia": "data_fim_vigencia",
        "DscPropriRegimePariticipacao": "proprietarios_regime",
        "DscSubBacia": "sub_bacia",
        "DscMuninicpios": "municipios",
    })
    df["fonte_orgao"] = "ANEEL / Dados Abertos (SIGA)"

    engine = get_engine()
    df.to_sql(SIGA_TABLE, engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {SIGA_TABLE} ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;"))
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{SIGA_TABLE}_ceg_nucleo ON {SIGA_TABLE} (ceg_nucleo);"))
        cnt = conn.execute(text(f"SELECT COUNT(*) FROM {SIGA_TABLE};")).scalar()
    logger.info(f"Table '{SIGA_TABLE}' ready with {cnt} rows.")
    return cnt


def run(offline: bool = False, only: Optional[List[str]] = None) -> Dict[str, int]:
    counts = ingest_layers(offline=offline, only=only)
    if not only or SIGA_TABLE in only:
        counts[SIGA_TABLE] = ingest_siga(offline=offline)
    calculate_energy_overlaps()
    logger.info("ANEEL/EPE ingestion summary:")
    for table, n in counts.items():
        logger.info(f"  {table:40s} {n:>6d}")
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ANEEL SIGEL / EPE energy infrastructure ETL for Pernambuco.")
    parser.add_argument("--offline", action="store_true", help="Reload from cached responses in data/raw/aneel/.")
    parser.add_argument("--only", nargs="+", metavar="TABLE", help="Only (re)build the given target tables.")
    args = parser.parse_args()
    run(offline=args.offline, only=args.only)
