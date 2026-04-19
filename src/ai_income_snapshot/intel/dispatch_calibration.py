from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..models import Company, Opportunity
from ..utils import normalize_text


@dataclass(slots=True)
class DispatchCalibration:
    dispatch_weight: float = 0.30
    strategic_priority_weight: float = 0.30
    urgency_weight: float = 0.20
    ticket_weight: float = 0.20
    relationship_weight: float = 0.20
    sector_alignment_weight: float = 0.10
    target_ticket_min_eur: float = 750.0
    target_ticket_max_eur: float = 1200.0
    fallback_strategic_priority: int = 3
    fallback_urgency_level: int = 3
    relationship_scores: dict[str, float] = field(
        default_factory=lambda: {
            "cold": 0.30,
            "warm": 0.60,
            "hot": 0.90,
            "existing_client": 1.00,
        }
    )
    only_private_companies: bool = True
    min_estimated_ticket_eur: float = 0.0
    allowed_regions: list[str] = field(default_factory=list)
    excluded_name_keywords: list[str] = field(
        default_factory=lambda: [
            "ayuntamiento",
            "ministerio",
            "consejeria",
            "diputacion",
            "comunidad autonoma",
            "universidad",
            "consorcio",
            "mancomunidad",
            "cabildo",
            "fundacion publica",
            "entidad publica",
        ]
    )
    private_cif_prefixes: list[str] = field(default_factory=lambda: ["A", "B", "C", "D", "E", "F", "G", "J", "N", "W"])
    private_legal_forms: list[str] = field(
        default_factory=lambda: ["s.l.", "s.l", "sl", "s.a.", "s.a", "sa", "s.l.u.", "slu", "cooperativa"]
    )
    hot_threshold: float = 0.55
    warm_threshold: float = 0.38
    hot_dispatch_min: float = 0.55


def load_dispatch_calibration(path: str | Path | None) -> DispatchCalibration:
    if not path:
        return DispatchCalibration()

    config_path = Path(path)
    if not config_path.exists():
        return DispatchCalibration()

    with config_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    calibration = DispatchCalibration()
    calibration.dispatch_weight = float(raw.get("dispatch_weight", calibration.dispatch_weight))
    calibration.strategic_priority_weight = float(
        raw.get("strategic_priority_weight", calibration.strategic_priority_weight)
    )
    calibration.urgency_weight = float(raw.get("urgency_weight", calibration.urgency_weight))
    calibration.ticket_weight = float(raw.get("ticket_weight", calibration.ticket_weight))
    calibration.relationship_weight = float(raw.get("relationship_weight", calibration.relationship_weight))
    calibration.sector_alignment_weight = float(
        raw.get("sector_alignment_weight", calibration.sector_alignment_weight)
    )
    calibration.target_ticket_min_eur = float(raw.get("target_ticket_min_eur", calibration.target_ticket_min_eur))
    calibration.target_ticket_max_eur = float(raw.get("target_ticket_max_eur", calibration.target_ticket_max_eur))
    calibration.fallback_strategic_priority = int(
        raw.get("fallback_strategic_priority", calibration.fallback_strategic_priority)
    )
    calibration.fallback_urgency_level = int(raw.get("fallback_urgency_level", calibration.fallback_urgency_level))

    relationship_scores = raw.get("relationship_scores")
    if isinstance(relationship_scores, dict):
        calibration.relationship_scores = {
            normalize_text(str(key)): float(value) for key, value in relationship_scores.items()
        }

    calibration.only_private_companies = bool(raw.get("only_private_companies", calibration.only_private_companies))
    calibration.min_estimated_ticket_eur = float(
        raw.get("min_estimated_ticket_eur", calibration.min_estimated_ticket_eur)
    )

    allowed_regions = raw.get("allowed_regions")
    if isinstance(allowed_regions, list):
        calibration.allowed_regions = [normalize_text(str(region)) for region in allowed_regions if str(region).strip()]

    excluded_keywords = raw.get("excluded_name_keywords")
    if isinstance(excluded_keywords, list):
        calibration.excluded_name_keywords = [
            normalize_text(str(keyword)) for keyword in excluded_keywords if str(keyword).strip()
        ]

    private_prefixes = raw.get("private_cif_prefixes")
    if isinstance(private_prefixes, list):
        calibration.private_cif_prefixes = [str(prefix).strip().upper() for prefix in private_prefixes if str(prefix).strip()]

    private_legal_forms = raw.get("private_legal_forms")
    if isinstance(private_legal_forms, list):
        calibration.private_legal_forms = [
            normalize_text(str(legal_form)) for legal_form in private_legal_forms if str(legal_form).strip()
        ]

    calibration.hot_threshold = float(raw.get("hot_threshold", calibration.hot_threshold))
    calibration.warm_threshold = float(raw.get("warm_threshold", calibration.warm_threshold))
    calibration.hot_dispatch_min = float(raw.get("hot_dispatch_min", calibration.hot_dispatch_min))

    return calibration


