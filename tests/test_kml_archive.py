"""
Tests for streaming ZIP assembly.

Exports can reach tens of thousands of features, and the API container has no writable data
mount, so the archive is streamed rather than buffered or written to disk.
"""
import io
import xml.etree.ElementTree as ET
import zipfile

import pytest

from src.kml_writer import KmlItem, LayerGroup, stream_archive

POLY = "<Polygon><outerBoundaryIs><LinearRing><coordinates>0,0 1,0 1,1 0,0</coordinates></LinearRing></outerBoundaryIs></Polygon>"


def _item(code="PE-1", name=None):
    props = {"cod_imovel": code} if name is None else {"nome": name}
    return KmlItem(geometry_kml=POLY, properties=props,
                   layer_id="area_imovel_1", layer_name="CAR - Imóveis Cadastrados",
                   fill_color="#84cc16", border_color="#4d7c0f")


def _group(n=3, count=None, layer_id="area_imovel_1", layer_name="CAR - Imóveis Cadastrados", items=None):
    items = items if items is not None else [_item(f"PE-{i}") for i in range(n)]
    return LayerGroup(layer_id=layer_id, layer_name=layer_name,
                      fill_color="#84cc16", border_color="#4d7c0f",
                      count=count if count is not None else len(items), items=items)


def _collect(chunks):
    data = b"".join(chunks)
    return zipfile.ZipFile(io.BytesIO(data))


# --- archive integrity ---------------------------------------------------------------

def test_layer_mode_produces_one_kml_per_layer_plus_readme():
    zf = _collect(stream_archive([_group(), _group(2, layer_id="tis_poligonais", layer_name="Terras Indígenas")],
                                 grouping="layer", readme_text="filtro X"))
    assert zf.testzip() is None
    names = sorted(zf.namelist())
    assert names == ["LEIAME.txt", "area_imovel_1.kml", "tis_poligonais.kml"]
    assert "filtro X" in zf.read("LEIAME.txt").decode()


def test_layer_mode_entries_are_well_formed_with_the_right_placemark_count():
    zf = _collect(stream_archive([_group(4)], grouping="layer"))
    doc = zf.read("area_imovel_1.kml").decode()
    ET.fromstring(doc)
    assert doc.count("<Placemark>") == 4
    assert "<name>CAR - Imóveis Cadastrados (4)</name>" in doc


def test_layer_mode_splits_oversized_layers():
    zf = _collect(stream_archive([_group(5)], grouping="layer", max_per_file=2))
    kmls = sorted(n for n in zf.namelist() if n.endswith(".kml"))
    assert kmls == ["area_imovel_1_parte01.kml", "area_imovel_1_parte02.kml", "area_imovel_1_parte03.kml"]
    assert sum(zf.read(n).decode().count("<Placemark>") for n in kmls) == 5
    for n in kmls:
        ET.fromstring(zf.read(n).decode())


# --- per-feature mode ----------------------------------------------------------------

def test_feature_mode_gives_colliding_titles_distinct_entry_names():
    # area_imovel_1 has 36 duplicate cod_imovel values, and apps_1 is 273k rows over 47k
    # codes, so titles collide constantly. The row-number suffix is what keeps names unique.
    items = [_item(name="Fazenda Igual") for _ in range(3)]
    zf = _collect(stream_archive([_group(items=items)], grouping="feature"))
    kmls = [n for n in zf.namelist() if n.endswith(".kml")]
    assert len(kmls) == 3
    assert len(set(kmls)) == 3
    assert all(n.startswith("area_imovel_1/") for n in kmls)


def test_feature_mode_entries_are_single_feature_documents():
    zf = _collect(stream_archive([_group(2)], grouping="feature"))
    for name in (n for n in zf.namelist() if n.endswith(".kml")):
        doc = zf.read(name).decode()
        ET.fromstring(doc)
        assert doc.count("<Placemark>") == 1


# --- streaming behaviour -------------------------------------------------------------

def test_archive_is_emitted_incrementally_not_buffered():
    chunks = [c for c in stream_archive([_group(400)], grouping="layer") if c]
    assert len(chunks) > 1, "a single chunk means the whole archive was buffered"


def test_items_may_be_a_generator():
    gen = (_item(f"PE-{i}") for i in range(3))
    zf = _collect(stream_archive([_group(count=3, items=gen)], grouping="layer"))
    assert zf.read("area_imovel_1.kml").decode().count("<Placemark>") == 3


def test_empty_export_still_produces_a_valid_archive():
    zf = _collect(stream_archive([], grouping="layer", readme_text="nada"))
    assert zf.testzip() is None
    assert zf.namelist() == ["LEIAME.txt"]
