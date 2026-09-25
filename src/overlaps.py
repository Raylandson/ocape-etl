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

        UNION ALL

        -- 5. CAR/SICAR (area_imovel_1) overlapping with FUNAI Indigenous Lands
        SELECT
            ('Imóvel CAR (' || COALESCE(p.municipio, 'PE') || ')')::varchar(150) AS property_name,
            p.cod_imovel AS property_code,
            'area_imovel_1'::varchar(50) AS property_source,
            t.terrai_nom AS traditional_name,
            'tis_poligonais'::varchar(50) AS traditional_source,
            ST_Force2D(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geometry, t.geometry), 3)))::geometry(MultiPolygon, 4326) AS geometry
        FROM area_imovel_1 p
        JOIN tis_poligonais t ON ST_Intersects(p.geometry, t.geometry)
        WHERE ST_Dimension(ST_Intersection(p.geometry, t.geometry)) = 2

        UNION ALL

        -- 6. CAR/SICAR (area_imovel_1) overlapping with Quilombolas
        SELECT
            ('Imóvel CAR (' || COALESCE(p.municipio, 'PE') || ')')::varchar(150) AS property_name,
            p.cod_imovel AS property_code,
            'area_imovel_1'::varchar(50) AS property_source,
            q.nm_comunid AS traditional_name,
            'areas_de_quilombolas_pe'::varchar(50) AS traditional_source,
            ST_Force2D(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geometry, q.geometry), 3)))::geometry(MultiPolygon, 4326) AS geometry
        FROM area_imovel_1 p
        JOIN areas_de_quilombolas_pe q ON ST_Intersects(p.geometry, q.geometry)
        WHERE ST_Dimension(ST_Intersection(p.geometry, q.geometry)) = 2

        UNION ALL

        -- 7. SIGEF Brasil overlapping with ICMBio Federal Conservation Units
        SELECT
            p.nome_area AS property_name,
            p.codigo_imo AS property_code,
            'sigef_brasil_pe'::varchar(50) AS property_source,
            u.nomeuc AS traditional_name,
            'limiteucsfederais_a'::varchar(50) AS traditional_source,
            ST_Force2D(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geometry, u.geometry), 3)))::geometry(MultiPolygon, 4326) AS geometry
        FROM sigef_brasil_pe p
        JOIN limiteucsfederais_a u ON ST_Intersects(p.geometry, u.geometry)
        WHERE ST_Dimension(ST_Intersection(p.geometry, u.geometry)) = 2

        UNION ALL

        -- 8. SIGEF Brasil overlapping with ICMBio Embargo Areas
        SELECT
            p.nome_area AS property_name,
            p.codigo_imo AS property_code,
            'sigef_brasil_pe'::varchar(50) AS property_source,
            ('Embargo ' || COALESCE(e.numero_emb, 'S/N') || ' (' || COALESCE(e.autuado, 'N/D') || ')')::varchar(200) AS traditional_name,
            'embargos_icmbio'::varchar(50) AS traditional_source,
            ST_Force2D(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geometry, e.geometry), 3)))::geometry(MultiPolygon, 4326) AS geometry
        FROM sigef_brasil_pe p
        JOIN embargos_icmbio e ON ST_Intersects(p.geometry, e.geometry)
        WHERE ST_Dimension(ST_Intersection(p.geometry, e.geometry)) = 2

        UNION ALL

        -- 9. SNCI Brasil overlapping with ICMBio Federal Conservation Units
        SELECT
            p.nome_imove AS property_name,
            p.cod_imovel AS property_code,
            'imovel_certificado_snci_brasil_pe'::varchar(50) AS property_source,
            u.nomeuc AS traditional_name,
            'limiteucsfederais_a'::varchar(50) AS traditional_source,
            ST_Force2D(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geometry, u.geometry), 3)))::geometry(MultiPolygon, 4326) AS geometry
        FROM imovel_certificado_snci_brasil_pe p
        JOIN limiteucsfederais_a u ON ST_Intersects(p.geometry, u.geometry)
        WHERE ST_Dimension(ST_Intersection(p.geometry, u.geometry)) = 2

        UNION ALL

        -- 10. SNCI Brasil overlapping with ICMBio Embargo Areas
        SELECT
            p.nome_imove AS property_name,
            p.cod_imovel AS property_code,
            'imovel_certificado_snci_brasil_pe'::varchar(50) AS property_source,
            ('Embargo ' || COALESCE(e.numero_emb, 'S/N') || ' (' || COALESCE(e.autuado, 'N/D') || ')')::varchar(200) AS traditional_name,
            'embargos_icmbio'::varchar(50) AS traditional_source,
            ST_Force2D(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geometry, e.geometry), 3)))::geometry(MultiPolygon, 4326) AS geometry
        FROM imovel_certificado_snci_brasil_pe p
        JOIN embargos_icmbio e ON ST_Intersects(p.geometry, e.geometry)
        WHERE ST_Dimension(ST_Intersection(p.geometry, e.geometry)) = 2

        UNION ALL

        -- 11. CAR/SICAR (area_imovel_1) overlapping with ICMBio Embargo Areas
        SELECT
            ('Imóvel CAR (' || COALESCE(p.municipio, 'PE') || ')')::varchar(150) AS property_name,
            p.cod_imovel AS property_code,
            'area_imovel_1'::varchar(50) AS property_source,
            ('Embargo ' || COALESCE(e.numero_emb, 'S/N') || ' (' || COALESCE(e.autuado, 'N/D') || ')')::varchar(200) AS traditional_name,
            'embargos_icmbio'::varchar(50) AS traditional_source,
            ST_Force2D(ST_Multi(ST_CollectionExtract(ST_Intersection(p.geometry, e.geometry), 3)))::geometry(MultiPolygon, 4326) AS geometry
        FROM area_imovel_1 p
        JOIN embargos_icmbio e ON ST_Intersects(p.geometry, e.geometry)
        WHERE ST_Dimension(ST_Intersection(p.geometry, e.geometry)) = 2
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


