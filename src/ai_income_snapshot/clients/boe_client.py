from __future__ import annotations

from datetime import date
from typing import Any

from ..models import Opportunity
from ..utils import normalize_text
from .bdns_client import infer_topic_tags
from .http import SimpleHttpClient


class BOEClient:
    def __init__(self, base_url: str = "https://www.boe.es/datosabiertos/api", timeout_seconds: int = 25):
        self.base_url = base_url.rstrip("/")
        self.http = SimpleHttpClient(timeout_seconds=timeout_seconds)

    def fetch_sumario(self, target_date: date) -> dict[str, Any]:
        url = f"{self.base_url}/boe/sumario/{target_date.strftime('%Y%m%d')}"
        return self.http.get_json(url, headers={"Accept": "application/json"})

    def extract_subsidy_signals(self, target_date: date) -> list[Opportunity]:
        payload = self.fetch_sumario(target_date)
        diarios = payload.get("data", {}).get("sumario", {}).get("diario", [])
        signals: list[Opportunity] = []

        for diario in ensure_list(diarios):
            for seccion in ensure_list(diario.get("seccion", [])):
                for departamento in ensure_list(seccion.get("departamento", [])):
                    epigrafes = departamento.get("epigrafe")
                    if not epigrafes and isinstance(departamento.get("texto"), dict):
                        epigrafes = departamento.get("texto", {}).get("epigrafe")

                    for epigrafe in ensure_list(epigrafes or []):
                        for item in ensure_list(epigrafe.get("item", [])):
                            title = " ".join(str(item.get("titulo", "")).split())
                            if not is_subsidy_title(title):
                                continue

                            identifier = item.get("identificador", "")
                            url_html = item.get("url_html")
                            if isinstance(url_html, dict):
                                url_html = url_html.get("texto")

                            signals.append(
                                Opportunity(
                                    source="boe",
                                    external_id=str(identifier),
                                    title=title,
                                    published_at=target_date,
                                    url=url_html,
                                    topic_tags=infer_topic_tags(title),
                                    region_hint=None,
                                )
                            )

        return signals


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def is_subsidy_title(title: str) -> bool:
    normalized = normalize_text(title)
    return any(term in normalized for term in ["subvenc", "ayuda", "incentivo", "financiacion"])
