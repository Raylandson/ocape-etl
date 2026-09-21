"""
ETL DataJud Module: Extract, Classify, Geolocate, and Ingest Agrarian & Land Conflict Lawsuits
from CNJ Public API (TJPE and TRF5) into PostGIS database.
"""

import hashlib
import json
import logging
import math
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import text
from src.database import get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

DATAJUD_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# Targeted TPU Assuntos related to agrarian and land conflicts
# 11412: Conflito fundiário coletivo rural
# 11413: Conflito fundiário coletivo urbano
# 10124: Desapropriação por Interesse Social para Reforma Agrária
# 11873: Política fundiária e da reforma agrária
# 12031: Desapropriação para Regularização de Comunidade Quilombola
# 10104: Restituição de área - FUNAI
# 15114: Caso Povo Indígena Xucuru vs. Brasil
# 3647: Crimes praticados contra os índios e a cultura indígena
# 10094: Terras Devolutas
# 10100: Reintegração de Posse
# 10434: Reintegração de Posse
# 10444: Posse
# 10445: Esbulho / Turbação / Ameaça
# 10446: Imissão
# 10451: Divisão e Demarcação
# 10453: Retificação de Área de Imóvel
# 10500: Usucapião Especial Rural (Lei 6.969/1981)
# 10457: Usucapião Especial Constitucional
# 10460: Usucapião Especial Coletiva
# 10458: Usucapião Extraordinária
# 10459: Usucapião Ordinária
# 7640: Interdito Proibitório
# 3425: Esbulho possessório (Penal)
# 5995 / 10185: Títulos da Dívida Agrária (TDA)
# 9985: Direito Agrário / Administrativo

TARGET_ASSUNTO_CODES = [
    11412, 11413, 10124, 11873, 12031, 10104, 15114, 3647,
    10094, 10100, 10434, 10444, 10445, 10446, 10451, 10453,
    10500, 10457, 10460, 10458, 10459, 7640, 3425, 5995, 10185, 9985
]

# Targeted Procedural Classes:
# 91: Desapropriação Imóvel Rural por Interesse Social
# 90: Desapropriação
# 96: Discriminatória (Ação Discriminatória)
# 1707: Reintegração / Manutenção de Posse
# 1709: Interdito Proibitório
# 34: Demarcação / Divisão
# 49: Usucapião
# 65: Ação Civil Pública
# 63: Ação Civil Coletiva
TARGET_CLASSE_CODES = [91, 90, 96, 1707, 1709, 34, 49, 65, 63]

# Subsections of TRF5 in Pernambuco (JFPE) mapped to IBGE codes & names
TRF5_PE_SUBSECOES = {
    "8300": (2611606, "Recife"),
    "8301": (2611606, "Recife"),
    "8302": (2611101, "Petrolina"),
    "8303": (2606002, "Garanhuns"),
    "8304": (2604106, "Caruaru"),
    "8305": (2611606, "Recife"),
    "8306": (2611606, "Recife"),
    "8307": (2610004, "Palmares"),
    "8308": (2613909, "Serra Talhada"),
    "8309": (2612208, "Salgueiro"),
    "8310": (2601102, "Arcoverde"),
    "8311": (2606200, "Goiana"),
    "8312": (2603801, "Carpina"),
    "8313": (2602902, "Cabo de Santo Agostinho"),
    "8314": (2607901, "Jaboatão dos Guararapes"),
    "8315": (2609907, "Ouricuri"),
    "0000": (2611606, "Recife (TRF5 Sede)"),
}

