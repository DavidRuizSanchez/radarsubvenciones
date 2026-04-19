from datetime import date

from ai_income_snapshot.models import Company, LeadScore, Opportunity
from ai_income_snapshot.sales_process import (
    funnel_stats,
    get_leads_for_run,
    get_run,
    init_sales_db,
    list_runs,
    save_run_and_leads,
    update_lead_progress,
)


def build_sample_lead() -> LeadScore:
    company = Company(
        company_id="cmp-001",
        name="Empresa Demo",
        region="Madrid",
        cif="B12345678",
        website="https://empresa-demo.example",
    )
    opportunity = Opportunity(
        source="bdns",
        external_id="BDNS-2026-0001",
        title="Programa de digitalizacion pyme",
        published_at=date(2026, 4, 20),
        url="https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/000001",
        topic_tags=["digitalizacion"],
        region_hint="Madrid",
    )
    return LeadScore(
        company=company,
        fit_score=0.9,
        intent_score=0.8,
        history_score=0.5,
        technical_score=0.9,
        dispatch_score=0.7,
        dispatch_weight=0.2,
        final_score=0.84,
        lead_tier="HOT",
        next_action="Llamar en 24h",
        top_opportunity_summary="Ayuda para digitalizacion con cobertura del 45%.",
        qualification_reason="Encaja por CNAE y por señales de inversion en su web.",
        suggested_contact_email="contacto@empresa-demo.example",
        contact_email_confidence=0.8,
        contact_email_source="website",
        reasons=["encaje sectorial", "proyecto activo"],
        matched_opportunities=[opportunity],
        historical_awards_count=2,
        website_signal_excerpt="Proyecto de modernizacion de procesos",
    )


def test_save_and_update_commercial_process(tmp_path):
    db_path = tmp_path / "sales_pipeline.db"
    init_sales_db(db_path)

    lead = build_sample_lead()
    save_run_and_leads(
        db_path=db_path,
        run_metadata={
            "run_id": "20260420_120000",
            "run_directory": "outputs/20260420_120000",
            "companies_source": "auto_discovery_bdns",
            "companies_input_count": 1,
            "companies_count": 1,
            "companies_filtered_out_count": 0,
            "opportunities_count": 1,
            "bulletin_signals_count": 1,
            "topics": "digitalizacion",
        },
        leads=[lead],
    )

    runs = list_runs(db_path)
    assert len(runs) == 1
    assert runs[0]["run_id"] == "20260420_120000"

    run_info = get_run(db_path, "20260420_120000")
    assert run_info is not None
    assert run_info["companies_count"] == 1

    leads = get_leads_for_run(db_path, "20260420_120000")
    assert len(leads) == 1
    assert leads[0]["status"] == "NUEVO"
    assert leads[0]["company_name"] == "Empresa Demo"
    assert leads[0]["suggested_contact_email"] == "contacto@empresa-demo.example"

    stats_before = funnel_stats(db_path, "20260420_120000")
    assert stats_before["status"]["NUEVO"] == 1
    assert stats_before["status"]["CONTACTADO"] == 0
    assert stats_before["tier"]["HOT"] == 1

    lead_id = int(leads[0]["id"])
    update_lead_progress(
        db_path=db_path,
        lead_id=lead_id,
        status="CONTACTADO",
        notes="Primer email enviado",
        channel="email",
        next_follow_up_date="2026-04-22",
    )

    updated = get_leads_for_run(db_path, "20260420_120000")[0]
    assert updated["status"] == "CONTACTADO"
    assert updated["last_contact_channel"] == "email"
    assert updated["next_follow_up_date"] == "2026-04-22"
    assert updated["notes"] == "Primer email enviado"

    stats_after = funnel_stats(db_path, "20260420_120000")
    assert stats_after["status"]["NUEVO"] == 0
    assert stats_after["status"]["CONTACTADO"] == 1


def test_update_lead_progress_normalizes_invalid_values(tmp_path):
    db_path = tmp_path / "sales_pipeline.db"
    init_sales_db(db_path)

    lead = build_sample_lead()
    save_run_and_leads(
        db_path=db_path,
        run_metadata={
            "run_id": "20260420_130000",
            "run_directory": "outputs/20260420_130000",
            "companies_source": "csv",
            "companies_input_count": 1,
            "companies_count": 1,
            "companies_filtered_out_count": 0,
            "opportunities_count": 1,
            "bulletin_signals_count": 0,
            "topics": "",
        },
        leads=[lead],
    )

    lead_id = int(get_leads_for_run(db_path, "20260420_130000")[0]["id"])
    update_lead_progress(
        db_path=db_path,
        lead_id=lead_id,
        status="ESTADO_RARO",
        notes="  nota de prueba  ",
        channel="fax",
        next_follow_up_date="2026-04-23",
    )

    updated = get_leads_for_run(db_path, "20260420_130000")[0]
    assert updated["status"] == "NUEVO"
    assert updated["last_contact_channel"] == ""
    assert updated["notes"] == "nota de prueba"
