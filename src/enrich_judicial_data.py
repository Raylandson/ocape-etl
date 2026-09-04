"""
Enrich Judicial Data: Integrates territorial jurisdictions (TJPE and JFPE)
into processos_conflitos_judiciais and generates comprehensive 185-municipality summary.
"""

import logging
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import text
from src.database import get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# TRF5 Vara to Subseção mapping from official JFPE docx
VARA_TO_SUBSECAO = {
    1: ("Recife (Sede)", 2611606), 2: ("Recife (Sede)", 2611606), 3: ("Recife (Sede)", 2611606),
    4: ("Recife (Sede)", 2611606), 5: ("Recife (Sede)", 2611606), 6: ("Recife (Sede)", 2611606),
    7: ("Recife (Sede)", 2611606), 8: ("Petrolina", 2611101), 9: ("Recife (Sede)", 2611606),
    10: ("Recife (Sede)", 2611606), 11: ("Recife (Sede)", 2611606), 12: ("Recife (Sede)", 2611606),
    13: ("Recife (Sede)", 2611606), 14: ("Recife (Sede)", 2611606), 15: ("Recife (Sede)", 2611606),
    16: ("Caruaru", 2604106), 17: ("Petrolina", 2611101), 18: ("Serra Talhada", 2613909),
    19: ("Recife (Sede)", 2611606), 20: ("Salgueiro", 2612208), 21: ("Recife (Sede)", 2611606),
    22: ("Recife (Sede)", 2611606), 23: ("Garanhuns", 2606002), 24: ("Caruaru", 2604106),
    25: ("Goiana", 2606200), 26: ("Palmares", 2610004), 27: ("Ouricuri", 2609907),
    28: ("Arcoverde", 2601102), 29: ("Jaboatão dos Guararapes", 2607901),
    30: ("Jaboatão dos Guararapes", 2607901), 31: ("Caruaru", 2604106), 32: ("Garanhuns", 2606002),
    33: ("Recife (Sede)", 2611606), 34: ("Cabo de Santo Agostinho", 2602902),
    35: ("Cabo de Santo Agostinho", 2602902), 36: ("Recife (Sede)", 2611606),
    37: ("Caruaru", 2604106), 38: ("Serra Talhada", 2613909)
}


