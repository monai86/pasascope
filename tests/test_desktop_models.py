"""Speech-model downloads: checked by SHA-256, never left half-written."""

import hashlib
import io

import pytest

from packages.desktop.core import models
from packages.desktop.core.models import ModelDownloadError, ModelFile, ModelSpec


def _spec(files: dict[str, bytes], *, wrong: str | None = None) -> ModelSpec:
    return ModelSpec(
        key="test",
        folder="test-model",
        files=tuple(
            ModelFile(name, f"https://example.invalid/{name}",
                      "0" * 64 if name == wrong else hashlib.sha256(data).hexdigest(), len(data))
            for name, data in files.items()
        ),
    )


def _opener(files: dict[str, bytes], calls: list[str]):
    def open_url(url: str):
        name = url.rsplit("/", 1)[1]
        calls.append(name)
        return io.BytesIO(files[name])
    return open_url


def test_download_checks_every_file_and_moves_the_folder_into_place(tmp_path, monkeypatch):
    monkeypatch.setenv(models.MODELS_ENV, str(tmp_path))
    files = {"model.bin": b"weights" * 1000, "config.json": b"{}"}
    spec = _spec(files)
    seen: list[tuple[int, int]] = []
    calls: list[str] = []
    folder = models.download(spec, lambda done, total: seen.append((done, total)), opener=_opener(files, calls))
    assert folder == tmp_path / "test-model" and models.is_installed(spec)
    assert (folder / "model.bin").read_bytes() == files["model.bin"]
    assert seen[-1] == (spec.size, spec.size)
    assert not (tmp_path / "test-model.partial").exists()
    # Already installed: nothing is fetched again.
    calls.clear()
    models.download(spec, opener=_opener(files, calls))
    assert calls == []


def test_a_file_with_the_wrong_hash_is_not_kept(tmp_path, monkeypatch):
    monkeypatch.setenv(models.MODELS_ENV, str(tmp_path))
    files = {"model.bin": b"weights", "config.json": b"{}"}
    spec = _spec(files, wrong="config.json")
    with pytest.raises(ModelDownloadError):
        models.download(spec, opener=_opener(files, []))
    assert not models.is_installed(spec)
    assert not (tmp_path / "test-model").exists()
    # The good file stays in the partial folder, so a retry does not fetch it again.
    calls: list[str] = []
    with pytest.raises(ModelDownloadError):
        models.download(spec, opener=_opener(files, calls))
    assert calls == ["config.json"]


def test_cancel_stops_the_download(tmp_path, monkeypatch):
    monkeypatch.setenv(models.MODELS_ENV, str(tmp_path))
    files = {"model.bin": b"x" * (models.CHUNK * 2)}
    with pytest.raises(ModelDownloadError):
        models.download(_spec(files), opener=_opener(files, []), cancelled=lambda: True)
    assert not (tmp_path / "test-model").exists()


def test_the_thai_model_is_pinned_to_the_project_conversion():
    names = {f.name for f in models.THAI_WHISPER.files}
    assert {"model.bin", "config.json", "vocabulary.json", "tokenizer.json"} <= names
    assert all(len(f.sha256) == 64 and "/resolve/" in f.url and "/main/" not in f.url for f in models.THAI_WHISPER.files)


def test_accurate_mode_without_the_thai_model_points_to_the_download(tmp_path, monkeypatch):
    from packages.desktop.core import DesktopService, open_workspace

    monkeypatch.setenv(models.MODELS_ENV, str(tmp_path / "models"))
    monkeypatch.setenv("PASASCOPE_ASR_THAI_MODEL_PATH", str(tmp_path / "nowhere"))
    service = DesktopService(open_workspace(tmp_path / "ws"))
    service.set_transcription_mode("accurate")
    available, reason = service.transcription_availability()
    assert not available and ("Download" in reason or "ดาวน์โหลด" in reason)
    assert not service.thai_model_status()["installed"]
