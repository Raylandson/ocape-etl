"""
Tests for the saved-filter -> SQL compiler.

Two properties matter more than the rest and have dedicated guards:

* **No user input ever reaches the SQL text.** Conditions read `search_index.props`, so field
  names bind as jsonb *values*, not identifiers. Nothing a user types should appear in `sql`.
* **Spatial conditions must compile to the materialised-CTE form.** The obvious correlated
  EXISTS is 62x slower on real data (13,960 ms vs 226 ms), and the difference is invisible
  until someone runs it against 433k rows.
"""
import re

import pytest

from src.filter_compiler import FilterError, compile_filter

SENTINEL = "ZZQQ_SENTINEL"


def f(**kw):
    base = {"version": 1, "blocks": [{"layer": "area_imovel_1", "conditions": []}]}
    base.update(kw)
    return base


def block(layer="area_imovel_1", **kw):
    b = {"layer": layer, "conditions": []}
    b.update(kw)
    return b


# --- validation ----------------------------------------------------------------------

def test_unknown_layer_is_rejected(catalog):
    with pytest.raises(FilterError, match="camada_inexistente"):
        compile_filter(f(blocks=[block(layer="camada_inexistente")]), catalog)


def test_unknown_field_is_rejected_naming_field_and_layer(catalog):
    with pytest.raises(FilterError) as e:
        compile_filter(f(blocks=[block(conditions=[{"field": "nao_existe", "op": "eq", "value": "x"}])]), catalog)
    assert "nao_existe" in str(e.value)
    assert "area_imovel_1" in str(e.value)


@pytest.mark.parametrize("hostile", ['a"b', "a;DROP TABLE x", "' OR 1=1--", "ind_status; --", "Ind_Status"])
def test_hostile_field_names_are_rejected_and_never_reach_the_sql(catalog, hostile):
    with pytest.raises(FilterError):
        compile_filter(f(blocks=[block(conditions=[{"field": hostile, "op": "eq", "value": "x"}])]), catalog)


def test_unknown_operator_is_rejected(catalog):
    with pytest.raises(FilterError, match="op"):
        compile_filter(f(blocks=[block(conditions=[{"field": "ind_status", "op": "pwn", "value": "x"}])]), catalog)


def test_future_schema_version_is_rejected(catalog):
    with pytest.raises(FilterError, match="version"):
        compile_filter(f(version=2), catalog)


def test_definition_must_have_at_least_one_block(catalog):
    with pytest.raises(FilterError, match="blocks"):
        compile_filter(f(blocks=[]), catalog)


# --- parameterisation ----------------------------------------------------------------

def test_values_and_field_names_bind_as_parameters(catalog):
    c = compile_filter(f(blocks=[block(conditions=[{"field": "ind_status", "op": "eq", "value": SENTINEL}])]), catalog)
    assert SENTINEL not in c.sql
    assert SENTINEL in c.params.values()
    assert "ind_status" in c.params.values()      # the field is a value, not an identifier


def test_every_placeholder_is_bound_and_names_are_unique(catalog):
    c = compile_filter(f(
        text="abc",
        blocks=[
            block(conditions=[{"field": "ind_status", "op": "eq", "value": "AT"},
                              {"field": "num_area", "op": "gte", "value": 100}],
                  spatial=[{"relation": "intersects", "layer": "tis_poligonais"}]),
            block(layer="autos_infracao_icmbio",
                  conditions=[{"field": "nome_uc", "op": "is_null"}],
                  spatial=[{"relation": "not_intersects", "layer": "tis_poligonais"}]),
        ],
    ), catalog)
    # The lookbehind skips `::numeric` / `::text` casts, which are not placeholders.
    placeholders = set(re.findall(r"(?<!:):([a-z_][a-z0-9_]*)", c.sql))
    assert placeholders == set(c.params), f"unbound or unused: {placeholders ^ set(c.params)}"


# --- operators -----------------------------------------------------------------------

def test_equality_uses_the_containment_fast_path(catalog):
    c = compile_filter(f(blocks=[block(conditions=[{"field": "ind_status", "op": "eq", "value": "AT"}])]), catalog)
    assert "@>" in c.sql and "jsonb_build_object" in c.sql


def test_numeric_comparison_is_guarded_by_a_case(catalog):
    c = compile_filter(f(blocks=[block(conditions=[{"field": "num_area", "op": "gte", "value": 100}])]), catalog)
    assert "CASE" in c.sql and "jsonb_typeof" in c.sql
    # A bare cast outside a CASE raises on the first non-numeric row; AND-chained guards are
    # not safe either because the planner may reorder them.
    assert not re.search(r"(?<!THEN )\(\s*s\.props\s*->>\s*:p\d+\s*\)::numeric", c.sql)


