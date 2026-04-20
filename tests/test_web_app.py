from ai_income_snapshot.jobs import JobTracker
from ai_income_snapshot.web_app import create_app, is_safe_run_id, parse_positive_int, parse_topics


def test_parse_topics_ignores_empty_values():
    topics = parse_topics("digitalizacion, innovacion, ,eficiencia energetica")
    assert topics == ["digitalizacion", "innovacion", "eficiencia energetica"]


def test_is_safe_run_id_allows_expected_pattern():
    assert is_safe_run_id("20260420_003556")
    assert is_safe_run_id("run-001")
    assert not is_safe_run_id("../etc")
    assert not is_safe_run_id("../../secret")


def test_parse_positive_int_uses_default_for_invalid_input():
    assert parse_positive_int("20", default=99) == 20
    assert parse_positive_int("0", default=99) == 99
    assert parse_positive_int("-2", default=99) == 99
    assert parse_positive_int("texto", default=99) == 99


def test_job_tracker_exposes_progress_percent():
    tracker = JobTracker()
    job = tracker.create()
    tracker.set_progress(job.job_id, current=25, total=100, stage="Analizando…")
    state = tracker.get(job.job_id).as_dict()
    assert state["status"] == "running"
    assert state["progress_percent"] == 25
    assert state["stage"] == "Analizando…"

    tracker.mark_completed(job.job_id, "run-xyz")
    state = tracker.get(job.job_id).as_dict()
    assert state["status"] == "completed"
    assert state["result_run_id"] == "run-xyz"


def test_pipeline_progress_endpoint_returns_404_for_unknown_job(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    app = create_app()
    client = app.test_client()
    response = client.get("/pipeline/progress/ghost-id")
    assert response.status_code == 404
