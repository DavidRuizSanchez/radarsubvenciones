from ai_income_snapshot.intel.matching import lexical_match_score
from ai_income_snapshot.models import Company, Opportunity


def test_lexical_match_non_zero_on_shared_terms():
    company = Company(
        company_id="1",
        name="Eco Digital Madrid",
        region="Madrid",
        sector_tags=["digitalizacion", "eficiencia energetica"],
    )
    opportunity = Opportunity(
        source="bdns",
        external_id="123",
        title="Ayudas a la digitalizacion y eficiencia energetica de pymes en Madrid",
        published_at=None,
        url=None,
        topic_tags=["digitalizacion", "eficiencia_energetica"],
        region_hint="madrid",
    )

    score = lexical_match_score(company, opportunity)
    assert score > 0
