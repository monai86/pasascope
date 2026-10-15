"""
HostedWhisperProvider — Whisper transcription through an external service.

Sends the stored recording to an OpenAI-compatible ``/audio/transcriptions``
endpoint (Groq by default). The recording leaves this deployment, so the
provider is off unless the operator enables it, and the settings route reports
it as external so the web app can say so before a recording is made.

The service returns timed segments without speaker separation: every line is
labelled ``UNK`` for the therapist to assign. A failed call is reported as a
failure; this provider never substitutes text.
"""
from __future__ import annotations

import math
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.asr_providers.base import (
    BaseTranscriptionProvider,
    ProviderAvailability,
    TranscriptLine,
    TranscriptionResult,
)

# Upload limit of the default service's free tier.
MAX_HOSTED_AUDIO_BYTES = 25 * 1024 * 1024
UNCLEAR_CONFIDENCE_THRESHOLD = 0.30
# "thai_specialized" names an on-device model; the service detects the language.
_LANGUAGE_HINTS = {"thai": "th", "english": "en"}
_TIMEOUT = httpx.Timeout(300.0, connect=10.0)


def _client() -> httpx.Client:
    return httpx.Client(timeout=_TIMEOUT)


class HostedWhisperProvider(BaseTranscriptionProvider):
    @property
    def provider_id(self) -> str:
        return "hosted_whisper"

    @property
    def provider_name(self) -> str:
        return "HostedWhisperProvider"

    @property
    def provider_version(self) -> str:
        return "v1-openai-compatible"

    def get_provider_metadata(self) -> dict:
        settings = get_settings()
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "description": (
                "Whisper transcription by an external service. The recording is sent "
                "outside this deployment. Experimental draft output; therapist review required."
            ),
            "is_stub": False,
            "runs_locally": False,
            "model_size": settings.asr_hosted_model,
            "language_strategy": settings.asr_language_strategy,
            "external_dependencies": ["hosted transcription API"],
            "clinical_caution": (
                "Automatic transcription of child speech is error-prone and speakers are not "
                "separated. Therapist must listen to the audio and correct all content."
            ),
        }

    def check_availability(self) -> ProviderAvailability:
        settings = get_settings()
        if not settings.asr_hosted_enabled:
            return ProviderAvailability(
                available=False,
                reason="Hosted transcription is disabled. Set PASASCOPE_ASR_HOSTED_ENABLED=true to enable it.",
                missing_dependencies=["PASASCOPE_ASR_HOSTED_ENABLED"],
            )
        if not settings.asr_hosted_api_key.strip():
            return ProviderAvailability(
                available=False,
                reason="Hosted transcription has no API key.",
                missing_dependencies=["PASASCOPE_ASR_HOSTED_API_KEY"],
            )
        if settings.storage_mode not in {"local", "local_private"}:
            return ProviderAvailability(
                available=False,
                reason="Hosted transcription needs recordings stored on this machine.",
            )
        return ProviderAvailability(available=True, reason="Hosted transcription is ready.")

    def transcribe(
        self,
        audio_ref: str,
        config: dict | None = None,
    ) -> TranscriptionResult:
        availability = self.check_availability()
        if not availability:
            return self._result("unavailable", error_message=availability.reason)

        audio_path = (config or {}).get("audio_path")
        if not audio_path or not Path(audio_path).is_file():
            return self._result("failed", error_message="The recording for this job was not found in local storage.")
        path = Path(audio_path)
        if path.stat().st_size > MAX_HOSTED_AUDIO_BYTES:
            return self._result(
                "failed",
                error_message="The recording is larger than 25 MB, the limit of the transcription service.",
            )

        settings = get_settings()
        data = {"model": settings.asr_hosted_model, "response_format": "verbose_json", "temperature": "0"}
        language = _LANGUAGE_HINTS.get(settings.asr_language_strategy)
        if language:
            data["language"] = language
        try:
            with _client() as client, path.open("rb") as handle:
                response = client.post(
                    f"{settings.asr_hosted_base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.asr_hosted_api_key}"},
                    data=data,
                    # The stored name is opaque; only its extension tells the service the format.
                    files={"file": (f"recording{path.suffix.lower()}", handle)},
                )
        except httpx.HTTPError as exc:
            return self._result("failed", error_message=f"Hosted transcription failed: {type(exc).__name__}.")
        if response.status_code == 429:
            return self._result(
                "failed",
                error_message="The transcription service is at its usage limit. Try again later.",
            )
        if response.status_code >= 400:
            return self._result(
                "failed",
                error_message=f"Hosted transcription failed with status {response.status_code}.",
            )
        try:
            body = response.json()
        except ValueError:
            return self._result("failed", error_message="Hosted transcription returned an unreadable response.")

        lines: list[TranscriptLine] = []
        for segment in body.get("segments") or []:
            text = str(segment.get("text") or "").strip()
            if not text:
                continue
            confidence = _segment_confidence(segment)
            lines.append(
                TranscriptLine(
                    line_id=f"hw-{len(lines) + 1:03d}",
                    speaker="UNK",
                    text=text,
                    start_ms=_to_ms(segment.get("start")),
                    end_ms=_to_ms(segment.get("end")),
                    confidence=confidence,
                    source="asr",
                    unclear=confidence is not None and confidence < UNCLEAR_CONFIDENCE_THRESHOLD,
                )
            )
        if not lines:
            return self._result("failed", error_message="No speech was recognised in this recording.")

        return TranscriptionResult(
            status="completed",
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            transcript_lines=lines,
            language=_language_code(body.get("language")) or language or "und",
            confidence_available=any(line.confidence is not None for line in lines),
            word_timestamps_available=False,
            speaker_segments_available=False,
            warnings=[
                "Automatic draft from an external service: wording must be checked against the recording.",
                "Speakers were not separated: assign the speaker of every line.",
            ],
            provider_metadata={
                "model": settings.asr_hosted_model,
                "language_strategy": settings.asr_language_strategy,
                "external": True,
            },
        )

    def _result(self, status: str, *, error_message: str) -> TranscriptionResult:
        return TranscriptionResult(
            status=status,
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            transcript_lines=[],
            error_message=error_message,
        )


def _to_ms(seconds: object) -> int | None:
    try:
        return int(round(float(seconds) * 1000))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _segment_confidence(segment: dict) -> float | None:
    """Mean token probability of a segment, from its average log-probability."""
    try:
        value = math.exp(float(segment["avg_logprob"]))
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    return round(min(max(value, 0.0), 1.0), 3)


def _language_code(reported: object) -> str:
    """Two-letter code for the language name or code a service reports."""
    name = str(reported or "").strip().lower()
    return {"thai": "th", "english": "en"}.get(name, name if len(name) == 2 else "")
