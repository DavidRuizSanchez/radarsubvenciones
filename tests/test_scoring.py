from ai_income_snapshot.intel.scoring import history_score_from_awards, weighted_final_score


def test_history_score_bands():
    assert history_score_from_awards(0) == 0.2
    assert history_score_from_awards(2) == 0.5
    assert history_score_from_awards(8) == 0.8
    assert history_score_from_awards(40) == 0.65


def test_weighted_score_in_range():
    score = weighted_final_score(
        fit_score=0.7,
        intent_score=0.8,
        history_score=0.5,
        fit_weight=0.45,
        intent_weight=0.35,
        history_weight=0.20,
    )
    assert 0 <= score <= 1