# Fallback coordinates for PE municipalities
FALLBACK_MUNICIPALITY_COORDS = {
    2611606: (-34.8770, -8.0578, "Recife"),
    2607604: (-34.8486, -7.7478, "Ilha de Itamaracá"),
    2603454: (-34.9819, -8.0205, "Camaragibe"),
    2605459: (-32.4297, -3.8576, "Fernando de Noronha"),
    2602902: (-35.0347, -8.2831, "Cabo de Santo Agostinho"),
    2604106: (-35.9711, -8.2833, "Caruaru"),
    2611101: (-40.5008, -9.3891, "Petrolina"),
    2606002: (-36.4928, -8.8907, "Garanhuns"),
    2601102: (-37.0583, -8.4192, "Arcoverde"),
    2613909: (-38.2981, -7.9914, "Serra Talhada"),
    2612208: (-39.1246, -8.0744, "Salgueiro"),
    2609907: (-40.0818, -7.8828, "Ouricuri"),
    2606200: (-35.0003, -7.5583, "Goiana"),
    2603801: (-35.2508, -7.8503, "Carpina"),
    2610004: (-35.5908, -8.6831, "Palmares"),
    2607901: (-35.0147, -8.1128, "Jaboatão dos Guararapes"),
    2609600: (-35.2975, -8.0089, "Olinda"),
    2610707: (-34.8728, -7.9408, "Paulista"),
    2611002: (-38.2197, -8.9792, "Petrolândia"),
    2605707: (-38.5689, -8.6014, "Floresta"),
    2600203: (-41.0094, -8.5147, "Afrânio"),
    2605103: (-37.6439, -8.0872, "Custódia"),
    2614709: (-36.2869, -8.2858, "Tacaimbó"),
    2606507: (-36.8550, -9.0469, "Iati"),
}


def load_municipality_lookup(engine) -> Dict[int, Tuple[float, float, str]]:
    """Loads exact city center / sede coordinates and municipal names for all 185 Pernambuco municipalities."""
    lookup = {}
    
    # 1. Load official IBGE municipal sedes (city center coordinates)
    sedes_file = BASE_DIR / "src" / "pe_municipios_sedes.json"
    if sedes_file.exists():
        try:
            with open(sedes_file, "r", encoding="utf-8") as f:
                sedes_data = json.load(f)
                for ibge_str, d in sedes_data.items():
                    lookup[int(ibge_str)] = (float(d["lon"]), float(d["lat"]), d["name"])
            logger.info(f"Loaded {len(lookup)} official municipal sedes from {sedes_file.name}.")
        except Exception as e:
            logger.warning(f"Could not load sedes file: {e}")

    # 2. Seed with any remaining fallback coordinates
    for ibge, (lon, lat, name) in FALLBACK_MUNICIPALITY_COORDS.items():
        if ibge not in lookup:
            lookup[ibge] = (lon, lat, name)

    return lookup


def classify_conflict(assuntos_codigos: List[int], classe_codigo: Optional[int], assuntos_nomes: List[str], classe_nome: Optional[str]) -> str:
    """Categorizes a lawsuit into one of the 6 major agrarian/land conflict categories."""
    full_text = (" ".join(assuntos_nomes) + " " + (classe_nome or "")).lower()

    # 1. Povos Indígenas & Comunidades Quilombolas
    if any(c in [12031, 10104, 15114, 3647] for c in assuntos_codigos) or \
       any(k in full_text for k in ["quilombola", "indígena", "indio", "xucuru", "funai"]):
        return "Povos Indígenas & Territórios Quilombolas"

    # 2. Conflito Coletivo & Agrário
    if any(c in [11412, 11413, 9985] for c in assuntos_codigos) or \
       any(k in full_text for k in ["conflito fundiário coletivo", "conflito agrário", "direito agrário"]):
        return "Conflito Coletivo Rural & Agrário"

    # 3. Reforma Agrária & Desapropriação
    if any(c in [10124, 11873, 5995, 10185] for c in assuntos_codigos) or classe_codigo in [91, 90] or \
       any(k in full_text for k in ["reforma agrária", "dívida agrária", "tda", "desapropriação"]):
        return "Reforma Agrária & Desapropriação"

    # 4. Terras Devolutas & Ação Discriminatória
    if any(c in [10094, 10451, 10453, 10105] for c in assuntos_codigos) or classe_codigo in [96, 34] or \
       any(k in full_text for k in ["discriminatória", "terras devolutas", "demarcação"]):
        return "Terras Devolutas & Ações Discriminatórias"

    # 5. Posse & Reintegração
    if any(c in [10100, 10434, 10444, 10445, 10446, 7640, 3425] for c in assuntos_codigos) or classe_codigo in [1707, 1709] or \
       any(k in full_text for k in ["reintegração", "esbulho", "turbação", "interdito proibitório", "imissão"]):
        return "Reintegração e Conflito de Posse"

    # 6. Usucapião Rural
    if any(c in [10500, 10457, 10460, 10458, 10459] for c in assuntos_codigos) or classe_codigo == 49 or \
       "usucapião" in full_text:
        return "Usucapião e Regularização de Posse"

    return "Outros Conflitos Fundiários"


