"""
ETL DataJud Module: Extract, Classify, Geolocate, and Ingest Agrarian & Land Conflict Lawsuits
from CNJ Public API (TJPE and TRF5) into PostGIS database.

Supports:
- Full streaming ingestion with cursor pagination (search_after)
- Resilient retry logic with exponential backoff for HTTP 429 (rate limit) and network timeouts
- Checkpointing to allow seamless resumption if interrupted
- Batch streaming into PostgreSQL to prevent memory exhaustion
"""

import argparse
import hashlib
import json
import logging
import math
import os
import random
import re
import socket
import ssl
import sys
import time
import urllib.error
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

CHECKPOINT_DIR = BASE_DIR / "data" / "extracted"
CHECKPOINT_FILE = CHECKPOINT_DIR / "datajud_checkpoints.json"

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

    for ibge, (lon, lat, name) in FALLBACK_MUNICIPALITY_COORDS.items():
        if ibge not in lookup:
            lookup[ibge] = (lon, lat, name)

    return lookup


def classify_conflict(assuntos_codigos: List[int], classe_codigo: Optional[int], assuntos_nomes: List[str], classe_nome: Optional[str]) -> str:
    """Categorizes a lawsuit into one of the major agrarian/land conflict categories."""
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
    dist = ((h >> 8) % 1000) / 1000.0 * radius_km
    d_lat = (dist * math.sin(angle)) / 111.0
    d_lon = (dist * math.cos(angle)) / (111.0 * math.cos(math.radians(base_lat)))
    return base_lon + d_lon, base_lat + d_lat


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parses various date formats from DataJud."""
    if not date_str:
        return None
    try:
        if "T" in date_str:
            clean_str = date_str.replace("Z", "").split(".")[0]
            return datetime.fromisoformat(clean_str)
        if len(date_str) == 14:
            return datetime.strptime(date_str, "%Y%m%d%H%M%S")
        if len(date_str) == 8:
            return datetime.strptime(date_str, "%Y%m%d")
    except Exception:
        pass
    return None


def format_cnj(raw_num: str) -> str:
    """Format raw CNJ process number into standard masked format NNNNNNN-DD.YYYY.J.TR.OOOO."""
    digits = re.sub(r'\D', '', str(raw_num or ''))
    if len(digits) == 20:
        return f"{digits[:7]}-{digits[7:9]}.{digits[9:13]}.{digits[13:14]}.{digits[14:16]}.{digits[16:20]}"
    return str(raw_num or 'N/A')


def load_checkpoints() -> Dict[str, Any]:
    """Loads extraction checkpoints from disk."""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load checkpoint file: {e}")
    return {
        "TJPE": {"search_after": None, "pages_completed": 0, "records_ingested": 0, "status": "pending"},
        "TRF5": {"search_after": None, "pages_completed": 0, "records_ingested": 0, "status": "pending"}
    }


def save_checkpoints(data: Dict[str, Any]):
    """Persists extraction checkpoints to disk."""
    try:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Could not save checkpoint file: {e}")


def fetch_datajud_page(
    tribunal: str,
    size: int = 100,
    search_after: Optional[List[Any]] = None,
    extra_must: Optional[List[Dict]] = None,
    timeout: int = 60
) -> Tuple[str, Optional[Dict[str, Any]], str]:
    """
    Executes a single HTTP query against CNJ DataJud Elasticsearch endpoint.
    Uses lean field projection (_source) to drastically reduce server deserialization overhead.

    Returns:
        (status, data, message)
        - status: "success" | "retryable" | "unrecoverable"
        - data: parsed JSON dict on success, None on error
        - message: descriptive string for logging / backoff calculation
    """
    ctx = ssl.create_default_context()
    url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal.lower()}/_search"

    should_clauses = [
        {"terms": {"assuntos.codigo": TARGET_ASSUNTO_CODES}},
        {"terms": {"classe.codigo": TARGET_CLASSE_CODES}}
    ]

    must_clauses = []
    if extra_must:
        must_clauses.extend(extra_must)

    # Specific field projection drastically reduces server serialization overhead and prevents
    # Elasticsearch threadpool saturation (es_rejected_execution_exception) on CNJ's shared cluster.
    query_body = {
        "size": size,
        "_source": [
            "id", "numeroProcesso", "grau", "dataAjuizamento",
            "classe.codigo", "classe.nome",
            "assuntos.codigo", "assuntos.nome",
            "orgaoJulgador.codigo", "orgaoJulgador.nome", "orgaoJulgador.codigoMunicipioIBGE",
            "movimentos.nome", "movimentos.dataHora"
        ],
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

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(query_body).encode("utf-8"),
            headers={
                "Authorization": f"APIKey {DATAJUD_KEY}",
                "Content-Type": "application/json"
            }
        )

        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return "success", data, "OK"

    except urllib.error.HTTPError as e:
        if e.code == 429:
            err_msg = ""
            try:
                err_msg = e.read().decode("utf-8")
            except Exception:
                pass

            if "es_rejected_execution_exception" in err_msg:
                return "retryable", None, "CNJ Elasticsearch queue saturated (1000/1000 queued tasks)"
            return "retryable", None, "HTTP 429 Too Many Requests"

        elif e.code in (500, 502, 503, 504):
            return "retryable", None, f"Server error HTTP {e.code}"
        else:
            return "unrecoverable", None, f"HTTP {e.code}: {e.reason}"

    except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
        return "retryable", None, f"Connection timeout/network error ({e})"

    except Exception as e:
        return "unrecoverable", None, f"Unexpected error ({e})"


def fetch_datajud_batch_with_retry(
    tribunal: str,
    size: int = 100,
    search_after: Optional[List[Any]] = None,
    extra_must: Optional[List[Dict]] = None,
    timeout: int = 60,
    max_retries: int = 6,
    initial_backoff: float = 16.0
) -> Optional[Dict[str, Any]]:
    """Legacy helper wrapper for single-tribunal scripts with self-contained retry."""
    for attempt in range(max_retries):
        status, data, msg = fetch_datajud_page(tribunal, size, search_after, extra_must, timeout)
        if status == "success":
            return data
        if status == "unrecoverable":
            logger.error(f"[{tribunal.upper()}] Unrecoverable error: {msg}")
            return None
        wait_sec = min(120.0, initial_backoff * (1.5 ** attempt) + random.uniform(1.0, 3.0))
        logger.warning(f"[{tribunal.upper()}] {msg}. Waiting {wait_sec:.1f}s (retry {attempt + 1}/{max_retries})...")
        time.sleep(wait_sec)
    return None


def transform_single_record(item: Dict[str, Any], muni_lookup: Dict[int, Tuple[float, float, str]]) -> Optional[Dict[str, Any]]:
    """Transforms, classifies, and geolocates a single raw process record."""
    tribunal_source = item["tribunal_source"]
    s = item["source"]
    raw_num = s.get("numeroProcesso") or "N/A"
    clean_digits = re.sub(r'\D', '', str(raw_num))
    proc_id = s.get("id") or f"{tribunal_source}_{raw_num}"

    # For TRF5, if not already filtered, ensure it belongs to Pernambuco (JFPE)
    if tribunal_source == "TRF5":
        # In TRF5, 4.05.83xx identifies Pernambuco federal section
        if "40583" not in clean_digits and not any(clean_digits.endswith(sub) for sub in TRF5_PE_SUBSECOES.keys()):
            return None

    numero_processo = format_cnj(raw_num)
    grau = s.get("grau") or "G1"
    data_ajuiz = parse_date(s.get("dataAjuizamento"))
    
    classe_info = s.get("classe", {})
    if isinstance(classe_info, list) and classe_info:
        classe_info = classe_info[0] if isinstance(classe_info[0], dict) else {}
    elif not isinstance(classe_info, dict):
        classe_info = {}

    raw_classe_cod = classe_info.get("codigo")
    classe_codigo = None
    if raw_classe_cod is not None:
        if isinstance(raw_classe_cod, list) and raw_classe_cod:
            raw_classe_cod = raw_classe_cod[0]
        try:
            classe_codigo = int(str(raw_classe_cod).strip())
        except (ValueError, TypeError):
            classe_codigo = None
    classe_nome = str(classe_info.get("nome")) if classe_info.get("nome") else None

    raw_assuntos = s.get("assuntos", [])
    flat_assuntos = []
    if isinstance(raw_assuntos, list):
        for item_a in raw_assuntos:
            if isinstance(item_a, list):
                for sub_a in item_a:
                    if isinstance(sub_a, dict):
                        flat_assuntos.append(sub_a)
            elif isinstance(item_a, dict):
                flat_assuntos.append(item_a)
    elif isinstance(raw_assuntos, dict):
        flat_assuntos.append(raw_assuntos)

    assuntos_codigos = []
    assuntos_nomes = []
    assuntos_pairs = []
    for a in flat_assuntos:
        if isinstance(a, dict):
            raw_c = a.get("codigo")
            if isinstance(raw_c, list) and raw_c:
                raw_c = raw_c[0]
            try:
                if raw_c is not None:
                    c_int = int(str(raw_c).strip())
                    assuntos_codigos.append(c_int)
            except (ValueError, TypeError):
                pass
            n = a.get("nome")
            if n:
                assuntos_nomes.append(str(n).strip())
                assuntos_pairs.append(f"{raw_c}: {n}")
            elif raw_c:
                assuntos_pairs.append(str(raw_c))

    assuntos_str = "; ".join(assuntos_pairs)

    categoria = classify_conflict(assuntos_codigos, classe_codigo, assuntos_nomes, classe_nome)

    org = s.get("orgaoJulgador", {})
    if isinstance(org, list) and org:
        org = org[0] if isinstance(org[0], dict) else {}
    elif not isinstance(org, dict):
        org = {}
    org_codigo = org.get("codigo")
    if isinstance(org_codigo, list) and org_codigo:
        org_codigo = org_codigo[0]
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
    
    if tribunal_source == "TRF5" or not muni_ibge:
        subsecao_code = clean_digits[-4:] if len(clean_digits) >= 4 else "8300"
        if subsecao_code in TRF5_PE_SUBSECOES:
            muni_ibge, muni_nome = TRF5_PE_SUBSECOES[subsecao_code]
        else:
            muni_ibge = 2611606
            muni_nome = "Recife (JFPE)"
    elif muni_ibge in muni_lookup:
        muni_nome = muni_lookup[muni_ibge][2]

    if muni_ibge in muni_lookup:
        base_lon, base_lat, muni_name_found = muni_lookup[muni_ibge]
        if muni_nome == "Pernambuco":
            muni_nome = muni_name_found
    else:
        base_lon, base_lat, _ = FALLBACK_MUNICIPALITY_COORDS[2611606]

    lon, lat = compute_deterministic_jitter(proc_id, base_lon, base_lat, radius_km=0.8)

    movimentos = s.get("movimentos", [])
    total_mov = len(movimentos) if isinstance(movimentos, list) else 0
    ultimo_mov = None
    data_ultimo_mov = None
    if isinstance(movimentos, list) and movimentos:
        last_m = movimentos[-1]
        if isinstance(last_m, dict):
            ultimo_mov = last_m.get("nome")
            data_ultimo_mov = parse_date(last_m.get("dataHora"))

    if tribunal_source == "TJPE":
        url_consulta = "https://pje.tjpe.jus.br/1g/ConsultaPublica/listView.seam"
    else:
        url_consulta = "https://pje.trf5.jus.br/pje/ConsultaPublica/listView.seam"

    return {
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


def ensure_schema(engine):
    """Creates database schema and indexes if they do not exist."""
    with engine.begin() as conn:
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

            CREATE INDEX IF NOT EXISTS idx_processos_conflitos_geom 
            ON public.processos_conflitos_judiciais USING GIST (geometry);

            CREATE INDEX IF NOT EXISTS idx_processos_conflitos_cat 
            ON public.processos_conflitos_judiciais (categoria_conflito);

            CREATE INDEX IF NOT EXISTS idx_processos_conflitos_trib 
            ON public.processos_conflitos_judiciais (tribunal);

            CREATE INDEX IF NOT EXISTS idx_processos_conflitos_muni 
            ON public.processos_conflitos_judiciais (municipio_ibge);
        """))