# Energy footprints (ANEEL / SIGEL) crossed against community, traditional and protected territories.
# Each SELECT must return: energia_fonte, energia_id, energia_nome, energia_tipo, ato_legal, forma,
# largura_m, geometry.
ENERGY_FOOTPRINTS = {
    # One footprint per distinct DUP polygon: DUPs sharing a polygon (the same strip declared by more
    # than one REA) are merged with their acts listed together, so the area is not counted twice.
    # Records flagged with erro_origem (polygon copied from another project) are excluded.
    "aneel_dup_pe": """
        SELECT 'aneel_dup_pe'::varchar(50) AS energia_fonte, MIN(e.id) AS energia_id,
               string_agg(DISTINCT COALESCE(e.empreem, e.ato_legal), ' | ') AS energia_nome,
               string_agg(DISTINCT 'DUP — ' || COALESCE(e.modalidade, 'N/D') || ' — ' || COALESCE(e.objeto_text, 'N/D'), ' | ') AS energia_tipo,
               string_agg(DISTINCT e.ato_legal, ' | ') AS ato_legal,
               MAX(e.forma) AS forma, MAX(e.largura_m) AS largura_m,
               (array_agg(e.geometry))[1] AS geometry
        FROM aneel_dup_pe e
        WHERE e.erro_origem IS NULL
        GROUP BY e.grupo_geometria""",
    "aneel_eol_parques_pe": """
        SELECT 'aneel_eol_parques_pe'::varchar(50), e.id, e.nome_eol::text,
               'Parque Eólico (' || COALESCE(e.fase, 'N/D') || ')', NULL::text, 'area', NULL::numeric, e.geometry
        FROM aneel_eol_parques_pe e""",
    "aneel_ufv_parques_pe": """
        SELECT 'aneel_ufv_parques_pe'::varchar(50), e.id, e.nome::text,
               'Parque Solar (' || COALESCE(e.fase, 'N/D') || ')', NULL::text, 'area', NULL::numeric, e.geometry
        FROM aneel_ufv_parques_pe e""",
    "aneel_ufv_subestacoes_pe": """
        SELECT 'aneel_ufv_subestacoes_pe'::varchar(50), e.id, COALESCE(e.nome_se, e.nome_resp)::text,
               'Subestação de Usina Solar', NULL::text, 'area', NULL::numeric, e.geometry
        FROM aneel_ufv_subestacoes_pe e""",
    "aneel_hidro_reservatorios_pe": """
        SELECT 'aneel_hidro_reservatorios_pe'::varchar(50), e.id, e.usina::text,
               'Reservatório ' || COALESCE(e.tipo_ahe, 'AHE'), e.origem_res::text, 'area', NULL::numeric, e.geometry
        FROM aneel_hidro_reservatorios_pe e""",
}