def compute_deterministic_jitter(proc_id: str, base_lon: float, base_lat: float, radius_km: float = 1.2) -> Tuple[float, float]:
    """Generates a deterministic micro-offset based on process ID hash so multiple lawsuits in the same comarca do not stack exactly on 1 point."""
    h = int(hashlib.md5(proc_id.encode("utf-8")).hexdigest(), 16)
    angle = (h % 360) * (math.pi / 180.0)
    dist = ((h >> 8) % 1000) / 1000.0 * radius_km  # 0 to radius_km
    
    # 1 degree lat ~ 111 km, 1 degree lon ~ 111 * cos(lat) km
    d_lat = (dist * math.sin(angle)) / 111.0
    d_lon = (dist * math.cos(angle)) / (111.0 * math.cos(math.radians(base_lat)))
    
    return base_lon + d_lon, base_lat + d_lat


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parses various date formats from DataJud."""
    if not date_str:
        return None
    try:
        # e.g. "2026-07-17T04:13:28.065000Z"
        if "T" in date_str:
            clean_str = date_str.replace("Z", "").split(".")[0]
            return datetime.fromisoformat(clean_str)
        # e.g. "20240912153746" or "20170206000000"
        if len(date_str) == 14:
            return datetime.strptime(date_str, "%Y%m%d%H%M%S")
        if len(date_str) == 8:
            return datetime.strptime(date_str, "%Y%m%d")
    except Exception:
        pass
    return None


def fetch_datajud_batch(tribunal: str, size: int = 100, search_after: Optional[List[Any]] = None, extra_must: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Fetches a batch from DataJud API."""
    ctx = ssl.create_default_context()
    url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search"

    should_clauses = [
        {"terms": {"assuntos.codigo": TARGET_ASSUNTO_CODES}},
        {"terms": {"classe.codigo": TARGET_CLASSE_CODES}}
    ]

    must_clauses = []
    if extra_must:
        must_clauses.extend(extra_must)

    query_body = {
        "size": size,
        "query": {
            "bool": {
                "must": must_clauses,
                "should": should_clauses,
                "minimum_should_match": 1
            }
        },
        "sort": [
            {"dataAjuizamento": {"order": "desc"}},
            {"id.keyword": {"order": "asc"}}
        ]
    }

    if search_after:
        query_body["search_after"] = search_after

    req = urllib.request.Request(
        url,
        data=json.dumps(query_body).encode("utf-8"),
        headers={
            "Authorization": f"APIKey {DATAJUD_KEY}",
            "Content-Type": "application/json"
        }
    )

    with urllib.request.urlopen(req, context=ctx, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_datajud_processes(max_pages_per_tribunal: int = 10) -> List[Dict[str, Any]]:
    """Extracts processes from TJPE and TRF5."""
    all_processes = []
    
    # 1. TJPE (All comarcas are in Pernambuco)
    logger.info("Extracting agrarian and land conflict lawsuits from TJPE...")
    search_after = None
    for page in range(max_pages_per_tribunal):
        try:
            res = fetch_datajud_batch("tjpe", size=100, search_after=search_after)
            hits = res.get("hits", {}).get("hits", [])
            if not hits:
                break
            for h in hits:
                all_processes.append({"tribunal_source": "TJPE", "source": h["_source"]})
            logger.info(f"  TJPE Page {page + 1}: fetched {len(hits)} records (Total: {len(all_processes)})")
            if "sort" in hits[-1]:
                search_after = hits[-1]["sort"]
            else:
                break
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"  Error fetching TJPE page {page + 1}: {e}")
            break

    # 2. TRF5 (Pernambuco Section - *40583*)
    logger.info("Extracting agrarian and land conflict lawsuits from TRF5 (Seção Pernambuco)...")
    search_after = None
    extra_must_trf5 = [{"wildcard": {"numeroProcesso": "*40583*"}}]
    for page in range(max_pages_per_tribunal):
        try:
            res = fetch_datajud_batch("trf5", size=100, search_after=search_after, extra_must=extra_must_trf5)
            hits = res.get("hits", {}).get("hits", [])
            if not hits:
                break
            for h in hits:
                all_processes.append({"tribunal_source": "TRF5", "source": h["_source"]})
            logger.info(f"  TRF5 Page {page + 1}: fetched {len(hits)} records (Total: {len(all_processes)})")
            if "sort" in hits[-1]:
                search_after = hits[-1]["sort"]
            else:
                break
            time.sleep(0.3)
        except Exception as e:
            logger.error(f"  Error fetching TRF5 page {page + 1}: {e}")
            break

    logger.info(f"Extraction complete! Total raw records collected: {len(all_processes)}")
    return all_processes


