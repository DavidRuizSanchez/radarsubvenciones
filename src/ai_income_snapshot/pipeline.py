from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .clients.bdns_client import BDNSClient
from .clients.bocm_client import BOCMClient
from .clients.boe_client import BOEClient
from .config import DEFAULT_TOPICS, Settings, lookback_window
from .intel.dispatch_calibration import (
    classify_lead_tier,
    combine_with_dispatch,
    compute_dispatch_score,
    load_dispatch_calibration,
    passes_commercial_filters,
)
from .intel.contact_finder import ContactFinder
from .intel.matching import top_matches
from .intel.lead_explanations import (
    build_next_action,
    build_qualification_reason,
    summarize_top_opportunity,
)
from .intel.scoring import explain_score, history_score_from_awards, weighted_final_score
from .intel.website_guesser import guess_websites_bulk
from .intel.website_signals import WebsiteSignalAnalyzer
from .models import LeadScore, Opportunity
from .reporting import ensure_run_directory, write_leads_csv, write_markdown_summary, write_signals_csv
from .utils import load_companies_csv


@dataclass(slots=True)
class PipelineResult:
    run_directory: Path
    leads: list[LeadScore]
    opportunities_count: int
    bulletin_signals_count: int
    companies_count: int
    companies_input_count: int
    companies_filtered_out_count: int
    companies_source: str


