from __future__ import annotations

import re
from html import unescape

from ..models import SignalAnalysis
from ..utils import normalize_text
from ..clients.http import SimpleHttpClient


INVESTMENT_HINTS = [
    "inversion",
    "inversiones",
    "plan estrategico",
    "nuevo proyecto",
    "i+d",
    "investigacion",
    "digitalizacion",
    "automatizacion",
    "descarbonizacion",
    "eficiencia energetica",
    "expansion",
    "ampliacion",
]


class WebsiteSignalAnalyzer:
    def __init__(self, timeout_seconds: int = 20):
        self.http = SimpleHttpClient(timeout_seconds=timeout_seconds)

    def analyze(self, website_url: str | None) -> SignalAnalysis:
        if not website_url:
            return SignalAnalysis(
                investment_signal_score=0.35,
                matched_terms=[],
                word_count=0,
                sample_excerpt="Sin web en el CSV de entrada: score neutral por defecto.",
            )

        try:
            html = self.http.get_text(website_url, headers={"User-Agent": "RadarCapitalPublico/0.1"}, retries=1)
        except Exception as error:  # noqa: BLE001
            return SignalAnalysis(
                investment_signal_score=0.30,
                matched_terms=[],
                word_count=0,
                sample_excerpt=f"No se pudo leer la web ({error}). Score conservador.",
            )

        visible_text = extract_visible_text(html)
        normalized = normalize_text(visible_text)
        matched_terms = sorted({hint for hint in INVESTMENT_HINTS if hint in normalized})

        weighted_hits = 0
        for hint in matched_terms:
            if hint in {"i+d", "plan estrategico", "nuevo proyecto", "digitalizacion"}:
                weighted_hits += 2
            else:
                weighted_hits += 1

        score = min(1.0, max(0.15, weighted_hits / 10))
        words = re.findall(r"\b\w+\b", normalized)
        excerpt = " ".join(words[:60])

        return SignalAnalysis(
            investment_signal_score=score,
            matched_terms=matched_terms,
            word_count=len(words),
            sample_excerpt=excerpt,
        )


def extract_visible_text(html: str) -> str:
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
    cleaned = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", cleaned)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()