def upsert_records_batch(engine, records: List[Dict[str, Any]]):
    """Upserts a batch of transformed records into PostGIS."""
    if not records:
        return

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

    with engine.begin() as conn:
        for rec in records:
            conn.execute(upsert_stmt, rec)


def stream_ingest_round_robin(
    tribunals: List[str],
    engine,
    muni_lookup: Dict[int, Tuple[float, float, str]],
    max_pages_per_tribunal: Optional[int] = None,
    batch_size: int = 100,
    inter_court_delay: float = 3.0,
    single_court_delay: float = 8.0,
    reset_checkpoint: bool = False
) -> Dict[str, int]:
    """
    Streams and ingests lawsuits in an interleaved round-robin fashion across multiple courts.
    For example: 1 page TJPE -> 1 page TRF5 -> 1 page TJPE -> 1 page TRF5...
    Features:
    - Per-attempt yielding: if a court encounters a 429 or 504, it backs off and yields immediately to the next court instead of monopolizing the retry loop.
    - Adaptive batch sizing: automatically scales batch size from 100 to 50 under cluster queue pressure to ease Elasticsearch fetch deserialization.
    - Coordinated cluster cooldown: if all courts are cooling down from CNJ threadpool saturation, pauses once for the remaining duration.
    - Fully resumable: checkpoints are persisted after every ingested batch.
    """
    checkpoints = load_checkpoints()
    active_tribunals = []
    consecutive_empty: Dict[str, int] = {}
    consecutive_errors: Dict[str, int] = {}
    consecutive_success: Dict[str, int] = {}
    cooldown_until: Dict[str, float] = {}
    current_batch_size: Dict[str, int] = {}

    for trib in tribunals:
        t_key = trib.upper()
        consecutive_empty[t_key] = 0
        consecutive_errors[t_key] = 0
        consecutive_success[t_key] = 0
        cooldown_until[t_key] = 0.0
        current_batch_size[t_key] = batch_size

        if reset_checkpoint or t_key not in checkpoints:
            checkpoints[t_key] = {
                "search_after": None,
                "pages_completed": 0,
                "records_ingested": 0,
                "status": "in_progress",
                "last_updated": datetime.now().isoformat()
            }
        t_state = checkpoints[t_key]
        if t_state.get("status") == "completed":
            logger.info(f"[{t_key}] Marked as completed in checkpoint. Skipping.")
        else:
            t_state["status"] = "in_progress"
            active_tribunals.append(t_key)

    logger.info(
        f"Starting Interleaved Round-Robin extraction across: {', '.join(active_tribunals)}..."
    )
    for t_key in active_tribunals:
        st = checkpoints[t_key]
        logger.info(
            f"  * {t_key}: Resuming from Page {st.get('pages_completed', 0) + 1} "
            f"({st.get('records_ingested', 0)} records previously ingested)"
        )

    round_num = 0

    while active_tribunals:
        round_num += 1

        now = time.time()
        # If all active tribunals are in cooldown, pause until the earliest cooldown expires
        ready_tribunals = [t for t in active_tribunals if now >= cooldown_until[t]]
        if not ready_tribunals:
            earliest = min(cooldown_until[t] for t in active_tribunals)
            wait_s = max(1.0, min(earliest - now, 60.0))
            logger.info(
                f"[Cluster Cooldown] All courts cooling down from CNJ threadpool load. "
                f"Pausing {wait_s:.1f}s before next cycle..."
            )
            time.sleep(wait_s)

        logger.info(f"\n--- Round-Robin Cycle {round_num} (Active Courts: {', '.join(active_tribunals)}) ---")
        to_remove = []

        for trib_key in list(active_tribunals):
            trib_state = checkpoints[trib_key]
            page_num = trib_state.get("pages_completed", 0)
            total_ingested = trib_state.get("records_ingested", 0)
            search_after = trib_state.get("search_after")

            if max_pages_per_tribunal is not None and page_num >= max_pages_per_tribunal:
                logger.info(f"[{trib_key}] Reached configured max pages limit ({max_pages_per_tribunal}). Stopping.")
                trib_state["status"] = "paused_at_limit"
                save_checkpoints(checkpoints)
                to_remove.append(trib_key)
                continue

            now = time.time()
            if now < cooldown_until[trib_key]:
                rem = cooldown_until[trib_key] - now
                logger.info(f"[{trib_key}] Cooling down ({rem:.1f}s remaining). Yielding turn.")
                continue

            next_page = page_num + 1
            cur_size = current_batch_size[trib_key]
            logger.info(f"[{trib_key}] Fetching Page {next_page} (batch_size={cur_size})...")

            extra_must = [{"wildcard": {"numeroProcesso": "*40583*"}}] if trib_key == "TRF5" else None
            req_timeout = 75 if trib_key == "TRF5" else 60

            status, res, msg = fetch_datajud_page(
                tribunal=trib_key,
                size=cur_size,
                search_after=search_after,
                extra_must=extra_must,
                timeout=req_timeout
            )

            if status == "success":
                consecutive_errors[trib_key] = 0
                consecutive_success[trib_key] += 1

                # Restore batch size if we were throttled down and reached stability
                if consecutive_success[trib_key] >= 3 and cur_size < batch_size:
                    current_batch_size[trib_key] = batch_size
                    logger.info(f"[{trib_key}] Connection stable. Restoring batch_size to {batch_size}.")

                hits = res.get("hits", {}).get("hits", []) if res else []
                total_hits_info = res.get("hits", {}).get("total", {}) if res else {}
                if isinstance(total_hits_info, dict):
                    total_matching = total_hits_info.get("value")
                    if total_matching:
                        trib_state["total_matching"] = total_matching

                if not hits:
                    consecutive_empty[trib_key] += 1
                    logger.info(f"[{trib_key}] No records returned on page {next_page}. (Empty check {consecutive_empty[trib_key]}/2)")
                    if consecutive_empty[trib_key] >= 2:
                        logger.info(f"[{trib_key}] Extraction completed! All available records downloaded.")
                        trib_state["status"] = "completed"
                        trib_state["search_after"] = None
                        save_checkpoints(checkpoints)
                        to_remove.append(trib_key)
                        continue
                else:
                    consecutive_empty[trib_key] = 0

                    transformed_batch = []
                    for h in hits:
                        try:
                            item = {"tribunal_source": trib_key, "source": h.get("_source", {})}
                            rec = transform_single_record(item, muni_lookup)
                            if rec:
                                transformed_batch.append(rec)
                        except Exception as e:
                            logger.warning(f"[{trib_key}] Skipping malformed record {h.get('_id', 'unknown')}: {e}")

                    upsert_records_batch(engine, transformed_batch)
                    total_ingested += len(transformed_batch)

                    last_sort = hits[-1].get("sort")
                    trib_state["search_after"] = last_sort
                    trib_state["pages_completed"] = next_page
                    trib_state["records_ingested"] = total_ingested
                    trib_state["last_updated"] = datetime.now().isoformat()
                    trib_state["status"] = "in_progress"
                    save_checkpoints(checkpoints)

                    last_date = hits[-1]["_source"].get("dataAjuizamento")
                    logger.info(
                        f"  [{trib_key}] Page {next_page} ingested {len(transformed_batch)} records "
                        f"(Total: {total_ingested} | Last filing date: {last_date})"
                    )

                pacing = inter_court_delay if len(active_tribunals) > 1 else single_court_delay
                if pacing > 0:
                    time.sleep(pacing)

            elif status == "retryable":
                consecutive_errors[trib_key] += 1
                consecutive_success[trib_key] = 0
                err_count = consecutive_errors[trib_key]

                # Dynamically reduce batch size under queue congestion to ease ES fetch phase
                if cur_size > 50:
                    current_batch_size[trib_key] = 50
                    logger.info(f"[{trib_key}] Temporarily reducing batch_size to 50 to relieve Elasticsearch fetch threadpool.")

                wait_sec = min(120.0, 16.0 * (1.35 ** min(err_count, 6)) + random.uniform(1.0, 4.0))
                cooldown_until[trib_key] = time.time() + wait_sec

                logger.warning(
                    f"[{trib_key}] {msg}. Cooling down for {wait_sec:.1f}s (streak: {err_count}). "
                    f"Yielding immediately to next court..."
                )
                # DO NOT REMOVE from active_tribunals!
                # We yield immediately to the other court!

            elif status == "unrecoverable":
                logger.error(f"[{trib_key}] Unrecoverable error ({msg}). Pausing {trib_key}.")
                trib_state["status"] = "error_paused"
                save_checkpoints(checkpoints)
                to_remove.append(trib_key)

        for rem in to_remove:
            if rem in active_tribunals:
                active_tribunals.remove(rem)

    return {t: checkpoints[t].get("records_ingested", 0) for t in tribunals}