def enrich_lawsuits(engine):
    """Enriches public.processos_conflitos_judiciais with territorial jurisdiction metadata."""
    logger.info("Enriching processos_conflitos_judiciais with comarca and jurisdiction metadata...")

    with engine.begin() as conn:
        # 1. Add columns if not exist
        conn.execute(text("""
            ALTER TABLE public.processos_conflitos_judiciais 
            ADD COLUMN IF NOT EXISTS comarca_sede_nome VARCHAR(150),
            ADD COLUMN IF NOT EXISTS comarca_sede_ibge INTEGER,
            ADD COLUMN IF NOT EXISTS municipios_abrangidos TEXT,
            ADD COLUMN IF NOT EXISTS total_municipios_abrangidos INTEGER,
            ADD COLUMN IF NOT EXISTS tem_municipios_filhos BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS tipo_jurisdicao VARCHAR(50);
        """))

        # 2. Update TJPE lawsuits using public.jurisdicao_tjpe
        logger.info("Updating TJPE lawsuits...")
        # Match via comarca_ibge (when process is filed at sede)
        conn.execute(text("""
            UPDATE public.processos_conflitos_judiciais p
            SET 
                comarca_sede_nome = j.comarca_nome,
                comarca_sede_ibge = j.comarca_ibge,
                municipios_abrangidos = j.municipios_abrangidos,
                total_municipios_abrangidos = j.total_municipios_comarca,
                tem_municipios_filhos = (j.total_municipios_comarca > 1),
                tipo_jurisdicao = 'Comarca Estadual (TJPE)'
            FROM public.jurisdicao_tjpe j
            WHERE p.tribunal = 'TJPE' 
              AND p.municipio_ibge = j.comarca_ibge
              AND j.eh_sede = TRUE;
        """))

        # Match via municipio_ibge (when process is filed at a filha / termo judiciário or district)
        conn.execute(text("""
            UPDATE public.processos_conflitos_judiciais p
            SET 
                comarca_sede_nome = j.comarca_nome,
                comarca_sede_ibge = j.comarca_ibge,
                municipios_abrangidos = j.municipios_abrangidos,
                total_municipios_abrangidos = j.total_municipios_comarca,
                tem_municipios_filhos = (j.total_municipios_comarca > 1),
                tipo_jurisdicao = 'Comarca Estadual (TJPE)'
            FROM public.jurisdicao_tjpe j
            WHERE p.tribunal = 'TJPE' 
              AND p.comarca_sede_nome IS NULL
              AND p.municipio_ibge = j.municipio_ibge;
        """))

        # Fallback for any TJPE that matched on comarca name
        conn.execute(text("""
            UPDATE public.processos_conflitos_judiciais p
            SET 
                comarca_sede_nome = j.comarca_nome,
                comarca_sede_ibge = j.comarca_ibge,
                municipios_abrangidos = j.municipios_abrangidos,
                total_municipios_abrangidos = j.total_municipios_comarca,
                tem_municipios_filhos = (j.total_municipios_comarca > 1),
                tipo_jurisdicao = 'Comarca Estadual (TJPE)'
            FROM public.jurisdicao_tjpe j
            WHERE p.tribunal = 'TJPE' 
              AND p.comarca_sede_nome IS NULL
              AND LOWER(p.municipio_nome) = LOWER(j.comarca_nome)
              AND j.eh_sede = TRUE;
        """))

        # 3. Update TRF5 lawsuits using public.jurisdicao_jfpe
        logger.info("Updating TRF5 lawsuits...")
        subsecoes = conn.execute(text("""
            SELECT DISTINCT subsecao_nome, subsecao_sede_nome, subsecao_ibge, total_municipios_subsecao, municipios_abrangidos
            FROM public.jurisdicao_jfpe;
        """)).fetchall()

        sub_map = {s[0]: s for s in subsecoes}

        trf5_rows = conn.execute(text("""
            SELECT id, orgao_julgador_nome, numero_processo, municipio_ibge, municipio_nome
            FROM public.processos_conflitos_judiciais
            WHERE tribunal = 'TRF5';
        """)).fetchall()

        update_stmt = text("""
            UPDATE public.processos_conflitos_judiciais
            SET 
                comarca_sede_nome = :sede_nome,
                comarca_sede_ibge = :sede_ibge,
                municipios_abrangidos = :abrangidos,
                total_municipios_abrangidos = :total,
                tem_municipios_filhos = TRUE,
                tipo_jurisdicao = 'Subseção Federal (JFPE)'
            WHERE id = :id;
        """)

        for r in trf5_rows:
            pid, orgao, num_proc, m_ibge, m_nome = r
            m_vara = re.search(r'(\d+)ª\s*Vara', orgao or '')
            sub_target = None
            if m_vara:
                v_num = int(m_vara.group(1))
                if v_num in VARA_TO_SUBSECAO:
                    sub_target = VARA_TO_SUBSECAO[v_num][0]
            
            if not sub_target:
                for s_key in sub_map:
                    if s_key.split()[0].lower() in (m_nome or '').lower():
                        sub_target = s_key
                        break
            if not sub_target:
                sub_target = "Recife (Sede)"

            if sub_target in sub_map:
                s_info = sub_map[sub_target]
                conn.execute(update_stmt, {
                    "id": pid,
                    "sede_nome": s_info[1],
                    "sede_ibge": s_info[2],
                    "abrangidos": s_info[4],
                    "total": s_info[3]
                })

        # 4. Create / Refresh comprehensive 185-municipality summary
        logger.info("Rebuilding public.processos_conflitos_municipios covering all 185 municipalities...")
        conn.execute(text("DROP TABLE IF EXISTS public.processos_conflitos_municipios CASCADE;"))
        conn.execute(text("""
            CREATE TABLE public.processos_conflitos_municipios AS
            WITH processos_por_comarca AS (
                SELECT 
                    comarca_sede_ibge,
                    COUNT(*) AS total_processos,
                    COUNT(*) FILTER (WHERE categoria_conflito = 'Reintegração e Conflito de Posse') AS total_posse,
                    COUNT(*) FILTER (WHERE categoria_conflito = 'Reforma Agrária & Desapropriação') AS total_reforma_agraria,
                    COUNT(*) FILTER (WHERE categoria_conflito = 'Povos Indígenas & Territórios Quilombolas') AS total_indigena_quilombola,
                    COUNT(*) FILTER (WHERE categoria_conflito = 'Terras Devolutas & Ações Discriminatórias') AS total_devolutas_discriminatoria,
                    COUNT(*) FILTER (WHERE categoria_conflito = 'Usucapião e Regularização de Posse') AS total_usucapiao,
                    COUNT(*) FILTER (WHERE categoria_conflito = 'Conflito Coletivo Rural & Agrário') AS total_coletivo_agrario
                FROM public.processos_conflitos_judiciais
                WHERE comarca_sede_ibge IS NOT NULL
                GROUP BY comarca_sede_ibge
            )
            SELECT 
                j.municipio_ibge,
                j.municipio_nome,
                j.tjpe_comarca_nome AS comarca_sede_nome,
                j.tjpe_comarca_ibge AS comarca_sede_ibge,
                j.tjpe_eh_sede AS eh_comarca_sede,
                j.tjpe_tipo_vinculo AS tipo_vinculo,
                j.tjpe_total_municipios_comarca AS total_municipios_comarca,
                j.tjpe_comarca_abrangencia AS comarca_abrangencia,
                j.jfpe_subsecoes,
                j.jfpe_varas,
                COALESCE(p.total_processos, 0) AS total_processos_comarca,
                COALESCE(p.total_posse, 0) AS total_posse,
                COALESCE(p.total_reforma_agraria, 0) AS total_reforma_agraria,
                COALESCE(p.total_indigena_quilombola, 0) AS total_indigena_quilombola,
                COALESCE(p.total_devolutas_discriminatoria, 0) AS total_devolutas_discriminatoria,
                COALESCE(p.total_usucapiao, 0) AS total_usucapiao,
                COALESCE(p.total_coletivo_agrario, 0) AS total_coletivo_agrario,
                j.geometry
            FROM public.jurisdicoes_pe_municipios j
            LEFT JOIN processos_por_comarca p ON j.tjpe_comarca_ibge = p.comarca_sede_ibge;

            CREATE INDEX idx_processos_muni_geom 
            ON public.processos_conflitos_municipios USING GIST (geometry);

            CREATE INDEX idx_processos_muni_ibge 
            ON public.processos_conflitos_municipios (municipio_ibge);
        """))

    logger.info("Enrichment completed successfully!")


