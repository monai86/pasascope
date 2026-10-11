import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AudioFileMetadata


client = TestClient(app)

HEADERS = {
    "x-mock-user-id": "therapist-demo",
    "x-mock-role": "therapist",
    "x-organization-id": "pilot_org_001",
}


@pytest.fixture
def repo_with_audio():
    repo = MockRepository()
    # Add verified audio file to session_demo_001
    audio = AudioFileMetadata(
        audio_file_id="audio_demo_001",
        organization_id="pilot_org_001",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="sample.wav",
        content_type="audio/wav",
        size_bytes=10240,
        storage_mode="local_private",
        object_key="pilot_org_001/case_demo_001/session_demo_001/audio_demo_001.wav",
        upload_status="uploaded",
        duration_seconds=120.0,
        sample_rate_hz=16000,
        channels=2,
        checksum_sha256="4a7d1ed414474e4033ac29ccb8653d9b",
    )
    repo.audio_files[audio.audio_file_id] = audio
    app.dependency_overrides[get_repository] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_repository, None)


def test_waveform_peaks_returns_binary_stream(repo_with_audio):
    response = client.get(
        "/api/v1/sessions/session_demo_001/audio/waveform-peaks",
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert "x-points-per-second" in response.headers
    # The peaks are a generated placeholder, and the response must say so.
    assert response.headers["x-waveform-source"] == "synthetic"
    assert "x-duration-ms" in response.headers
    assert "x-channels" in response.headers
    assert len(response.content) > 0


def test_playback_grant_requires_consent_and_returns_signed_url(repo_with_audio):
    response = client.post(
        "/api/v1/sessions/session_demo_001/audio/playback-grant",
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert "playback_url" in data
    assert "expires_at" in data
    assert "audio_sha256" in data
    assert data["audio_sha256"] == "4a7d1ed414474e4033ac29ccb8653d9b"


def test_playback_grant_rejects_revoked_consent(repo_with_audio):
    # Revoke consent for the case
    repo_with_audio.cases["case_demo_001"].consent_status = "revoked"
    response = client.post(
        "/api/v1/sessions/session_demo_001/audio/playback-grant",
        headers=HEADERS,
    )
    assert response.status_code == 403


def _local_upload(client, repo, *, declared_size: int):
    from app.schemas.clinical import AudioUploadRequest
    from app.services.audio_job_service import create_audio_upload_job

    job = create_audio_upload_job(
        repo,
        "session_demo_001",
        AudioUploadRequest(filename="sample.wav", content_type="audio/wav", size_bytes=declared_size),
    )
    return job.details["audio_file"]["audio_file_id"]


def test_local_upload_rejects_bodies_that_do_not_match_the_intent(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.api.v1.dependencies import get_repository
    from app.core.config import get_settings
    from app.main import app
    from app.repositories.mock_repository import MockRepository

    monkeypatch.setenv("LINGUALENS_STORAGE_MODE", "local_private")
    monkeypatch.setenv("LINGUALENS_LOCAL_STORAGE_ROOT", str(tmp_path))
    get_settings.cache_clear()
    repo = MockRepository()
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        client = TestClient(app)
        too_large_id = _local_upload(client, repo, declared_size=16)
        too_small_id = _local_upload(client, repo, declared_size=16)
        exact_id = _local_upload(client, repo, declared_size=16)

        too_large = client.put(f"/api/v1/audio/{too_large_id}/upload-file", content=b"x" * 4096)
        too_small = client.put(f"/api/v1/audio/{too_small_id}/upload-file", content=b"x" * 4)
        exact = client.put(f"/api/v1/audio/{exact_id}/upload-file", content=b"x" * 16)
    finally:
        app.dependency_overrides.clear()
        monkeypatch.undo()
        get_settings.cache_clear()

    assert too_large.status_code == 413
    assert too_small.status_code == 400
    assert exact.status_code == 200
    assert repo.audio_files[too_large_id].upload_status == "pending"
    assert repo.audio_files[exact_id].upload_status == "pending_verification"
    assert len(repo.audio_files[exact_id].checksum_sha256) == 64
    assert [path.name for path in tmp_path.rglob("*") if path.is_file()] == [
        repo.audio_files[exact_id].object_key.split("/")[-1]
    ]


def test_cancelled_job_is_not_run_by_the_worker_and_completed_job_cannot_be_cancelled():
    from fastapi.testclient import TestClient

    from app.api.v1.dependencies import get_repository
    from app.main import app
    from app.repositories.mock_repository import MockRepository
    from app.schemas.clinical import AudioProcessRequest, JobStatus
    from app.services.audio_job_service import create_audio_processing_job, run_audio_processing_job

    repo = MockRepository()
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        client = TestClient(app)
        queued = create_audio_processing_job(
            repo, "session_demo_001", AudioProcessRequest(provider="manual", draft_text="*CHI:\thello .")
        )
        cancelled = client.post(f"/api/v1/jobs/{queued.job_id}/cancel")
        after_worker = run_audio_processing_job(repo, queued.job_id)

        finished = create_audio_processing_job(
            repo, "session_demo_001", AudioProcessRequest(provider="manual", draft_text="*CHI:\thello .")
        )
        repo.jobs[finished.job_id].status = JobStatus.transcription_completed
        cancel_finished = client.post(f"/api/v1/jobs/{finished.job_id}/cancel")
    finally:
        app.dependency_overrides.clear()

    assert cancelled.json()["status"] == "cancelled"
    assert after_worker.status == JobStatus.cancelled
    assert repo.sessions["session_demo_001"].transcript_id is None
    assert cancel_finished.json()["status"] == "transcription_completed"

