#!/usr/bin/env python3
"""
ETL Pipeline: Campanha Nacional Despejo Zero (Pernambuco)
=========================================================
Fetches and ingests community land and housing conflict data from the official
Despejo Zero platform (https://mapa.despejozero.org.br/), filtering for
the State of Pernambuco.

Attributes extracted:
- Community title & slug
- Municipality & UF
- Numbers of threatened, evicted, and legally suspended families
- Primary conflict causes (e.g. Reintegração de Posse, Obras Públicas, Área de Risco)
- Legal support (Defensoria Pública, Assessoria Jurídica Popular)
- Promoter agents (Público, Privado)
- Full case narratives and chronological update dates

Target PostGIS Table: public.despejo_zero_pe
Spatial Reference: EPSG:4326 (Point)
"""

import json
import logging
import math
import hashlib
import re
import urllib.request
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import geopandas as gpd
from shapely.geometry import Point
from sqlalchemy import text

from src.config import BASE_DIR, RAW_DATA_DIR, EXTRACTED_DATA_DIR
from src.database import get_engine, init_postgis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

API_URL = "https://mapa.despejozero.org.br/wp-json/conflitosurbanos/v1/busca"
RAW_FILE = RAW_DATA_DIR / "despejo_zero_brasil.json"
TARGET_DIR = EXTRACTED_DATA_DIR / "despejo_zero_pe"
TARGET_GEOJSON = TARGET_DIR / "despejo_zero_pe.geojson"