class RadarCapitalPipeline:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.bdns = BDNSClient(self.settings)
        self.boe = BOEClient(base_url=self.settings.boe_base_url, timeout_seconds=self.settings.request_timeout_seconds)
        self.bocm = BOCMClient(base_url=self.settings.bocm_base_url, timeout_seconds=self.settings.request_timeout_seconds)
        self.web_analyzer = WebsiteSignalAnalyzer(timeout_seconds=self.settings.request_timeout_seconds)
        self.contact_finder = ContactFinder(timeout_seconds=self.settings.request_timeout_seconds)

    def run(
        self,
        companies_csv_path: str | Path | None = None,
        output_dir: str | Path = "outputs",
        topics: list[str] | None = None,
        calibration_file: str | Path | None = None,
        auto_discover_companies: bool = False,
        max_discovered_companies: int = 100,
        discovery_region_filter: str = "",
    ) -> PipelineResult:
        topics = topics or DEFAULT_TOPICS
        start_date, end_date = lookback_window(self.settings.lookback_days)
        opportunities = self.bdns.collect_target_opportunities(topics, start_date, end_date)
        dispatch_calibration = load_dispatch_calibration(calibration_file)

        companies_source = "csv"
        if auto_discover_companies:
            companies_source = "auto_discovery_bdns"
            companies = self.bdns.discover_companies_from_concessions(
                keywords=topics,
                start_date=start_date,
                end_date=end_date,
                max_companies=max_discovered_companies,
                region_filter=discovery_region_filter,
            )
            self._enrich_with_guessed_websites(companies)
        else:
            if companies_csv_path is None:
                raise ValueError(
                    "Falta el CSV de empresas. Define companies_csv_path o activa auto_discover_companies."
                )
            companies = load_companies_csv(companies_csv_path)

        if not companies:
            if auto_discover_companies:
                raise ValueError(
                    "No se han descubierto empresas automáticamente. "
                    "Prueba ampliando LOOKBACK_DAYS o quitando el filtro de región."
                )
            raise ValueError(
                "No se ha cargado ninguna empresa del CSV. "
                "Rellena al menos la columna 'name' (y recomendado: 'region', 'service_focus_tags')."
            )

        companies_input_count = len(companies)
        companies = [company for company in companies if passes_commercial_filters(company, dispatch_calibration)]
        companies_filtered_out_count = companies_input_count - len(companies)
        if not companies:
            raise ValueError(
                "Tras aplicar filtros comerciales no quedan empresas válidas. "
                "Ajusta reglas en calibración (privadas, región, ticket mínimo)."
            )

        bulletin_signals = self._collect_bulletin_signals(end_date)

        scored_leads: list[LeadScore] = []
        for company in companies:
            resolved_website = self.contact_finder.resolve_website(company.website, company.name)
            if resolved_website:
                company.website = resolved_website

            matches = top_matches(company, opportunities, top_n=5)
            matched_opps = [opportunity for opportunity, _ in matches]
            fit_score = matches[0][1] if matches else 0.0

            web_signal = self.web_analyzer.analyze(company.website)
            intent_score = web_signal.investment_signal_score

            awards_count = 0
            if company.cif:
                awards_count = self.bdns.historical_awards_count(company.cif)
            history_score = history_score_from_awards(awards_count)

            technical_score = weighted_final_score(
                fit_score=fit_score,
                intent_score=intent_score,
                history_score=history_score,
                fit_weight=self.settings.fit_weight,
                intent_weight=self.settings.intent_weight,
                history_weight=self.settings.history_weight,
            )
            dispatch_score = compute_dispatch_score(company, matched_opps, dispatch_calibration)
            final_score = combine_with_dispatch(
                technical_score=technical_score,
                dispatch_score=dispatch_score,
                dispatch_weight=dispatch_calibration.dispatch_weight,
            )
            lead_tier = classify_lead_tier(
                final_score=final_score,
                dispatch_score=dispatch_score,
                calibration=dispatch_calibration,
            )
            top_opportunity = matched_opps[0] if matched_opps else None
            top_opportunity_summary = summarize_top_opportunity(top_opportunity)
            contact_suggestion = self.contact_finder.suggest_contact(company.website, company.name)

            qualification_reason = build_qualification_reason(
                company=company,
                top_opportunity=top_opportunity,
                fit_score=fit_score,
                intent_score=intent_score,
                history_score=history_score,
                historical_awards_count=awards_count,
                dispatch_score=dispatch_score,
                website_signal_excerpt=web_signal.sample_excerpt,
            )
            next_action = build_next_action(
                company=company,
                lead_tier=lead_tier,
                top_opportunity=top_opportunity,
                suggested_contact_email=contact_suggestion.email,
                fit_score=fit_score,
                intent_score=intent_score,
                historical_awards_count=awards_count,
            )

            lead = LeadScore(
                company=company,
                fit_score=fit_score,
                intent_score=intent_score,
                history_score=history_score,
                technical_score=technical_score,
                dispatch_score=dispatch_score,
                dispatch_weight=dispatch_calibration.dispatch_weight,
                final_score=final_score,
                lead_tier=lead_tier,
                next_action=next_action,
                top_opportunity_summary=top_opportunity_summary,
                qualification_reason=qualification_reason,
                suggested_contact_email=contact_suggestion.email,
                contact_email_confidence=contact_suggestion.confidence,
                contact_email_source=contact_suggestion.source,
                reasons=[],
                matched_opportunities=matched_opps,
                historical_awards_count=awards_count,
                website_signal_excerpt=web_signal.sample_excerpt,
            )
            lead.reasons = explain_score(lead)
            scored_leads.append(lead)

        scored_leads.sort(key=lambda item: item.final_score, reverse=True)

        run_directory = ensure_run_directory(output_dir)
        write_leads_csv(run_directory / "leads.csv", scored_leads)
        write_signals_csv(run_directory / "boletines_signals.csv", bulletin_signals)
        write_markdown_summary(run_directory / "resumen.md", scored_leads, bulletin_signals)

        return PipelineResult(
            run_directory=run_directory,
            leads=scored_leads,
            opportunities_count=len(opportunities),
            bulletin_signals_count=len(bulletin_signals),
            companies_count=len(companies),
            companies_input_count=companies_input_count,
            companies_filtered_out_count=companies_filtered_out_count,
            companies_source=companies_source,
        )

    def _enrich_with_guessed_websites(self, companies: list) -> None:
        """Adivina website para empresas auto-descubiertas que lleguen sin web."""
        pending = [company for company in companies if not company.website]
        if not pending:
            return

        guesses = guess_websites_bulk([company.name for company in pending])
        for company in pending:
            url = guesses.get(company.name.strip())
            if url:
                company.website = url

    def _collect_bulletin_signals(self, target_date: date) -> list[Opportunity]:
        signals: list[Opportunity] = []
        seen_ids: set[tuple[str, str]] = set()

        boe_days_to_scan = max(1, min(10, self.settings.lookback_days))
        for delta in range(boe_days_to_scan):
            day = target_date - timedelta(days=delta)
            try:
                boe_day_signals = self.boe.extract_subsidy_signals(day)
            except Exception:
                # El BOE puede no tener edición para ciertas fechas; se ignora para no romper el pipeline.
                continue
            self._append_unique_signals(signals, boe_day_signals, seen_ids)

        try:
            bocm_signals = self.bocm.fetch_latest_subsidy_signals()
            self._append_unique_signals(signals, bocm_signals, seen_ids)
        except Exception:
            # Si falla BOCM, mantenemos resiliencia.
            pass

        return signals

    @staticmethod
    def _append_unique_signals(
        accumulator: list[Opportunity],
        candidates: list[Opportunity],
        seen_ids: set[tuple[str, str]],
    ) -> None:
        for signal in candidates:
            signal_key = (signal.source, signal.external_id or signal.title)
            if signal_key in seen_ids:
                continue
            seen_ids.add(signal_key)
            accumulator.append(signal)
