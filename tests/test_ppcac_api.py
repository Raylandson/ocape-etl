import pytest
from fastapi.testclient import TestClient
from src.search_api import app

client = TestClient(app)


def test_get_ppcac_areas():
    response = client.get("/ppcac/areas")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 80
    assert "stats" in data
    assert data["stats"]["ativos"] == 70
    assert data["stats"]["arquivados"] == 10
    assert data["stats"]["com_geometria_exata"] >= 60
    assert data["stats"]["com_poligono"] >= 25
    assert data["stats"]["com_car"] >= 35
    assert len(data["areas"]) == 80

    first = data["areas"][0]
    assert "id" in first
    assert "nome_area" in first
    assert "municipio" in first
    assert "processos_judiciais" in first
    assert "processos_mppe" in first
    assert "processos_sei" in first
    assert "bbox" in first
    assert "tem_geometria_exata" in first
    assert "geometry" in first
    assert first["geometry"] is not None
    assert "type" in first["geometry"]
    assert "fonte_geometria" in first
    assert "tipo_geometria" in first
    assert "car_codigos" in first
    assert "iterpe_nomes" in first
    assert "incra_projetos" in first

    # Check a known SIGEF area returns a Polygon geometry with CAR
    roncador = next((a for a in data["areas"] if "Roncadorzinho" in a["nome_area"]), None)
    assert roncador is not None
    assert roncador["fonte_geometria"] == "SIGEF_PRIVADO"
    assert roncador["tipo_geometria"] == "POLYGON"
    assert roncador["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert len(roncador["car_codigos"]) > 0

    # Check Negros de Gilú returns ITERPE polygon
    gilu = next((a for a in data["areas"] if "Gilú" in a["nome_area"]), None)
    assert gilu is not None
    assert gilu["fonte_geometria"] == "ITERPE"
    assert gilu["tipo_geometria"] == "POLYGON"
    assert gilu["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert len(gilu["car_codigos"]) > 0



def test_get_ppcac_areas_filters():
    # Filter ATIVO
    res_ativos = client.get("/ppcac/areas?situacao=ATIVO")
    assert res_ativos.status_code == 200
    data_ativos = res_ativos.json()
    assert data_ativos["total"] == 70
    assert all(a["situacao"] == "ATIVO" for a in data_ativos["areas"])

    # Filter ARQUIVADO
    res_arq = client.get("/ppcac/areas?situacao=ARQUIVADO")
    assert res_arq.status_code == 200
    data_arq = res_arq.json()
    assert data_arq["total"] == 10
    assert all(a["situacao"] == "ARQUIVADO" for a in data_arq["areas"])

    # Text search
    res_q = client.get("/ppcac/areas?q=roncadorzinho")
    assert res_q.status_code == 200
    data_q = res_q.json()
    assert data_q["total"] >= 1
    assert "Roncadorzinho" in data_q["areas"][0]["nome_area"]

    # Accented text search (e.g., 'várzea' matching 'Várzea Velha' and unaccented DB text)
    res_accent = client.get("/ppcac/areas?q=várzea")
    assert res_accent.status_code == 200
    data_accent = res_accent.json()
    assert data_accent["total"] >= 1
    assert any("Várzea" in a["nome_area"] or "Varzea" in a["nome_area"] for a in data_accent["areas"])

    # Search by judicial lawsuit number
    res_proc = client.get("/ppcac/areas?q=0000336-88.2019.8.17.3170")
    assert res_proc.status_code == 200
    data_proc = res_proc.json()
    assert data_proc["total"] >= 1
    assert "Barão do Rio Branco" in data_proc["areas"][0]["nome_area"]

    # Search by municipality with accent
    res_mun = client.get("/ppcac/areas?municipio=São Bento")
    assert res_mun.status_code == 200
    data_mun = res_mun.json()
    assert data_mun["total"] >= 1
    assert any("São Bento" in a["municipio"] or "Sao Bento" in a["municipio"] for a in data_mun["areas"])


def test_get_ppcac_filter_keys():
    response = client.get("/ppcac/filter-keys")
    assert response.status_code == 200
    data = response.json()

    assert "processos_conflitos_judiciais" in data
    assert isinstance(data["processos_conflitos_judiciais"], list)
    assert len(data["processos_conflitos_judiciais"]) > 0

    assert "despejo_zero_pe" in data
    assert isinstance(data["despejo_zero_pe"], list)
