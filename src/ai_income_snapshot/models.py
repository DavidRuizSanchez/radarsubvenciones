from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class Company:
    company_id: str
    name: str
    region: str
    cnae: str | None = None
    cif: str | None = None
    website: str | None = None
    sector_tags: list[str] = field(default_factory=list)
    service_focus_tags: list[str] = field(default_factory=list)
    preferred_regions: list[str] = field(default_factory=list)
    strategic_priority: int | None = None
    urgency_level: int | None = None
    estimated_ticket_eur: float | None = None
    relationship_level: str | None = None
    notes: str | None = None


@dataclass(slots=True)
class Opportunity:
    source: str
    external_id: str
    title: str
    published_at: date | None
    url: str | None
    topic_tags: list[str] = field(default_factory=list)
    region_hint: str | None = None


@dataclass(slots=True)
class SignalAnalysis:
    investment_signal_score: float
    matched_terms: list[str]
    word_count: int
    sample_excerpt: str
    company_summary: str = ""


@dataclass(slots=True)
class LeadScore:
    company: Company
    fit_score: float
    intent_score: float
    history_score: float
    technical_score: float
    dispatch_score: float
    dispatch_weight: float
    final_score: float
    lead_tier: str
    next_action: str
    top_opportunity_summary: str
    qualification_reason: str
    suggested_contact_email: str
    contact_email_confidence: float
    contact_email_source: str
    reasons: list[str]
    matched_opportunities: list[Opportunity]
    historical_awards_count: int
    website_signal_excerpt: str
    company_summary: str = ""
