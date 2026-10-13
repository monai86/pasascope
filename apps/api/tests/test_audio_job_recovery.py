from __future__ import annotations

from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import JobStatus, ProcessingJob
from app.services.audio_job_service import (
    _ensure_no_active_job_for_audio_artifact,
    recover_interrupted_jobs,
)
from app.tasks.job_queue import MemoryJobQueue

SESSION_ID = "session_demo_001"


def _job(repo: MockRepository, job_id: str, status: JobStatus, *, transcription: bool = True) -> ProcessingJob:
    details: dict = {"audio_file_id": f"audio_{job_id}", "status_history": [status.value]}
    if transcription:
        details["queued_payload"] = {"audio_id": f"audio_{job_id}", "provider": "mock"}
    job = ProcessingJob(job_id=job_id, session_id=SESSION_ID, status=status, message="", details=details)
    repo.jobs[job_id] = job
    return job


def test_waiting_jobs_are_queued_again_and_started_jobs_are_failed():
    repo = MockRepository()
    queue = MemoryJobQueue()
    waiting = _job(repo, "job_waiting", JobStatus.queued)
    started = _job(repo, "job_started", JobStatus.processing)
    half_done = _job(repo, "job_half_done", JobStatus.transcription_completed)
    finished = _job(repo, "job_finished", JobStatus.needs_review)
    upload = _job(repo, "job_upload", JobStatus.queued, transcription=False)

    outcome = recover_interrupted_jobs(repo, queue)

    assert outcome == {"requeued": 1, "failed": 2}
    assert queue.size() == 1 and queue.dequeue().job_id == waiting.job_id
    for job in (started, half_done):
        assert job.status == JobStatus.failed
        assert job.error_code == "interrupted"
        assert job.details["status_history"][-1] == JobStatus.failed.value
    assert finished.status == JobStatus.needs_review
    assert upload.status == JobStatus.queued
    failures = [item for item in repo.audit_log if item["action"] == "audio.process_failed"]
    assert {item["target_id"] for item in failures} == {started.job_id, half_done.job_id}


def test_a_failed_interrupted_job_no_longer_blocks_a_new_one():
    repo = MockRepository()
    started = _job(repo, "job_started", JobStatus.processing)

    recover_interrupted_jobs(repo, MemoryJobQueue())

    # Raises while an active job holds the recording.
    _ensure_no_active_job_for_audio_artifact(
        repo, session_id=SESSION_ID, audio_file_id=started.details["audio_file_id"]
    )


def test_recovery_is_safe_to_repeat():
    repo = MockRepository()
    queue = MemoryJobQueue()
    _job(repo, "job_waiting", JobStatus.queued)
    _job(repo, "job_started", JobStatus.processing)

    recover_interrupted_jobs(repo, queue)
    second = recover_interrupted_jobs(repo, queue)

    assert second == {"requeued": 1, "failed": 0}
    assert queue.size() == 1
