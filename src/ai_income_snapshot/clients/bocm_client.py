from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date

from ..models import Opportunity
from ..utils import normalize_text
from .bdns_client import infer_topic_tags
from .http import SimpleHttpClient


class BOCMClient:
    def __init__(self, base_url: str = "https://www.bocm.es", timeout_seconds: int = 25):
        self.base_url = base_url.rstrip("/")
        self.http = SimpleHttpClient(timeout_seconds=timeout_seconds)

    def latest_sumario_xml_url(self) -> str:
        homepage = self.http.get_text(f"{self.base_url}/")
        match = re.search(
            r"/boletin/CM_Boletin_BOCM/\d{4}/\d{2}/\d{2}/BOCM-\d+\.xml",
            homepage,
            flags=re.IGNORECASE,
        )
        if not match:
            raise RuntimeError("No se encontro URL de sumario XML en la portada del BOCM")
        return f"{self.base_url}{match.group(0)}"

    def fetch_latest_subsidy_signals(self) -> list[Opportunity]:
        xml_url = self.latest_sumario_xml_url()
        xml_content = self.http.get_text(xml_url)
        root = ET.fromstring(xml_content)

        date_text = root.findtext("./metadatos/fecha_publicacion")
        published_at = None
        if date_text:
            # El XML usa formato YYYY/MM/DD
            published_at = date.fromisoformat(date_text.replace("/", "-"))

        signals: list[Opportunity] = []
        for node in root.findall(".//disposicion"):
            title = " ".join((node.findtext("titulo") or "").split())
            if not title:
                continue
            if not is_subsidy_title(title):
                continue

            identifier = (node.findtext("identificador") or "").strip()
            url_html = (node.findtext("url_html") or "").strip() or None

            signals.append(
                Opportunity(
                    source="bocm",
                    external_id=identifier,
                    title=title,
                    published_at=published_at,
                    url=url_html,
                    topic_tags=infer_topic_tags(title),
                    region_hint="madrid",
                )
            )

        return signals


def is_subsidy_title(title: str) -> bool:
    normalized = normalize_text(title)
    return any(term in normalized for term in ["subvenc", "ayuda", "incentivo", "financiacion"])
