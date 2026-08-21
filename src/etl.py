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

    # Find all .shp files in the extracted data directory recursively
    shp_files = list(EXTRACTED_DATA_DIR.glob("**/*.shp"))
    if not shp_files:
        logger.warning(f"No .shp files found in directory: {EXTRACTED_DATA_DIR}")
        return

    logger.info(f"Found {len(shp_files)} shapefile(s) to process.")

    import sys
    force = "--force" in sys.argv

    for shp_path in shp_files:
        filename = shp_path.stem
        table_name = sanitize_name(filename)

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

            # 3. Standardize column names
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

            # 4. Spatial transformation to EPSG:4326 (WGS84)
            if gdf.crs is None:
                logger.warning(f"Warning: GeoDataFrame for '{filename}' has no CRS defined. Setting to EPSG:4326 by default.")
                gdf.set_crs("EPSG:4326", inplace=True)
            else:
                logger.info(f"Transforming CRS from {gdf.crs.to_string()} to EPSG:4326...")
                gdf = gdf.to_crs(epsg=4326)

            # 5. Save to PostGIS (which automatically creates the spatial index GIST)
            logger.info(f"Writing to database table '{table_name}'...")
            gdf.to_postgis(
                name=table_name,
                con=engine,
                if_exists='replace',
                index=False
            )
            
            # 6. Verify row count and ensure GIST index
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