def format_cnj(raw_num: str) -> str:
    """Format raw CNJ process number into standard masked format NNNNNNN-DD.YYYY.J.TR.OOOO."""
    digits = re.sub(r'\D', '', str(raw_num or ''))
    if len(digits) == 20:
        return f"{digits[:7]}-{digits[7:9]}.{digits[9:13]}.{digits[13:14]}.{digits[14:16]}.{digits[16:20]}"
    return str(raw_num or 'N/A')


def process_and_geolocate_records(raw_records: List[Dict[str, Any]], muni_lookup: Dict[int, Tuple[float, float, str]]) -> List[Dict[str, Any]]:
    """Transforms, classifies, and geolocates process records."""
    processed = []
    seen_ids = set()

    for item in raw_records:
        tribunal_source = item["tribunal_source"]
        s = item["source"]
        raw_num = s.get("numeroProcesso") or "N/A"
        proc_id = s.get("id") or f"{tribunal_source}_{raw_num}"
        if proc_id in seen_ids:
            continue
        seen_ids.add(proc_id)

        numero_processo = format_cnj(raw_num)
        grau = s.get("grau") or "G1"
        data_ajuiz = parse_date(s.get("dataAjuizamento"))
        
        classe_info = s.get("classe", {})
        classe_codigo = classe_info.get("codigo")
        classe_nome = classe_info.get("nome")

        assuntos = s.get("assuntos", [])
        assuntos_codigos = [a.get("codigo") for a in assuntos if a.get("codigo")]
        assuntos_nomes = [a.get("nome") for a in assuntos if a.get("nome")]
        assuntos_str = "; ".join(f"{a.get('codigo')}: {a.get('nome')}" for a in assuntos)

        # Categorize
        categoria = classify_conflict(assuntos_codigos, classe_codigo, assuntos_nomes, classe_nome)

        # Court & Municipality
        org = s.get("orgaoJulgador", {})
        org_codigo = org.get("codigo")
        org_nome = org.get("nome") or "Vara não informada"
        
        raw_muni_ibge = org.get("codigoMunicipioIBGE")
        muni_ibge = None
        if raw_muni_ibge is not None:
            try:
                clean_ibge = int(str(raw_muni_ibge).strip())
                if clean_ibge > 0:
                    muni_ibge = clean_ibge
            except Exception:
                muni_ibge = None

        muni_nome = "Pernambuco"
        
        # TRF5 resolution from number or court name if IBGE is 0 / None
        if tribunal_source == "TRF5" or not muni_ibge:
            clean_digits = re.sub(r'\D', '', numero_processo)
            subsecao_code = clean_digits[-4:] if len(clean_digits) >= 4 else "8300"
            if subsecao_code in TRF5_PE_SUBSECOES:
                muni_ibge, muni_nome = TRF5_PE_SUBSECOES[subsecao_code]
            else:
                muni_ibge = 2611606
                muni_nome = "Recife (JFPE)"
        elif muni_ibge in muni_lookup:
            muni_nome = muni_lookup[muni_ibge][2]

        # Coordinates (Sede Municipal / Fórum)
        if muni_ibge in muni_lookup:
            base_lon, base_lat, muni_name_found = muni_lookup[muni_ibge]
            if muni_nome == "Pernambuco":
                muni_nome = muni_name_found
        else:
            base_lon, base_lat, _ = FALLBACK_MUNICIPALITY_COORDS[2611606]

        lon, lat = compute_deterministic_jitter(proc_id, base_lon, base_lat, radius_km=0.8)

        # Timeline / Movements
        movimentos = s.get("movimentos", [])
        total_mov = len(movimentos)
        ultimo_mov = movimentos[-1].get("nome") if movimentos else None
        data_ultimo_mov = parse_date(movimentos[-1].get("dataHora")) if movimentos else None

        # Public Consultation URL
        if tribunal_source == "TJPE":
            url_consulta = f"https://pje.tjpe.jus.br/1g/ConsultaPublica/listView.seam"
        else:
            url_consulta = f"https://pje.trf5.jus.br/pje/ConsultaPublica/listView.seam"

        record = {
            "id": proc_id,
            "numero_processo": numero_processo,
            "tribunal": tribunal_source,
            "grau": grau,
            "data_ajuizamento": data_ajuiz,
            "categoria_conflito": categoria,
            "classe_codigo": classe_codigo,
            "classe_nome": classe_nome,
            "assuntos_codigos": assuntos_codigos,
            "assuntos_nomes": assuntos_nomes,
            "assuntos_str": assuntos_str,
            "orgao_julgador_codigo": org_codigo,
            "orgao_julgador_nome": org_nome,
            "municipio_ibge": int(muni_ibge) if muni_ibge else None,
            "municipio_nome": muni_nome,
            "ultimo_movimento": ultimo_mov,
            "data_ultimo_movimento": data_ultimo_mov,
            "total_movimentos": total_mov,
            "url_consulta_publica": url_consulta,
            "lon": lon,
            "lat": lat
        }
        processed.append(record)

    return processed


