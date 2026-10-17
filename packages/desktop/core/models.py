"""The speech models the desktop app downloads on first use, checked byte for byte.

The Thai-specialised Whisper model (``biodatlab/whisper-th-medium-combined``,
Apache-2.0) is published as transformers weights, which faster-whisper cannot
open. The CTranslate2 files below come from a public conversion
(``CodeHardThailand/whisper-th-medium-combined-ct2``, Apache-2.0) and the
tokenizer files from the original repository, each pinned to a commit and
to the SHA-256 of the copy this project converted itself with
``scripts/convert_thai_whisper.sh``: the downloaded model is the same model,
bit for bit.

The multilingual Whisper ``small`` (language detection, fast mode) and the
child/adult voice model download themselves on first use; ``prefetch_others``
fetches them ahead of time so the first recording is not held up.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil

from packages.desktop.core.workspace import default_home

MODELS_ENV = "PASASCOPE_MODELS_HOME"
CHUNK = 1 << 20
_CONVERTED = "https://huggingface.co/CodeHardThailand/whisper-th-medium-combined-ct2/resolve/07a52f19f64ed6a57a3abdee534fcf74c808905c"
_ORIGINAL = "https://huggingface.co/biodatlab/whisper-th-medium-combined/resolve/eebf84255cc7f242a504f64ec09ec33d32903fe1"


@dataclass(frozen=True)
class ModelFile:
    name: str
    url: str
    sha256: str
    size: int


@dataclass(frozen=True)
class ModelSpec:
    key: str
    folder: str
    files: tuple[ModelFile, ...]

    @property
    def size(self) -> int:
        return sum(f.size for f in self.files)


THAI_WHISPER = ModelSpec(
    key="thai_whisper",
    folder="whisper-th-medium-combined-ct2",
    files=(
        ModelFile("model.bin", f"{_CONVERTED}/model.bin",
                  "27577575a4608196c7cd756a40a26753d297c0aa60ef50deb573ed0f9ab002ea", 1527906453),
        ModelFile("config.json", f"{_CONVERTED}/config.json",
                  "3622a2ddc41ec0e0fd4e68c13c6830f03b90c38d89aaad184de02c8c642cf807", 2257),
        ModelFile("vocabulary.json", f"{_CONVERTED}/vocabulary.json",
                  "5ad28279db5e546349708b9a74736e2c018737ac5a600f1048f1f26c99b85b47", 1068103),
        ModelFile("tokenizer.json", f"{_ORIGINAL}/tokenizer.json",
                  "a10d05b346bd872cbbdcb276355105de0787334deafa2c93c68d8d22c4d84bbf", 2481188),
        ModelFile("preprocessor_config.json", f"{_ORIGINAL}/preprocessor_config.json",
                  "a6a76d28c93edb273669eb9e0b0636a2bddbb1272c3261e47b7ca6dfdbac1b8d", 339),
    ),
)


class ModelDownloadError(RuntimeError):
    pass


def models_home() -> Path:
    """Where downloaded models live: shared by the real and the demo data folders.

    A dot-folder, so backups (which skip dot-folders) do not carry 1.5 GB of
    model weights that can be downloaded again.
    """
    configured = os.environ.get(MODELS_ENV, "").strip()
    return Path(configured).expanduser() if configured else default_home() / ".speech-models"


def model_dir(spec: ModelSpec = THAI_WHISPER) -> Path:
    return models_home() / spec.folder


def is_installed(spec: ModelSpec = THAI_WHISPER, folder: Path | None = None) -> bool:
    """Every file is present at its expected size (the hash was checked when it was downloaded)."""
    folder = folder or model_dir(spec)
    return all((folder / f.name).is_file() and (folder / f.name).stat().st_size == f.size for f in spec.files)


def use_downloaded_thai_model() -> Path | None:
    """Point transcription at the downloaded Thai model unless one is configured or ships with the code.

    Returns the folder in use, or None when no Thai model is on this computer.
    """
    from src.audio_pipeline.whisper_transcribe import (
        THAI_SPECIALIZED_PATH_ENV,
        thai_specialized_model_path,
        thai_specialized_model_ready,
    )

    if os.environ.get(THAI_SPECIALIZED_PATH_ENV, "").strip() or thai_specialized_model_ready():
        return thai_specialized_model_path() if thai_specialized_model_ready() else None
    if is_installed(THAI_WHISPER):
        os.environ[THAI_SPECIALIZED_PATH_ENV] = str(model_dir(THAI_WHISPER))
        return model_dir(THAI_WHISPER)
    return None


def download(
    spec: ModelSpec = THAI_WHISPER,
    progress: Callable[[int, int], None] | None = None,
    *,
    opener: Callable[[str], object] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    """Download every file of ``spec``, check each SHA-256, then move the folder into place.

    ``progress(done_bytes, total_bytes)`` is called as data arrives. Nothing is
    left half-written: files go to a ``.partial`` folder that replaces the
    model folder only when all of them match.
    """
    import urllib.request

    opener = opener or (lambda url: urllib.request.urlopen(url, timeout=60))
    target = model_dir(spec)
    if is_installed(spec, target):
        return target
    partial = target.with_name(target.name + ".partial")
    partial.mkdir(parents=True, exist_ok=True)
    total, done = spec.size, 0
    for item in spec.files:
        destination = partial / item.name
        if destination.is_file() and destination.stat().st_size == item.size and _sha256(destination) == item.sha256:
            done += item.size
            if progress:
                progress(done, total)
            continue
        digest = hashlib.sha256()
        with opener(item.url) as response, destination.open("wb") as sink:
            for chunk in iter(lambda: response.read(CHUNK), b""):
                if cancelled and cancelled():
                    raise ModelDownloadError("Download cancelled.")
                digest.update(chunk)
                sink.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
        if digest.hexdigest() != item.sha256:
            destination.unlink(missing_ok=True)
            raise ModelDownloadError(f"{item.name} does not match its expected SHA-256; it was not kept.")
    if target.exists():
        shutil.rmtree(target)
    partial.replace(target)
    return target


def prefetch_others() -> None:
    """Fetch the models that otherwise download on first use: Whisper small and the child/adult model."""
    from faster_whisper.utils import download_model

    from src.audio_pipeline.child_adult_frames import ensure_model

    download_model("small")
    ensure_model()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()
