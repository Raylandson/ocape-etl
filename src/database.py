import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from src.config import DATABASE_URL

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def get_engine():
    """Create and return the SQLAlchemy engine."""
    return create_engine(DATABASE_URL)

def init_postgis():
    """Ensure that the database is accessible and the PostGIS extension is enabled."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            # Check connection
            conn.execute(text("SELECT 1;"))
            logger.info("Database connection established successfully.")

            # Enable PostGIS extension if it doesn't exist
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
            logger.info("Extension 'postgis' verified/created successfully.")
    except SQLAlchemyError as e:
        logger.error(f"Error initializing database or PostGIS extension: {e}")
        raise