def main():
    engine = get_engine()
    enrich_lawsuits(engine)

    # Verification counts
    with engine.connect() as conn:
        tot_enriched = conn.execute(text("""
            SELECT COUNT(*) FROM public.processos_conflitos_judiciais 
            WHERE comarca_sede_nome IS NOT NULL;
        """)).scalar()
        tot_filhos = conn.execute(text("""
            SELECT COUNT(*) FROM public.processos_conflitos_judiciais 
            WHERE tem_municipios_filhos = TRUE;
        """)).scalar()
        muni_count = conn.execute(text("""
            SELECT COUNT(*) FROM public.processos_conflitos_municipios;
        """)).scalar()
        termos_count = conn.execute(text("""
            SELECT COUNT(*) FROM public.processos_conflitos_municipios
            WHERE eh_comarca_sede = FALSE;
        """)).scalar()

        print("\n==================== ENRICHMENT REPORT ====================")
        print(f"  Total Lawsuits with Resolved Jurisdiction : {tot_enriched}")
        print(f"  Lawsuits in Comarcas/Subs Covering Filhas : {tot_filhos}")
        print(f"  Municipalities in Statewide Summary Table : {muni_count} (out of 185)")
        print(f"  Termos Judiciários (Municípios Filhas)    : {termos_count}")
        print("===========================================================\n")


if __name__ == "__main__":
    main()
