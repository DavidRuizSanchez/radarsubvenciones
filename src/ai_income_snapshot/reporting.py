from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .models import LeadScore, Opportunity


def ensure_run_directory(base_output_dir: str | Path) -> Path:
    root = Path(base_output_dir)
    root.mkdir(parents=True, exist_ok=True)
    run_dir = root / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_leads_csv(path: Path, leads: list[LeadScore]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "company_id",
                "company_name",
                "company_website",
                "cif",
                "region",
                "fit_score",
                "intent_score",
                "history_score",
                "technical_score",
                "dispatch_score",
                "dispatch_weight",
                "final_score",
                "lead_tier",
                "next_action",
                "suggested_contact_email",
                "contact_email_confidence",
                "contact_email_source",
                "top_opportunity_summary",
                "qualification_reason",
                "historical_awards_count",
                "top_opportunity_id",
                "top_opportunity_title",
                "top_opportunity_url",
            ]
        )

        for lead in leads:
            top = lead.matched_opportunities[0] if lead.matched_opportunities else None
            writer.writerow(
                [
                    lead.company.company_id,
                    lead.company.name,
                    lead.company.website or "",
                    lead.company.cif or "",
                    lead.company.region,
                    f"{lead.fit_score:.4f}",
                    f"{lead.intent_score:.4f}",
                    f"{lead.history_score:.4f}",
                    f"{lead.technical_score:.4f}",
                    f"{lead.dispatch_score:.4f}",
                    f"{lead.dispatch_weight:.4f}",
                    f"{lead.final_score:.4f}",
                    lead.lead_tier,
                    sanitize_inline_text(lead.next_action),
                    lead.suggested_contact_email,
                    f"{lead.contact_email_confidence:.3f}",
                    lead.contact_email_source,
                    sanitize_inline_text(lead.top_opportunity_summary),
                    sanitize_inline_text(lead.qualification_reason),
                    lead.historical_awards_count,
                    top.external_id if top else "",
                    sanitize_inline_text(top.title) if top else "",
                    top.url if top else "",
                ]
            )


def write_signals_csv(path: Path, signals: list[Opportunity]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["source", "external_id", "published_at", "title", "url", "topic_tags"])
        for signal in signals:
            writer.writerow(
                [
                    signal.source,
                    signal.external_id,
                    signal.published_at.isoformat() if signal.published_at else "",
                    sanitize_inline_text(signal.title),
                    signal.url or "",
                    ";".join(signal.topic_tags),
                ]
            )


def write_markdown_summary(path: Path, leads: list[LeadScore], bulletins: list[Opportunity]) -> None:
    with path.open("w", encoding="utf-8") as file:
        file.write("# Radar de Capital Público - Snapshot\n\n")
        file.write(f"Leads priorizados: **{len(leads)}**\n\n")

        file.write("## Top 10 Leads\n\n")
        for index, lead in enumerate(leads[:10], start=1):
            file.write(f"### {index}. {lead.company.name} ({lead.final_score:.2f})\n")
            file.write(f"- Región: {lead.company.region}\n")
            file.write(f"- CIF: {lead.company.cif or 'N/D'}\n")
            file.write(f"- Razones: {' | '.join(lead.reasons)}\n")
            file.write(f"- Por qué califica: {lead.qualification_reason}\n")
            file.write(f"- Resumen convocatoria: {lead.top_opportunity_summary}\n")
            file.write(f"- Siguiente acción: {lead.next_action}\n")
            file.write(
                f"- Email sugerido: {lead.suggested_contact_email or 'N/D'} "
                f"(confianza {lead.contact_email_confidence:.2f}, fuente: {lead.contact_email_source})\n"
            )
            file.write(f"- Extracto web: {lead.website_signal_excerpt[:280]}\n")

            if lead.matched_opportunities:
                top = lead.matched_opportunities[0]
                top_title = sanitize_inline_text(top.title)
                file.write(f"- Convocatoria top: {top.external_id} - {top_title}\n")
                if top.url:
                    file.write(f"- URL: {top.url}\n")

            file.write("\n")

        file.write("## Señales BOE/BOCM\n\n")
        if not bulletins:
            file.write("Sin señales de ayudas detectadas en la última lectura de boletines.\n")
            return

        for signal in bulletins[:30]:
            date_text = signal.published_at.isoformat() if signal.published_at else "N/D"
            signal_title = sanitize_inline_text(signal.title)
            file.write(f"- [{signal.source.upper()}][{date_text}] {signal.external_id}: {signal_title}\n")
            if signal.url:
                file.write(f"  - {signal.url}\n")


def sanitize_inline_text(value: str) -> str:
    return " ".join(value.split())