def run(
    max_pages: Optional[int] = None,
    tribunal: str = "ALL",
    reset_checkpoint: bool = False,
    delay: float = 3.0,
    enrich_only: bool = False
):
    """
    Main execution pipeline:
    1. Sets up schema
    2. Runs interleaved round-robin streaming ingestion across TJPE and TRF5
    3. Runs territorial jurisdiction enrichment
    4. Refreshes aggregated municipal summaries
    """
    from src.enrich_judicial_data import enrich_lawsuits

    engine = get_engine()
    ensure_schema(engine)
    muni_lookup = load_municipality_lookup(engine)

    interrupted = False
    if not enrich_only:
        tribunals_to_run = ["TJPE", "TRF5"] if tribunal.upper() == "ALL" else [tribunal.upper()]

        try:
            stream_ingest_round_robin(
                tribunals=tribunals_to_run,
                engine=engine,
                muni_lookup=muni_lookup,
                max_pages_per_tribunal=max_pages,
                inter_court_delay=delay,
                single_court_delay=8.0,
                reset_checkpoint=reset_checkpoint
            )
        except KeyboardInterrupt:
            logger.info(
                f"\n[INTERRUPTED] Extraction paused by user (Ctrl+C). "
                f"All progress up to the last completed batch is safely saved in checkpoints."
            )
            interrupted = True
        except Exception as e:
            logger.error(f"Error during round-robin streaming ingestion: {e}", exc_info=True)

    # Enrich comarca metadata and refresh public.processos_conflitos_municipios
    # even if interrupted so the latest ingested records are mapped and visible
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
        unique_procs = conn.execute(text("SELECT COUNT(DISTINCT numero_processo) FROM public.processos_conflitos_judiciais;")).scalar()
        print(f"\nTOTAL JUDICIAL CONFLICT LAWSUITS INGESTED: {tot} (Unique numbers: {unique_procs})")
        if interrupted:
            print("\n  >> Extraction was paused. To resume where you left off, simply run:")
            print("     uv run python src/etl_datajud.py")
        print("===========================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DataJud CNJ Streaming Ingestion Pipeline")
    parser.add_argument("--tribunal", choices=["TJPE", "TRF5", "ALL"], default="ALL", help="Target court (default: ALL)")
    parser.add_argument("--max-pages", type=int, default=None, help="Max pages per court (default: None for full ingestion)")
    parser.add_argument("--delay", type=float, default=3.0, help="Inter-court delay between requests in seconds (default: 3.0)")
    parser.add_argument("--reset-checkpoint", action="store_true", help="Reset checkpoint and start from page 1")
    parser.add_argument("--enrich-only", action="store_true", help="Only run comarca enrichment and municipal summaries")
    args = parser.parse_args()

    run(
        max_pages=args.max_pages,
        tribunal=args.tribunal,
        reset_checkpoint=args.reset_checkpoint,
        delay=args.delay,
        enrich_only=args.enrich_only
    )
