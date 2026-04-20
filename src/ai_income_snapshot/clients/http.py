from __future__ import annotations

import time
from typing import Any

import requests


DEFAULT_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class SimpleHttpClient:
    def __init__(self, timeout_seconds: int = 45):
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": DEFAULT_BROWSER_USER_AGENT,
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.9,*/*;q=0.8",
            }
        )

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        retries: int = 2,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                return response.json()
            except Exception as error:  # noqa: BLE001
                last_error = error
                if attempt < retries:
                    time.sleep(1.2 * (attempt + 1))

        raise RuntimeError(f"Fallo HTTP GET {url}: {last_error}")

    def get_text(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        retries: int = 2,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                return response.text
            except Exception as error:  # noqa: BLE001
                last_error = error
                if attempt < retries:
                    time.sleep(1.2 * (attempt + 1))

        raise RuntimeError(f"Fallo HTTP GET {url}: {last_error}")