def test_date_comparison_handles_both_dd_mm_yyyy_and_iso(catalog):
    c = compile_filter(f(blocks=[block(conditions=[{"field": "dat_criaca", "op": "date_gte", "value": "2020-01-01"}])]), catalog)
    assert "DD/MM/YYYY" in c.sql
    assert "::date" in c.sql


def test_text_match_is_accent_and_case_folded(catalog):
    c = compile_filter(f(blocks=[block(conditions=[{"field": "des_condic", "op": "contains", "value": "Aguardando"}])]), catalog)
    assert "unaccent" in c.sql and "lower" in c.sql and "LIKE" in c.sql


def test_like_wildcards_in_user_values_are_escaped(catalog):
    c = compile_filter(f(blocks=[block(conditions=[{"field": "des_condic", "op": "contains", "value": "100%_x"}])]), catalog)
    assert any("100\\%\\_x" == v for v in c.params.values())


def test_match_mode_selects_and_or_or(catalog):
    conds = [{"field": "ind_status", "op": "eq", "value": "AT"},
             {"field": "ind_tipo", "op": "eq", "value": "IRU"}]
    assert " AND " in compile_filter(f(blocks=[block(match="all", conditions=conds)]), catalog).sql
    assert " OR " in compile_filter(f(blocks=[block(match="any", conditions=conds)]), catalog).sql


# --- spatial: the performance-critical shape ------------------------------------------

def test_intersects_compiles_to_a_materialised_cte_not_a_correlated_exists(catalog):
    c = compile_filter(f(blocks=[block(spatial=[{"relation": "intersects", "layer": "tis_poligonais"}])]), catalog)
    assert "AS MATERIALIZED" in c.sql, "without MATERIALIZED the planner inlines and reverts to the 14 s plan"
    assert "&&" in c.sql, "the explicit bbox operator keeps the GIST index condition visible"
    assert "ST_Intersects" in c.sql
    assert "EXISTS (SELECT 1 FROM search_index" not in c.sql


def test_not_intersects_is_an_anti_join_against_the_materialised_set(catalog):
    c = compile_filter(f(blocks=[block(spatial=[{"relation": "not_intersects", "layer": "tis_poligonais"}])]), catalog)
    assert "AS MATERIALIZED" in c.sql
    assert "NOT EXISTS" in c.sql
    assert "EXISTS (SELECT 1 FROM search_index" not in c.sql


def test_spatial_target_layer_is_validated(catalog):
    with pytest.raises(FilterError):
        compile_filter(f(blocks=[block(spatial=[{"relation": "intersects", "layer": "nope"}])]), catalog)


def test_unknown_spatial_relation_is_rejected(catalog):
    with pytest.raises(FilterError):
        compile_filter(f(blocks=[block(spatial=[{"relation": "touches", "layer": "tis_poligonais"}])]), catalog)


# --- shape of the output --------------------------------------------------------------

def test_multiple_blocks_produce_one_union_all_branch_each(catalog):
    c = compile_filter(f(blocks=[block(), block(layer="tis_poligonais"), block(layer="autos_infracao_icmbio")]), catalog)
    assert c.sql.count("UNION ALL") == 2
    assert c.layers == ("area_imovel_1", "tis_poligonais", "autos_infracao_icmbio")


def test_block_with_no_conditions_is_a_valid_layer_only_query(catalog):
    c = compile_filter(f(), catalog)
    assert "layer_id" in c.sql
    assert c.layers == ("area_imovel_1",)


@pytest.mark.parametrize("select,marker", [
    ("count", "count(*)"),
    ("count_by_layer", "GROUP BY"),
    ("ids", "SELECT"),
    ("features", "ST_AsKML"),
])
def test_select_modes(catalog, select, marker):
    c = compile_filter(f(), catalog, select=select)
    assert marker in c.sql


def test_limit_is_bound_not_interpolated(catalog):
    c = compile_filter(f(), catalog, select="features", limit=500)
    assert "LIMIT" in c.sql
    assert 500 in c.params.values()


def test_free_text_reuses_the_trigram_columns(catalog):
    c = compile_filter(f(text="batateira"), catalog)
    assert "search_text" in c.sql


def test_no_placeholder_is_followed_by_a_postgres_cast(catalog):
    """SQLAlchemy's text() bind regex ends in `(?!:)`, so `:p::text` is never bound and leaks
    into the SQL as literal text. Casts must be written CAST(:p AS type)."""
    c = compile_filter(f(
        text="x",
        blocks=[block(conditions=[
            {"field": "ind_status", "op": "eq", "value": "AT"},
            {"field": "num_area", "op": "between", "value": [1, 2]},
            {"field": "dat_criaca", "op": "date_lte", "value": "2020-01-01"},
            {"field": "municipio", "op": "in", "value": ["Petrolina", "Salgueiro"]},
        ])],
    ), catalog)
    assert not re.search(r":[a-z_][a-z0-9_]*::", c.sql)