def fetch_or_load_raw_data() -> Dict[str, Any]:
    """Fetch raw data from Despejo Zero API or load from cached file."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check if raw file exists and has size
    if RAW_FILE.exists() and RAW_FILE.stat().st_size > 100000:
        logger.info(f"Loading cached raw Despejo Zero data from {RAW_FILE}")
        with open(RAW_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    logger.info(f"Fetching Despejo Zero data from {API_URL}...")
    req = urllib.request.Request(
        API_URL,
        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode("utf-8")
        data = json.loads(content)

    with open(RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved raw payload ({len(content)} bytes) to {RAW_FILE}")
    return data


def format_slug_name(slug: str) -> str:
    """Format municipality slug (e.g. 'vitoria-de-santo-antao-pe' -> 'Vitória de Santo Antão')."""
    if not slug:
        return "Pernambuco"
    s = re.sub(r"-pe$", "", slug, flags=re.IGNORECASE)
    parts = s.split("-")
    capitalized = []
    lowercase_words = {"de", "da", "do", "das", "dos", "e"}
    for i, p in enumerate(parts):
        if i > 0 and p.lower() in lowercase_words:
            capitalized.append(p.lower())
        else:
            capitalized.append(p.capitalize())
    return " ".join(capitalized)


def format_taxonomy_label(slug: str) -> str:
    """Humanize taxonomy slugs."""
    mapping = {
        "ameaca": "Ameaça de Despejo",
        "remocao-parcial": "Remoção Parcial Executada",
        "remocao-total": "Despejo/Remoção Total Executada",
        "suspensao-temporaria": "Ordem de Despejo Suspensa Temporariamente",
        "suspensao-definitiva": "Despejo Suspenso Definitivamente / Conflito Sanado",
        "reintegracao-de-posse-violacao-da-posse-ou-propriedade-do-autor-do-processo": "Ação de Reintegração de Posse",
        "area-de-risco": "Alegação de Área de Risco Geológico/Hidrológico",
        "area-de-protecao-ambiental": "Conflito em Área de Proteção Ambiental",
        "impacto-de-obras-publicas-projetos-de-urbanizacao": "Impacto de Obras Públicas / Projetos de Urbanização",
        "violacao-de-contrato-de-locacao": "Inadimplência / Rescisão de Locação",
    }
    return mapping.get(slug, slug.replace("-", " ").title() if slug else "Não informado")


def compute_jitter(key: str, base_lon: float, base_lat: float, radius_km: float = 0.35) -> Tuple[float, float]:
    """Generates a micro-offset for coincident points so multiple cases in the same location are visible."""
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
    angle = (h % 360) * (math.pi / 180.0)
    dist = ((h >> 8) % 1000) / 1000.0 * radius_km
    d_lat = (dist * math.sin(angle)) / 111.0
    d_lon = (dist * math.cos(angle)) / (111.0 * math.cos(math.radians(base_lat)))
    return base_lon + d_lon, base_lat + d_lat


def parse_int_safe(val: Any) -> int:
    """Safely parse integer count."""
    try:
        if val is None:
            return 0
        s = str(val).strip()
        digits = re.sub(r"[^\d]", "", s)
        return int(digits) if digits else 0
    except Exception:
        return 0


def load_pe_polygon():
    """Load the official IBGE Pernambuco state boundary polygon."""
    pe_boundary_path = BASE_DIR / "src" / "pe_boundary.geojson"
    if pe_boundary_path.exists():
        pe_gdf = gpd.read_file(pe_boundary_path)
        return pe_gdf.geometry.union_all()
    return None


def ingest_despejo_zero():
    """Main ingestion pipeline."""
    init_postgis()
    engine = get_engine()
    pe_polygon = load_pe_polygon()

    raw_data = fetch_or_load_raw_data()
    all_conflitos = raw_data.get("conflito", [])
    logger.info(f"Total national records parsed: {len(all_conflitos)}")

    # Filter Pernambuco records
    pe_records = []
    for c in all_conflitos:
        tax = c.get("tax", {})
        ufs = [str(u).lower().strip() for u in tax.get("uf", [])]
        munis = [str(m).lower().strip() for m in tax.get("municipio", [])]

        # Explicit non-PE state exclusion
        other_ufs = {u for u in ufs if u != "pe"}
        if other_ufs:
            continue
        if any(re.search(r"-(?!pe)[a-z]{2}$", m) for m in munis):
            continue

        is_pe = ("pe" in ufs) or any(m.endswith("-pe") for m in munis)

        if not is_pe and pe_polygon is not None:
            # Fallback to physical geometric intersection
            try:
                lat = float(c.get("meta", {}).get("localizacao_lat", 0))
                lng = float(c.get("meta", {}).get("localizacao_lng", 0))
                pt = Point(lng, lat)
                if pe_polygon.contains(pt):
                    is_pe = True
            except (ValueError, TypeError):
                pass

        if is_pe:
            pe_records.append(c)

    logger.info(f"Identified {len(pe_records)} records strictly in Pernambuco.")

    # Track coordinate frequencies for jitter
    coord_counts: Dict[Tuple[float, float], int] = {}
    cleaned_rows = []

    for item in pe_records:
        cid = item.get("ID")
        title = item.get("post_title", "").strip()
        slug = item.get("post_name", "").strip()
        post_date = item.get("post_date")
        post_modified = item.get("post_modified")

        meta = item.get("meta", {})
        tax = item.get("tax", {})

        raw_lat = meta.get("localizacao_lat")
        raw_lng = meta.get("localizacao_lng")

        try:
            lat = float(raw_lat)
            lng = float(raw_lng)
        except (ValueError, TypeError):
            logger.warning(f"Skipping record {cid} '{title}': invalid coordinates ({raw_lat}, {raw_lng})")
            continue

        # In Pernambuco: Longitude is around -34 to -41, Latitude is -7 to -9.6.
        # Check inverted coordinates:
        if lat < -30.0 and lng > -30.0:
            lat, lng = lng, lat

        # Check bounds
        if not ((-10.5 <= lat <= -3.0) and (-42.5 <= lng <= -32.0)):
            logger.warning(f"Skipping record {cid} '{title}': coordinates outside Pernambuco ({lat}, {lng})")
            continue

        orig_coord = (round(lat, 5), round(lng, 5))
        occurrences = coord_counts.get(orig_coord, 0)
        coord_counts[orig_coord] = occurrences + 1

        # Apply deterministic jitter if coordinate has duplicates
        if occurrences > 0:
            j_lng, j_lat = compute_jitter(f"{cid}_{title}_{occurrences}", lng, lat, radius_km=0.45)
        else:
            j_lng, j_lat = lng, lat

        geom = Point(j_lng, j_lat)

        # Taxonomies
        munis = tax.get("municipio", [])
        muni_slug = munis[0] if munis else "pe"
        municipio_name = format_slug_name(muni_slug)

        status_slugs = tax.get("status_conflito", [])
        status_labels = [format_taxonomy_label(s) for s in status_slugs]
        status_str = "; ".join(status_labels) if status_labels else "Não informado"

        causa_slugs = tax.get("causa_do_conflito", [])
        causa_labels = [format_taxonomy_label(s) for s in causa_slugs]
        causa_str = "; ".join(causa_labels) if causa_labels else "Conflito Fundiário / Posse"

        # Families
        fam_ameacadas = parse_int_safe(meta.get("numero_de_familias_ameacadas"))
        fam_despejadas = parse_int_safe(meta.get("numero_de_familias_despejadas"))
        fam_suspensas = parse_int_safe(meta.get("numero_de_familias_suspensao_definitiva"))
        total_fam = fam_ameacadas + fam_despejadas + fam_suspensas

        # Legal support & agents
        juridico = meta.get("acompanhamento_juridico_do_caso", [])
        juridico_str = "; ".join(juridico) if isinstance(juridico, list) else str(juridico or "Não informado")

        agentes = meta.get("agentes_promotores_publicos_ou_privados", [])
        agentes_str = "; ".join(agentes) if isinstance(agentes, list) else str(agentes or "Não informado")

        descricao = meta.get("descricao", "") or ""

        cleaned_rows.append({
            "conflito_id": int(cid),
            "nome_comunidade": title,
            "slug": slug,
            "municipio": municipio_name,
            "uf": "PE",
            "familias_ameacadas": fam_ameacadas,
            "familias_despejadas": fam_despejadas,
            "familias_suspensas": fam_suspensas,
            "total_familias": total_fam,
            "status_conflito": status_str,
            "causa_conflito": causa_str,
            "acompanhamento_juridico": juridico_str,
            "agente_promotor": agentes_str,
            "descricao": descricao,
            "data_registro": post_date,
            "data_atualizacao": post_modified,
            "lat_original": lat,
            "lon_original": lng,
            "geometry": geom
        })

    logger.info(f"Successfully processed {len(cleaned_rows)} valid georeferenced records for Pernambuco.")

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(cleaned_rows, geometry="geometry", crs="EPSG:4326")

    # Export to GeoJSON
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    gdf.to_file(TARGET_GEOJSON, driver="GeoJSON")
    logger.info(f"Exported clean GeoJSON to {TARGET_GEOJSON}")

    # Write to PostGIS
    table_name = "despejo_zero_pe"
    logger.info(f"Writing to database table 'public.{table_name}'...")

    gdf.to_postgis(
        name=table_name,
        con=engine,
        schema="public",
        if_exists="replace",
        index=False
    )

    # Create primary key and spatial index
    with engine.begin() as conn:
        conn.execute(text(f"""
            ALTER TABLE public.{table_name} 
            ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;
        """))
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_geometry 
            ON public.{table_name} USING GIST (geometry);
        """))
        conn.execute(text(f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_municipio 
            ON public.{table_name} (municipio);
        """))

    logger.info(f"Table 'public.{table_name}' created and indexed successfully.")

    # Print summary statistics
    total_threatened = gdf["familias_ameacadas"].sum()
    total_evicted = gdf["familias_despejadas"].sum()
    top_munis = gdf["municipio"].value_counts().head(8).to_dict()

    print("\n" + "=" * 70)
    print("CAMPANHA DESPEJO ZERO - PERNAMBUCO INGESTION SUMMARY")
    print("=" * 70)
    print(f"Total Georeferenced Conflicts:  {len(gdf)}")
    print(f"Total Threatened Families:     {total_threatened:,}")
    print(f"Total Evicted Families:        {total_evicted:,}")
    print(f"Top Conflict Municipalities:   {top_munis}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    ingest_despejo_zero()
