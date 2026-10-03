import pytest
from pathlib import Path
from src.etl_ppcac import parse_ppcac_spreadsheet

SPREADSHEET_PATH = Path("data/raw/Planilha_da_Relacao_Conflitos_09.02.2026.xlsx")


@pytest.mark.skipif(not SPREADSHEET_PATH.exists(), reason="Spreadsheet file not present")
def test_parse_ppcac_extracts_80_areas():
    areas = parse_ppcac_spreadsheet(SPREADSHEET_PATH)
    assert len(areas) == 80, f"Expected 80 consolidated areas, got {len(areas)}"

    # Check key areas exist
    names = {a["nome_area"] for a in areas}
    assert "Engenho Barro Branco" in names
    assert "Engenho Roncadorzinho" in names
    assert "Comunidade Quilombola Negros de Gilú" in names


@pytest.mark.skipif(not SPREADSHEET_PATH.exists(), reason="Spreadsheet file not present")
def test_rectify_shifted_columns():
    areas = parse_ppcac_spreadsheet(SPREADSHEET_PATH)
    area_map = {a["nome_area"]: a for a in areas}

    # Row 104: Gleba 3 da Fazenda Boa Vista dos Mocós (Caruaru)
    mocos = None
    for name, a in area_map.items():
        if "Boa Vista" in name and "Mocós" in name:
            mocos = a
            break
    assert mocos is not None
    assert "0009683-52.2017.8.17.2480" in mocos["processos_judiciais"]
    assert any("3900032476" in s for s in mocos["processos_sei"])

    # Row 108: Engenho Pernambuquinho (Água Preta)
    pernamb = area_map.get("Engenho Pernambuquinho")
    assert pernamb is not None
    assert any("02072.000.282/2024" in m for m in pernamb["processos_mppe"])
    assert any("0031200020.001041/2025-55" in s for s in pernamb["processos_sei"])
    assert pernamb["situacao"] == "ARQUIVADO"


@pytest.mark.skipif(not SPREADSHEET_PATH.exists(), reason="Spreadsheet file not present")
def test_merged_cell_forward_fill():
    areas = parse_ppcac_spreadsheet(SPREADSHEET_PATH)
    congacari = None
    for a in areas:
        if "Congaçari" in a["nome_area"]:
            congacari = a
            break
    assert congacari is not None
    assert congacari["municipio"] == "Igarassu"
    # Should have captured 3 processes from rows 14, 15, 16
    jud_digits = [p.replace("-", "").replace(".", "").replace(" ", "") for p in congacari["processos_judiciais"]]
    assert any("00031805820158170710" in p for p in jud_digits)
    assert any("00023840320238172710" in p for p in jud_digits)
    assert any("00036001020248179000" in p for p in jud_digits)


def test_ingest_ppcac_links_sigef_polygons():
    from src.database import get_engine
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        has_table = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ppcac_conflitos_pe')")).scalar()
        if not has_table:
            pytest.skip("ppcac_conflitos_pe table does not exist")

        # Verify Batateiras polygon from sigef_casos_analisados
        batateira = conn.execute(text("""
            SELECT fonte_geometria, tipo_geometria, ST_GeometryType(geometry)
            FROM ppcac_conflitos_pe
            WHERE nome_area ILIKE '%Batateira%'
        """)).fetchone()
        assert batateira is not None
        assert batateira[0] == "SIGEF_CASOS_ANALISADOS"
        assert batateira[1] == "POLYGON"
        assert batateira[2] in ("ST_Polygon", "ST_MultiPolygon")

        # Verify Roncadorzinho polygon from sigef_privado_pe
        roncador = conn.execute(text("""
            SELECT fonte_geometria, tipo_geometria, ST_GeometryType(geometry), cardinality(car_codigos)
            FROM ppcac_conflitos_pe
            WHERE nome_area ILIKE '%Roncadorzinho%'
        """)).fetchone()
        assert roncador is not None
        assert roncador[0] == "SIGEF_PRIVADO"
        assert roncador[1] == "POLYGON"
        assert roncador[2] in ("ST_Polygon", "ST_MultiPolygon")
        assert roncador[3] > 0

        # Verify Negros de Gilú polygon from iterpe_glebas_pe
        gilu = conn.execute(text("""
            SELECT fonte_geometria, tipo_geometria, ST_GeometryType(geometry), iterpe_nomes, cardinality(car_codigos)
            FROM ppcac_conflitos_pe
            WHERE nome_area ILIKE '%Gilú%'
        """)).fetchone()
        assert gilu is not None
        assert gilu[0] == "ITERPE"
        assert gilu[1] == "POLYGON"
        assert gilu[2] in ("ST_Polygon", "ST_MultiPolygon")
        assert len(gilu[3]) > 0
        assert gilu[4] > 0

        # Verify total polygon count
        poly_count = conn.execute(text("SELECT count(*) FROM ppcac_conflitos_pe WHERE tipo_geometria = 'POLYGON'")).scalar()
        assert poly_count >= 25

