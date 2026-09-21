"""
Unified ETL Pipeline Runner: Orchestrates and executes all data ingestion,
enrichment, and spatial processing pipelines with a single command.
"""

import sys
import time
import logging
import argparse
import subprocess
from pathlib import Path
from typing import List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def run_pipeline_step(name: str, func, *args, **kwargs) -> Tuple[str, bool, float]:
    """Executes a pipeline step and measures execution time."""
    logger.info("=" * 75)
    logger.info(f"STARTING STEP: {name}")
    logger.info("=" * 75)
    start_time = time.time()
    success = False
    try:
        func(*args, **kwargs)
        success = True
    except Exception as e:
        logger.error(f"Error during step '{name}': {e}", exc_info=True)
    elapsed = time.time() - start_time
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"COMPLETED STEP: {name} [{status}] in {elapsed:.2f}s\n")
    return name, success, elapsed


def restart_martin():
    """Restarts the Martin vector tile server container."""
    logger.info("Restarting Martin vector tile server (docker compose restart martin)...")
    try:
        res = subprocess.run(
            ["docker", "compose", "restart", "martin"],
            cwd=BASE_DIR,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Martin restarted successfully.")
        logger.info(res.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not restart Martin container: {e}. Please run 'docker compose restart martin' manually.")


def main():
    parser = argparse.ArgumentParser(
        description="Unified ETL Runner: Ingest all spatial, judicial, and community datasets into PostGIS."
    )
    parser.add_argument(
        "--skip-unpack",
        action="store_true",
        help="Skip unpacking data/raw/ archives into data/extracted/."
    )
    parser.add_argument(
        "--force-unpack",
        action="store_true",
        help="Force re-extraction of all archives even if target directory exists."
    )
    parser.add_argument(
        "--step",
        choices=["unpack", "etl", "jurisdicoes", "datajud", "sigef_historico", "moradia_iterpe", "despejo_zero"],
        help="Run only a specific pipeline step."
    )
    parser.add_argument(
        "--restart-martin",
        action="store_true",
        default=True,
        help="Automatically restart Martin tile server container after ingestion (default: True)."
    )
    parser.add_argument(
        "--no-restart-martin",
        action="store_false",
        dest="restart_martin",
        help="Do not restart Martin tile server container."
    )

    args = parser.parse_args()

    overall_start = time.time()
    results: List[Tuple[str, bool, float]] = []

    print("\n" + "=" * 75)
    print("LAND CONFLICT MAPPING PLATFORM — UNIFIED PIPELINE RUNNER")
    print("=" * 75 + "\n")

    # Step 0: Unpack raw data archives
    if not args.skip_unpack and (not args.step or args.step == "unpack"):
        from src.unpack_raw import unpack_all
        results.append(run_pipeline_step("0. Unpack Raw Archives", unpack_all, force=args.force_unpack))

    # Step 1: Ingest Shapefiles & Calculate Overlaps
    if not args.step or args.step == "etl":
        from src.etl import run_etl
        results.append(run_pipeline_step("1. Shapefiles & Spatial Overlaps", run_etl))

    # Step 2: Territorial Jurisdictions (TJPE & JFPE)
    if not args.step or args.step == "jurisdicoes":
        from src.process_jurisdicoes import main as run_jurisdicoes
        results.append(run_pipeline_step("2. Territorial Jurisdictions (TJPE & JFPE)", run_jurisdicoes))

    # Step 3: Judicial Conflict Lawsuits (DataJud CNJ)
    if not args.step or args.step == "datajud":
        from src.etl_datajud import run as run_datajud
        results.append(run_pipeline_step("3. Judicial Conflicts (DataJud CNJ)", run_datajud))

    # Step 4: SIGEF Historical Retifications & CAR Analyzed Cases (Batateiras)
    if not args.step or args.step == "sigef_historico":
        from src.import_sigef_historico import main as run_sigef_historico
        results.append(run_pipeline_step("4. SIGEF Historical Retifications & CAR Cases", run_sigef_historico))

    # Step 5: Moradia Legal (TJPE) & Acervo Fundiário (ITERPE)
    if not args.step or args.step == "moradia_iterpe":
        from src.etl_moradia_iterpe import ingest_moradia_legal, ingest_iterpe
        def run_moradia_iterpe():
            ingest_moradia_legal()
            ingest_iterpe()
        results.append(run_pipeline_step("5. Moradia Legal & ITERPE Acervo", run_moradia_iterpe))

    # Step 6: Campanha Nacional Despejo Zero
    if not args.step or args.step == "despejo_zero":
        from src.etl_despejo_zero import ingest_despejo_zero
        results.append(run_pipeline_step("6. Campanha Despejo Zero", ingest_despejo_zero))

    # Step 7: Restart Martin Vector Tile Server
    if args.restart_martin and not args.step:
        restart_martin()

    overall_elapsed = time.time() - overall_start

    # Execution Summary
    print("\n" + "=" * 75)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 75)
    print(f"{'Step Name':45s} | {'Status':>10s} | {'Time (s)':>10s}")
    print("-" * 75)
    all_success = True
    for name, success, elapsed in results:
        status = "SUCCESS" if success else "FAILED"
        if not success:
            all_success = False
        print(f"{name:45s} | {status:>10s} | {elapsed:>9.2f}s")
    print("-" * 75)
    print(f"Total Pipeline Runtime: {overall_elapsed:.2f} seconds")
    print(f"Overall Result: {'ALL STEPS SUCCEEDED' if all_success else 'SOME STEPS FAILED'}")
    print("=" * 75 + "\n")

    if not all_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
