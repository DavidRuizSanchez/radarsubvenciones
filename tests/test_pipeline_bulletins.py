from datetime import date, timedelta

from ai_income_snapshot.config import Settings
from ai_income_snapshot.models import Opportunity
from ai_income_snapshot.pipeline import RadarCapitalPipeline


class FakeBOE:
    def __init__(self, signals_by_day: dict[date, list[Opportunity]], failing_days: set[date] | None = None):
        self.signals_by_day = signals_by_day
        self.failing_days = failing_days or set()
        self.calls: list[date] = []

    def extract_subsidy_signals(self, target_date: date) -> list[Opportunity]:
        self.calls.append(target_date)
        if target_date in self.failing_days:
            raise RuntimeError("Sin edición BOE")
        return self.signals_by_day.get(target_date, [])


class FakeBOCM:
    def __init__(self, signals: list[Opportunity]):
        self.signals = signals
        self.calls = 0

    def fetch_latest_subsidy_signals(self) -> list[Opportunity]:
        self.calls += 1
        return self.signals


def test_collect_bulletin_signals_scans_recent_days_and_deduplicates():
    settings = Settings(lookback_days=5)
    pipeline = RadarCapitalPipeline(settings=settings)

    target_day = date(2026, 4, 20)
    repeated_signal = Opportunity(
        source="boe",
        external_id="BOE-A-1",
        title="Ayudas a la innovación",
        published_at=target_day - timedelta(days=1),
        url=None,
        topic_tags=["innovacion"],
        region_hint=None,
    )
    second_signal = Opportunity(
        source="boe",
        external_id="BOE-A-2",
        title="Subvenciones para digitalización",
        published_at=target_day - timedelta(days=2),
        url=None,
        topic_tags=["digitalizacion"],
        region_hint=None,
    )
    bocm_signal = Opportunity(
        source="bocm",
        external_id="BOCM-1",
        title="Ayudas para eficiencia energética",
        published_at=target_day - timedelta(days=2),
        url=None,
        topic_tags=["eficiencia energetica"],
        region_hint="madrid",
    )

    fake_boe = FakeBOE(
        signals_by_day={
            target_day - timedelta(days=1): [repeated_signal],
            target_day - timedelta(days=2): [repeated_signal, second_signal],
        },
        failing_days={target_day},
    )
    fake_bocm = FakeBOCM(signals=[bocm_signal])

    pipeline.boe = fake_boe
    pipeline.bocm = fake_bocm

    signals = pipeline._collect_bulletin_signals(target_day)

    assert len(fake_boe.calls) == 5
    assert fake_bocm.calls == 1
    assert len(signals) == 3
    assert [signal.external_id for signal in signals] == ["BOE-A-1", "BOE-A-2", "BOCM-1"]


def test_collect_bulletin_signals_caps_scan_to_ten_days():
    settings = Settings(lookback_days=45)
    pipeline = RadarCapitalPipeline(settings=settings)
    target_day = date(2026, 4, 20)

    fake_boe = FakeBOE(signals_by_day={})
    fake_bocm = FakeBOCM(signals=[])
    pipeline.boe = fake_boe
    pipeline.bocm = fake_bocm

    pipeline._collect_bulletin_signals(target_day)

    assert len(fake_boe.calls) == 10
