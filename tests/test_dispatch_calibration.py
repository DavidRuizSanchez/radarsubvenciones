from ai_income_snapshot.intel.dispatch_calibration import (
    DispatchCalibration,
    combine_with_dispatch,
    compute_dispatch_score,
)
from ai_income_snapshot.models import Company, Opportunity


def test_combine_with_dispatch_uses_weight():
    final_score = combine_with_dispatch(technical_score=0.4, dispatch_score=0.8, dispatch_weight=0.25)
    assert final_score == 0.5


def test_dispatch_score_in_range_for_company_profile():
    company = Company(
        company_id="c1",
        name="Gestoria Test",
        region="Madrid",
        sector_tags=["innovacion"],
        service_focus_tags=["innovacion", "digitalizacion"],
        strategic_priority=5,
        urgency_level=4,
        estimated_ticket_eur=1000,
        relationship_level="warm",
    )
    opportunity = Opportunity(
        source="bdns",
        external_id="123",
        title="Ayudas a la digitalizacion",
        published_at=None,
        url=None,
        topic_tags=["innovacion", "digitalizacion"],
        region_hint="madrid",
    )

    score = compute_dispatch_score(
        company=company,
        matched_opportunities=[opportunity],
        calibration=DispatchCalibration(),
    )
    assert 0 <= score <= 1
    assert score > 0.6
