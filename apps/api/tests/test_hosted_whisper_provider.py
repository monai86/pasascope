from __future__ import annotations

import math

import httpx
import pytest

from app.core.config import Settings
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AudioFileMetadata, JobStatus, TranscriptionJobRequest
from app.services import audio_job_service
from app.services.asr_providers import hosted_whisper_provider
from app.services.asr_providers.hosted_whisper_provider import HostedWhisperProvider
from app.services.audio_job_service import create_audio_processing_job, run_audio_processing_job

API_KEY = "test-key-not-real"


@pytest.fixture
def hosted_enabled(tmp_path, monkeypatch):
    """Hosted transcription switched on, with storage rooted in a temp directory."""
    settings = Settings(
        asr_hosted_enabled=True,
        asr_hosted_api_key=API_KEY,
        local_storage_root=str(tmp_path),
    )
    monkeypatch.setattr(hosted_whisper_provider, "get_settings", lambda: settings)
    monkeypatch.setattr(audio_job_service, "get_settings", lambda: settings)
    return settings


def _use_service(monkeypatch, handler):
    """Answer the provider's HTTP calls with ``handler`` and record them."""
    requests: list[httpx.Request] = []

    def recording_handler(request: httpx.Request) -> httpx.Response:
        request.read()
        requests.append(request)
        return handler(request)

    monkeypatch.setattr(
        hosted_whisper_provider,
        "_client",
        lambda: httpx.Client(transport=httpx.MockTransport(recording_handler)),
    )
    return requests


def _recording(tmp_path, name: str = "clip.webm", content: bytes = b"not-real-audio"):
    path = tmp_path / name
    path.write_bytes(content)
    return path


def _segments_response(*segments: dict, language: str = "Thai") -> httpx.Response:
    return httpx.Response(200, json={"language": language, "segments": list(segments)})


def test_disabled_by_default_and_never_calls_the_service(monkeypatch, tmp_path):
    requests = _use_service(monkeypatch, lambda request: httpx.Response(500))
    provider = HostedWhisperProvider()

    assert provider.check_availability().available is False
    result = provider.transcribe("aud_test", {"audio_path": str(_recording(tmp_path))})

    assert result.status == "unavailable"
    assert requests == []


def test_enabled_without_a_key_is_unavailable(monkeypatch):
    settings = Settings(asr_hosted_enabled=True, asr_hosted_api_key="  ")
    monkeypatch.setattr(hosted_whisper_provider, "get_settings", lambda: settings)

    availability = HostedWhisperProvider().check_availability()

    assert availability.available is False
    assert availability.missing_dependencies == ["PASASCOPE_ASR_HOSTED_API_KEY"]


def test_runtime_validation_rejects_hosted_transcription_without_a_key():
    with pytest.raises(ValueError, match="Hosted transcription"):
        Settings(asr_hosted_enabled=True).validate_runtime_security()


def test_metadata_says_the_recording_leaves_the_deployment(hosted_enabled):
    metadata = HostedWhisperProvider().get_provider_metadata()

    assert metadata["runs_locally"] is False
    assert metadata["model_size"] == "whisper-large-v3"


def test_sends_the_recording_and_maps_timed_segments(hosted_enabled, monkeypatch, tmp_path):
    requests = _use_service(
        monkeypatch,
        lambda request: _segments_response(
            {"start": 0.0, "end": 1.24, "text": " เล่นอะไรดี ", "avg_logprob": math.log(0.9)},
            {"start": 1.5, "end": 2.5, "text": "", "avg_logprob": -0.1},
            {"start": 3.0, "end": 3.6, "text": "เล่นรถ", "avg_logprob": math.log(0.2)},
        ),
    )

    result = HostedWhisperProvider().transcribe("aud_test", {"audio_path": str(_recording(tmp_path))})

    assert result.status == "completed"
    assert result.language == "th"
    assert result.speaker_segments_available is False
    assert [(line.speaker, line.text, line.start_ms, line.end_ms) for line in result.transcript_lines] == [
        ("UNK", "เล่นอะไรดี", 0, 1240),
        ("UNK", "เล่นรถ", 3000, 3600),
    ]
    assert [line.confidence for line in result.transcript_lines] == [0.9, 0.2]
    assert [line.unclear for line in result.transcript_lines] == [False, True]

    (request,) = requests
    assert str(request.url) == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    body = request.content
    assert b"not-real-audio" in body
    assert b'filename="recording.webm"' in body
    assert b"whisper-large-v3" in body
    assert b'name="language"\r\n\r\nth' in body


