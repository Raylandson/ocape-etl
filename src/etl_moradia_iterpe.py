import re
import math
import json
import logging
import hashlib
import unicodedata
from pathlib import Path
from typing import Dict, Tuple, Optional, Any, List

import shapely
from shapely.geometry import Polygon, MultiPolygon, Point, GeometryCollection
import geopandas as gpd
from sqlalchemy import text
from src.database import get_engine
from src.config import BASE_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EXTRACTED_DIR = BASE_DIR / "data" / "extracted"
MORADIA_KML = EXTRACTED_DIR / "moradia_legal_pe" / "doc.kml"
ITERPE_DIR = EXTRACTED_DIR / "iterpe_acervo_fundiario"
MUNIS_JSON = BASE_DIR / "src" / "pe_municipios_sedes.json"


def normalize_str(s: str) -> str:
    """Normalize string removing accents and extra spaces."""
    if not s:
        return ""
    n = unicodedata.normalize("NFKD", s)
    ascii_str = n.encode("ASCII", "ignore").decode("utf-8")
    return re.sub(r"\s+", " ", ascii_str).strip().upper()


def load_municipalities_lookup() -> Tuple[Dict[str, Tuple[float, float, str, int]], Tuple[float, float]]:
    """Loads municipal centroids from JSON and returns normalized_name -> (lon, lat, official_name, ibge)."""
    with open(MUNIS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    lookup = {}
    recife_coords = (-34.877, -8.0579)
    for ibge_str, val in data.items():
        name = val["name"]
        lon = val["lon"]
        lat = val["lat"]
        norm = normalize_str(name)
        lookup[norm] = (lon, lat, name, int(ibge_str))
        if norm == "RECIFE":
            recife_coords = (lon, lat)

    return lookup, recife_coords


def compute_deterministic_jitter(key: str, base_lon: float, base_lat: float, radius_km: float = 1.0) -> Tuple[float, float]:
    """Generates a deterministic micro-offset based on key hash."""
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
    angle = (h % 360) * (math.pi / 180.0)
    dist = ((h >> 8) % 1000) / 1000.0 * radius_km
    d_lat = (dist * math.sin(angle)) / 111.0
    d_lon = (dist * math.cos(angle)) / (111.0 * math.cos(math.radians(base_lat)))
    return base_lon + d_lon, base_lat + d_lat


def format_cnj(raw_num: str) -> str:
    """Format raw CNJ process number into standard masked format NNNNNNN-DD.YYYY.J.TR.OOOO."""
    digits = re.sub(r"\D", "", str(raw_num or ""))
    if len(digits) == 20:
        return f"{digits[:7]}-{digits[7:9]}.{digits[9:13]}.{digits[13:14]}.{digits[14:16]}.{digits[16:20]}"
    return str(raw_num or "N/A")


def ensure_multipolygon(geom: Any) -> Optional[MultiPolygon]:
    """Sanitizes geometry, strips 3D coords, and ensures valid MultiPolygon."""
    if geom is None or geom.is_empty:
        return None
    geom = shapely.make_valid(geom)
    geom = shapely.force_2d(geom)
    if isinstance(geom, MultiPolygon):
        return geom
    elif isinstance(geom, Polygon):
        return MultiPolygon([geom])
    elif isinstance(geom, GeometryCollection):
        polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        if not polys:
            return None
        flat_polys = []
        for p in polys:
            if isinstance(p, Polygon):
                flat_polys.append(p)
            elif isinstance(p, MultiPolygon):
                flat_polys.extend(p.geoms)
        if flat_polys:
            return MultiPolygon(flat_polys)
    return None


def ingest_moradia_legal():
    """Ingests TJPE Moradia Legal polygons and processes into PostGIS."""
    if not MORADIA_KML.exists():
        logger.error(f"Moradia Legal KML not found at {MORADIA_KML}")
        return

    logger.info(f"Reading Moradia Legal KML from {MORADIA_KML}...")
    with open(MORADIA_KML, "r", encoding="utf-8", errors="ignore") as f:
        kml_content = f.read()

    muni_lookup, recife_coords = load_municipalities_lookup()
    placemarks = re.findall(r"<Placemark>.*?</Placemark>", kml_content, re.DOTALL)
    logger.info(f"Found {len(placemarks)} placemarks in Moradia Legal KML.")

    # 1. Parse Polygons (REURB community boundaries)
    polygon_records = []
    process_records = []

    for pm in placemarks:
        name_m = re.search(r"<name>(.*?)</name>", pm)
        name = name_m.group(1).strip() if name_m else "Sem Nome"

        # Check for Polygon
        if "<Polygon>" in pm:
            # Parse coordinates
            coords_match = re.search(r"<coordinates>(.*?)</coordinates>", pm, re.DOTALL)
            if not coords_match:
                continue
            raw_pts = coords_match.group(1).strip().split()
            pts = []
            for p_str in raw_pts:
                parts = p_str.split(",")
                if len(parts) >= 2:
                    try:
                        pts.append((float(parts[0]), float(parts[1])))
                    except ValueError:
                        continue
            if len(pts) < 3:
                continue

            raw_poly = Polygon(pts)
            geom = ensure_multipolygon(raw_poly)
            if geom is None:
                continue

            # Extract municipality and community name
            muni_nome = "Pernambuco"
            comunidade_nome = name
            if " - " in name:
                parts = name.split(" - ", 1)
                prefix_norm = normalize_str(parts[0])
                if prefix_norm in muni_lookup:
                    muni_nome = muni_lookup[prefix_norm][2]
                    comunidade_nome = parts[1].strip()
                elif prefix_norm.startswith("IBIRA"):
                    muni_nome = "Ibirajuba"
                    comunidade_nome = parts[1].strip()
            else:
                # Many un-prefixed names are ZEIS of Recife
                muni_nome = "Recife"

            polygon_records.append({
                "nome": name,
                "municipio": muni_nome,
                "comunidade": comunidade_nome,
                "tipo": "REURB / Regularização Fundiária",
                "origem": "TJPE - Moradia Legal (NUREF)",
                "geometry": geom
            })

        # Process Record (Individual Usucapião case)
        else:
            proc_raw = name
            proc_num = format_cnj(proc_raw)
            
            def get_data_field(field_name: str) -> str:
                m = re.search(rf'<Data name="{field_name}">\s*<value>(.*?)</value>', pm)
                return m.group(1).strip() if m else ""

            idmoradia = get_data_field("idmoradia")
            orgao = get_data_field("orgao_judiciario")
            logradouro = get_data_field("logradouro")
            numero = get_data_field("numero")
            bairro = get_data_field("bairro")
            cidade_raw = get_data_field("cidade")
            cep = get_data_field("cep")
            obs = get_data_field("obs")
            matricula_resp = get_data_field("matricula_resp")
            nome_resp = get_data_field("nome_resp")
            dt_cadastro = get_data_field("dt_cadastro")

            # Resolve coordinates from city or court
            norm_cidade = normalize_str(cidade_raw)
            muni_ibge = None
            muni_final = cidade_raw or "Pernambuco"
            base_lon, base_lat = recife_coords

            if norm_cidade in muni_lookup:
                base_lon, base_lat, muni_final, muni_ibge = muni_lookup[norm_cidade]
            else:
                # Try finding municipality in orgao_judiciario (e.g. "3 VARA CIVEL DA COMARCA DE GARANHUNS")
                norm_orgao = normalize_str(orgao)
                found = False
                for m_norm, val in muni_lookup.items():
                    if len(m_norm) > 4 and m_norm in norm_orgao:
                        base_lon, base_lat, muni_final, muni_ibge = val
                        found = True
                        break
                if not found:
                    base_lon, base_lat = recife_coords
                    muni_final = "Recife"
                    muni_ibge = 2611606

            jitter_key = f"{proc_num}_{idmoradia}_{base_lon}_{base_lat}"
            pt_lon, pt_lat = compute_deterministic_jitter(jitter_key, base_lon, base_lat, radius_km=1.5)

            process_records.append({
                "numero_processo": proc_num,
                "idmoradia": idmoradia,
                "orgao_judiciario": orgao,
                "logradouro": logradouro,
                "numero": numero,
                "bairro": bairro,
                "cidade": muni_final,
                "municipio_ibge": muni_ibge,
                "cep": cep,
                "observacao": obs,
                "matricula_responsavel": matricula_resp,
                "nome_responsavel": nome_resp,
                "data_cadastro": dt_cadastro,
                "geometry": Point(pt_lon, pt_lat)
            })

    engine = get_engine()

    # Ingest Polygons
    if polygon_records:
        gdf_poly = gpd.GeoDataFrame(polygon_records, crs="EPSG:4326")
        logger.info(f"Loaded {len(gdf_poly)} Moradia Legal REURB polygons. Writing to 'moradia_legal_pe'...")
        gdf_poly.to_postgis("moradia_legal_pe", engine, if_exists="replace", index=False)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE moradia_legal_pe ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;"))
            conn.execute(text("""
                ALTER TABLE moradia_legal_pe ADD COLUMN IF NOT EXISTS area_ha NUMERIC;
                UPDATE moradia_legal_pe SET area_ha = ROUND((ST_Area(geometry::geography) / 10000.0)::numeric, 2);
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_moradia_legal_pe_geom ON moradia_legal_pe USING GIST (geometry);"))
            conn.commit()
            cnt = conn.execute(text("SELECT COUNT(*) FROM moradia_legal_pe;")).scalar()
            logger.info(f"Table 'moradia_legal_pe' ready with {cnt} rows and spatial GIST index.")

    # Ingest Processes
    if process_records:
        gdf_proc = gpd.GeoDataFrame(process_records, crs="EPSG:4326")
        logger.info(f"Loaded {len(gdf_proc)} Moradia Legal process points. Writing to 'moradia_legal_processos_pe'...")
        gdf_proc.to_postgis("moradia_legal_processos_pe", engine, if_exists="replace", index=False)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE moradia_legal_processos_pe ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_moradia_legal_proc_geom ON moradia_legal_processos_pe USING GIST (geometry);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_moradia_legal_proc_num ON moradia_legal_processos_pe (numero_processo);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_moradia_legal_proc_cid ON moradia_legal_processos_pe (cidade);"))
            conn.commit()
            cnt = conn.execute(text("SELECT COUNT(*) FROM moradia_legal_processos_pe;")).scalar()
            logger.info(f"Table 'moradia_legal_processos_pe' ready with {cnt} rows and spatial GIST index.")


def ingest_iterpe():
    """Ingests ITERPE macro-glebas and smallholder possessions into PostGIS."""
    if not ITERPE_DIR.exists():
        logger.error(f"ITERPE directory not found at {ITERPE_DIR}")
        return

    engine = get_engine()

    # 1. Macro Glebas and Quilombos
    gleba_files = [
        ("gleba_arcoverde.kml", "Gleba Arcoverde", "Arcoverde", "Gleba Estadual Arrecadada"),
        ("gleba_calcado_angelim_04_finalizada.kml", "Gleba Calçado / Angelim 04", "Calçado", "Gleba Estadual Arrecadada"),
        ("gleba_saojoao_01_finalizada.kml", "Gleba São João 01 (Aroeira)", "São João", "Gleba Estadual Arrecadada"),
        ("gleba_saojoao_03_finalizada.kml", "Gleba São João 03 (Taquari)", "São João", "Gleba Estadual Arrecadada"),
        ("gleba_triunfo_finalizada.kml", "Gleba Triunfo", "Triunfo", "Gleba Estadual Arrecadada"),
        ("gleba_petrolandia_registro_749.kml", "Gleba Petrolândia (Registro 749)", "Petrolândia", "Gleba Estadual Arrecadada"),
        ("gleba_petrolandia_32294_2008.kml", "Gleba Petrolândia II (Dec. 32.294/08)", "Petrolândia", "Gleba Estadual Arrecadada"),
        ("ame_garanhuns_q_castainho.kml", "Território Quilombola Castainho", "Garanhuns", "Território Quilombola Estadual"),
        ("sit_itacuruba_q_negros_de_gilu.kml", "Território Quilombola Negros de Gilu", "Itacuruba", "Território Quilombola Estadual")
    ]

    macro_records = []
    for fname, name, muni, tipo in gleba_files:
        fpath = ITERPE_DIR / fname
        if not fpath.exists():
            continue
        try:
            gdf = gpd.read_file(fpath)
            for _, row in gdf.iterrows():
                r_geom = row.geometry
                # Fix ITERPE source error in gleba_saojoao_03_finalizada.kml:
                # The file published by ITERPE accidentally bundled a 177-polygon triangulated CAD grid of SERTAO_ARARIPE
                # with the true Gleba Taquari in São João (Agreste Meridional).
                # We isolate the genuine Gleba Taquari in São João (lon >= -38.0) and discard the spurious mesh.
                if fname == "gleba_saojoao_03_finalizada.kml" and hasattr(r_geom, "geoms"):
                    real_parts = [p for p in r_geom.geoms if p.bounds[2] >= -38.0]
                    if real_parts:
                        r_geom = MultiPolygon(real_parts) if len(real_parts) > 1 else real_parts[0]
                    else:
                        continue
                geom = ensure_multipolygon(r_geom)
                if geom:
                    macro_records.append({
                        "nome": name,
                        "municipio": muni,
                        "tipo": tipo,
                        "origem": "ITERPE - Gerência de Ações Fundiárias (GERAF)",
                        "arquivo_fonte": fname,
                        "geometry": geom
                    })
        except Exception as e:
            logger.error(f"Error reading {fname}: {e}")

    if macro_records:
        gdf_macro = gpd.GeoDataFrame(macro_records, crs="EPSG:4326")
        logger.info(f"Loaded {len(gdf_macro)} ITERPE macro-glebas. Writing to 'iterpe_glebas_pe'...")
        gdf_macro.to_postgis("iterpe_glebas_pe", engine, if_exists="replace", index=False)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE iterpe_glebas_pe ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;"))
            conn.execute(text("""
                ALTER TABLE iterpe_glebas_pe ADD COLUMN IF NOT EXISTS area_ha NUMERIC;
                UPDATE iterpe_glebas_pe SET area_ha = ROUND((ST_Area(geometry::geography) / 10000.0)::numeric, 2);
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_iterpe_glebas_pe_geom ON iterpe_glebas_pe USING GIST (geometry);"))
            conn.commit()
            cnt = conn.execute(text("SELECT COUNT(*) FROM iterpe_glebas_pe;")).scalar()
            logger.info(f"Table 'iterpe_glebas_pe' ready with {cnt} rows and spatial GIST index.")

    # 2. Malha de Posses (Family Farming Parcels)
    posses_files = [
        ("malha_posses_carnaiba.kml", "Carnaíba"),
        ("malha_posses_itapetim.kml", "Itapetim"),
        ("malha_posses_camocimdesaofelix.kml", "Camocim de São Félix")
    ]

    posses_records = []
    for fname, default_muni in posses_files:
        fpath = ITERPE_DIR / fname
        if not fpath.exists():
            continue
        logger.info(f"Reading possession parcels from {fname}...")
        try:
            gdf = gpd.read_file(fpath)
            for _, row in gdf.iterrows():
                geom = ensure_multipolygon(row.geometry)
                if not geom:
                    continue
                
                num_lote = str(row.get("NUM_LOTE") or "").strip()
                comarca = str(row.get("COMARCA") or default_muni).strip()
                decreto = str(row.get("DECRETO") or "").strip()
                matricula = str(row.get("MATRICULA") or "").strip()
                livro = str(row.get("LIVRO") or "").strip()
                folha = str(row.get("FOLHA") or "").strip()
                registro = str(row.get("REGISTRO") or "").strip()
                muni_ibge = str(row.get("CD_MUN") or "").strip()

                posses_records.append({
                    "num_lote": num_lote,
                    "comarca": comarca,
                    "municipio": default_muni,
                    "municipio_ibge": int(muni_ibge) if muni_ibge.isdigit() else None,
                    "decreto": decreto,
                    "matricula": matricula,
                    "livro": livro,
                    "folha": folha,
                    "registro": registro,
                    "tipo": "Posse Rural / Agricultura Familiar",
                    "origem": "ITERPE - Malha de Posses de Terras Devolutas",
                    "geometry": geom
                })
        except Exception as e:
            logger.error(f"Error processing {fname}: {e}")

    if posses_records:
        gdf_posses = gpd.GeoDataFrame(posses_records, crs="EPSG:4326")
        logger.info(f"Loaded {len(gdf_posses)} ITERPE smallholder parcels. Writing to 'iterpe_malha_posses_pe'...")
        gdf_posses.to_postgis("iterpe_malha_posses_pe", engine, if_exists="replace", index=False)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE iterpe_malha_posses_pe ADD COLUMN IF NOT EXISTS id SERIAL PRIMARY KEY;"))
            conn.execute(text("""
                ALTER TABLE iterpe_malha_posses_pe ADD COLUMN IF NOT EXISTS area_ha NUMERIC;
                UPDATE iterpe_malha_posses_pe SET area_ha = ROUND((ST_Area(geometry::geography) / 10000.0)::numeric, 2);
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_iterpe_posses_geom ON iterpe_malha_posses_pe USING GIST (geometry);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_iterpe_posses_muni ON iterpe_malha_posses_pe (municipio);"))
            conn.commit()
            cnt = conn.execute(text("SELECT COUNT(*) FROM iterpe_malha_posses_pe;")).scalar()
            logger.info(f"Table 'iterpe_malha_posses_pe' ready with {cnt} rows and spatial GIST index.")


if __name__ == "__main__":
    logger.info("Starting Moradia Legal and ITERPE ETL Pipeline...")
    ingest_moradia_legal()
    ingest_iterpe()
    logger.info("ETL Pipeline completed successfully!")
