"""Gestor in-memory de jobs del pipeline.

Pensado para ejecuciones lanzadas desde la interfaz web: cada ejecución del
pipeline se registra con un ``job_id`` y el backend puede pollear su estado.
No persiste (los jobs viven en memoria del proceso Flask); al reiniciar el
servidor se pierden. Suficiente para el MVP.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class JobState:
    job_id: str
    status: str = "pending"   # pending | running | completed | failed
    stage: str = "Preparando ejecución…"
    progress_current: int = 0
    progress_total: int = 0
    result_run_id: str = ""
    error_message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        total = self.progress_total or 0
        current = self.progress_current or 0
        percent = int(round(100 * current / total)) if total else 0
        return {
            "job_id": self.job_id,
            "status": self.status,
            "stage": self.stage,
            "progress_current": current,
            "progress_total": total,
            "progress_percent": max(0, min(100, percent)),
            "result_run_id": self.result_run_id,
            "error_message": self.error_message,
            "extra": self.extra,
        }


class JobTracker:
    """Almacén thread-safe de estados de job. Acceso vía ``set_*`` y ``get``."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, JobState] = {}

    def create(self) -> JobState:
        job = JobState(job_id=uuid4().hex)
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> JobState | None:
        with self._lock:
            return self._jobs.get(job_id)

    def set_stage(self, job_id: str, stage: str, total: int | None = None, current: int | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.stage = stage
            if total is not None:
                job.progress_total = total
            if current is not None:
                job.progress_current = current
            if job.status == "pending":
                job.status = "running"

    def set_progress(self, job_id: str, current: int, total: int | None = None, stage: str | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.progress_current = current
            if total is not None:
                job.progress_total = total
            if stage is not None:
                job.stage = stage
            if job.status == "pending":
                job.status = "running"

    def mark_completed(self, job_id: str, result_run_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "completed"
            job.stage = "Completado"
            job.result_run_id = result_run_id
            if job.progress_total:
                job.progress_current = job.progress_total

    def mark_failed(self, job_id: str, error_message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "failed"
            job.error_message = error_message
            job.stage = "Error"
