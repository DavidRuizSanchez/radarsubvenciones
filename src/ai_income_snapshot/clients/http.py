from __future__ import annotations

import time
from typing import Any

import requests


class SimpleHttpClient:
    def __init__(self, timeout_seconds: int = 25):
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

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
