from ai_income_snapshot.intel.dispatch_calibration import (
    DispatchCalibration,
    classify_lead_tier,
    passes_commercial_filters,
)
from ai_income_snapshot.models import Company


def test_filters_drop_public_entity_by_name():
    calibration = DispatchCalibration()
    company = Company(company_id="1", name="AYUNTAMIENTO DE MADRID", region="Madrid", cif="P2807900B")
    assert not passes_commercial_filters(company, calibration)


def test_filters_accept_private_company_by_cif_prefix():
    calibration = DispatchCalibration()
    company = Company(company_id="2", name="MECANIZADOS DEMO", region="Madrid", cif="B12345678")
    assert passes_commercial_filters(company, calibration)


def test_lead_tier_classification():
    calibration = DispatchCalibration(hot_threshold=0.62, warm_threshold=0.45, hot_dispatch_min=0.60)
    assert classify_lead_tier(0.70, 0.70, calibration) == "HOT"
    assert classify_lead_tier(0.50, 0.30, calibration) == "WARM"
    assert classify_lead_tier(0.30, 0.80, calibration) == "COLD"
