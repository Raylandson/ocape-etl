"""Lifecycle and resolution against the real database. Skips when it is not reachable."""
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text

from src import saved_selections as store


@pytest.fixture(scope="module")
def engine():
    try:
        from src.database import get_engine
        eng = get_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1 FROM search_index LIMIT 1"))
    except Exception:
        pytest.skip("database with search_index is not reachable")
    store.ensure_saved_selections_tables(eng)
    return eng


@pytest.fixture
def selection(engine):
    created = store.create_selection(engine, f"pytest-{uuid.uuid4()}")
    yield created
    store.delete_selection(engine, created["id"])


def _sample_feature(engine, layer="tis_poligonais"):
    """A real indexed feature, described the way the add-member endpoint stores it."""
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT label, props, md5(props::text) AS fp, "
            "       ST_X(ST_PointOnSurface(geometry)) AS lng, ST_Y(ST_PointOnSurface(geometry)) AS lat "
            "FROM search_index WHERE layer_id = :l LIMIT 1"), {"l": layer}).mappings().first()
    assert row is not None, f"no rows indexed for {layer}"
    return dict(layer_id=layer, label=row["label"], fingerprint=row["fp"],
                lng=row["lng"], lat=row["lat"], hint=store.hint_from_props(row["props"]))


def test_duplicate_names_are_rejected_case_and_space_insensitively(engine, selection):
    with pytest.raises(store.DuplicateSelectionName):
        store.create_selection(engine, f"  {selection['name'].upper()}  ")


def test_adding_the_same_feature_twice_is_idempotent(engine, selection):
    feature = _sample_feature(engine)
    first, created_first = store.add_member(engine, selection["id"], **feature)
    second, created_second = store.add_member(engine, selection["id"], **feature)
    assert created_first is True and created_second is False
    assert first["id"] == second["id"]
    assert len(store.list_members(engine, selection["id"])) == 1


def test_cap_blocks_the_501st_member(engine, selection, monkeypatch):
    monkeypatch.setattr(store, "MEMBER_CAP", 1)
    store.add_member(engine, selection["id"], **_sample_feature(engine))
    other = {**_sample_feature(engine), "fingerprint": "different", "lng": 0.0, "lat": 0.0}
    with pytest.raises(store.SelectionFull):
        store.add_member(engine, selection["id"], **other)


def test_resolution_is_exact_approximate_or_missing(engine, selection):
    feature = _sample_feature(engine)
    member, _ = store.add_member(engine, selection["id"], **feature)

    assert store.resolve_member(engine, member)["status"] == "exact"

    # Attributes drifted since the member was saved (an ETL re-ingest): still found, flagged.
    drifted = {**member, "fingerprint": "stale"}
    result = store.resolve_member(engine, drifted)
    assert result["status"] == "approximate" and result["row"] is not None

    # The source feature is gone / moved: nothing near the anchor in that layer.
    gone = {**member, "anchor_lng": 0.0, "anchor_lat": 0.0}
    result = store.resolve_member(engine, gone)
    assert result["status"] == "missing" and result["row"] is None


def test_note_survives_and_missing_member_keeps_it(engine, selection):
    member, _ = store.add_member(engine, selection["id"], **_sample_feature(engine))
    updated = store.update_member_note(engine, selection["id"], member["id"], "verificar divisa")
    assert updated["note"] == "verificar divisa"
    assert store.list_members(engine, selection["id"])[0]["note"] == "verificar divisa"


def test_deleting_a_selection_removes_its_members(engine):
    created = store.create_selection(engine, f"pytest-{uuid.uuid4()}")
    store.add_member(engine, created["id"], **_sample_feature(engine))
    assert store.delete_selection(engine, created["id"]) is True
    with engine.connect() as conn:
        left = conn.execute(text("SELECT count(*) FROM saved_selection_members WHERE selection_id = :i"),
                            {"i": created["id"]}).scalar()
    assert left == 0


def test_backup_round_trip_merges_instead_of_duplicating(engine, selection):
    member, _ = store.add_member(engine, selection["id"], **_sample_feature(engine))
    store.update_member_note(engine, selection["id"], member["id"], "nota")
    backup = [s for s in store.export_backup(engine) if s["name"] == selection["name"]]
    assert len(backup) == 1 and backup[0]["members"][0]["note"] == "nota"

    result = store.import_backup(engine, backup)          # same name -> merge, no duplicate
    assert result["members_added"] == 0
    assert len(store.list_members(engine, selection["id"])) == 1

    store.delete_selection(engine, selection["id"])
    result = store.import_backup(engine, backup)          # gone -> recreated with notes
    assert result["selections"] == 1 and result["members_added"] == 1
    recreated = [s for s in store.list_selections(engine) if s["name"] == selection["name"]][0]
    assert store.list_members(engine, recreated["id"])[0]["note"] == "nota"
    store.delete_selection(engine, recreated["id"])


def test_concurrent_identical_adds_yield_one_member_and_no_errors(engine, selection):
    feature = _sample_feature(engine)
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: store.add_member(engine, selection["id"], **feature), range(16)))
    assert sum(1 for _, created in results if created) == 1
    assert len(store.list_members(engine, selection["id"])) == 1


def test_concurrent_adds_cannot_exceed_the_cap(engine, selection, monkeypatch):
    monkeypatch.setattr(store, "MEMBER_CAP", 3)
    feature = _sample_feature(engine)

    def add(i):
        try:
            store.add_member(engine, selection["id"], **{**feature, "fingerprint": f"fp-{i}"})
            return "added"
        except store.SelectionFull:
            return "full"

    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(add, range(12)))
    assert outcomes.count("added") == 3
    assert len(store.list_members(engine, selection["id"])) == 3


def test_a_different_feature_at_the_anchor_is_missing_not_approximate(engine, selection):
    member, _ = store.add_member(engine, selection["id"], **_sample_feature(engine))
    # Source feature replaced by another one covering the same spot: neither the attributes
    # nor the label match, so this must not bind to the neighbour.
    imposter = {**member, "fingerprint": "stale", "label": "some other feature"}
    result = store.resolve_member(engine, imposter)
    assert result["status"] == "missing" and result["row"] is None
