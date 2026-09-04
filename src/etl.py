import logging
import re
import unicodedata
from pathlib import Path
import geopandas as gpd
from sqlalchemy import text
from src.config import EXTRACTED_DATA_DIR
from src.database import get_engine, init_postgis

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def sanitize_name(name: str) -> str:
    """
    Sanitize a string to be SQL-safe:
    - Convert to lowercase
    - Normalize unicode (remove accents)
    - Replace spaces and hyphens with underscores
    - Remove all other non-alphanumeric characters (except underscores)
    - Remove consecutive underscores
    """
    # Normalize to decompose accents (NFKD)
    normalized = unicodedata.normalize('NFKD', name)
    # Encode as ASCII and decode to strip accents
    ascii_str = normalized.encode('ASCII', 'ignore').decode('utf-8')
    # Lowercase and strip whitespace
    s = ascii_str.lower().strip()
    # Replace spaces and hyphens with underscores
    s = re.sub(r'[\s\-]+', '_', s)
    # Remove any character that is not lowercase, digit, or underscore
    s = re.sub(r'[^a-z0-9_]', '', s)
    # Deduplicate underscores
    s = re.sub(r'_+', '_', s)
    return s.strip('_')

import shapely.ops

def sanitize_and_fix_geometries(gdf: gpd.GeoDataFrame, filename: str) -> gpd.GeoDataFrame:
    """
    1. Filter out empty, null, or extreme non-finite sentinel coordinates.
    2. Detect inverted coordinates (Lat, Lon instead of Lon, Lat) and swap them.
    """
    # Filter empty or null geometries
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()

    # Filter out extreme sentinel values (like -1.79e+308 in some GIS point exports)
    def is_finite_geom(geom):
        try:
            b = geom.bounds
            return all(abs(v) < 100000 for v in b)
        except Exception:
            return False

    finite_mask = gdf.geometry.apply(is_finite_geom)
    removed_count = len(gdf) - finite_mask.sum()
    if removed_count > 0:
        logger.warning(f"Removed {removed_count} non-finite/sentinel geometries from '{filename}'.")
    gdf = gdf[finite_mask].copy()

    if gdf.empty:
        return gdf

    # Detect inverted coordinates:
    # In Brazil: Longitude (X) is in [-75, -30], Latitude (Y) is in [-35, 6].
    # If miny < -35 and minx > -35 (meaning X has latitudes and Y has longitudes), swap (y, x).
    minx, miny, maxx, maxy = gdf.total_bounds
    if miny < -35.0 and minx > -35.0:
        logger.info(
            f"Detected inverted coordinate axis (Lat, Lon) in '{filename}' "
            f"(bounds: [{minx:.2f}, {miny:.2f}, {maxx:.2f}, {maxy:.2f}]). "
            f"Swapping coordinates to standard (Lon, Lat)..."
        )
        gdf.geometry = gdf.geometry.apply(lambda g: shapely.ops.transform(lambda x, y, *z: (y, x), g))
        new_minx, new_miny, new_maxx, new_maxy = gdf.total_bounds
        logger.info(f"Coordinates swapped successfully. New bounds: [{new_minx:.2f}, {new_miny:.2f}, {new_maxx:.2f}, {new_maxy:.2f}]")

    return gdf

def load_pe_boundary():
    """Load the official IBGE Pernambuco state boundary geometry."""
    pe_boundary_path = Path(__file__).parent / "pe_boundary.geojson"
    if pe_boundary_path.exists():
        pe_gdf = gpd.read_file(pe_boundary_path)
        return pe_gdf.geometry.union_all()
    logger.warning("Pernambuco boundary file 'pe_boundary.geojson' not found. Spatial boundary filter will be disabled.")
    return None

def is_in_pe_territory(geom) -> bool:
    """Check if geometry bounding box falls within Pernambuco mainland or Fernando de Noronha envelope."""
    try:
        b = geom.bounds
        in_mainland = (-41.60 <= b[0] <= -34.70) and (-9.60 <= b[1] <= -7.20)
        in_noronha = (-32.60 <= b[0] <= -32.30) and (-4.00 <= b[1] <= -3.70)
        return in_mainland or in_noronha
    except Exception:
        return False

