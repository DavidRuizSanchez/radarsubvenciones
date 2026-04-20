"""Adivina el website oficial de una empresa a partir de su razón social.

Usado en auto-discovery BDNS, donde BDNS no publica el dominio corporativo.
Solo devuelve una URL si responde HTTP 2xx/3xx — nunca inventa un dominio.
"""
from __future__ import annotations

import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Sufijos societarios a eliminar del nombre antes de generar slug.
LEGAL_SUFFIXES = [
    "sociedad limitada laboral",
    "sociedad limitada unipersonal",
    "sociedad anonima",
    "sociedad cooperativa",
    "sociedad limitada",
    "sociedad mercantil",
    "sociedad civil",
    "comunidad de bienes",
    "sucursal en espana",
    "s l l",
    "s l u",
    "s l p",
    "s c p",
    "s coop",
    "s l",
    "s a",
    "slu",
    "sll",
    "scp",
    "slp",
    "sl",
    "sa",
    "srl",
    "cb",
    "lim",
    "limitada",
    "anonima",
    "cooperativa",
    "sociedad",
]

# TLDs a probar, en orden de preferencia.
CANDIDATE_TLDS = [".es", ".com"]


def slugify_company_name(name: str) -> str:
    """Quita acentos, sufijos societarios y caracteres raros. Devuelve slug compacto."""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    # Elimina puntuación común pero mantiene espacios para detectar sufijos.
    normalized = re.sub(r"[.,;:()\"'/\\]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Quita sufijos societarios (ordenados por longitud desc para evitar matches parciales).
    for suffix in sorted(LEGAL_SUFFIXES, key=len, reverse=True):
        pattern = rf"(?:\s|^){re.escape(suffix)}\b"
        normalized = re.sub(pattern, " ", normalized)

    normalized = re.sub(r"\s+", " ", normalized).strip()
    # Compacta a alfanumérico, sin espacios.
    slug = re.sub(r"[^a-z0-9]", "", normalized)
    return slug


def candidate_urls(name: str) -> list[str]:
    """Genera URLs candidatas a probar. Vacío si el slug no es viable."""
    slug = slugify_company_name(name)
    if len(slug) < 4:
        return []

    urls: list[str] = []
    for tld in CANDIDATE_TLDS:
        urls.append(f"https://www.{slug}{tld}")
    return urls


def probe_url(url: str, timeout_seconds: float = 4.0) -> bool:
    """True si la URL responde con status 2xx/3xx. False si falla o 4xx/5xx."""
    try:
        response = requests.head(
            url,
            timeout=timeout_seconds,
            allow_redirects=True,
            headers={"User-Agent": BROWSER_USER_AGENT},
        )
    except requests.RequestException:
        return False
    return 200 <= response.status_code < 400


def guess_website_for_company(name: str, timeout_seconds: float = 4.0) -> str | None:
    """Prueba URLs candidatas en orden y devuelve la primera que responde."""
    for url in candidate_urls(name):
        if probe_url(url, timeout_seconds=timeout_seconds):
            return url
    return None


def guess_websites_bulk(
    names: list[str],
    max_workers: int = 10,
    timeout_seconds: float = 4.0,
) -> dict[str, str]:
    """Adivina websites para una lista de nombres en paralelo. Devuelve {nombre: url}."""
    results: dict[str, str] = {}
    unique_names = list({name.strip() for name in names if name and name.strip()})

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_name = {
            executor.submit(guess_website_for_company, name, timeout_seconds): name
            for name in unique_names
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                url = future.result()
            except Exception:  # noqa: BLE001
                url = None
            if url:
                results[name] = url
    return results
