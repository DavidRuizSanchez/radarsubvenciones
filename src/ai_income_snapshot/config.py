from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(slots=True)
class Settings:
    # API real de BDNS — la única que devuelve JSON. Solo soporta vpd=GE,
    # pero ese endpoint estatal ya agrega concesiones de todas las CCAA
    # (cada registro lleva nivel1=AUTONOMICA/ESTATAL y nivel2 con la región).
    bdns_base_url: str = os.getenv("BDNS_BASE_URL", "https://www.infosubvenciones.es/bdnstrans/api")
    boe_base_url: str = os.getenv("BOE_BASE_URL", "https://www.boe.es/datosabiertos/api")
    bocm_base_url: str = os.getenv("BOCM_BASE_URL", "https://www.bocm.es")
    vpd: str = os.getenv("SNPSAP_VPD", "GE")
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
    max_pages_per_keyword: int = int(os.getenv("MAX_PAGES_PER_KEYWORD", "2"))
    page_size: int = int(os.getenv("PAGE_SIZE", "50"))

    # Peso del scoring
    fit_weight: float = float(os.getenv("FIT_WEIGHT", "0.45"))
    intent_weight: float = float(os.getenv("INTENT_WEIGHT", "0.35"))
    history_weight: float = float(os.getenv("HISTORY_WEIGHT", "0.20"))

    # Lookback para convocatorias
    lookback_days: int = int(os.getenv("LOOKBACK_DAYS", "45"))


DEFAULT_TOPICS = [
    "digitalizacion",
    "innovacion",
    "eficiencia energetica",
    "industria",
    "sostenibilidad",
    "descarbonizacion",
]


def lookback_window(days: int) -> tuple[date, date]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date
