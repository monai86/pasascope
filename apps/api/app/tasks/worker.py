"""Worker entrypoint for local asynchronous audio jobs."""

import time

from app.api.v1.dependencies import get_repository
from app.services.audio_job_service import run_audio_processing_job
from app.tasks.job_queue import get_job_queue


def run_worker_once() -> dict:
    queue = get_job_queue()
    queued = queue.dequeue()
    if queued is None:
        return {"status": "idle", "processed": 0}
    repo = get_repository()
    job = run_audio_processing_job(repo, queued.job_id)
    return {"status": "processed", "processed": 1, "job_id": job.job_id, "job_status": job.status.value}


def run_worker() -> str:
    result = run_worker_once()
    if result["status"] == "idle":
        return "lingualens worker is ready; no queued jobs."
    return f"lingualens worker processed job {result['job_id']} with status {result['job_status']}."


def run_worker_forever(poll_seconds: float = 1.0) -> None:
    """Drain a durable (Redis) queue until the process is stopped.

    The memory queue is drained inside the API process instead; a separate
    worker process cannot see it.
    """

    while True:
        if run_worker_once()["status"] == "idle":
            time.sleep(poll_seconds)


if __name__ == "__main__":
    run_worker_forever()
