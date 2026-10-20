"""Errors, small helpers and constants the workflow mixins share."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
import shutil
import subprocess
from typing import Any

from packages.desktop.core.i18n import tr


ProgressCallback = Callable[[float, str], None]

AUDIO_SUFFIXES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/x-m4a",
    ".mp4": "video/mp4",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
}


class WorkflowError(Exception):
    """A step that cannot run now; the message is shown to the therapist as is."""


class QaOverrideRequired(WorkflowError):
    """The transcript failed QA; attesting it needs a reason from the therapist."""

    def __init__(self, issues: list) -> None:
        super().__init__(tr("transcript ไม่ผ่านการตรวจรูปแบบ ต้องระบุเหตุผลจึงจะรับรองได้", "The transcript failed the format check; give a reason to attest it."))
        self.issues = issues


class TranscriptionCancelled(Exception):
    """Raised from the progress callback to stop a running transcription."""


def _utc(value: datetime | None) -> datetime:
    """Records read back from SQLite carry naive UTC times; new ones are aware."""
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _day(value: Any) -> str:
    """A session date as 17/10/2026, whether it is stored as a date or as text."""
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])
        except ValueError:
            return value
    return value.strftime("%d/%m/%Y") if hasattr(value, "strftime") else str(value)


def _status_value(status: Any) -> str:
    return status.value if hasattr(status, "value") else str(status)


# Report language → the template that writes it (fixed wording, no model).
REPORT_PROVIDERS = {"th": "template_th", "en": "template_clinic_en"}


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _looks_like_chat(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("@") or "\n*" in text or stripped.startswith("*")


def _safe_filename(name: str) -> str:
    cleaned = "".join(ch for ch in Path(name).name if ch not in '/\\:') .replace("..", "_")
    return cleaned or "recording"


def _audio_duration(path: Path) -> float | None:
    try:
        import soundfile

        return float(soundfile.info(str(path)).duration)
    except Exception:  # noqa: BLE001 - formats libsndfile cannot read are measured by ffprobe
        pass
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return float(out.stdout.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _upload_message(reason: str) -> str:
    return {
        "unsupported file": tr("ไฟล์ชนิดนี้ใช้ไม่ได้ ใช้ .wav .mp3 .m4a .mp4 .webm หรือ .ogg", "This file type is not supported; use .wav .mp3 .m4a .mp4 .webm or .ogg."),
        "audio too long or too large": tr("ไฟล์เสียงใหญ่เกิน 250 MB", "The recording is larger than 250 MB."),
        "unsafe filename": tr("ชื่อไฟล์ใช้ไม่ได้", "Invalid file name."),
    }.get(reason, reason)


def _validation_message(exc: Exception) -> str:
    errors = getattr(exc, "errors", lambda: [])()
    if not errors:
        return str(exc)
    first = errors[0]
    field = ".".join(str(part) for part in first.get("loc", ()))
    return tr(f"{field}: {first.get('msg', 'ค่าไม่ถูกต้อง')}", f"{field}: {first.get('msg', 'invalid value')}")


def _decode_for_listening(source: Path, target: Path) -> None:
    """Decode ``source`` to 16-bit WAV at its own sample rate, keeping stereo (PyAV, no system ffmpeg)."""
    import av
    import soundfile

    with av.open(str(source)) as container:
        stream = container.streams.audio[0]
        channels = 2 if (stream.channels or 1) >= 2 else 1
        rate = stream.rate or 44100
        resampler = av.AudioResampler(format="s16", layout="stereo" if channels == 2 else "mono", rate=rate)
        with soundfile.SoundFile(str(target), "w", samplerate=rate, channels=channels, subtype="PCM_16") as sink:
            def write(frames) -> None:
                for frame in frames:
                    sink.write(frame.to_ndarray().reshape(-1, channels))

            for frame in container.decode(stream):
                write(resampler.resample(frame))
            write(resampler.resample(None))