def create_schema_and_ingest(records: List[Dict[str, Any]], engine):
    """Creates database schema and inserts processed conflict records into PostGIS."""
    logger.info("Setting up PostGIS tables for DataJud conflicts...")
    
    with engine.begin() as conn:
        # 1. Create table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.processos_conflitos_judiciais (
                id VARCHAR(100) PRIMARY KEY,
                numero_processo VARCHAR(40) NOT NULL,
                tribunal VARCHAR(10) NOT NULL,
                grau VARCHAR(10),
                data_ajuizamento TIMESTAMP,
                categoria_conflito VARCHAR(100) NOT NULL,
                classe_codigo INTEGER,
                classe_nome VARCHAR(255),
                assuntos_codigos INTEGER[],
                assuntos_nomes TEXT[],
                assuntos_str TEXT,
                orgao_julgador_codigo INTEGER,
                orgao_julgador_nome VARCHAR(255),
                municipio_ibge INTEGER,
                municipio_nome VARCHAR(150),
                ultimo_movimento TEXT,
                data_ultimo_movimento TIMESTAMP,
                total_movimentos INTEGER,
                url_consulta_publica TEXT,
                comarca_sede_nome VARCHAR(150),
                comarca_sede_ibge INTEGER,
                municipios_abrangidos TEXT,
                total_municipios_abrangidos INTEGER,
                tem_municipios_filhos BOOLEAN DEFAULT FALSE,
                tipo_jurisdicao VARCHAR(50),
                geometry GEOMETRY(Point, 4326)
            );
        """))

        # 2. Create spatial and b-tree indexes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_processos_conflitos_geom 
            ON public.processos_conflitos_judiciais USING GIST (geometry);

            CREATE INDEX IF NOT EXISTS idx_processos_conflitos_cat 
            ON public.processos_conflitos_judiciais (categoria_conflito);

            CREATE INDEX IF NOT EXISTS idx_processos_conflitos_trib 
            ON public.processos_conflitos_judiciais (tribunal);

            CREATE INDEX IF NOT EXISTS idx_processos_conflitos_muni 
            ON public.processos_conflitos_judiciais (municipio_ibge);
        """))

        # 3. Upsert records
        logger.info(f"Ingesting {len(records)} conflict records into public.processos_conflitos_judiciais...")
        upsert_stmt = text("""
            INSERT INTO public.processos_conflitos_judiciais (
                id, numero_processo, tribunal, grau, data_ajuizamento,
                categoria_conflito, classe_codigo, classe_nome,
                assuntos_codigos, assuntos_nomes, assuntos_str,
                orgao_julgador_codigo, orgao_julgador_nome,
                municipio_ibge, municipio_nome,
                ultimo_movimento, data_ultimo_movimento, total_movimentos,
                url_consulta_publica, geometry
            ) VALUES (
                :id, :numero_processo, :tribunal, :grau, :data_ajuizamento,
                :categoria_conflito, :classe_codigo, :classe_nome,
                :assuntos_codigos, :assuntos_nomes, :assuntos_str,
                :orgao_julgador_codigo, :orgao_julgador_nome,
                :municipio_ibge, :municipio_nome,
                :ultimo_movimento, :data_ultimo_movimento, :total_movimentos,
                :url_consulta_publica, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            )
            ON CONFLICT (id) DO UPDATE SET
                numero_processo = EXCLUDED.numero_processo,
                tribunal = EXCLUDED.tribunal,
                grau = EXCLUDED.grau,
                data_ajuizamento = EXCLUDED.data_ajuizamento,
                categoria_conflito = EXCLUDED.categoria_conflito,
                classe_codigo = EXCLUDED.classe_codigo,
                classe_nome = EXCLUDED.classe_nome,
                assuntos_codigos = EXCLUDED.assuntos_codigos,
                assuntos_nomes = EXCLUDED.assuntos_nomes,
                assuntos_str = EXCLUDED.assuntos_str,
                orgao_julgador_codigo = EXCLUDED.orgao_julgador_codigo,
                orgao_julgador_nome = EXCLUDED.orgao_julgador_nome,
                municipio_ibge = EXCLUDED.municipio_ibge,
                municipio_nome = EXCLUDED.municipio_nome,
                ultimo_movimento = EXCLUDED.ultimo_movimento,
                data_ultimo_movimento = EXCLUDED.data_ultimo_movimento,
                total_movimentos = EXCLUDED.total_movimentos,
                url_consulta_publica = EXCLUDED.url_consulta_publica,
                geometry = EXCLUDED.geometry;
        """)

        for rec in records:
            conn.execute(upsert_stmt, rec)

        # 4. Create / Refresh aggregated table by municipality
        conn.execute(text("""
            DROP TABLE IF EXISTS public.processos_conflitos_municipios CASCADE;
            CREATE TABLE public.processos_conflitos_municipios AS
            SELECT 
                municipio_ibge,
                municipio_nome,
                COUNT(*) AS total_processos,
                COUNT(*) FILTER (WHERE categoria_conflito = 'Reintegração e Conflito de Posse') AS total_posse,
                COUNT(*) FILTER (WHERE categoria_conflito = 'Reforma Agrária & Desapropriação') AS total_reforma_agraria,
                COUNT(*) FILTER (WHERE categoria_conflito = 'Povos Indígenas & Territórios Quilombolas') AS total_indigena_quilombola,
                COUNT(*) FILTER (WHERE categoria_conflito = 'Terras Devolutas & Ações Discriminatórias') AS total_devolutas_discriminatoria,
                COUNT(*) FILTER (WHERE categoria_conflito = 'Usucapião e Regularização de Posse') AS total_usucapiao,
                COUNT(*) FILTER (WHERE categoria_conflito = 'Conflito Coletivo Rural & Agrário') AS total_coletivo_agrario,
                ST_Centroid(ST_Collect(geometry)) AS geometry
            FROM public.processos_conflitos_judiciais
            WHERE municipio_ibge IS NOT NULL
            GROUP BY municipio_ibge, municipio_nome;

            CREATE INDEX IF NOT EXISTS idx_processos_muni_geom 
            ON public.processos_conflitos_municipios USING GIST (geometry);
        """))

    logger.info("Successfully ingested and indexed judicial conflict data into PostGIS!")


def run():
    """Main execution function."""
    from src.enrich_judicial_data import enrich_lawsuits
    engine = get_engine()
    muni_lookup = load_municipality_lookup(engine)
    raw_records = extract_datajud_processes(max_pages_per_tribunal=10)
    processed_records = process_and_geolocate_records(raw_records, muni_lookup)
    create_schema_and_ingest(processed_records, engine)
    enrich_lawsuits(engine)

    # Print summary statistics
    with engine.connect() as conn:
        res = conn.execute(text("""
            SELECT tribunal, categoria_conflito, COUNT(*) 
            FROM public.processos_conflitos_judiciais 
            GROUP BY tribunal, categoria_conflito 
            ORDER BY tribunal, COUNT(*) DESC;
        """))
        print("\n==================== INGESTION SUMMARY ====================")
        for r in res:
            print(f"  {r[0]} | {r[1]:<45}: {r[2]} processos")
        
        tot = conn.execute(text("SELECT COUNT(*) FROM public.processos_conflitos_judiciais;")).scalar()
        print(f"\nTOTAL JUDICIAL CONFLICT LAWSUITS INGESTED: {tot}")
        print("===========================================================\n")


if __name__ == "__main__":
    run()