# (table, name expression, territory type label)
TERRITORIES = [
    ("tis_poligonais", "t.terrai_nom", "Terra Indígena (FUNAI)"),
    ("areas_de_quilombolas_pe", "t.nm_comunid", "Território Quilombola (INCRA)"),
    ("assentamentos_incra_pe", "t.no_projeto || ' (' || COALESCE(t.cd_sipra, 's/ código') || ')'", "Assentamento (INCRA SIPRA)"),
    ("iterpe_glebas_pe", "t.nome", "Gleba Estadual (ITERPE)"),
    ("iterpe_malha_posses_pe", "'Lote ' || COALESCE(t.num_lote, 's/n') || ' — ' || COALESCE(t.municipio, 'PE')", "Posse Rural (ITERPE)"),
    ("limiteucsfederais_a", "t.nomeuc", "UC Federal (ICMBio)"),
    ("ucs_estaduais_cprh_pe", "t.nome_uc", "UC Estadual (CPRH)"),
]

# Sliver filter applied to each part of an intersection. Areal footprints (parks, reservoirs) drawn on
# different base maps than the territories produce shoreline/edge slivers; strips only lose noise.
SLIVER_MIN_AREA_M2 = 1000      # areal footprints: parts smaller than 0.1 ha are dropped...
SLIVER_MIN_WIDTH_M = 10        # ...as are parts narrower than 10 m
STRIP_MIN_AREA_M2 = 100        # strips (forma = 'faixa'): only parts under 100 m² are dropped