def combine_with_dispatch(
    technical_score: float,
    dispatch_score: float,
    dispatch_weight: float,
) -> float:
    clamped_weight = _clamp(dispatch_weight)
    raw = technical_score * (1 - clamped_weight) + dispatch_score * clamped_weight
    return round(_clamp(raw), 4)


def compute_dispatch_score(
    company: Company,
    matched_opportunities: list[Opportunity],
    calibration: DispatchCalibration,
) -> float:
    strategic_score = _priority_score(company.strategic_priority, calibration.fallback_strategic_priority)
    urgency_score = _priority_score(company.urgency_level, calibration.fallback_urgency_level)
    ticket_score = _ticket_score(
        estimated_ticket=company.estimated_ticket_eur,
        target_min=calibration.target_ticket_min_eur,
        target_max=calibration.target_ticket_max_eur,
    )
    relationship_score = _relationship_score(company.relationship_level, calibration.relationship_scores)
    sector_alignment = _sector_alignment_score(company, matched_opportunities)

    total_weight = (
        calibration.strategic_priority_weight
        + calibration.urgency_weight
        + calibration.ticket_weight
        + calibration.relationship_weight
        + calibration.sector_alignment_weight
    )
    if total_weight <= 0:
        return 0.5

    weighted = (
        strategic_score * calibration.strategic_priority_weight
        + urgency_score * calibration.urgency_weight
        + ticket_score * calibration.ticket_weight
        + relationship_score * calibration.relationship_weight
        + sector_alignment * calibration.sector_alignment_weight
    ) / total_weight

    return round(_clamp(weighted), 4)


def _priority_score(value: int | None, fallback: int) -> float:
    level = fallback if value is None else value
    return _clamp(level / 5)


def _ticket_score(estimated_ticket: float | None, target_min: float, target_max: float) -> float:
    if estimated_ticket is None:
        return 0.5

    if target_min <= estimated_ticket <= target_max:
        return 1.0

    if estimated_ticket < target_min and target_min > 0:
        return _clamp(estimated_ticket / target_min)

    if estimated_ticket > target_max and estimated_ticket > 0:
        return _clamp(target_max / estimated_ticket)

    return 0.5


def _relationship_score(level: str | None, relationship_scores: dict[str, float]) -> float:
    if not level:
        return 0.4

    normalized = normalize_text(level)
    if normalized in relationship_scores:
        return _clamp(relationship_scores[normalized])

    return 0.4


def _sector_alignment_score(company: Company, matched_opportunities: list[Opportunity]) -> float:
    if not matched_opportunities:
        return 0.5

    top_opportunity = matched_opportunities[0]
    company_focus = {
        normalize_text(tag)
        for tag in (company.service_focus_tags or company.sector_tags)
        if normalize_text(tag)
    }
    opportunity_tags = {normalize_text(tag) for tag in top_opportunity.topic_tags if normalize_text(tag)}

    if not company_focus or not opportunity_tags:
        return 0.5

    shared = company_focus.intersection(opportunity_tags)
    return _clamp(len(shared) / len(company_focus))


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def passes_commercial_filters(company: Company, calibration: DispatchCalibration) -> bool:
    company_name = normalize_text(company.name)
    company_region = normalize_text(company.region)

    if any(keyword in company_name for keyword in calibration.excluded_name_keywords):
        return False

    if calibration.only_private_companies and not _looks_like_private_company(company, calibration):
        return False

    if calibration.min_estimated_ticket_eur > 0 and company.estimated_ticket_eur is not None:
        if company.estimated_ticket_eur < calibration.min_estimated_ticket_eur:
            return False

    if calibration.allowed_regions:
        if not any(region in company_region for region in calibration.allowed_regions):
            return False

    return True


def classify_lead_tier(
    final_score: float,
    dispatch_score: float,
    calibration: DispatchCalibration,
) -> str:
    if final_score >= calibration.hot_threshold and dispatch_score >= calibration.hot_dispatch_min:
        return "HOT"
    if final_score >= calibration.warm_threshold:
        return "WARM"
    return "COLD"


def suggest_next_action(lead_tier: str) -> str:
    actions = {
        "HOT": "Contacto directo en 24h con propuesta concreta y llamada agendada.",
        "WARM": "Contacto en 72h con email de valor + seguimiento telefónico ligero.",
        "COLD": "Nurturing: guardar en secuencia y revisar en próximo ciclo semanal.",
    }
    return actions.get(lead_tier, "Revisar manualmente.")


def _looks_like_private_company(company: Company, calibration: DispatchCalibration) -> bool:
    if company.cif:
        prefix = company.cif.strip().upper()[:1]
        if prefix and prefix in calibration.private_cif_prefixes:
            return True
        if prefix and prefix in {"P", "Q", "R", "S"}:
            return False

    company_name = normalize_text(company.name)
    return any(legal_form in company_name for legal_form in calibration.private_legal_forms)
