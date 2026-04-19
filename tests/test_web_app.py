from ai_income_snapshot.web_app import is_safe_run_id, parse_positive_int, parse_topics


def test_parse_topics_ignores_empty_values():
    topics = parse_topics("digitalizacion, innovacion, ,eficiencia energetica")
    assert topics == ["digitalizacion", "innovacion", "eficiencia energetica"]


def test_is_safe_run_id_allows_expected_pattern():
    assert is_safe_run_id("20260420_003556")
    assert is_safe_run_id("run-001")
    assert not is_safe_run_id("../etc")
    assert not is_safe_run_id("../../secret")


def test_parse_positive_int_uses_default_for_invalid_input():
    assert parse_positive_int("20", default=99) == 20
    assert parse_positive_int("0", default=99) == 99
    assert parse_positive_int("-2", default=99) == 99
    assert parse_positive_int("texto", default=99) == 99
