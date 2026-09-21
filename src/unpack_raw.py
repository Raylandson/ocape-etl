"""
Automated Unpacker: Decompresses and prepares raw source archives from data/raw/
into data/extracted/ for ETL ingestion.
"""

import os
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Dict, Optional

from src.config import RAW_DATA_DIR, EXTRACTED_DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Explicit mapping of raw file patterns to target directory names under data/extracted/
RAW_ARCHIVE_MAPPING: Dict[str, str] = {
    # SICAR / CAR layers
    "APP_SICAR.zip": "apps_sicar",
    "AREA_IMOVEL_SICAR.zip": "area_imovel_sicar",
    "RESERVA_LEGAL_SICAR.zip": "reserva_legal_sicar",
    "VEGETACAO_NATIVA_SICAR.zip": "vegetacao_nativa_sicar",
    
    # Traditional lands (FUNAI & INCRA)
    "Áreas de Quilombolas_PE.zip": "areas_de_quilombolas_pe",
    "tis_poligonais.zip": "tis_poligonais",
    
    # INCRA certified properties (SNCI)
    "Imóvel certificado SNCI Brasil_PE.zip": "imovel_certificado_snci_brasil_pe",
    "Imóvel certificado SNCI Privado_PE.zip": "imovel_certificado_snci_privado_pe",
    "Imóvel certificado SNCI Público_PE.zip": "imovel_certificado_snci_publico_pe",
    
    # INCRA SIGEF
    "Sigef Brasil_PE.zip": "sigef_brasil_pe",
    "Sigef Privado_PE.zip": "sigef_privado_pe",
    "Sigef Público_PE.zip": "sigef_publico_pe",
    
    # ICMBio Environmental Layers
    "autos_infracao_icmbio.zip": "autos_infracao_icmbio",
    "embargos_icmbio.zip": "embargos_icmbio",
    "limiteucsfederais_a_icmbio.zip": "limiteucsfederais_a",
    
    # MapBiomas Deforestation Alerts
    "mapbiomas_alerts_with_intersections2026_09.zip": "mapbiomas_alertas",
    "mapbiomas_car_with_alerts_and_intersections2026_09.zip": "mapbiomas_car_alertas",
    
    # Territorial & Census Layers
    "PE_setores_CD2022.zip": "pe_setores_cd2022",
    "PROCESSOS_MINERARIOS_PE.zip": "processos_minerarios_pe",
    "ibge_favelas_comunidades_pe.zip": "ibge_favelas_comunidades_pe",
    
    # State & Community Layers
    "iterpe_acervo_fundiario.zip": "iterpe_acervo_fundiario",
    "despejo_zero_pe.zip": "despejo_zero_pe",
}

# Standalone files that should be placed in dedicated extracted folders
STANDALONE_FILES: Dict[str, str] = {
    "assentamentos_incra_pe.geojson": "assentamentos_incra_pe",
    "ucs_estaduais_cprh_pe.geojson": "ucs_estaduais_cprh_pe",
}

# KMZ files to extract doc.kml from
KMZ_FILES: Dict[str, str] = {
    "moradia_legal_tjpe_2025.kmz": "moradia_legal_pe",
}


def unpack_zip(zip_path: Path, target_dir: Path, force: bool = False):
    """Safely extracts a ZIP archive into target directory, flattening any single top-level folder."""
    if target_dir.exists() and any(target_dir.iterdir()) and not force:
        logger.info(f"Skipping '{zip_path.name}': target '{target_dir.name}' already contains files.")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Extracting '{zip_path.name}' -> '{target_dir.name}/'...")

    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()
        # Check if all files are wrapped in a single root folder with the same name
        top_dirs = {m.filename.split("/")[0] for m in members if "/" in m.filename}
        single_wrapper = len(top_dirs) == 1 and all(m.filename.startswith(f"{list(top_dirs)[0]}/") for m in members if not m.is_dir())

        for member in members:
            if member.is_dir():
                continue
            
            # Determine destination path
            if single_wrapper:
                # Strip leading wrapper directory
                rel_parts = member.filename.split("/")[1:]
                dest_path = target_dir.joinpath(*rel_parts)
            else:
                dest_path = target_dir / Path(member.filename).name

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

    logger.info(f"Successfully extracted '{zip_path.name}'.")


def unpack_kmz(kmz_path: Path, target_dir: Path, force: bool = False):
    """Extracts doc.kml from a KMZ archive into target directory."""
    target_kml = target_dir / "doc.kml"
    if target_kml.exists() and not force:
        logger.info(f"Skipping '{kmz_path.name}': target '{target_kml.name}' already exists.")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Extracting KMZ '{kmz_path.name}' -> '{target_kml}'...")

    with zipfile.ZipFile(kmz_path, "r") as zf:
        # Search for doc.kml or any .kml
        kml_members = [m for m in zf.infolist() if m.filename.lower().endswith(".kml")]
        if not kml_members:
            logger.warning(f"No .kml file found inside KMZ '{kmz_path.name}'.")
            return
        
        # Prefer doc.kml, otherwise take the first .kml
        doc_member = next((m for m in kml_members if m.filename.lower() == "doc.kml"), kml_members[0])
        with zf.open(doc_member) as src, open(target_kml, "wb") as dst:
            shutil.copyfileobj(src, dst)

    logger.info(f"Successfully extracted '{target_kml.name}' from '{kmz_path.name}'.")


def copy_standalone(file_path: Path, target_dir: Path, force: bool = False):
    """Copies a standalone data file into its target folder in data/extracted/."""
    target_file = target_dir / file_path.name
    if target_file.exists() and not force:
        logger.info(f"Skipping '{file_path.name}': target already exists.")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Copying '{file_path.name}' -> '{target_dir.name}/'...")
    shutil.copy2(file_path, target_file)
    logger.info(f"Successfully copied '{file_path.name}'.")


def unpack_all(force: bool = False):
    """Unpacks all available raw archives and files from data/raw/ into data/extracted/."""
    if not RAW_DATA_DIR.exists():
        logger.error(f"Raw data directory does not exist: {RAW_DATA_DIR}")
        return

    EXTRACTED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Starting raw data unpacking from '{RAW_DATA_DIR}' into '{EXTRACTED_DATA_DIR}'...")

    # 1. Unpack ZIP archives
    for archive_name, target_subdir in RAW_ARCHIVE_MAPPING.items():
        archive_path = RAW_DATA_DIR / archive_name
        if archive_path.exists():
            target_dir = EXTRACTED_DATA_DIR / target_subdir
            unpack_zip(archive_path, target_dir, force=force)
        else:
            logger.debug(f"Archive not found in data/raw/: '{archive_name}' (optional/not downloaded).")

    # 2. Unpack KMZ files
    for kmz_name, target_subdir in KMZ_FILES.items():
        kmz_path = RAW_DATA_DIR / kmz_name
        if kmz_path.exists():
            target_dir = EXTRACTED_DATA_DIR / target_subdir
            unpack_kmz(kmz_path, target_dir, force=force)

    # 3. Copy standalone files
    for file_name, target_subdir in STANDALONE_FILES.items():
        file_path = RAW_DATA_DIR / file_name
        if file_path.exists():
            target_dir = EXTRACTED_DATA_DIR / target_subdir
            copy_standalone(file_path, target_dir, force=force)

    logger.info("Unpacking completed.")


if __name__ == "__main__":
    import sys
    force_flag = "--force" in sys.argv
    unpack_all(force=force_flag)
