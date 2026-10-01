"""
Unified Search Index Builder: Denormalizes the identifying fields of every displayed
map layer (codes, names, case numbers, CPF/CNPJ, municipalities) into a single
`search_index` table with trigram indexes, served by `src/search_api.py`.

Each row keeps the source feature's full attribute set (`props`) and geometry so the
frontend can zoom to, highlight, and open the regular popup for a search hit without
querying the vector tiles.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import text
from src.database import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

INDEX_TABLE = "search_index"
MUNICIPIOS_TABLE = "jurisdicoes_pe_municipios"

# One entry per searchable map layer (table name == frontend layer id). Order sets the
# tie-break rank in search results: curated/small layers first, bulk registries last.
#   label: first non-empty column is the result title
#   codes: identifiers (also indexed with punctuation stripped, e.g. CNJ, CPF, CAR codes)
#   text:  free-text descriptors (holders, names, categories)
#   place: municipality-like columns, shown as the result subtitle
#   ibge:  integer IBGE municipality columns resolved to names via MUNICIPIOS_TABLE
SEARCH_SOURCES: List[Dict] = [
    {"table": "sigef_casos_analisados", "label": ["nome_imovel", "titulo_fase"],
     "codes": ["codigo_imo", "parcela_codigo", "matricula_cartorio", "art"],
     "text": ["titulo_fase", "fase", "proprietaria", "responsavel_tecnico"], "place": ["municipio"]},
    {"table": "car_casos_analisados", "label": ["nome_imovel", "cod_imovel"],
     "codes": ["cod_imovel", "cpf_declarante", "codigo_protocolo", "matricula_cartorio"],
     "text": ["declarante"], "place": ["municipio"]},
    {"table": "tis_poligonais", "label": ["terrai_nom"], "codes": ["terrai_cod"],
     "text": ["etnia_nome", "fase_ti", "modalidade"], "place": ["municipio"]},
    {"table": "areas_de_quilombolas_pe", "label": ["nm_comunid"],
     "codes": ["nr_process", "cd_quilomb", "cd_sipra"], "text": ["fase"], "place": ["nm_municip"]},
    {"table": "limiteucsfederais_a", "label": ["nomeuc"], "codes": ["cnuc"],
     "text": ["sigla_cate", "categoria"], "place": []},
    {"table": "ucs_estaduais_cprh_pe", "label": ["nome_uc"], "codes": ["cd_cnuc", "uc_id"],
     "text": ["nomeabrev", "categoria"], "place": ["municipio"]},
    {"table": "assentamentos_incra_pe", "label": ["no_projeto"], "codes": ["cd_sipra"],
     "text": ["sg_modalidade"], "place": ["no_municipio"]},
    {"table": "despejo_zero_pe", "label": ["nome_comunidade"], "codes": ["conflito_id"],
     "text": ["agente_promotor", "causa_conflito"], "place": ["municipio"]},
    {"table": "moradia_legal_pe", "label": ["nome", "comunidade"], "codes": [],
     "text": ["comunidade", "tipo"], "place": ["municipio"]},
    {"table": "iterpe_glebas_pe", "label": ["nome"], "codes": [], "text": ["tipo"], "place": ["municipio"]},
    {"table": "imovel_certificado_snci_privado_pe", "label": ["nome_imove", "cod_imovel"],
     "codes": ["cod_imovel", "num_certif", "num_proces"], "text": [], "place": ["uf_municip"]},
    {"table": "imovel_certificado_snci_publico_pe", "label": ["nome_imove", "cod_imovel"],
     "codes": ["cod_imovel", "num_certif", "num_proces"], "text": [], "place": ["uf_municip"]},
    {"table": "sigef_privado_pe", "label": ["nome_area", "codigo_imo"],
     "codes": ["codigo_imo", "parcela_co", "registro_m", "art"], "text": ["rt"], "place": [],
     "ibge": ["municipio"]},
    {"table": "sigef_publico_pe", "label": ["nome_area", "codigo_imo"],
     "codes": ["codigo_imo", "parcela_co", "registro_m", "art"], "text": ["rt"], "place": [],
     "ibge": ["municipio"]},
    {"table": "embargos_icmbio", "label": ["autuado", "numero_emb"],
     "codes": ["numero_emb", "numero_ai", "cpf_cnpj", "processo"], "text": ["nome_uc"], "place": ["municipio"]},
    {"table": "autos_infracao_icmbio", "label": ["autuado", "numero_ai"],
     "codes": ["numero_ai", "cpf_cnpj", "processo"], "text": ["nome_uc"], "place": ["municipio"]},
    {"table": "aneel_sobreposicoes_territorios_pe", "label": ["energia_nome"], "codes": ["ato_legal"],
     "text": ["territorio_nome", "territorio_tipo"], "place": []},
    {"table": "aneel_dup_pe", "label": ["empreem", "ato_legal"], "codes": ["ato_legal", "ceg", "coddup"],
     "text": ["modalidade"], "place": ["municipios"]},
    {"table": "aneel_eol_usinas_pe", "label": ["nome"], "codes": ["ceg", "proc_aneel", "ato_legal"],
     "text": ["proprietar"], "place": ["municipios"]},
    {"table": "aneel_eol_parques_pe", "label": ["nome_eol"], "codes": [], "text": [], "place": ["municipios"]},
    {"table": "aneel_eol_aerogeradores_pe", "label": ["den_aeg", "nome_eol"], "codes": ["ceg"],
     "text": ["nome_eol", "proprietario"], "place": ["municipios"]},
    {"table": "aneel_eol_interferencia_pe", "label": ["nome_eol"], "codes": [], "text": [], "place": ["municipios"]},
    {"table": "aneel_ufv_usinas_pe", "label": ["nome"], "codes": ["ceg", "cnpj", "proc_aneel", "ato_legal"],
     "text": ["proprietar"], "place": ["municipios"]},
    {"table": "aneel_ufv_parques_pe", "label": ["nome"], "codes": ["ceg"], "text": ["nome_comp"],
     "place": ["municipios"]},
    {"table": "aneel_ufv_paineis_pe", "label": ["nome"], "codes": ["ceg"], "text": ["nome_comp"],
     "place": ["municipios"]},
    {"table": "aneel_ufv_subestacoes_pe", "label": ["nome_se", "nome_resp", "ceg"], "codes": ["ceg", "cnpj"],
     "text": ["nome_resp"], "place": ["municipios"]},
    {"table": "aneel_ute_usinas_pe", "label": ["nome"], "codes": ["ceg", "cnpj", "proc_aneel", "ato_legal"],
     "text": ["proprietar"], "place": ["municipios"]},
    {"table": "aneel_hidro_aproveitamentos_pe", "label": ["nome"], "codes": ["ceg", "cnpj", "proc_aneel", "ato_legal"],
     "text": ["proprietar", "rio"], "place": ["municipios"]},
    {"table": "aneel_hidro_reservatorios_pe", "label": ["usina"], "codes": ["ceg"], "text": ["rio"],
     "place": ["municipios"]},
    {"table": "aneel_lt_interesse_restrito_pe", "label": ["nome_resp"], "codes": ["ceg", "cnpj"],
     "text": [], "place": ["municipios"]},
    {"table": "epe_linhas_transmissao_pe", "label": ["nome"], "codes": [], "text": ["concession"],
     "place": ["municipios"]},
    {"table": "epe_subestacoes_pe", "label": ["nome"], "codes": [], "text": ["concession"],
     "place": ["municipios"]},
    {"table": "processos_minerarios_pe", "label": ["processo"], "codes": ["processo"],
     "text": ["nome", "subs", "fase", "uso"], "place": []},
    {"table": "ibge_favelas_comunidades_pe", "label": ["nm_fcu"], "codes": ["cd_fcu", "cd_setor"],
     "text": ["nm_bairro", "nm_nu"], "place": ["nm_mun"]},
    {"table": "iterpe_malha_posses_pe", "label": ["num_lote"], "codes": ["num_lote", "matricula", "decreto", "registro"],
     "text": ["comarca", "tipo"], "place": ["municipio"]},
    {"table": "alerts_with_intersections", "label": ["alertcode"],
     "codes": ["alertcode", "alertid", "cdsicar", "cdprisigef", "cdpubsigef"], "text": [], "place": ["city"]},
    {"table": "car_with_alerts_and_intersections", "label": ["codsicar"], "codes": ["codsicar", "alertcode"],
     "text": [], "place": ["city"]},
    {"table": "moradia_legal_processos_pe", "label": ["numero_processo"],
     "codes": ["numero_processo", "idmoradia", "cep", "matricula_responsavel"],
     "text": ["nome_responsavel", "logradouro", "bairro"], "place": ["cidade"]},
    {"table": "processos_conflitos_judiciais", "label": ["numero_processo"], "codes": ["numero_processo"],
     "text": ["classe_nome", "categoria_conflito", "orgao_julgador_nome"], "place": ["municipio_nome"]},
    {"table": "area_imovel_1", "label": ["cod_imovel"], "codes": ["cod_imovel"], "text": [], "place": ["municipio"]},
]


def _norm(expr: str) -> str:
    return f"lower(unaccent({expr}))"


def _code_norm(expr: str) -> str:
    return f"regexp_replace({_norm(expr)}, '[^a-z0-9]', '', 'g')"


def _as_text(col: str) -> str:
    return f"NULLIF(btrim(t.\"{col}\"::text), '')"


def _fetch_columns(conn) -> Dict[str, Set[str]]:
    rows = conn.execute(text(
        "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public'"
    )).fetchall()
    columns: Dict[str, Set[str]] = {}
    for table_name, column_name in rows:
        columns.setdefault(table_name, set()).add(column_name)
    return columns


def _build_insert(source: Dict, rank: int, available: Set[str], has_municipios: bool) -> Optional[str]:
    table = source["table"]
    pick = lambda cols: [c for c in cols if c in available]

    label_cols = pick(source["label"])
    code_cols = pick(source["codes"])
    text_cols = pick(source["text"])
    place_cols = pick(source["place"])
    ibge_cols = pick(source.get("ibge", [])) if has_municipios else []

    if not label_cols:
        logger.warning(f"Skipping '{table}': none of the label columns {source['label']} exist.")
        return None

    place_exprs = [_as_text(c) for c in place_cols] + [
        f"(SELECT m.municipio_nome::text FROM {MUNICIPIOS_TABLE} m WHERE m.municipio_ibge = t.\"{c}\" LIMIT 1)"
        for c in ibge_cols
    ]
    label_expr = f"COALESCE({', '.join(_as_text(c) for c in label_cols)})"
    code_expr = f"COALESCE({', '.join(_as_text(c) for c in code_cols)})" if code_cols else "NULL"
    place_expr = f"COALESCE({', '.join(place_exprs)})" if place_exprs else "NULL"

    all_exprs = [_as_text(c) for c in dict.fromkeys(label_cols + code_cols + text_cols)] + place_exprs
    search_text = _norm(f"concat_ws(' ', {', '.join(all_exprs)})")
    codes = (
        f"concat_ws(' ', {', '.join(_code_norm(_as_text(c)) for c in code_cols)})"
        if code_cols else "''"
    )

    return f"""
        INSERT INTO {INDEX_TABLE}
            (layer_id, layer_rank, label, label_norm, code, place, search_text, codes, props, geometry)
        SELECT
            '{table}', {rank}, label, {_norm('label')}, code, place, search_text, codes, props, geometry
        FROM (
            SELECT
                {label_expr} AS label,
                {code_expr} AS code,
                {place_expr} AS place,
                {search_text} AS search_text,
                {codes} AS codes,
                to_jsonb(t) - 'geometry' AS props,
                ST_Force2D(t.geometry) AS geometry
            FROM "{table}" t
            WHERE t.geometry IS NOT NULL
        ) s
        WHERE label IS NOT NULL
    """


def build_search_index():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))

        columns = _fetch_columns(conn)
        has_municipios = MUNICIPIOS_TABLE in columns

        conn.execute(text(f"DROP TABLE IF EXISTS {INDEX_TABLE};"))
        conn.execute(text(f"""
            CREATE TABLE {INDEX_TABLE} (
                id bigserial PRIMARY KEY,
                layer_id text NOT NULL,
                layer_rank integer NOT NULL,
                label text NOT NULL,
                label_norm text NOT NULL,
                code text,
                place text,
                search_text text NOT NULL,
                codes text NOT NULL,
                props jsonb NOT NULL,
                geometry geometry(Geometry, 4326) NOT NULL
            );
        """))

        for rank, source in enumerate(SEARCH_SOURCES):
            table = source["table"]
            if "geometry" not in columns.get(table, set()):
                logger.warning(f"Skipping '{table}': table or geometry column not found.")
                continue
            sql = _build_insert(source, rank, columns[table], has_municipios)
            if sql is None:
                continue
            inserted = conn.execute(text(sql)).rowcount
            logger.info(f"Indexed {inserted:>7,} rows from '{table}'.")

        logger.info("Creating trigram, layer and spatial indexes...")
        conn.execute(text(f"CREATE INDEX idx_{INDEX_TABLE}_search_text ON {INDEX_TABLE} USING gin (search_text gin_trgm_ops);"))
        conn.execute(text(f"CREATE INDEX idx_{INDEX_TABLE}_codes ON {INDEX_TABLE} USING gin (codes gin_trgm_ops);"))
        conn.execute(text(f"CREATE INDEX idx_{INDEX_TABLE}_layer_id ON {INDEX_TABLE} (layer_id);"))
        conn.execute(text(f"CREATE INDEX idx_{INDEX_TABLE}_geometry ON {INDEX_TABLE} USING gist (geometry);"))

        total = conn.execute(text(f"SELECT count(*) FROM {INDEX_TABLE};")).scalar()

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"ANALYZE {INDEX_TABLE};"))

    logger.info(f"Search index '{INDEX_TABLE}' built with {total:,} rows.")


if __name__ == "__main__":
    build_search_index()
