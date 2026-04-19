from __future__ import annotations

import re
from collections import Counter

from ..models import Company, Opportunity
from ..utils import normalize_text


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    tokens = re.findall(r"[a-z0-9]{3,}", normalized)
    return [token for token in tokens if token not in STOPWORDS]


def company_profile_terms(company: Company) -> list[str]:
    terms = []
    terms.extend(tokenize(company.name))
    terms.extend(tokenize(company.region))
    if company.cnae:
        terms.extend(tokenize(company.cnae))
    for tag in company.sector_tags:
        terms.extend(tokenize(tag))
    return terms


def opportunity_terms(opportunity: Opportunity) -> list[str]:
    terms = tokenize(opportunity.title)
    terms.extend(tokenize(" ".join(opportunity.topic_tags)))
    if opportunity.region_hint:
        terms.extend(tokenize(opportunity.region_hint))
    return terms


def lexical_match_score(company: Company, opportunity: Opportunity) -> float:
    company_terms = company_profile_terms(company)
    opp_terms = opportunity_terms(opportunity)
    if not company_terms or not opp_terms:
        return 0.0

    company_counter = Counter(company_terms)
    opp_counter = Counter(opp_terms)
    shared_terms = set(company_counter).intersection(opp_counter)
    overlap = sum(min(company_counter[term], opp_counter[term]) for term in shared_terms)
    denominator = max(len(company_terms), len(opp_terms), 1)
    base_score = overlap / denominator

    # Bonus ligero por coincidencia geográfica cuando hay pista regional.
    company_region = normalize_text(company.region)
    region_bonus = 0.0
    if company_region and opportunity.region_hint and company_region in normalize_text(opportunity.region_hint):
        region_bonus = 0.1

    return min(base_score + region_bonus, 1.0)


def top_matches(company: Company, opportunities: list[Opportunity], top_n: int = 5) -> list[tuple[Opportunity, float]]:
    scored = [(opportunity, lexical_match_score(company, opportunity)) for opportunity in opportunities]
    scored.sort(key=lambda item: item[1], reverse=True)
    # Devuelve al menos una oportunidad si existe catálogo.
    if scored and scored[0][1] == 0:
        return scored[:1]
    return [item for item in scored[:top_n] if item[1] > 0.0]


STOPWORDS = {
    "para",
    "con",
    "por",
    "las",
    "los",
    "del",
    "que",
    "una",
    "uno",
    "como",
    "desde",
    "sobre",
    "esta",
    "este",
    "subvencion",
    "subvenciones",
    "ayudas",
    "convocatoria",
    "convocatorias",
}
