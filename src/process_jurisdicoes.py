"""
Process Judicial Jurisdictions: Extract Comarcas & Municipalities from TJPE and JFPE DOCX documents,
normalize against IBGE database, export structured CSVs, and load into PostgreSQL/PostGIS.
"""

import csv
import json
import logging
import re
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "data" / "extracted" / "jurisdicoes"
SEDES_FILE = BASE_DIR / "src" / "pe_municipios_sedes.json"

TJPE_DOCX = RAW_DIR / "TJPE (Justiça Estadual) - Comarcas e municípios abrangidos.docx"
JFPE_DOCX = RAW_DIR / "JFPE (Justiça Federal) - Seções judiciárias e municípios abrangidos.docx"

# Aliases dictionary to handle phonetic or orthographic variations
NAME_ALIASES = {
    "iguaraci": "iguaracy",
    "sao caitano": "sao caetano",
    "palmerina": "palmeirina",
    "gloria de goita": "gloria do goita",
    "nova petrolandia": "petrolandia",
    "itamaraca": "ilha de itamaraca",
    "ilha de itamaraca": "ilha de itamaraca",
    "sao vicente ferrer": "sao vicente ferrer",
    "belem de maria": "belem de maria",
    "belem do sao francisco": "belem do sao francisco"
}


def normalize_text(text_val: str) -> str:
    """Removes accents, lowercases, replaces hyphens and extra spaces."""
    t = "".join(c for c in unicodedata.normalize("NFKD", text_val) if not unicodedata.combining(c))
    t = t.lower().replace("-", " ")
    return " ".join(t.split())


