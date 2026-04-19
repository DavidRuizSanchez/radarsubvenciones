from __future__ import annotations

from ..models import LeadScore


def history_score_from_awards(total_awards: int) -> float:
    if total_awards <= 0:
        return 0.2
    if total_awards <= 3:
        return 0.5
    if total_awards <= 15:
        return 0.8
    return 0.65


def weighted_final_score(
    fit_score: float,
    intent_score: float,
    history_score: float,
    fit_weight: float,
    intent_weight: float,
    history_weight: float,
) -> float:
    total_weight = fit_weight + intent_weight + history_weight
    if total_weight <= 0:
        return 0.0
    raw = (
        fit_score * fit_weight
        + intent_score * intent_weight
        + history_score * history_weight
    ) / total_weight
    return round(max(0.0, min(1.0, raw)), 4)


def explain_score(lead: LeadScore) -> list[str]:
    reasons = [
        f"Encaje oportunidad-empresa: {lead.fit_score:.2f}",
        f"Señales de inversión web: {lead.intent_score:.2f}",
        f"Histórico BDNS del CIF: {lead.history_score:.2f} ({lead.historical_awards_count} concesiones)",
        f"Score técnico total: {lead.technical_score:.2f}",
        f"Score despacho: {lead.dispatch_score:.2f} (peso {lead.dispatch_weight:.2f})",
        f"Semáforo comercial: {lead.lead_tier}",
    ]
    if lead.matched_opportunities:
        reasons.append(f"Mejor convocatoria detectada: {lead.matched_opportunities[0].external_id}")
    return reasons
