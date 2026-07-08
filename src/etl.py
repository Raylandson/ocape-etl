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

    for shp_path in shp_files:
        filename = shp_path.stem
        table_name = sanitize_name(filename)
        logger.info(f"Processing '{filename}' -> target table '{table_name}'")

        try:
            # 1. Load GeoDataFrame directly from the extracted shapefile
            logger.info(f"Reading file from {shp_path.resolve()}...")
            gdf = gpd.read_file(shp_path)
            
            if gdf.empty:
                logger.warning(f"File '{filename}' contains no data. Skipping.")
                continue

            logger.info(f"Loaded {len(gdf)} features.")

            # 2. Standardize column names
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

            # 3. Spatial transformation to EPSG:4326 (WGS84)
            if gdf.crs is None:
                logger.warning(f"Warning: GeoDataFrame for '{filename}' has no CRS defined. Setting to EPSG:4326 by default.")
                gdf.set_crs("EPSG:4326", inplace=True)
            else:
                logger.info(f"Transforming CRS from {gdf.crs.to_string()} to EPSG:4326...")
                gdf = gdf.to_crs(epsg=4326)

            # 4. Save to PostGIS (which automatically creates the spatial index GIST)
            logger.info(f"Writing to database table '{table_name}'...")
            gdf.to_postgis(
                name=table_name,
                con=engine,
                if_exists='replace',
                index=False
            )
            
            # 5. Verify row count
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

