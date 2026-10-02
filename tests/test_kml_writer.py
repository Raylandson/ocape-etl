"""
Tests for the server-side KML writer, a port of frontend/src/app/services/kml-export.service.ts.

The writer is pure: geometry arrives as a pre-rendered <...> fragment from PostGIS ST_AsKML,
so none of this needs a database.
"""
import xml.etree.ElementTree as ET

import pytest

from src.kml_writer import (
    KmlItem,
    build_document,
    escape_xml,
    extended_data,
    feature_title,
    hex_to_kml_color,
    html_description,
    sanitize_filename,
)

POLY = "<Polygon><outerBoundaryIs><LinearRing><coordinates>0,0 1,0 1,1 0,0</coordinates></LinearRing></outerBoundaryIs></Polygon>"


# --- 1. colour conversion: CSS #RRGGBB[AA] -> Google Earth AABBGGRR -------------------

@pytest.mark.parametrize("css,alpha,expected", [
    ("#84cc16", "ff", "ff16cc84"),
    ("84cc16", "ff", "ff16cc84"),      # '#' is optional
    ("#abc", "ff", "ffccbbaa"),        # 3-char shorthand expands
    ("#84cc16", "66", "6616cc84"),     # translucent fill default
    ("#84cc1680", "ff", "8016cc84"),   # 8-char carries its own alpha, overriding the default
])
def test_hex_to_kml_color(css, alpha, expected):
    assert hex_to_kml_color(css, alpha) == expected


@pytest.mark.parametrize("bad", ["", None])
def test_hex_to_kml_color_falls_back_to_opaque_black(bad):
    assert hex_to_kml_color(bad) == "ff000000"


# --- 2. XML escaping -----------------------------------------------------------------

def test_escape_xml_covers_all_five_entities():
    assert escape_xml("""a&b<c>d"e'f""") == "a&amp;b&lt;c&gt;d&quot;e&apos;f"


@pytest.mark.parametrize("value,expected", [(None, ""), (0, "0"), (12, "12"), (True, "True")])
def test_escape_xml_accepts_non_strings(value, expected):
    assert escape_xml(value) == expected


# --- 3. filenames --------------------------------------------------------------------

def test_sanitize_filename_strips_accents_and_collapses_separators():
    assert sanitize_filename("Sítio Batateiras nº 1") == "sitio_batateiras_n_1"


def test_sanitize_filename_keeps_extension_characters():
    assert sanitize_filename("area_imovel_1.kml") == "area_imovel_1.kml"


# --- 4. the title fallback chain -----------------------------------------------------

@pytest.mark.parametrize("props,expected", [
    ({"nome_imovel": "Fazenda A", "nome": "ignored"}, "Fazenda A"),   # first rung wins
    ({"nome_area": "Area B"}, "Area B"),
    ({"no_projeto": "PA Serra"}, "PA Serra"),
    ({"nomeuc": "UC X"}, "UC X"),
    ({"nm_fcu": "Favela Y"}, "Favela Y"),
    ({"traditional_name": "Xukuru"}, "Xukuru"),
    ({"numero_processo": "0801234-55.2024.8.17.0001"}, "Processo CNJ 0801234-55.2024.8.17.0001"),
    ({"processo": "848.123/2019"}, "Processo ANM 848.123/2019"),
    ({"cod_imovel": "PE-2605707-ABC"}, "CAR PE-2605707-ABC"),
    ({"codigo_imo": "SIG-1"}, "SIGEF SIG-1"),
    ({"alertcode": 9912}, "Alerta #9912"),
    ({"numero_ai": "AI-7"}, "Auto #AI-7"),
    ({"numero_emb": "EMB-3"}, "Embargo #EMB-3"),
])
def test_feature_title_chain(props, expected):
    assert feature_title(props, "Camada") == expected


def test_feature_title_falls_back_to_layer_and_id():
    assert feature_title({"objectid": 42}, "Camada") == "Camada (ID: 42)"
    assert feature_title({}, "Camada") == "Camada (ID: 1)"
    assert feature_title(None, "Camada") == "Camada"


def test_feature_title_skips_empty_values():
    # JS `||` falls through on empty strings; the port must do the same.
    assert feature_title({"nome_imovel": "", "nome_area": "Real"}, "Camada") == "Real"


