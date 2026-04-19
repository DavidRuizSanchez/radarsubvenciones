from __future__ import annotations

from datetime import datetime
import sqlite3
from pathlib import Path
from typing import Any

from .models import LeadScore

STATUS_OPTIONS = [
    "NUEVO",
    "CONTACTADO",
    "RESPONDIDO",
    "REUNION",
    "OFERTA",
    "CERRADO_GANADO",
    "CERRADO_PERDIDO",
    "DESCARTADO",
]

CHANNEL_OPTIONS = ["email", "telefono", "linkedin", "whatsapp", "otro"]


def init_sales_db(db_path: str | Path) -> None:
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    with _connect(db_file) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                run_directory TEXT NOT NULL,
                companies_source TEXT NOT NULL,
                companies_input_count INTEGER NOT NULL,
                companies_count INTEGER NOT NULL,
                companies_filtered_out_count INTEGER NOT NULL,
                opportunities_count INTEGER NOT NULL,
                bulletin_signals_count INTEGER NOT NULL,
                topics TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS commercial_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                company_id TEXT,
                company_name TEXT NOT NULL,
                cif TEXT,
                region TEXT,
                final_score REAL NOT NULL,
                lead_tier TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'NUEVO',
                suggested_contact_email TEXT,
                contact_email_confidence REAL,
                contact_email_source TEXT,
                opportunity_id TEXT,
                opportunity_title TEXT,
                opportunity_url TEXT,
                opportunity_summary TEXT,
                qualification_reason TEXT,
                next_action TEXT,
                commercial_pitch TEXT,
                notes TEXT DEFAULT '',
                last_contact_channel TEXT DEFAULT '',
                next_follow_up_date TEXT DEFAULT '',
                updated_at TEXT NOT NULL,
                UNIQUE(run_id, company_id, opportunity_id)
            )
            """
        )


def save_run_and_leads(
    db_path: str | Path,
    run_metadata: dict[str, Any],
    leads: list[LeadScore],
) -> None:
    timestamp = _now_iso()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO runs (
                run_id,
                created_at,
                run_directory,
                companies_source,
                companies_input_count,
                companies_count,
                companies_filtered_out_count,
                opportunities_count,
                bulletin_signals_count,
                topics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_metadata["run_id"],
                timestamp,
                run_metadata["run_directory"],
                run_metadata["companies_source"],
                run_metadata["companies_input_count"],
                run_metadata["companies_count"],
                run_metadata["companies_filtered_out_count"],
                run_metadata["opportunities_count"],
                run_metadata["bulletin_signals_count"],
                run_metadata.get("topics", ""),
            ),
        )

        for lead in leads:
            top = lead.matched_opportunities[0] if lead.matched_opportunities else None
            conn.execute(
                """
                INSERT INTO commercial_leads (
                    run_id,
                    company_id,
                    company_name,
                    cif,
                    region,
                    final_score,
                    lead_tier,
                    status,
                    suggested_contact_email,
                    contact_email_confidence,
                    contact_email_source,
                    opportunity_id,
                    opportunity_title,
                    opportunity_url,
                    opportunity_summary,
                    qualification_reason,
                    next_action,
                    commercial_pitch,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, company_id, opportunity_id)
                DO UPDATE SET
                    final_score=excluded.final_score,
                    lead_tier=excluded.lead_tier,
                    suggested_contact_email=excluded.suggested_contact_email,
                    contact_email_confidence=excluded.contact_email_confidence,
                    contact_email_source=excluded.contact_email_source,
                    opportunity_title=excluded.opportunity_title,
                    opportunity_url=excluded.opportunity_url,
                    opportunity_summary=excluded.opportunity_summary,
                    qualification_reason=excluded.qualification_reason,
                    next_action=excluded.next_action,
                    commercial_pitch=excluded.commercial_pitch,
                    updated_at=excluded.updated_at
                """,
                (
                    run_metadata["run_id"],
                    lead.company.company_id,
                    lead.company.name,
                    lead.company.cif or "",
                    lead.company.region,
                    lead.final_score,
                    lead.lead_tier,
                    "NUEVO",
                    lead.suggested_contact_email,
                    lead.contact_email_confidence,
                    lead.contact_email_source,
                    top.external_id if top else "",
                    top.title if top else "",
                    top.url if top else "",
                    lead.top_opportunity_summary,
                    lead.qualification_reason,
                    lead.next_action,
                    build_default_pitch(lead),
                    timestamp,
                ),
            )


def list_runs(db_path: str | Path, limit: int = 25) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                run_id,
                created_at,
                run_directory,
                companies_source,
                companies_input_count,
                companies_count,
                companies_filtered_out_count,
                opportunities_count,
                bulletin_signals_count,
                topics
            FROM runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_run(db_path: str | Path, run_id: str) -> dict[str, Any] | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                run_id,
                created_at,
                run_directory,
                companies_source,
                companies_input_count,
                companies_count,
                companies_filtered_out_count,
                opportunities_count,
                bulletin_signals_count,
                topics
            FROM runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

    return dict(row) if row else None


def get_leads_for_run(db_path: str | Path, run_id: str) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                run_id,
                company_id,
                company_name,
                cif,
                region,
                final_score,
                lead_tier,
                status,
                suggested_contact_email,
                contact_email_confidence,
                contact_email_source,
                opportunity_id,
                opportunity_title,
                opportunity_url,
                opportunity_summary,
                qualification_reason,
                next_action,
                commercial_pitch,
                notes,
                last_contact_channel,
                next_follow_up_date,
                updated_at
            FROM commercial_leads
            WHERE run_id = ?
            ORDER BY final_score DESC, id ASC
            """,
            (run_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def update_lead_progress(
    db_path: str | Path,
    lead_id: int,
    status: str,
    notes: str,
    channel: str,
    next_follow_up_date: str,
) -> None:
    normalized_status = status if status in STATUS_OPTIONS else "NUEVO"
    normalized_channel = channel if channel in CHANNEL_OPTIONS else ""

    with _connect(db_path) as conn:
        conn.execute(
            """
            UPDATE commercial_leads
            SET
                status = ?,
                notes = ?,
                last_contact_channel = ?,
                next_follow_up_date = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                normalized_status,
                notes.strip(),
                normalized_channel,
                next_follow_up_date.strip(),
                _now_iso(),
                lead_id,
            ),
        )


def funnel_stats(db_path: str | Path, run_id: str) -> dict[str, Any]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM commercial_leads
            WHERE run_id = ?
            GROUP BY status
            """,
            (run_id,),
        ).fetchall()

        tier_rows = conn.execute(
            """
            SELECT lead_tier, COUNT(*) AS total
            FROM commercial_leads
            WHERE run_id = ?
            GROUP BY lead_tier
            """,
            (run_id,),
        ).fetchall()

    status_map = {status: 0 for status in STATUS_OPTIONS}
    for row in rows:
        status_map[row["status"]] = int(row["total"])

    tier_map = {"HOT": 0, "WARM": 0, "COLD": 0}
    for row in tier_rows:
        tier_map[row["lead_tier"]] = int(row["total"])

    return {
        "status": status_map,
        "tier": tier_map,
        "total": sum(status_map.values()),
    }


def build_default_pitch(lead: LeadScore) -> str:
    top = lead.matched_opportunities[0] if lead.matched_opportunities else None
    conv = f"{top.external_id} - {top.title}" if top else "convocatoria no identificada"

    return (
        f"Hola, he detectado una oportunidad de subvención que puede encajar con {lead.company.name}: {conv}. "
        f"Resumen: {lead.top_opportunity_summary} "
        f"Motivo de encaje: {lead.qualification_reason}"
    )


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
