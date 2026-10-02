"""Shared fixtures. Nothing here touches a database."""
import pytest

#: Mirrors the real `information_schema.columns` shape: table -> {column: data_type}.
#: Column sets match the live tables (see docs/specs §3.5).
FAKE_CATALOG = {
    "area_imovel_1": {
        "cod_tema": "text", "nom_tema": "text", "cod_imovel": "text",
        "mod_fiscal": "double precision", "num_area": "double precision",
        "ind_status": "text", "ind_tipo": "text", "des_condic": "text",
        "municipio": "text", "cod_estado": "text",
        "dat_criaca": "text", "dat_atuali": "text",
    },
    "tis_poligonais": {
        "gid": "integer", "terrai_nom": "text", "terrai_cod": "text",
        "etnia_nome": "text", "fase_ti": "text", "modalidade": "text", "municipio": "text",
    },
    "autos_infracao_icmbio": {
        "ogc_fid": "integer", "autuado": "text", "numero_ai": "text",
        "cpf_cnpj": "text", "processo": "text", "nome_uc": "text", "municipio": "text",
        "data_lavratura": "date",
    },
}


@pytest.fixture
def catalog():
    return FAKE_CATALOG
