from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urljoin, urlparse

from ..clients.http import SimpleHttpClient

EMAIL_REGEX = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", flags=re.IGNORECASE)

GENERIC_LOCALS_PRIORITY = [
    "subvenciones",
    "ayudas",
    "grants",
    "licitaciones",
    "comercial",
    "ventas",
    "contact",
    "contacto",
    "info",
    "hola",
    "hello",
    "administracion",
]

BLACKLIST_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "domain.com",
    "correo.com",
}

CONTACT_PATHS = [
    "",
    "/contacto",
    "/contact",
    "/contact-us",
    "/empresa/contacto",
    "/about/contact",
]


@dataclass(slots=True)
class ContactSuggestion:
    email: str
    confidence: float
    source: str
    alternatives: list[str]


class ContactFinder:
    def __init__(self, timeout_seconds: int = 20):
        self.http = SimpleHttpClient(timeout_seconds=timeout_seconds)

    def suggest_contact(self, website_url: str | None, company_name: str = "") -> ContactSuggestion:
        if not website_url:
            return ContactSuggestion(
                email="",
                confidence=0.0,
                source="sin_web",
                alternatives=[],
            )

        normalized_base_url = ensure_url(website_url)
        domain = extract_domain(normalized_base_url)
        if not domain:
            return ContactSuggestion(
                email="",
                confidence=0.0,
                source="url_no_valida",
                alternatives=[],
            )

        candidates: list[tuple[str, float, str]] = []
        visited_urls: set[str] = set()
        for path in CONTACT_PATHS:
            target_url = normalized_base_url if path == "" else urljoin(normalized_base_url, path)
            if target_url in visited_urls:
                continue
            visited_urls.add(target_url)
            try:
                html = self.http.get_text(target_url, headers={"User-Agent": "RadarCapitalPublico/0.1"}, retries=1)
            except Exception:  # noqa: BLE001
                continue

            emails = extract_emails_from_text(html)
            for email in emails:
                score = score_email_candidate(email, domain)
                if score > 0:
                    candidates.append((email, score, target_url))

        if candidates:
            candidates.sort(key=lambda item: item[1], reverse=True)
            best_email, best_score, best_source = candidates[0]
            alternatives = [email for email, _, _ in candidates[1:4]]
            return ContactSuggestion(
                email=best_email,
                confidence=round(best_score, 3),
                source=best_source,
                alternatives=alternatives,
            )

        inferred = infer_domain_email(domain, company_name)
        if inferred:
            return ContactSuggestion(
                email=inferred,
                confidence=0.22,
                source="inferido_dominio",
                alternatives=[f"info@{domain}", f"contacto@{domain}", f"comercial@{domain}"],
            )

        return ContactSuggestion(
            email="",
            confidence=0.0,
            source="sin_email_detectado",
            alternatives=[],
        )


def extract_emails_from_text(text: str) -> list[str]:
    matches = EMAIL_REGEX.findall(text)
    clean: list[str] = []
    seen: set[str] = set()

    for match in matches:
        email = sanitize_email(match)
        if not email:
            continue

        if email in seen:
            continue

        seen.add(email)
        clean.append(email)

    return clean


def sanitize_email(raw_email: str) -> str:
    email = raw_email.strip().lower()
    email = email.rstrip(".,;:\")'>]")
    if "@" not in email:
        return ""

    local, _, domain = email.partition("@")
    if not local or not domain:
        return ""

    if domain in BLACKLIST_DOMAINS:
        return ""

    if domain.startswith("localhost"):
        return ""

    return f"{local}@{domain}"


def score_email_candidate(email: str, site_domain: str) -> float:
    local, _, domain = email.partition("@")
    score = 0.35

    if domain == site_domain:
        score += 0.30
    elif domain.endswith(f".{site_domain}"):
        score += 0.20
    else:
        score -= 0.10

    if any(keyword in local for keyword in GENERIC_LOCALS_PRIORITY):
        score += 0.25

    if any(flag in local for flag in ["noreply", "no-reply", "do-not-reply"]):
        score -= 0.35

    if local.startswith("ventas") or local.startswith("comercial"):
        score += 0.08

    return max(0.0, min(1.0, score))


def infer_domain_email(domain: str, company_name: str = "") -> str:
    if not domain or domain in BLACKLIST_DOMAINS:
        return ""

    preferred_locals = ["contacto", "info", "comercial"]
    if "abogado" in company_name.lower() or "legal" in company_name.lower():
        preferred_locals.insert(0, "subvenciones")

    return f"{preferred_locals[0]}@{domain}"


def ensure_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        return ""

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    return url


def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
    except Exception:  # noqa: BLE001
        return ""

    netloc = (parsed.netloc or "").lower().strip()
    if not netloc:
        return ""

    if netloc.startswith("www."):
        netloc = netloc[4:]

    return netloc