def test_the_stored_file_name_is_not_sent(hosted_enabled, monkeypatch, tmp_path):
    requests = _use_service(
        monkeypatch,
        lambda request: _segments_response({"start": 0, "end": 1, "text": "เล่นรถ"}),
    )

    HostedWhisperProvider().transcribe(
        "aud_test", {"audio_path": str(_recording(tmp_path, name="obj_private_key.wav"))}
    )

    assert b"obj_private_key" not in requests[0].content
    assert b'filename="recording.wav"' in requests[0].content


def test_recording_over_the_service_limit_is_not_sent(hosted_enabled, monkeypatch, tmp_path):
    requests = _use_service(monkeypatch, lambda request: httpx.Response(500))
    monkeypatch.setattr(hosted_whisper_provider, "MAX_HOSTED_AUDIO_BYTES", 4)

    result = HostedWhisperProvider().transcribe("aud_test", {"audio_path": str(_recording(tmp_path))})

    assert result.status == "failed"
    assert "25 MB" in result.error_message
    assert requests == []


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (httpx.Response(429, json={"error": "rate"}), "usage limit"),
        (httpx.Response(401, json={"error": "secret detail"}), "status 401"),
        (httpx.Response(200, text="not json"), "unreadable"),
        (httpx.Response(200, json={"segments": []}), "No speech"),
    ],
)
def test_service_problems_are_failures_without_text(hosted_enabled, monkeypatch, tmp_path, response, expected):
    _use_service(monkeypatch, lambda request: response)

    result = HostedWhisperProvider().transcribe("aud_test", {"audio_path": str(_recording(tmp_path))})

    assert result.status == "failed"
    assert result.transcript_lines == []
    assert expected in result.error_message
    assert "secret detail" not in result.error_message


def test_network_error_is_a_failure(hosted_enabled, monkeypatch, tmp_path):
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    _use_service(monkeypatch, unreachable)

    result = HostedWhisperProvider().transcribe("aud_test", {"audio_path": str(_recording(tmp_path))})

    assert result.status == "failed"
    assert result.error_message == "Hosted transcription failed: ConnectError."


def test_job_creates_a_draft_with_speakers_left_for_the_therapist(hosted_enabled, monkeypatch, tmp_path):
    repo = MockRepository()
    session = repo.sessions["session_demo_001"]
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "obj_test.webm").write_bytes(b"not-real-audio")
    repo.audio_files["aud_test"] = AudioFileMetadata(
        audio_file_id="aud_test",
        organization_id=session.organization_id,
        session_id=session.session_id,
        case_id=session.case_id,
        original_filename="recording.webm",
        content_type="audio/webm",
        size_bytes=14,
        storage_mode="local_private",
        object_key="audio/obj_test.webm",
        upload_status="uploaded",
    )
    _use_service(
        monkeypatch,
        lambda request: _segments_response(
            {"start": 0.0, "end": 1.0, "text": "เล่นอะไรดี"},
            {"start": 1.5, "end": 2.5, "text": "เล่นรถ"},
        ),
    )

    job = create_audio_processing_job(
        repo, "session_demo_001", TranscriptionJobRequest(audio_id="aud_test", provider="hosted_whisper")
    )
    assert job.status == JobStatus.queued
    finished = run_audio_processing_job(repo, job.job_id)

    assert finished.status == JobStatus.needs_review
    transcript = repo.transcripts[repo.sessions["session_demo_001"].transcript_id]
    assert transcript.source == "asr_draft:hosted_whisper"
    assert [(str(u.speaker), u.text) for u in transcript.utterances] == [
        ("UNK", "เล่นอะไรดี"),
        ("UNK", "เล่นรถ"),
    ]
