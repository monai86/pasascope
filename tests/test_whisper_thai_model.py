"""The Thai-specialized Whisper strategy uses the converted model or fails openly."""
from __future__ import annotations

import pytest

from src.audio_pipeline import whisper_transcribe
from src.audio_pipeline.whisper_transcribe import (
    ThaiModelUnavailableError,
    WhisperTranscriber,
    thai_specialized_model_path,
)


class _FakeWhisperModel:
    def __init__(self, model_size_or_path, **kwargs):
        self.source = model_size_or_path


def _transcriber() -> WhisperTranscriber:
    transcriber = WhisperTranscriber.__new__(WhisperTranscriber)
    transcriber._WhisperModel = _FakeWhisperModel
    transcriber.model_size = "medium"
    transcriber.device = "cpu"
    transcriber.compute_type = "int8"
    transcriber._model = None
    transcriber._model_th = None
    transcriber.last_model_id = None
    transcriber._detect_language = lambda audio_path: "th"
    return transcriber


@pytest.fixture(autouse=True)
def _empty_model_cache(monkeypatch):
    monkeypatch.setattr(whisper_transcribe, "_MODEL_CACHE", {})


def test_missing_model_raises_instead_of_using_the_multilingual_model(tmp_path, monkeypatch):
    monkeypatch.setenv("PASASCOPE_ASR_THAI_MODEL_PATH", str(tmp_path / "absent"))
    transcriber = _transcriber()

    with pytest.raises(ThaiModelUnavailableError, match="convert_thai_whisper.sh"):
        transcriber._load_thai_specialized()
    assert transcriber._model is None


def test_converted_model_is_loaded_from_its_path(tmp_path, monkeypatch):
    (tmp_path / "model.bin").write_bytes(b"")
    monkeypatch.setenv("PASASCOPE_ASR_THAI_MODEL_PATH", str(tmp_path))

    model = _transcriber()._load_thai_specialized()

    assert model.source == str(tmp_path)


def test_default_path_is_the_ignored_models_folder(monkeypatch):
    monkeypatch.delenv("PASASCOPE_ASR_THAI_MODEL_PATH", raising=False)

    path = thai_specialized_model_path()

    assert path.parent.name == "models"
    assert path.name == "whisper-th-medium-combined-ct2"


def test_thai_specialized_runs_without_the_default_prompt(tmp_path, monkeypatch):
    (tmp_path / "model.bin").write_bytes(b"")
    monkeypatch.setenv("PASASCOPE_ASR_THAI_MODEL_PATH", str(tmp_path))
    transcriber = _transcriber()
    transcriber.strategy = "thai_specialized"
    transcriber._explicit_language = None
    transcriber._initial_prompt = None
    prompts = []

    def _run_single(model, audio_path, *, prompt, **kwargs):
        prompts.append(prompt)
        return []

    transcriber._run_single = _run_single

    transcriber.transcribe("clip.wav", vad_filter=False)

    assert prompts == [None]


@pytest.mark.parametrize(
    ("heard", "expected_model"),
    [("th", "biodatlab/whisper-th-medium-combined"), ("en", "medium")],
)
def test_thai_specialized_sends_only_thai_recordings_to_the_thai_model(tmp_path, monkeypatch, heard, expected_model):
    (tmp_path / "model.bin").write_bytes(b"")
    monkeypatch.setenv("PASASCOPE_ASR_THAI_MODEL_PATH", str(tmp_path))
    transcriber = _transcriber()
    transcriber.strategy = "thai_specialized"
    transcriber._explicit_language = None
    transcriber._initial_prompt = None
    transcriber.last_model_id = None
    transcriber._detect_language = lambda audio_path: heard
    used = []

    def _run_single(model, audio_path, *, language, **kwargs):
        used.append((model.source, language))
        return []

    transcriber._run_single = _run_single

    transcriber.transcribe("clip.wav", vad_filter=False)

    assert transcriber.last_model_id == expected_model
    if heard == "th":
        assert used == [(str(tmp_path), "th")]
    else:
        assert used == [("medium", None)]
