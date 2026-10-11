from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AudioFileMetadata, JobStatus, TranscriptionJobRequest
from app.services import audio_job_service
from app.services.asr_providers import local_whisper_provider
from app.services.asr_providers.local_whisper_provider import LocalWhisperProvider
from app.services.audio_job_service import (
    create_audio_processing_job,
    run_audio_processing_job,
    validate_audio_upload,
)
from app.schemas.clinical import AudioUploadRequest


@dataclass
class _Word:
    text: str
    start: float
    end: float
    probability: float


@dataclass
class _Segment:
    start: float
    end: float
    text: str
    speaker: str | None = None
    language: str | None = "th"
    words: list = field(default_factory=list)


@pytest.fixture
def whisper_enabled(tmp_path, monkeypatch):
    """Local Whisper switched on, with storage rooted in a temp directory."""
    settings = Settings(asr_local_whisper_enabled=True, local_storage_root=str(tmp_path))
    monkeypatch.setattr(local_whisper_provider, "get_settings", lambda: settings)
    monkeypatch.setattr(audio_job_service, "get_settings", lambda: settings)
    monkeypatch.setattr(local_whisper_provider, "find_spec", lambda name: object())
    return settings


def _use_pipeline(monkeypatch, audio_to_cha):
    monkeypatch.setattr(
        local_whisper_provider,
        "import_module",
        lambda name: SimpleNamespace(audio_to_cha=audio_to_cha),
    )


def _stored_recording(repo: MockRepository, tmp_path, session_id: str = "session_demo_001") -> str:
    session = repo.sessions[session_id]
    (tmp_path / "audio").mkdir(exist_ok=True)
    (tmp_path / "audio" / "obj_test.webm").write_bytes(b"not-real-audio")
    repo.audio_files["aud_test"] = AudioFileMetadata(
        audio_file_id="aud_test",
        organization_id=session.organization_id,
        session_id=session_id,
        case_id=session.case_id,
        original_filename="recording.webm",
        content_type="audio/webm",
        size_bytes=14,
        storage_mode="local_private",
        object_key="audio/obj_test.webm",
        upload_status="uploaded",
    )
    return "aud_test"


def test_disabled_by_default_and_never_transcribes():
    provider = LocalWhisperProvider()

    assert provider.check_availability().available is False
    result = provider.transcribe("aud_test", {"audio_path": "/nonexistent.wav"})
    assert result.status == "unavailable"
    assert result.transcript_lines == []


def test_unavailable_when_faster_whisper_is_missing(whisper_enabled, monkeypatch):
    monkeypatch.setattr(local_whisper_provider, "find_spec", lambda name: None)

    availability = LocalWhisperProvider().check_availability()

    assert availability.available is False
    assert availability.missing_dependencies == ["faster-whisper"]


def test_remote_language_strategy_is_refused(whisper_enabled):
    whisper_enabled.asr_language_strategy = "api_openai"

    assert LocalWhisperProvider().check_availability().available is False


def test_pipeline_segments_become_reviewable_lines(whisper_enabled, monkeypatch, tmp_path):
    recording = tmp_path / "clip.wav"
    recording.write_bytes(b"x")
    calls = {}

    def fake_audio_to_cha(path, **kwargs):
        calls["path"] = path
        calls["kwargs"] = kwargs
        return SimpleNamespace(
            utterances=[
                _Segment(0.5, 2.1, "ไหนลองพูดซิ", speaker="INV", words=[_Word("ไหน", 0.5, 1.0, 0.9)]),
                _Segment(2.8, 4.5, "รถ แดง", speaker="CHI", words=[_Word("รถ", 2.8, 3.2, 0.2), _Word("แดง", 3.3, 3.7, 0.2)]),
                _Segment(5.0, 5.5, "   ", speaker="CHI"),
                _Segment(6.0, 7.0, "อะไรนะ", speaker=None),
            ]
        )

    _use_pipeline(monkeypatch, fake_audio_to_cha)

    result = LocalWhisperProvider().transcribe(
        "aud_test", {"audio_path": str(recording), "child_age_months": 48}
    )

    assert result.status == "completed"
    assert calls["path"] == recording
    assert calls["kwargs"]["strategy"] == "thai"
    assert calls["kwargs"]["model_size"] == "medium"
    assert calls["kwargs"]["child_age_months"] == 48
    assert [(line.speaker, line.text) for line in result.transcript_lines] == [
        ("INV", "ไหนลองพูดซิ"),
        ("CHI", "รถ แดง"),
        ("UNK", "อะไรนะ"),
    ]
    adult, child, unknown = result.transcript_lines
    assert (adult.start_ms, adult.end_ms) == (500, 2100)
    assert adult.confidence == 0.9 and adult.unclear is False
    assert child.confidence == 0.2 and child.unclear is True
    assert unknown.confidence is None
    assert all(line.source == "asr" for line in result.transcript_lines)
    assert result.speaker_segments_available is True
    assert result.language == "th"


