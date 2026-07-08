import logging
from sqlalchemy import text
from src.database import get_engine

logger = logging.getLogger(__name__)

def calculate_overlaps():
    """Calculate spatial intersections between all certified properties and traditional territories."""
    engine = get_engine()
    
    query_create = """
    DROP TABLE IF EXISTS public.land_overlaps;
    
    CREATE TABLE public.land_overlaps AS
    WITH raw_overlaps AS (
        -- 1. SIGEF Brasil (Public + Private) overlapping with FUNAI Indigenous Lands
        SELECT
            p.nome_area AS property_name,
            p.codigo_imo AS property_code,
            'sigef_brasil_pe'::varchar(50) AS property_source,
            t.terrai_nom AS traditional_name,
            'tis_poligonais'::varchar(50) AS traditional_source,
            ST_Force2D(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geometry, t.geometry), 3)))::geometry(MultiPolygon, 4326) AS geometry
        FROM sigef_brasil_pe p
        JOIN tis_poligonais t ON ST_Intersects(p.geometry, t.geometry)
        WHERE ST_Dimension(ST_Intersection(p.geometry, t.geometry)) = 2

        UNION ALL

        -- 2. SIGEF Brasil (Public + Private) overlapping with Quilombolas
        SELECT
            p.nome_area AS property_name,
            p.codigo_imo AS property_code,
            'sigef_brasil_pe'::varchar(50) AS property_source,
            q.nm_comunid AS traditional_name,
            'areas_de_quilombolas_pe'::varchar(50) AS traditional_source,
            ST_Force2D(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geometry, q.geometry), 3)))::geometry(MultiPolygon, 4326) AS geometry
        FROM sigef_brasil_pe p
        JOIN areas_de_quilombolas_pe q ON ST_Intersects(p.geometry, q.geometry)
        WHERE ST_Dimension(ST_Intersection(p.geometry, q.geometry)) = 2

        UNION ALL

        -- 3. SNCI Brasil (Public + Private) overlapping with FUNAI Indigenous Lands
        SELECT
            p.nome_imove AS property_name,
            p.cod_imovel AS property_code,
            'imovel_certificado_snci_brasil_pe'::varchar(50) AS property_source,
            t.terrai_nom AS traditional_name,
            'tis_poligonais'::varchar(50) AS traditional_source,
            ST_Force2D(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geometry, t.geometry), 3)))::geometry(MultiPolygon, 4326) AS geometry
        FROM imovel_certificado_snci_brasil_pe p
        JOIN tis_poligonais t ON ST_Intersects(p.geometry, t.geometry)
        WHERE ST_Dimension(ST_Intersection(p.geometry, t.geometry)) = 2

        UNION ALL

        -- 4. SNCI Brasil (Public + Private) overlapping with Quilombolas
        SELECT
            p.nome_imove AS property_name,
            p.cod_imovel AS property_code,
            'imovel_certificado_snci_brasil_pe'::varchar(50) AS property_source,
            q.nm_comunid AS traditional_name,
            'areas_de_quilombolas_pe'::varchar(50) AS traditional_source,
            ST_Force2D(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geometry, q.geometry), 3)))::geometry(MultiPolygon, 4326) AS geometry
        FROM imovel_certificado_snci_brasil_pe p
        JOIN areas_de_quilombolas_pe q ON ST_Intersects(p.geometry, q.geometry)
        WHERE ST_Dimension(ST_Intersection(p.geometry, q.geometry)) = 2
    )
    SELECT 
        row_number() OVER ()::integer AS id,
        *
    FROM raw_overlaps;
    
    CREATE INDEX IF NOT EXISTS sidx_land_overlaps_geometry ON public.land_overlaps USING gist(geometry);
    """
    
    logger.info("Calculating spatial overlaps between all properties (SIGEF/SNCI) and traditional territories...")
    with engine.begin() as conn:
        conn.execute(text(query_create))
        
        # Verify row count
        res = conn.execute(text("SELECT COUNT(*) FROM public.land_overlaps;"))
        count = res.scalar()
        logger.info(f"Overlaps calculation completed: found {count} overlapping polygons.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    calculate_overlaps()
