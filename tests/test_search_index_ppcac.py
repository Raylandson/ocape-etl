import pytest
from sqlalchemy import text
from src.database import get_engine


def test_ppcac_in_search_index():
    engine = get_engine()
    with engine.connect() as conn:
        # Check if table search_index exists
        has_table = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'search_index'
            )
        """)).scalar()
        if not has_table:
            pytest.skip("search_index table does not exist yet")

        # Query PPCAC entries
        res = conn.execute(text("""
            SELECT count(*) FROM search_index WHERE layer_id = 'ppcac_conflitos_pe'
        """)).scalar()
        assert res == 80, f"Expected 80 PPCAC rows in search_index, found {res}"

        # Verify search query for 'ppcac' returns rows
        ppcac_hits = conn.execute(text("""
            SELECT label, place, code FROM search_index 
            WHERE layer_id = 'ppcac_conflitos_pe' AND search_text LIKE '%ppcac%'
        """)).fetchall()
        assert len(ppcac_hits) == 80

        # Verify search query for a specific area name
        roncador = conn.execute(text("""
            SELECT label, place FROM search_index 
            WHERE layer_id = 'ppcac_conflitos_pe' AND search_text LIKE '%roncadorzinho%'
        """)).fetchone()
        assert roncador is not None
        assert "Roncadorzinho" in roncador[0]
        assert roncador[1] == "Barreiros"

        # Verify exact code search matches individual lawsuit without array brackets
        code_hit = conn.execute(text("""
            SELECT label, code, codes FROM search_index
            WHERE layer_id = 'ppcac_conflitos_pe' AND (' ' || codes || ' ') LIKE '% 00003368820198173170 %'
        """)).fetchone()
        assert code_hit is not None
        assert "Rio Branco" in code_hit[0]
        assert not code_hit[1].startswith("{")
        assert not code_hit[1].endswith("}")

