from __future__ import annotations

from ..models import Company, Opportunity
from ..utils import normalize_text


def summarize_top_opportunity(opportunity: Opportunity | None) -> str:
    if opportunity is None:
        return "Sin convocatoria priorizada para este lead."

    tags_text = ", ".join(opportunity.topic_tags[:3]) if opportunity.topic_tags else "subvención empresarial"
    date_text = opportunity.published_at.isoformat() if opportunity.published_at else "fecha no disponible"
    region_text = opportunity.region_hint or "ámbito no especificado"
    title_short = trim_sentence(opportunity.title, max_chars=150)

    return (
        f"{title_short}. Enfoque: {tags_text}. "
        f"Publicada: {date_text}. Ámbito: {region_text}."
    )


def build_qualification_reason(
    company: Company,
    top_opportunity: Opportunity | None,
    fit_score: float,
    intent_score: float,
    history_score: float,
    historical_awards_count: int,
    dispatch_score: float = 0.0,
    website_signal_excerpt: str = "",
) -> str:
    reasons: list[str] = []

    if top_opportunity:
        reasons.append(
            f"{company.name} encaja con convocatoria {top_opportunity.external_id} ({trim_sentence(top_opportunity.title, max_chars=90)})"
        )

        if top_opportunity.topic_tags:
            topic_text = ", ".join(top_opportunity.topic_tags[:2])
            reasons.append(f"encaje en líneas {topic_text}")

    if company.cnae:
        reasons.append(f"CNAE {company.cnae} informado")

    if fit_score >= 0.25:
        reasons.append(f"encaje temático alto ({fit_score:.2f})")
    elif fit_score >= 0.15:
        reasons.append(f"encaje temático razonable ({fit_score:.2f})")
    else:
        reasons.append(f"encaje temático bajo ({fit_score:.2f}), requiere validación manual")

    if intent_score >= 0.50:
        reasons.append(f"la web muestra señales claras de inversión ({intent_score:.2f})")
    elif intent_score >= 0.30:
        reasons.append(f"hay señales moderadas de inversión en la web ({intent_score:.2f})")
    elif company.website:
        reasons.append(f"señales web limitadas ({intent_score:.2f})")

    if website_signal_excerpt and intent_score >= 0.30:
        reasons.append(f"extracto detectado: \"{trim_sentence(website_signal_excerpt, max_chars=72)}\"")

    if historical_awards_count > 0 and history_score >= 0.5:
        reasons.append(f"histórico BDNS positivo ({historical_awards_count} concesiones)")
    elif historical_awards_count == 0:
        reasons.append("sin concesiones históricas detectadas en BDNS")

    if company.estimated_ticket_eur and company.estimated_ticket_eur >= 750:
        reasons.append(f"ticket potencial {company.estimated_ticket_eur:.0f}€ alineado con servicio")

    if top_opportunity and _region_alignment(company, top_opportunity):
        reasons.append(f"alineación geográfica ({company.region} ↔ {top_opportunity.region_hint})")

    if dispatch_score >= 0.65:
        reasons.append(f"prioridad comercial alta ({dispatch_score:.2f})")
    elif dispatch_score >= 0.45:
        reasons.append(f"prioridad comercial media ({dispatch_score:.2f})")

    if not reasons:
        return "Calificado por señal base del modelo, pendiente revisión manual."

    return "; ".join(reasons[:12]).capitalize() + "."


def build_next_action(
    company: Company,
    lead_tier: str,
    top_opportunity: Opportunity | None,
    suggested_contact_email: str,
    fit_score: float,
    intent_score: float,
    historical_awards_count: int,
) -> str:
    if lead_tier == "HOT":
        timing = "Hoy"
    elif lead_tier == "WARM":
        timing = "En 48h"
    else:
        timing = "Esta semana"

    if suggested_contact_email:
        channel = f"enviar email a {suggested_contact_email}"
    else:
        channel = "contactar por teléfono/LinkedIn y localizar email del responsable"

    if top_opportunity:
        opp_reference = f"{top_opportunity.external_id} ({trim_sentence(top_opportunity.title, max_chars=65)})"
    else:
        opp_reference = "la convocatoria priorizada detectada por el radar"

    if historical_awards_count > 0:
        proof = f"mencionar sus {historical_awards_count} concesiones previas para reforzar elegibilidad"
    else:
        proof = "incluir checklist de elegibilidad para validar requisitos en primera llamada"

    if fit_score < 0.18:
        qualification_step = "antes de enviar propuesta, validar CNAE y alcance territorial"
    elif intent_score >= 0.5:
        qualification_step = "proponer llamada de 15 min con foco en proyecto activo detectado en su web"
    else:
        qualification_step = "abrir conversación de diagnóstico y confirmar plan de inversión 2026"

    return (
        f"{timing} para {company.name}: {channel}, citando {opp_reference}; "
        f"{proof}; {qualification_step}."
    )


def trim_sentence(text: str, max_chars: int = 150) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


def _region_alignment(company: Company, opportunity: Opportunity) -> bool:
    company_region = normalize_text(company.region)
    opp_region = normalize_text(opportunity.region_hint or "")
    if not company_region or not opp_region:
        return False

    # heurística simple para detectar coincidencia parcial
    return company_region in opp_region or opp_region in company_region
