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
    ),
    clustered_raw AS (
        SELECT
            *,
            ST_ClusterDBSCAN(geometry, eps := 0.0001, minpoints := 1) OVER(PARTITION BY traditional_name) AS cluster_id
        FROM raw_overlaps
    ),
    grouped_overlaps AS (
        SELECT
            traditional_name,
            traditional_source,
            string_agg(DISTINCT NULLIF(TRIM(property_name), ''), '; ') AS property_name,
            string_agg(DISTINCT NULLIF(TRIM(property_code), ''), '; ') AS property_code,
            string_agg(DISTINCT NULLIF(TRIM(property_source), ''), '; ') AS property_source,
            ST_Union(geometry) AS geometry
        FROM clustered_raw
        GROUP BY traditional_name, traditional_source, cluster_id
    )
    SELECT 
        row_number() OVER ()::integer AS id,
        COALESCE(property_name, 'N/A') AS property_name,
        COALESCE(property_code, 'N/A') AS property_code,
        COALESCE(property_source, 'N/A') AS property_source,
        traditional_name,
        traditional_source,
        ST_Force2D(ST_Multi(geometry))::geometry(MultiPolygon, 4326) AS geometry
    FROM grouped_overlaps;
    
    CREATE INDEX IF NOT EXISTS sidx_land_overlaps_geometry ON public.land_overlaps USING gist(geometry);

    -- Calculate the center points of the overlapping regions
    DROP TABLE IF EXISTS public.land_overlaps_points;

    CREATE TABLE public.land_overlaps_points AS
    SELECT
        id,
        property_name,
        property_code,
        property_source,
        traditional_name,
        traditional_source,
        ST_PointOnSurface(geometry)::geometry(Point, 4326) AS geometry
    FROM public.land_overlaps;

    CREATE INDEX IF NOT EXISTS sidx_land_overlaps_points_geometry ON public.land_overlaps_points USING gist(geometry);
    """
    
    logger.info("Calculating spatial overlaps between all properties (SIGEF/SNCI) and traditional territories...")
    with engine.begin() as conn:
        conn.execute(text(query_create))
        
        # Verify row count
        res = conn.execute(text("SELECT COUNT(*) FROM public.land_overlaps;"))
        count = res.scalar()
        res_pts = conn.execute(text("SELECT COUNT(*) FROM public.land_overlaps_points;"))
        count_pts = res_pts.scalar()
        logger.info(f"Overlaps calculation completed: found {count} overlapping polygons and calculated {count_pts} center points.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    calculate_overlaps()
