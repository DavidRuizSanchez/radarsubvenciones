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
            # Sin web → score neutral y excerpt vacío (no se cita en el pitch).
            return SignalAnalysis(
                investment_signal_score=0.35,
                matched_terms=[],
                word_count=0,
                sample_excerpt="",
            )

        try:
            html = self.http.get_text(website_url, retries=1)
        except Exception:  # noqa: BLE001
            # La web bloquea o no responde: score conservador y excerpt vacío
            # para que el pitch comercial no cite el mensaje de error.
            return SignalAnalysis(
                investment_signal_score=0.30,
                matched_terms=[],
                word_count=0,
                sample_excerpt="",
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
        company_summary = extract_company_summary(html, visible_text)

        return SignalAnalysis(
            investment_signal_score=score,
            matched_terms=matched_terms,
            word_count=len(words),
            sample_excerpt=excerpt,
            company_summary=company_summary,
        )


def extract_visible_text(html: str) -> str:
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
    cleaned = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", cleaned)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


_META_DESCRIPTION_PATTERNS = [
    re.compile(r'<meta[^>]+name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*name=["\']description["\']', re.IGNORECASE),
]

_TITLE_PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def extract_company_summary(html: str, visible_text: str, max_chars: int = 320) -> str:
    """Resumen corto de a qué se dedica la empresa.

    Orden de preferencia: meta description > og:description > <title> > primeras
    frases del texto visible. Todo saneado a una línea y truncado.
    """
    for pattern in _META_DESCRIPTION_PATTERNS:
        match = pattern.search(html)
        if match:
            candidate = _clean_inline(unescape(match.group(1)))
            if len(candidate) >= 30:
                return _truncate(candidate, max_chars)

    title_match = _TITLE_PATTERN.search(html)
    if title_match:
        title = _clean_inline(unescape(title_match.group(1)))
        if len(title) >= 15:
            return _truncate(title, max_chars)

    if visible_text:
        snippet = _clean_inline(visible_text)
        if snippet:
            return _truncate(snippet, max_chars)

    return ""


def _clean_inline(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[: max_chars - 1].rstrip(" ,.;:-")
    return cut + "…"