def filter_to_pernambuco(gdf: gpd.GeoDataFrame, filename: str, pe_geom) -> gpd.GeoDataFrame:
    """
    Filter datasets to include only features within or relevant to the State of Pernambuco.
    - For limiteucsfederais_a: retain UCs that physically intersect Pernambuco.
    - For embargos_icmbio: retain embargos inside PE (intersecting PE geometry or PE attribute within PE bounds).
    - For autos_infracao_icmbio: retain infraction notices inside PE state territory or Fernando de Noronha.
    """
    if gdf.empty:
        return gdf

    initial_count = len(gdf)

    if filename == "limiteucsfederais_a":
        if pe_geom is not None:
            mask = gdf.intersects(pe_geom)
            gdf = gdf[mask].copy()
            logger.info(f"Filtered 'limiteucsfederais_a' from {initial_count} to {len(gdf)} Conservation Units in Pernambuco.")
        return gdf

    elif filename == "embargos_icmbio":
        mask_geom = gdf.intersects(pe_geom) if pe_geom is not None else False
        mask_uf = (gdf["uf"].astype(str).str.upper().str.strip() == "PE") & gdf.geometry.apply(is_in_pe_territory) if "uf" in gdf.columns else False
        mask = mask_geom | mask_uf
        gdf = gdf[mask].copy()
        logger.info(f"Filtered 'embargos_icmbio' from {initial_count} to {len(gdf)} embargo polygons in Pernambuco.")
        return gdf

    elif filename == "autos_infracao_icmbio":
        mask_geom = gdf.intersects(pe_geom) if pe_geom is not None else False
        mask_uf = (gdf["uf"].astype(str).str.upper().str.strip() == "PE") & gdf.geometry.apply(is_in_pe_territory) if "uf" in gdf.columns else False
        mask = mask_geom | mask_uf
        gdf = gdf[mask].copy()
        logger.info(f"Filtered 'autos_infracao_icmbio' from {initial_count} to {len(gdf)} infraction notices in Pernambuco.")
        return gdf

    elif filename == "alerts_with_intersections":
        # Fast filter by STATE attribute and spatial boundary
        mask_state = gdf["STATE"].astype(str).str.upper().str.contains("PERNAMBUCO", na=False) if "STATE" in gdf.columns else True
        gdf = gdf[mask_state].copy()
        if pe_geom is not None and not gdf.empty:
            gdf = gdf[gdf.intersects(pe_geom)].copy()
        logger.info(f"Filtered 'alerts_with_intersections' from {initial_count} to {len(gdf)} MapBiomas alerts in Pernambuco.")
        return gdf

    elif filename == "car_with_alerts_and_intersections":
        # Fast filter by CODSICAR prefix 'PE-' or STATE attribute and spatial boundary
        mask_cod = gdf["CODSICAR"].astype(str).str.startswith("PE-") if "CODSICAR" in gdf.columns else False
        mask_state = gdf["STATE"].astype(str).str.upper().str.contains("PERNAMBUCO", na=False) if "STATE" in gdf.columns else False
        gdf = gdf[mask_cod | mask_state].copy()
        if pe_geom is not None and not gdf.empty:
            gdf = gdf[gdf.intersects(pe_geom)].copy()
        logger.info(f"Filtered 'car_with_alerts_and_intersections' from {initial_count} to {len(gdf)} CAR properties with alerts in Pernambuco.")
        return gdf

    return gdf

