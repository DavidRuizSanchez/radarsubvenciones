from ai_income_snapshot.intel.lead_explanations import (
    build_next_action,
    build_qualification_reason,
    summarize_top_opportunity,
)
from ai_income_snapshot.models import Company, Opportunity


def test_summarize_top_opportunity_includes_key_fields():
    opportunity = Opportunity(
        source="bdns",
        external_id="123",
        title="Ayudas a la digitalizacion de pymes industriales",
        published_at=None,
        url="https://example.com",
        topic_tags=["digitalizacion", "industria"],
        region_hint="madrid",
    )
    summary = summarize_top_opportunity(opportunity)
    assert "digitalizacion" in summary.lower()
    assert "ámbito" in summary.lower()


def test_build_qualification_reason_mentions_fit_and_history():
    company = Company(
        company_id="1",
        name="Empresa Demo SL",
        region="Madrid",
        estimated_ticket_eur=900,
    )
    opportunity = Opportunity(
        source="bdns",
        external_id="456",
        title="Subvención a innovación",
        published_at=None,
        url=None,
        topic_tags=["innovacion"],
        region_hint="madrid",
    )

    reason = build_qualification_reason(
        company=company,
        top_opportunity=opportunity,
        fit_score=0.30,
        intent_score=0.55,
        history_score=0.80,
        historical_awards_count=4,
    )

    assert "encaje" in reason.lower()
    assert "histórico" in reason.lower()


def test_build_qualification_reason_is_personalized_with_company_and_opportunity():
    company = Company(
        company_id="2",
        name="Talleres Norte SL",
        region="Madrid",
        cnae="2562",
        website="https://talleresnorte.example",
    )
    opportunity = Opportunity(
        source="bdns",
        external_id="BDNS-789",
        title="Ayudas a proyectos de descarbonizacion industrial",
        published_at=None,
        url=None,
        topic_tags=["descarbonizacion", "industria"],
        region_hint="Comunidad de Madrid",
    )

    reason = build_qualification_reason(
        company=company,
        top_opportunity=opportunity,
        fit_score=0.34,
        intent_score=0.61,
        history_score=0.10,
        historical_awards_count=0,
        dispatch_score=0.73,
        website_signal_excerpt="Proyecto de renovacion de linea de produccion con ahorro energetico.",
    )

    assert "bdns-789" in reason.lower()
    assert "cnae 2562" in reason.lower()
    assert "prioridad comercial alta" in reason.lower()


def test_build_next_action_includes_specific_contact_and_opportunity():
    company = Company(company_id="3", name="Metalurgica Sur", region="Madrid")
    opportunity = Opportunity(
        source="bdns",
        external_id="BDNS-999",
        title="Convocatoria de digitalizacion de procesos industriales",
        published_at=None,
        url=None,
        topic_tags=["digitalizacion"],
        region_hint="Madrid",
    )

    action = build_next_action(
        company=company,
        lead_tier="HOT",
        top_opportunity=opportunity,
        suggested_contact_email="direccion@metalurgicasur.example",
        fit_score=0.31,
        intent_score=0.52,
        historical_awards_count=2,
    )

    assert "hoy" in action.lower()
    assert "direccion@metalurgicasur.example" in action.lower()
    assert "bdns-999" in action.lower()
    assert "concesiones previas" in action.lower()
