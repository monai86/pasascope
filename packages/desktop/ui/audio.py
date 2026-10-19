"""Play part of a recording, record from the microphone, and draw a waveform.

Playback and capture use ``sounddevice``; files are read with ``soundfile``
in blocks so a long recording is never loaded whole.
"""

from __future__ import annotations

from pathlib import Path
import threading
import time
from typing import Any

import numpy as np


def _sounddevice():
    import sounddevice

    return sounddevice


def waveform_peaks(path: Path, buckets: int = 1200) -> tuple[np.ndarray, float]:
    """Peak amplitude per bucket (0–1) and the duration in seconds."""
    import soundfile

    info = soundfile.info(str(path))
    total = int(info.frames)
    if total <= 0:
        return np.zeros(0, dtype="float32"), 0.0
    per_bucket = max(1, total // buckets)
    peaks: list[float] = []
    for block in soundfile.blocks(str(path), blocksize=per_bucket, dtype="float32", always_2d=True):
        peaks.append(float(np.abs(block).max()) if block.size else 0.0)
    values = np.asarray(peaks, dtype="float32")
    top = float(values.max()) if values.size else 0.0
    if top > 0:
        values = values / top
    return values, total / float(info.samplerate)


def _for_output_device(sd, data: np.ndarray, rate: int) -> tuple[np.ndarray, int]:
    """Resample to the output device's own rate with a proper filter.

    Left to the sound system, a 16 kHz clip on a 44.1 or 48 kHz device is
    converted on the fly, which adds crackle under load.
    """
    try:
        device_rate = int(sd.query_devices(kind="output")["default_samplerate"])
    except Exception:  # noqa: BLE001 - no device information: play as is
        return data, rate
    if not data.size or device_rate <= 0 or device_rate == rate:
        return data, rate
    from math import gcd

    from scipy.signal import resample_poly

    divisor = gcd(device_rate, int(rate))
    resampled = resample_poly(data, device_rate // divisor, int(rate) // divisor, axis=0)
    return np.clip(resampled, -1.0, 1.0).astype("float32"), device_rate


class SegmentPlayer:
    """Plays a time range of a WAV file and reports where playback is."""

    def __init__(self) -> None:
        self._path: Path | None = None
        self._started_at = 0.0
        self._start_sec = 0.0
        self._end_sec = 0.0
        self._lock = threading.Lock()
        self._playing = False

    def play(self, path: Path, start_sec: float, end_sec: float | None = None) -> None:
        import soundfile

        sd = _sounddevice()
        info = soundfile.info(str(path))
        duration = info.frames / float(info.samplerate)
        start_sec = max(0.0, min(start_sec, duration))
        end_sec = duration if end_sec is None else max(start_sec, min(end_sec, duration))
        data, rate = soundfile.read(
            str(path),
            start=int(start_sec * info.samplerate),
            stop=int(end_sec * info.samplerate),
            dtype="float32",
            always_2d=True,
        )
        data, rate = _for_output_device(sd, data, rate)
        sd.stop()
        with self._lock:
            self._path = path
            self._start_sec = start_sec
            self._end_sec = end_sec
            self._started_at = time.monotonic()
            self._playing = data.size > 0
        if data.size:
            # A roomy buffer: with the smallest one, a busy window or a running
            # transcription starves the sound card and the voice breaks up.
            sd.play(data, rate, latency="high", blocksize=2048)

    def stop(self) -> None:
        try:
            _sounddevice().stop()
        except Exception:  # noqa: BLE001 - no output device is not an error when stopping
            pass
        with self._lock:
            self._playing = False

    def position(self) -> float | None:
        """Seconds into the recording, or None when nothing is playing."""
        with self._lock:
            if not self._playing:
                return None
            now = self._start_sec + (time.monotonic() - self._started_at)
            if now >= self._end_sec:
                self._playing = False
                return None
            return now


class Recorder:
    """Records mono 16 kHz audio from the default input device."""

    RATE = 16000

    def __init__(self) -> None:
        self._chunks: list[np.ndarray] = []
        self._stream: Any = None
        self._level = 0.0
        self._lock = threading.Lock()
        self.started_at = 0.0

    @property
    def recording(self) -> bool:
        return self._stream is not None

    @property
    def level(self) -> float:
        return self._level

    def elapsed(self) -> float:
        return time.monotonic() - self.started_at if self.recording else 0.0

    def start(self) -> None:
        sd = _sounddevice()
        self._chunks = []

        def callback(indata, frames, time_info, status):  # noqa: ANN001 - sounddevice signature
            block = indata[:, 0].copy()
            with self._lock:
                self._chunks.append(block)
            self._level = float(np.sqrt(np.mean(block**2))) if block.size else 0.0

        self._stream = sd.InputStream(samplerate=self.RATE, channels=1, dtype="float32", callback=callback)
        self._stream.start()
        self.started_at = time.monotonic()

    def stop(self, destination: Path) -> Path | None:
        """Stop and write the take to ``destination``; None when nothing was captured."""
        import soundfile

        stream, self._stream = self._stream, None
        if stream is not None:
            stream.stop()
            stream.close()
        with self._lock:
            chunks, self._chunks = self._chunks, []
        self._level = 0.0
        if not chunks:
            return None
        audio = np.concatenate(chunks)
        destination.parent.mkdir(parents=True, exist_ok=True)
        soundfile.write(str(destination), audio, self.RATE, subtype="PCM_16")
        return destination

    def discard(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            stream.stop()
            stream.close()
        with self._lock:
            self._chunks = []
        self._level = 0.0
