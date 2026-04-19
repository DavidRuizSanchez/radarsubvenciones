from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

from .models import Company


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value.strip().lower())


def split_tags(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[;,|]", value)
    return [normalize_text(part) for part in parts if part.strip()]


def load_companies_csv(path: str | Path) -> list[Company]:
    companies: list[Company] = []
    with Path(path).open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            company = Company(
                company_id=row.get("company_id", "").strip() or row.get("name", "").strip(),
                name=row.get("name", "").strip(),
                region=row.get("region", "").strip(),
                cnae=row.get("cnae", "").strip() or None,
                cif=row.get("cif", "").strip() or None,
                website=row.get("website", "").strip() or None,
                sector_tags=split_tags(row.get("sector_tags")),
                service_focus_tags=split_tags(row.get("service_focus_tags")),
                preferred_regions=split_tags(row.get("preferred_regions")),
                strategic_priority=parse_int(row.get("strategic_priority")),
                urgency_level=parse_int(row.get("urgency_level")),
                estimated_ticket_eur=parse_float(row.get("estimated_ticket_eur")),
                relationship_level=row.get("relationship_level", "").strip() or None,
                notes=row.get("notes", "").strip() or None,
            )
            if company.name:
                companies.append(company)
    return companies


def to_ddmmyyyy(iso_date: str) -> str:
    # iso_date esperado: YYYY-MM-DD
    year, month, day = iso_date.split("-")
    return f"{day}/{month}/{year}"


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    clean = value.strip()
    if not clean:
        return None
    try:
        return int(clean)
    except ValueError:
        return None


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    clean = value.strip().replace(",", ".")
    if not clean:
        return None
    try:
        return float(clean)
    except ValueError:
        return None