def calculate_energy_overlaps():
    """Intersects official ANEEL footprints (DUP servitudes/expropriations, wind and solar parks,
    reservoirs) with territories into `aneel_sobreposicoes_territorios_pe`. Tables that are not
    loaded yet are skipped, so this can run right after `src/etl_aneel.py`.

    For strip footprints (DUP line servitudes) the meaningful measure is the crossing length
    (`extensao_travessia_km` = overlap area / strip width), not the hectares."""
    engine = get_engine()
    with engine.begin() as conn:
        def exists(table: str) -> bool:
            return conn.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": f"public.{table}"}).scalar()

        energy = [sql for tbl, sql in ENERGY_FOOTPRINTS.items() if exists(tbl)]
        territories = [t for t in TERRITORIES if exists(t[0])]
        if not energy or not territories:
            logger.warning("Energy overlaps skipped: ANEEL footprints or territory layers are not loaded.")
            return

        energy_sql = "\n        UNION ALL\n".join(energy)
        crossings_sql = "\n    UNION ALL\n".join(
            f"""    SELECT e.energia_fonte, e.energia_id, e.energia_nome, e.energia_tipo, e.ato_legal,
           e.forma, e.largura_m,
           '{tbl}'::varchar(50) AS territorio_fonte, ({name})::text AS territorio_nome,
           '{label}'::text AS territorio_tipo,
           ST_Area(ST_CollectionExtract(ST_MakeValid(t.geometry), 3)::geography) AS territorio_area_m2,
           ST_CollectionExtract(ST_Intersection(e.geometry, ST_CollectionExtract(ST_MakeValid(t.geometry), 3)), 3) AS geometry
    FROM energia e
    JOIN {tbl} t ON ST_Intersects(e.geometry, t.geometry)"""
            for tbl, name, label in territories
        )
        utm = "CASE WHEN ST_X(ST_Centroid(p.geom)) < -36 THEN 31984 ELSE 31985 END"

        conn.execute(text(f"""
            DROP TABLE IF EXISTS public.aneel_sobreposicoes_territorios_pe;
            CREATE TABLE public.aneel_sobreposicoes_territorios_pe AS
            WITH energia AS (
{energy_sql}
            ),
            crossings AS (
{crossings_sql}
            ),
            parts AS (
                SELECT c.*, k.geom_limpa, k.partes, k.partes_descartadas, k.area_descartada_m2
                FROM crossings c
                CROSS JOIN LATERAL (
                    SELECT ST_Collect(d.geom) FILTER (WHERE d.manter) AS geom_limpa,
                           COUNT(*) FILTER (WHERE d.manter) AS partes,
                           COUNT(*) FILTER (WHERE NOT d.manter) AS partes_descartadas,
                           COALESCE(SUM(d.area_m2) FILTER (WHERE NOT d.manter), 0) AS area_descartada_m2
                    FROM (
                        SELECT p.geom, ST_Area(p.geom::geography) AS area_m2,
                               CASE WHEN c.forma = 'faixa'
                                    THEN ST_Area(p.geom::geography) >= {STRIP_MIN_AREA_M2}
                                    ELSE ST_Area(p.geom::geography) >= {SLIVER_MIN_AREA_M2}
                                         AND (ST_MaximumInscribedCircle(ST_Transform(p.geom, {utm}))).radius * 2 >= {SLIVER_MIN_WIDTH_M}
                               END AS manter
                        FROM ST_Dump(c.geometry) p
                    ) d
                ) k
                WHERE c.geometry IS NOT NULL AND NOT ST_IsEmpty(c.geometry)
            )
            SELECT
                row_number() OVER (ORDER BY energia_fonte, energia_id, territorio_fonte, territorio_nome)::integer AS id,
                energia_fonte, energia_id, energia_nome, energia_tipo, ato_legal, forma,
                largura_m AS largura_faixa_m,
                territorio_fonte, territorio_nome, territorio_tipo,
                ROUND((ST_Area(geom_limpa::geography) / 10000.0)::numeric, 4) AS area_sobreposicao_ha,
                ROUND((100.0 * ST_Area(geom_limpa::geography) / NULLIF(territorio_area_m2, 0))::numeric, 2) AS pct_territorio,
                CASE WHEN forma = 'faixa' AND largura_m > 0
                     THEN ROUND((ST_Area(geom_limpa::geography) / largura_m / 1000.0)::numeric, 3) END AS extensao_travessia_km,
                partes::integer, partes_descartadas::integer,
                ROUND((area_descartada_m2 / 10000.0)::numeric, 4) AS area_descartada_ha,
                ST_Force2D(ST_Multi(geom_limpa))::geometry(MultiPolygon, 4326) AS geometry
            FROM parts
            WHERE geom_limpa IS NOT NULL;

            CREATE INDEX idx_aneel_sobreposicoes_territorios_pe_geometry
                ON public.aneel_sobreposicoes_territorios_pe USING GIST (geometry);
        """))

        if exists("aneel_eol_aerogeradores_pe"):
            conn.execute(text("""
                ALTER TABLE public.aneel_sobreposicoes_territorios_pe ADD COLUMN aerogeradores INTEGER;
                UPDATE public.aneel_sobreposicoes_territorios_pe s
                SET aerogeradores = (
                    SELECT COUNT(*) FROM aneel_eol_aerogeradores_pe a WHERE ST_Intersects(a.geometry, s.geometry)
                );
            """))

        count, dropped, dropped_ha = conn.execute(text("""
            SELECT COUNT(*), COALESCE(SUM(partes_descartadas), 0), COALESCE(SUM(area_descartada_ha), 0)
            FROM public.aneel_sobreposicoes_territorios_pe
        """)).one()
        logger.info(f"Energy overlaps completed: {count} footprint × territory intersections "
                    f"({dropped} sliver parts / {dropped_ha:.2f} ha discarded).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    calculate_overlaps()
    calculate_energy_overlaps()