def test_pipeline_failure_is_a_failure_without_text(whisper_enabled, monkeypatch, tmp_path):
    recording = tmp_path / "clip.wav"
    recording.write_bytes(b"x")

    def broken_audio_to_cha(path, **kwargs):
        raise RuntimeError(f"cannot decode {path}")

    _use_pipeline(monkeypatch, broken_audio_to_cha)

    result = LocalWhisperProvider().transcribe("aud_test", {"audio_path": str(recording)})

    assert result.status == "failed"
    assert result.transcript_lines == []
    assert str(recording) not in result.error_message


def test_silent_recording_is_a_failure(whisper_enabled, monkeypatch, tmp_path):
    recording = tmp_path / "clip.wav"
    recording.write_bytes(b"x")
    _use_pipeline(monkeypatch, lambda path, **kwargs: SimpleNamespace(utterances=[]))

    result = LocalWhisperProvider().transcribe("aud_test", {"audio_path": str(recording)})

    assert result.status == "failed"
    assert result.transcript_lines == []


def test_job_runs_local_whisper_on_the_stored_recording(whisper_enabled, monkeypatch, tmp_path):
    repo = MockRepository()
    audio_file_id = _stored_recording(repo, tmp_path)
    seen = {}

    def fake_audio_to_cha(path, **kwargs):
        seen["path"] = path
        return SimpleNamespace(
            utterances=[
                _Segment(0.0, 1.0, "เล่นอะไรดี", speaker="INV"),
                _Segment(1.5, 2.5, "เล่นรถ", speaker="CHI"),
            ]
        )

    _use_pipeline(monkeypatch, fake_audio_to_cha)

    job = create_audio_processing_job(
        repo, "session_demo_001", TranscriptionJobRequest(audio_id=audio_file_id, provider="local_whisper")
    )
    assert job.status == JobStatus.queued
    finished = run_audio_processing_job(repo, job.job_id)

    assert finished.status == JobStatus.needs_review
    assert seen["path"] == (tmp_path / "audio" / "obj_test.webm").resolve()
    transcript = repo.transcripts[repo.sessions["session_demo_001"].transcript_id]
    assert transcript.source == "asr_draft:local_whisper"
    assert transcript.therapist_attested is False
    assert [(str(u.speaker), u.text) for u in transcript.utterances] == [
        ("INV", "เล่นอะไรดี"),
        ("CHI", "เล่นรถ"),
    ]
    assert all(issue.code != "MOCK_ASR_OUTPUT" for issue in transcript.qa_issues)
    # The draft is declared Thai, so QA does not warn about undeclared Thai text.
    assert "@Languages:\ttha" in transcript.raw_text
    assert transcript.chat_metadata["languages"] == ["tha"]


def test_job_fails_without_a_transcript_when_whisper_fails(whisper_enabled, monkeypatch, tmp_path):
    repo = MockRepository()
    audio_file_id = _stored_recording(repo, tmp_path)
    transcript_before = repo.sessions["session_demo_001"].transcript_id
    transcripts_before = set(repo.transcripts)

    def broken_audio_to_cha(path, **kwargs):
        raise RuntimeError("decoder crashed")

    _use_pipeline(monkeypatch, broken_audio_to_cha)

    job = create_audio_processing_job(
        repo, "session_demo_001", TranscriptionJobRequest(audio_id=audio_file_id, provider="local_whisper")
    )
    finished = run_audio_processing_job(repo, job.job_id)

    assert finished.status == JobStatus.failed
    assert finished.error_code == "asr_failed"
    assert set(repo.transcripts) == transcripts_before
    assert repo.sessions["session_demo_001"].transcript_id == transcript_before


def test_unavailable_local_whisper_never_falls_back_silently(tmp_path):
    repo = MockRepository()
    audio_file_id = _stored_recording(repo, tmp_path)

    job = create_audio_processing_job(
        repo, "session_demo_001", TranscriptionJobRequest(audio_id=audio_file_id, provider="local_whisper")
    )

    assert job.status == JobStatus.failed
    assert job.error_code == "provider_unavailable"
    assert job.details["actual_provider"] is None


@pytest.mark.parametrize(
    "content_type",
    ["audio/webm", "audio/webm;codecs=opus", "audio/ogg; codecs=opus", "audio/mp4", "audio/wav"],
)
def test_browser_recording_types_are_accepted(content_type):
    validate_audio_upload(
        AudioUploadRequest(filename="recording.webm", content_type=content_type, size_bytes=1024)
    )


def test_non_audio_upload_is_still_rejected():
    with pytest.raises(ValueError, match="unsupported file"):
        validate_audio_upload(
            AudioUploadRequest(filename="notes.pdf", content_type="application/pdf", size_bytes=1024)
        )