def load_ibge_database() -> Dict[str, Dict]:
    """Loads all 185 Pernambuco municipalities from official IBGE dataset."""
    with open(SEDES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def build_name_to_ibge_lookup(ibge_data: Dict[str, Dict]) -> Dict[str, Tuple[int, str, float, float]]:
    """Builds a normalized name-to-IBGE dictionary."""
    lookup = {}
    for code_str, d in ibge_data.items():
        norm = normalize_text(d["name"])
        lookup[norm] = (int(code_str), d["name"], float(d["lon"]), float(d["lat"]))
    return lookup


def resolve_municipality(name: str, lookup: Dict[str, Tuple[int, str, float, float]]) -> Optional[Tuple[int, str, float, float]]:
    """Resolves a municipality name to (ibge_code, official_name, lon, lat)."""
    n = normalize_text(name)
    if n in NAME_ALIASES:
        n = NAME_ALIASES[n]
    if n in lookup:
        return lookup[n]
    return None


def extract_cell_lines(tc: ET.Element, ns: Dict[str, str]) -> List[str]:
    """Extracts text lines from a table cell, properly interpreting <w:br> and <w:p> line breaks."""
    lines = []
    for p in tc.findall("w:p", ns):
        parts = []
        for elem in p.iter():
            tag = elem.tag.split("}")[-1]
            if tag == "t" and elem.text:
                parts.append(elem.text)
            elif tag == "br":
                parts.append("\n")
        full = "".join(parts)
        for line in full.split("\n"):
            line = line.strip()
            if line:
                lines.append(line)
    return lines


def parse_tjpe_docx(lookup: Dict[str, Tuple[int, str, float, float]]) -> List[Dict]:
    """Parses the TJPE DOCX file into structured records."""
    logger.info(f"Parsing TJPE docx from {TJPE_DOCX}...")
    if not TJPE_DOCX.exists():
        raise FileNotFoundError(f"File not found: {TJPE_DOCX}")

    with zipfile.ZipFile(TJPE_DOCX) as z:
        tree = ET.fromstring(z.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        table = tree.find("w:body", ns).find("w:tbl", ns)

    rows = table.findall("w:tr", ns)
    records = []
    
    # First pass: map each comarca to its list of municipalities
    comarcas_dict = {}
    for r in rows:
        cells = r.findall("w:tc", ns)
        c0_lines = extract_cell_lines(cells[0], ns)
        c1_lines = extract_cell_lines(cells[1], ns)
        comarca_raw = " ".join(c0_lines).strip()
        if not comarca_raw or comarca_raw.upper() == "COMARCA":
            continue

        resolved_comarca = resolve_municipality(comarca_raw, lookup)
        comarca_ibge = resolved_comarca[0] if resolved_comarca else None
        comarca_clean_name = resolved_comarca[1] if resolved_comarca else comarca_raw

        munis_list = []
        for m in c1_lines:
            if m.upper() == "MUNICÍPIOS ABRANGIDOS":
                continue
            res_m = resolve_municipality(m, lookup)
            if not res_m:
                logger.error(f"Unmatched TJPE municipality: '{m}' in Comarca '{comarca_raw}'")
            else:
                munis_list.append(res_m)

        if comarca_clean_name not in comarcas_dict:
            comarcas_dict[comarca_clean_name] = {
                "comarca_ibge": comarca_ibge,
                "municipios": []
            }
        comarcas_dict[comarca_clean_name]["municipios"].extend(munis_list)

    # Second pass: build flat records with rich metadata
    for comarca_name, cdata in comarcas_dict.items():
        c_ibge = cdata["comarca_ibge"]
        munis = cdata["municipios"]
        total_munis = len(munis)
        muni_names = [m[1] for m in munis]
        abrangidos_str = "; ".join(muni_names)

        for m in munis:
            m_ibge, m_name, lon, lat = m
            eh_sede = (m_ibge == c_ibge)
            tipo_vinculo = "Sede da Comarca" if eh_sede else "Termo Judiciário (Município Abrangido)"
            records.append({
                "tribunal": "TJPE",
                "comarca_nome": comarca_name,
                "comarca_ibge": c_ibge,
                "municipio_nome": m_name,
                "municipio_ibge": m_ibge,
                "eh_sede": eh_sede,
                "tipo_vinculo": tipo_vinculo,
                "total_municipios_comarca": total_munis,
                "municipios_abrangidos": abrangidos_str,
                "lon": lon,
                "lat": lat
            })

    logger.info(f"TJPE parsed: {len(records)} municipality links across {len(comarcas_dict)} comarcas.")
    return records


def parse_jfpe_docx(lookup: Dict[str, Tuple[int, str, float, float]]) -> List[Dict]:
    """Parses the JFPE DOCX file into structured records."""
    logger.info(f"Parsing JFPE docx from {JFPE_DOCX}...")
    if not JFPE_DOCX.exists():
        raise FileNotFoundError(f"File not found: {JFPE_DOCX}")

    with zipfile.ZipFile(JFPE_DOCX) as z:
        tree = ET.fromstring(z.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        body = tree.find("w:body", ns)

    current_sec = None
    sec_data = []

    for child in body:
        tag = child.tag.split("}")[-1]
        if tag == "p":
            t = "".join(child.itertext()).strip()
            if t and t not in ["Seção Judiciária", "Subseções Judiciárias"] and not t.startswith("Fonte:"):
                current_sec = t
        elif tag == "tbl":
            rows = child.findall("w:tr", ns)
            if len(rows) >= 2:
                cells = rows[1].findall("w:tc", ns)
                varas = "".join(cells[0].itertext()).strip()
                munis_text = "".join(cells[1].itertext()).strip()
                sec_data.append((current_sec, varas, munis_text))

    records = []
    for s_name, varas, m_text in sec_data:
        clean_s_name = s_name.replace(" (Sede)", "").strip()
        res_sec = resolve_municipality(clean_s_name, lookup)
        sec_ibge = res_sec[0] if res_sec else None

        # Mask 'Abreu e Lima' to prevent incorrect split on conjunction ' e '
        m_clean = m_text.replace("Abreu e Lima", "__ABREU_E_LIMA__")
        m_clean = m_clean.replace(" e ", ", ")
        raw_items = [p.strip().rstrip(".") for p in m_clean.split(",") if p.strip()]
        clean_munis = [p.replace("__ABREU_E_LIMA__", "Abreu e Lima") for p in raw_items]

        resolved_munis = []
        for m in clean_munis:
            res_m = resolve_municipality(m, lookup)
            if not res_m:
                logger.error(f"Unmatched JFPE municipality: '{m}' in Subseção '{s_name}'")
            else:
                resolved_munis.append(res_m)

        total_munis = len(resolved_munis)
        abrangidos_str = "; ".join(m[1] for m in resolved_munis)

        for m in resolved_munis:
            m_ibge, m_name, lon, lat = m
            eh_sede = (m_ibge == sec_ibge)
            records.append({
                "tribunal": "TRF5/JFPE",
                "subsecao_nome": s_name,
                "subsecao_sede_nome": res_sec[1] if res_sec else clean_s_name,
                "subsecao_ibge": sec_ibge,
                "varas": varas,
                "municipio_nome": m_name,
                "municipio_ibge": m_ibge,
                "eh_sede": eh_sede,
                "total_municipios_subsecao": total_munis,
                "municipios_abrangidos": abrangidos_str,
                "lon": lon,
                "lat": lat
            })

    logger.info(f"JFPE parsed: {len(records)} municipality links across {len(sec_data)} subseções.")
    return records


def build_unified_territorial_dataset(
    tjpe_records: List[Dict],
    jfpe_records: List[Dict],
    ibge_data: Dict[str, Dict]
) -> List[Dict]:
    """Combines TJPE and JFPE jurisdictions into a master statewide table for all 185 municipalities."""
    tjpe_by_ibge = {r["municipio_ibge"]: r for r in tjpe_records}
    
    jfpe_by_ibge = {}
    for r in jfpe_records:
        mibge = r["municipio_ibge"]
        if mibge not in jfpe_by_ibge:
            jfpe_by_ibge[mibge] = []
        jfpe_by_ibge[mibge].append(r)

    unified = []
    for code_str, d in sorted(ibge_data.items(), key=lambda x: x[1]["name"]):
        ibge_code = int(code_str)
        muni_name = d["name"]
        lon = float(d["lon"])
        lat = float(d["lat"])

        tj_info = tjpe_by_ibge.get(ibge_code, {})
        jf_list = jfpe_by_ibge.get(ibge_code, [])

        jf_subsecoes = "; ".join(j["subsecao_nome"] for j in jf_list)
        jf_varas = " | ".join(f"{j['subsecao_nome']}: {j['varas']}" for j in jf_list)
        jf_eh_sede = any(j["eh_sede"] for j in jf_list)

        unified.append({
            "municipio_ibge": ibge_code,
            "municipio_nome": muni_name,
            "lon": lon,
            "lat": lat,
            # TJPE Estadual
            "tjpe_comarca_nome": tj_info.get("comarca_nome", ""),
            "tjpe_comarca_ibge": tj_info.get("comarca_ibge", ""),
            "tjpe_eh_sede": tj_info.get("eh_sede", False),
            "tjpe_tipo_vinculo": tj_info.get("tipo_vinculo", ""),
            "tjpe_total_municipios_comarca": tj_info.get("total_municipios_comarca", 1),
            "tjpe_comarca_abrangencia": tj_info.get("municipios_abrangidos", ""),
            # JFPE Federal
            "jfpe_subsecoes": jf_subsecoes,
            "jfpe_varas": jf_varas,
            "jfpe_eh_sede": jf_eh_sede
        })

    return unified


def export_csv(records: List[Dict], filepath: Path):
    """Exports records list to CSV file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        return
    fieldnames = list(records[0].keys())
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    logger.info(f"Saved CSV with {len(records)} rows: {filepath}")


def ingest_to_postgres(
    tjpe_records: List[Dict],
    jfpe_records: List[Dict],
    unified_records: List[Dict],
    engine
):
    """Creates tables and indexes in PostGIS for jurisdictions and territorial competences."""
    logger.info("Ingesting territorial jurisdiction tables into PostgreSQL/PostGIS...")
    with engine.begin() as conn:
        # 1. Table: jurisdicao_tjpe
        conn.execute(text("DROP TABLE IF EXISTS public.jurisdicao_tjpe CASCADE;"))
        conn.execute(text("""
            CREATE TABLE public.jurisdicao_tjpe (
                id SERIAL PRIMARY KEY,
                tribunal VARCHAR(20) NOT NULL,
                comarca_nome VARCHAR(150) NOT NULL,
                comarca_ibge INTEGER NOT NULL,
                municipio_nome VARCHAR(150) NOT NULL,
                municipio_ibge INTEGER NOT NULL,
                eh_sede BOOLEAN NOT NULL,
                tipo_vinculo VARCHAR(100) NOT NULL,
                total_municipios_comarca INTEGER NOT NULL,
                municipios_abrangidos TEXT NOT NULL,
                geometry GEOMETRY(Point, 4326)
            );
            CREATE INDEX idx_jurisdicao_tjpe_muni ON public.jurisdicao_tjpe (municipio_ibge);
            CREATE INDEX idx_jurisdicao_tjpe_comarca ON public.jurisdicao_tjpe (comarca_ibge);
            CREATE INDEX idx_jurisdicao_tjpe_geom ON public.jurisdicao_tjpe USING GIST (geometry);
        """))

        for r in tjpe_records:
            conn.execute(text("""
                INSERT INTO public.jurisdicao_tjpe (
                    tribunal, comarca_nome, comarca_ibge, municipio_nome, municipio_ibge,
                    eh_sede, tipo_vinculo, total_municipios_comarca, municipios_abrangidos, geometry
                ) VALUES (
                    :tribunal, :comarca_nome, :comarca_ibge, :municipio_nome, :municipio_ibge,
                    :eh_sede, :tipo_vinculo, :total_municipios_comarca, :municipios_abrangidos,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                );
            """), r)

        # 2. Table: jurisdicao_jfpe
        conn.execute(text("DROP TABLE IF EXISTS public.jurisdicao_jfpe CASCADE;"))
        conn.execute(text("""
            CREATE TABLE public.jurisdicao_jfpe (
                id SERIAL PRIMARY KEY,
                tribunal VARCHAR(20) NOT NULL,
                subsecao_nome VARCHAR(150) NOT NULL,
                subsecao_sede_nome VARCHAR(150) NOT NULL,
                subsecao_ibge INTEGER,
                varas TEXT NOT NULL,
                municipio_nome VARCHAR(150) NOT NULL,
                municipio_ibge INTEGER NOT NULL,
                eh_sede BOOLEAN NOT NULL,
                total_municipios_subsecao INTEGER NOT NULL,
                municipios_abrangidos TEXT NOT NULL,
                geometry GEOMETRY(Point, 4326)
            );
            CREATE INDEX idx_jurisdicao_jfpe_muni ON public.jurisdicao_jfpe (municipio_ibge);
            CREATE INDEX idx_jurisdicao_jfpe_subsecao ON public.jurisdicao_jfpe (subsecao_ibge);
            CREATE INDEX idx_jurisdicao_jfpe_geom ON public.jurisdicao_jfpe USING GIST (geometry);
        """))

        for r in jfpe_records:
            conn.execute(text("""
                INSERT INTO public.jurisdicao_jfpe (
                    tribunal, subsecao_nome, subsecao_sede_nome, subsecao_ibge, varas,
                    municipio_nome, municipio_ibge, eh_sede, total_municipios_subsecao, municipios_abrangidos, geometry
                ) VALUES (
                    :tribunal, :subsecao_nome, :subsecao_sede_nome, :subsecao_ibge, :varas,
                    :municipio_nome, :municipio_ibge, :eh_sede, :total_municipios_subsecao, :municipios_abrangidos,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                );
            """), r)

        # 3. Master Table: jurisdicoes_pe_municipios (185 municipalities)
        conn.execute(text("DROP TABLE IF EXISTS public.jurisdicoes_pe_municipios CASCADE;"))
        conn.execute(text("""
            CREATE TABLE public.jurisdicoes_pe_municipios (
                municipio_ibge INTEGER PRIMARY KEY,
                municipio_nome VARCHAR(150) NOT NULL,
                tjpe_comarca_nome VARCHAR(150) NOT NULL,
                tjpe_comarca_ibge INTEGER NOT NULL,
                tjpe_eh_sede BOOLEAN NOT NULL,
                tjpe_tipo_vinculo VARCHAR(100) NOT NULL,
                tjpe_total_municipios_comarca INTEGER NOT NULL,
                tjpe_comarca_abrangencia TEXT NOT NULL,
                jfpe_subsecoes TEXT NOT NULL,
                jfpe_varas TEXT NOT NULL,
                jfpe_eh_sede BOOLEAN NOT NULL,
                geometry GEOMETRY(Point, 4326)
            );
            CREATE INDEX idx_jurisdicoes_pe_geom ON public.jurisdicoes_pe_municipios USING GIST (geometry);
            CREATE INDEX idx_jurisdicoes_pe_comarca ON public.jurisdicoes_pe_municipios (tjpe_comarca_ibge);
        """))

        for r in unified_records:
            conn.execute(text("""
                INSERT INTO public.jurisdicoes_pe_municipios (
                    municipio_ibge, municipio_nome, tjpe_comarca_nome, tjpe_comarca_ibge,
                    tjpe_eh_sede, tjpe_tipo_vinculo, tjpe_total_municipios_comarca, tjpe_comarca_abrangencia,
                    jfpe_subsecoes, jfpe_varas, jfpe_eh_sede, geometry
                ) VALUES (
                    :municipio_ibge, :municipio_nome, :tjpe_comarca_nome, :tjpe_comarca_ibge,
                    :tjpe_eh_sede, :tjpe_tipo_vinculo, :tjpe_total_municipios_comarca, :tjpe_comarca_abrangencia,
                    :jfpe_subsecoes, :jfpe_varas, :jfpe_eh_sede,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                );
            """), r)

    logger.info("Territorial jurisdiction tables successfully created and indexed!")


def main():
    logger.info("=== Starting Jurisdictions Processing (TJPE & JFPE) ===")
    ibge_data = load_ibge_database()
    lookup = build_name_to_ibge_lookup(ibge_data)

    tjpe_records = parse_tjpe_docx(lookup)
    jfpe_records = parse_jfpe_docx(lookup)
    unified_records = build_unified_territorial_dataset(tjpe_records, jfpe_records, ibge_data)

    # Export CSVs
    export_csv(tjpe_records, OUTPUT_DIR / "tjpe_comarcas_municipios.csv")
    export_csv(jfpe_records, OUTPUT_DIR / "jfpe_subsecoes_municipios.csv")
    export_csv(unified_records, OUTPUT_DIR / "jurisdicoes_pe_completo.csv")

    # Ingest to PostgreSQL/PostGIS
    engine = get_engine()
    ingest_to_postgres(tjpe_records, jfpe_records, unified_records, engine)

    logger.info("=== Jurisdictions Processing Completed Successfully! ===")


if __name__ == "__main__":
    main()