def run_etl():
    """Main ETL process."""
    # Ensure database is up and PostGIS is enabled
    logger.info("Initializing database extension...")
    try:
        init_postgis()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    engine = get_engine()
    pe_geom = load_pe_boundary()

    # Find all .shp files in the extracted data directory recursively
    shp_files = list(EXTRACTED_DATA_DIR.glob("**/*.shp"))
    if not shp_files:
        logger.warning(f"No .shp files found in directory: {EXTRACTED_DATA_DIR}")
        return

    logger.info(f"Found {len(shp_files)} shapefile(s) to process.")

    import sys
    force = "--force" in sys.argv
    table_filter = None
    for arg in sys.argv[1:]:
        if arg.startswith("--table="):
            table_filter = arg.split("=")[1].lower()
        elif arg.startswith("--only-icmbio"):
            table_filter = "icmbio"

    for shp_path in shp_files:
        filename = shp_path.stem
        table_name = sanitize_name(filename)

        if table_filter:
            if table_filter == "icmbio" and not any(k in table_name for k in ["icmbio", "limiteucsfederais"]):
                continue
            elif table_filter != "icmbio" and table_name != table_filter:
                continue

        if not force:
            with engine.connect() as conn:
                table_exists = conn.execute(text(
                    f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '{table_name}');"
                )).scalar()
                if table_exists:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name};")).scalar()
                    if count > 0:
                        logger.info(f"Table '{table_name}' already exists with {count} rows. Skipping (use --force to reload).")
                        continue

        logger.info(f"Processing '{filename}' -> target table '{table_name}'")

        try:
            # 1. Load GeoDataFrame directly from the extracted shapefile
            logger.info(f"Reading file from {shp_path.resolve()}...")
            gdf = gpd.read_file(shp_path)
            
            if gdf.empty:
                logger.warning(f"File '{filename}' contains no data. Skipping.")
                continue

            logger.info(f"Loaded {len(gdf)} features.")

            # 2. Sanitize and fix geometries (remove sentinels and fix inverted axes)
            gdf = sanitize_and_fix_geometries(gdf, filename)
            if gdf.empty:
                logger.warning(f"File '{filename}' has no valid features after geometry cleaning. Skipping.")
                continue

            # 3. Filter to Pernambuco State territory
            gdf = filter_to_pernambuco(gdf, filename, pe_geom)
            if gdf.empty:
                logger.warning(f"File '{filename}' has no features located within Pernambuco. Skipping.")
                continue

            # 4. Standardize column names
            logger.info("Standardizing column names...")
            original_columns = gdf.columns.tolist()
            new_columns = {}
            for col in original_columns:
                if col == "geometry":
                    new_columns[col] = "geometry"
                else:
                    new_columns[col] = sanitize_name(col)
            
            gdf = gdf.rename(columns=new_columns)
            logger.info(f"Columns renamed to: {list(gdf.columns)}")

            # 5. Spatial transformation to EPSG:4326 (WGS84)
            if gdf.crs is None:
                logger.warning(f"Warning: GeoDataFrame for '{filename}' has no CRS defined. Setting to EPSG:4326 by default.")
                gdf.set_crs("EPSG:4326", inplace=True)
            else:
                logger.info(f"Transforming CRS from {gdf.crs.to_string()} to EPSG:4326...")
                gdf = gdf.to_crs(epsg=4326)

            # 6. Save to PostGIS (which automatically creates the spatial index GIST)
            logger.info(f"Writing to database table '{table_name}'...")
            gdf.to_postgis(
                name=table_name,
                con=engine,
                if_exists='replace',
                index=False
            )
            
            # 7. Verify row count and ensure GIST index
            with engine.connect() as conn:
                res = conn.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
                count = res.scalar()
                logger.info(f"Successfully loaded {count} rows into '{table_name}' and verified spatial index GIST.")

        except Exception as e:
            logger.error(f"Error processing file '{filename}': {e}", exc_info=True)

    # Calculate overlaps
    logger.info("Ingestion completed. Running overlaps calculation...")
    try:
        from src.overlaps import calculate_overlaps
        calculate_overlaps()
    except Exception as e:
        logger.error(f"Failed to calculate overlaps: {e}", exc_info=True)

if __name__ == "__main__":
    run_etl()


