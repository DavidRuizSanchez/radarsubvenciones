from __future__ import annotations

from datetime import date
import re
from typing import Any

from ..config import Settings
from ..models import Company, Opportunity
from ..utils import normalize_text, to_ddmmyyyy
from .http import SimpleHttpClient


class BDNSClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.http = SimpleHttpClient(timeout_seconds=settings.request_timeout_seconds)

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.settings.bdns_base_url.rstrip('/')}/{path.lstrip('/')}"
        return self.http.get_json(url, params=params)

    def search_convocatorias(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        page: int = 0,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        params = {
            "vpd": self.settings.vpd,
            "page": page,
            "pageSize": page_size or self.settings.page_size,
            "descripcion": keyword,
            "descripcionTipoBusqueda": 2,
            "fechaDesde": to_ddmmyyyy(start_date.isoformat()),
            "fechaHasta": to_ddmmyyyy(end_date.isoformat()),
            "order": "fechaRecepcion",
            "direccion": "desc",
        }
        return self._get("convocatorias/busqueda", params)

    def search_convocatorias_with_region(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        region_id: int,
        page: int = 0,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        params = {
            "vpd": self.settings.vpd,
            "page": page,
            "pageSize": page_size or self.settings.page_size,
            "descripcion": keyword,
            "descripcionTipoBusqueda": 2,
            "fechaDesde": to_ddmmyyyy(start_date.isoformat()),
            "fechaHasta": to_ddmmyyyy(end_date.isoformat()),
            "regiones": region_id,
            "order": "fechaRecepcion",
            "direccion": "desc",
        }
        return self._get("convocatorias/busqueda", params)

    def collect_target_opportunities(
        self,
        keywords: list[str],
        start_date: date,
        end_date: date,
    ) -> list[Opportunity]:
        opportunities_by_id: dict[str, Opportunity] = {}

        for keyword in keywords:
            for page in range(self.settings.max_pages_per_keyword):
                payload = self.search_convocatorias(keyword, start_date, end_date, page=page)
                records = payload.get("content", [])
                for record in records:
                    external_id = str(record.get("numeroConvocatoria", "")).strip()
                    if not external_id:
                        continue

                    published = record.get("fechaRecepcion")
                    published_at = None
                    if published:
                        published_at = date.fromisoformat(published)

                    title = " ".join(str(record.get("descripcion", "")).split())
                    topic_tags = infer_topic_tags(title)
                    region_hint = normalize_text(record.get("nivel1", "") or "")

                    opportunities_by_id[external_id] = Opportunity(
                        source="bdns",
                        external_id=external_id,
                        title=title,
                        published_at=published_at,
                        url=f"https://www.infosubvenciones.es/bdnstrans/GE/es/convocatoria/{external_id}",
                        topic_tags=topic_tags,
                        region_hint=region_hint,
                    )

                if payload.get("last", True):
                    break

        return list(opportunities_by_id.values())

    def historical_awards_count(self, cif: str) -> int:
        clean_cif = cif.strip().upper()
        if not clean_cif:
            return 0

        payload = self._get(
            "concesiones/busqueda",
            {
                "vpd": self.settings.vpd,
                "nifCif": clean_cif,
                "page": 0,
                "pageSize": 1,
            },
        )
        return int(payload.get("totalElements", 0) or 0)

    def discover_companies_from_concessions(
        self,
        keywords: list[str],
        start_date: date,
        end_date: date,
        max_companies: int = 100,
        region_filter: str = "",
    ) -> list[Company]:
        companies_by_key: dict[str, Company] = {}
        normalized_region_filter = normalize_text(region_filter)

        for keyword in keywords:
            for page in range(self.settings.max_pages_per_keyword):
                payload = self._get(
                    "concesiones/busqueda",
                    {
                        "vpd": self.settings.vpd,
                        "page": page,
                        "pageSize": self.settings.page_size,
                        "descripcion": keyword,
                        "descripcionTipoBusqueda": 2,
                        "fechaRegInicio": to_ddmmyyyy(start_date.isoformat()),
                        "fechaRegFin": to_ddmmyyyy(end_date.isoformat()),
                        "order": "fechaConcesion",
                        "direccion": "desc",
                    },
                )
                records = payload.get("content", [])
                for record in records:
                    discovered = _company_from_concesion_record(record)
                    if discovered is None:
                        continue

                    if normalized_region_filter and normalized_region_filter not in normalize_text(discovered.region):
                        # Filtro simple por región textual para control en interfaz.
                        continue

                    discovered.sector_tags = sorted(
                        set(discovered.sector_tags + infer_topic_tags(record.get("convocatoria", "")))
                    )

                    unique_key = discovered.cif or normalize_text(discovered.name)
                    if unique_key in companies_by_key:
                        existing = companies_by_key[unique_key]
                        existing.sector_tags = sorted(set(existing.sector_tags + discovered.sector_tags))
                        continue

                    companies_by_key[unique_key] = discovered
                    if len(companies_by_key) >= max_companies:
                        return list(companies_by_key.values())

                if payload.get("last", True):
                    break

        return list(companies_by_key.values())


def _company_from_concesion_record(record: dict[str, Any]) -> Company | None:
    raw_beneficiary = " ".join(str(record.get("beneficiario", "")).split())
    if not raw_beneficiary:
        return None

    parsed_cif, parsed_name = split_beneficiary(raw_beneficiary)
    if not parsed_name:
        return None

    source_region = " ".join(
        part for part in [str(record.get("nivel1", "")).strip(), str(record.get("nivel2", "")).strip()] if part
    )
    source_region = source_region or "N/D"
    person_id = str(record.get("idPersona", "")).strip()
    company_id = person_id if person_id else normalize_text(parsed_name).replace(" ", "-")

    importe = record.get("importe")
    estimated_ticket = None
    if isinstance(importe, (int, float)):
        estimated_ticket = float(importe)

    return Company(
        company_id=company_id,
        name=parsed_name,
        region=source_region,
        cif=parsed_cif,
        website=None,
        sector_tags=[],
        service_focus_tags=[],
        preferred_regions=[],
        strategic_priority=3,
        urgency_level=3,
        estimated_ticket_eur=estimated_ticket,
        relationship_level="cold",
        notes="Descubierta automáticamente desde BDNS/concesiones",
    )


def split_beneficiary(raw_value: str) -> tuple[str | None, str]:
    cleaned = " ".join(raw_value.split())
    first_token, separator, rest = cleaned.partition(" ")
    if not separator:
        return None, cleaned
    cif_candidate = first_token.upper()
    name = rest.strip()

    looks_like_code = bool(re.fullmatch(r"[A-Z0-9*]{7,16}", cif_candidate))
    contains_digit = any(char.isdigit() for char in cif_candidate)
    if not looks_like_code or not contains_digit:
        return None, cleaned
    if "*" in cif_candidate:
        return None, name

    return cif_candidate, name


def infer_topic_tags(title: str) -> list[str]:
    text = normalize_text(title)
    tags: set[str] = set()
    mapping = {
        "digitalizacion": ["digital", "software", "ia", "automatiz", "cloud", "ciber"],
        "innovacion": ["innov", "i+d", "investig", "tecnolog"],
        "eficiencia_energetica": ["eficiencia energetica", "energia", "descarbon", "renovable"],
        "industria": ["industria", "manufactura", "produccion", "planta"],
        "sostenibilidad": ["sostenibilidad", "economia circular", "residu", "ambiental"],
    }

    for tag, hints in mapping.items():
        if any(hint in text for hint in hints):
            tags.add(tag)

    if "subvenc" in text or "ayuda" in text:
        tags.add("subvencion")

    return sorted(tags)
