from src.saved_selections import MEMBER_CAP, hint_from_props, member_key, normalize_name


def test_normalize_name_matches_the_generated_column():
    assert normalize_name("  Fazenda X ") == "fazenda x"
    assert normalize_name("FAZENDA X") == normalize_name("fazenda x")


def test_hint_keeps_only_short_string_values():
    props = {"cod": "PE-1", "area": 12.5, "n": None, "empty": "", "long": "x" * 500, "ok": "a"}
    assert hint_from_props(props) == {"cod": "PE-1", "ok": "a"}


def test_hint_is_bounded_in_key_count():
    props = {f"k{i}": "v" for i in range(100)}
    assert len(hint_from_props(props)) <= 20


def test_member_key_identifies_a_feature_not_a_row():
    a = {"layer_id": "l", "fingerprint": "f", "anchor_lng": 1.0, "anchor_lat": 2.0, "note": "x"}
    b = {**a, "note": "different note", "id": "other"}
    assert member_key(a) == member_key(b)
    assert member_key(a) != member_key({**a, "anchor_lng": 1.5})


def test_cap_is_five_hundred():
    assert MEMBER_CAP == 500