# --- 5. balloon description ----------------------------------------------------------

def test_html_description_is_cdata_wrapped_and_skips_noise_fields():
    html = html_description("T", "Camada", {
        "cod_imovel": "PE-1", "geometry": "xxx", "ogc_fid": 3, "cor_hex": "#fff", "vazio": "",
    })
    assert html.lstrip().startswith("<![CDATA[")
    assert "PE-1" in html
    for noise in ("xxx", "ogc_fid", "cor_hex", "vazio"):
        assert noise not in html


def test_html_description_formats_area_and_dates_pt_br():
    # Only keys containing "area"/"data" get special formatting, matching the TS original.
    # Note `dat_criaca` does NOT contain "data", so it stays verbatim.
    html = html_description("T", "C", {
        "num_area": 1234.5678, "data_cadastro": "2020-07-08", "dat_criaca": "08/07/2020",
    })
    assert "1.234,5678 ha" in html
    assert "08/07/2020" in html          # both the ISO date and the verbatim one render this way


def test_html_description_escapes_injected_markup():
    html = html_description("T", "C", {"declarante": "<script>alert(1)</script>"})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


# --- 6. ExtendedData -----------------------------------------------------------------

def test_extended_data_serialises_complex_values_as_json():
    xml = extended_data({"a": 1, "b": {"k": "v"}, "c": None})
    assert '<Data name="a"><value>1</value></Data>' in xml
    # Values are XML-escaped even though they are JSON, exactly as the TS original does.
    assert "&quot;k&quot;: &quot;v&quot;" in xml
    assert 'name="c"' not in xml          # nulls are omitted


# --- 7/8. the document, and that it is well-formed XML -------------------------------

def _items():
    return [
        KmlItem(geometry_kml=POLY, properties={"cod_imovel": "PE-1"},
                layer_id="area_imovel_1", layer_name="CAR", fill_color="#84cc16", border_color="#4d7c0f"),
        KmlItem(geometry_kml=POLY, properties={"cod_imovel": "PE-2"},
                layer_id="area_imovel_1", layer_name="CAR", fill_color="#84cc16", border_color="#4d7c0f"),
        KmlItem(geometry_kml=POLY, properties={"terrai_nom": "Fulni-ô"},
                layer_id="tis_poligonais", layer_name="TI", fill_color="#ef4444", border_color="#b91c1c"),
    ]


def test_document_dedupes_styles_and_groups_folders_by_layer():
    doc = build_document("Export", _items())
    assert doc.count("<Style id=") == 2                     # two distinct layer/colour combos
    assert "<name>CAR (2)</name>" in doc                    # folder name carries the count
    assert "<name>TI (1)</name>" in doc
    assert doc.count("<Placemark>") == 3


def test_document_is_well_formed_xml():
    # A class of bug the TypeScript original could never catch.
    root = ET.fromstring(build_document("Export", _items()))
    assert root.tag.endswith("kml")


def test_document_with_hostile_content_is_still_well_formed():
    items = [KmlItem(geometry_kml=POLY,
                     properties={"nome": 'Fazenda "A" & <b>B</b>', "obs": "]]> break out"},
                     layer_id="x", layer_name='Camada & "Teste"')]
    ET.fromstring(build_document('Doc & <evil>', items))


def test_empty_document_is_well_formed():
    ET.fromstring(build_document("Vazio", []))


def test_explicit_title_overrides_the_property_chain():
    """search_index.label is authoritative: the inherited chain has no rung for several
    layers (tis_poligonais names live in `terrai_nom`) and would fall back to "(ID: n)"."""
    item = KmlItem(geometry_kml=POLY, properties={"terrai_nom": "Fulni-ô", "id": 130},
                   title="Fulni-ô", layer_id="tis_poligonais", layer_name="Terras Indígenas")
    assert "<name>Fulni-ô</name>" in build_document("D", [item])


def test_title_falls_back_to_the_chain_when_absent():
    item = KmlItem(geometry_kml=POLY, properties={"nome_imovel": "Fazenda A"},
                   layer_id="x", layer_name="Camada")
    assert "<name>Fazenda A</name>" in build_document("D", [item])
