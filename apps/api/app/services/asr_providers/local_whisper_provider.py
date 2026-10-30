"""
LocalWhisperProvider — on-device Whisper transcription with child/adult diarization.

Runs the research audio pipeline (``src/audio_pipeline``) on a recording that is
already stored on this machine. Nothing is sent to an external service, and a
failed run is reported as a failure: this provider never substitutes text.
"""
from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from pathlib import Path

from app.core.config import get_settings
from app.services.asr_providers.base import (
    BaseTranscriptionProvider,
    ProviderAvailability,
    TranscriptLine,
    TranscriptionResult,
)

# "api_openai" is deliberately absent: it would upload child audio.
LOCAL_LANGUAGE_STRATEGIES = frozenset({"auto", "english", "thai", "dual_pass", "thai_specialized"})
MODEL_SIZES = frozenset({"tiny", "base", "small", "medium", "large-v3"})
UNCLEAR_CONFIDENCE_THRESHOLD = 0.30
ADULT_SPEAKER_CODES = frozenset({"INV", "MOT", "FAT", "THER"})


class LocalWhisperProvider(BaseTranscriptionProvider):
    @property
    def provider_id(self) -> str:
        return "local_whisper"

    @property
    def provider_name(self) -> str:
        return "LocalWhisperProvider"

    @property
    def provider_version(self) -> str:
        return "v2-faster-whisper"

    def get_provider_metadata(self) -> dict:
        settings = get_settings()
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "description": (
                "On-device Whisper transcription with child/adult speaker separation. "
                "Experimental draft output; therapist review required."
            ),
            "is_stub": False,
            "runs_locally": True,
            "model_size": settings.asr_whisper_model_size,
            "language_strategy": settings.asr_language_strategy,
            "external_dependencies": ["faster-whisper"],
            "clinical_caution": (
                "Automatic transcription of child speech is error-prone. "
                "Therapist must listen to the audio and correct all content."
            ),
        }

    def check_availability(self) -> ProviderAvailability:
        settings = get_settings()
        if not settings.asr_local_whisper_enabled:
            return ProviderAvailability(
                available=False,
                reason="Local Whisper is disabled. Set PASASCOPE_ASR_LOCAL_WHISPER_ENABLED=true to enable it.",
                missing_dependencies=["PASASCOPE_ASR_LOCAL_WHISPER_ENABLED"],
            )
        if settings.storage_mode not in {"local", "local_private"}:
            return ProviderAvailability(
                available=False,
                reason="Local Whisper needs recordings stored on this machine.",
            )
        if settings.asr_whisper_model_size not in MODEL_SIZES:
            return ProviderAvailability(
                available=False,
                reason=f"Unsupported Whisper model size: {settings.asr_whisper_model_size}.",
            )
        if settings.asr_language_strategy not in LOCAL_LANGUAGE_STRATEGIES:
            return ProviderAvailability(
                available=False,
                reason=f"Unsupported local language strategy: {settings.asr_language_strategy}.",
            )
        if find_spec("faster_whisper") is None:
            return ProviderAvailability(
                available=False,
                reason="The faster-whisper package is not installed.",
                missing_dependencies=["faster-whisper"],
            )
        if settings.asr_language_strategy == "thai_specialized":
            whisper_transcribe = import_module("src.audio_pipeline.whisper_transcribe")
            if not whisper_transcribe.thai_specialized_model_ready():
                return ProviderAvailability(
                    available=False,
                    reason=(
                        "The Thai Whisper model has not been converted on this machine. "
                        "Run scripts/convert_thai_whisper.sh or set PASASCOPE_ASR_THAI_MODEL_PATH."
                    ),
                    missing_dependencies=["PASASCOPE_ASR_THAI_MODEL_PATH"],
                )
        return ProviderAvailability(available=True, reason="Local Whisper is ready.")

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

        settings = get_settings()
        try:
            audio_to_cha = import_module("src.audio_pipeline.pipeline").audio_to_cha
            pipeline_result = audio_to_cha(
                Path(audio_path),
                model_size=settings.asr_whisper_model_size,
                strategy=settings.asr_language_strategy,
                child_age_months=(config or {}).get("child_age_months"),
                validate=False,
                progress_callback=(config or {}).get("progress_callback"),
            )
        except Exception as exc:
            return self._result("failed", error_message=f"Local Whisper transcription failed: {type(exc).__name__}.")

        lines: list[TranscriptLine] = []
        languages: set[str] = set()
        has_words = False
        from src.audio_pipeline.chat_formatter import draft_utterance_text as draft_text

        for segment in pipeline_result.utterances:
            if not (segment.text or "").strip():
                continue
            # CHAT form: segmented words, &- fillers and [/] retraces, so the
            # therapist corrects a draft that already follows CLAN's rules.
            text = draft_text(segment) or (segment.text or "").strip()
            words = list(segment.words or [])
            has_words = has_words or bool(words)
            confidence = (
                round(sum(word.probability for word in words) / len(words), 3)
                if words
                else None
            )
            speaker = (segment.speaker or "").upper()
            if speaker != "CHI" and speaker not in ADULT_SPEAKER_CODES:
                speaker = "UNK"
            if segment.language:
                languages.add(segment.language)
            lines.append(
                TranscriptLine(
                    line_id=f"lw-{len(lines) + 1:03d}",
                    speaker=speaker,
                    text=text,
                    start_ms=int(round(segment.start * 1000)),
                    end_ms=int(round(segment.end * 1000)),
                    confidence=confidence,
                    source="asr",
                    unclear=confidence is not None and confidence < UNCLEAR_CONFIDENCE_THRESHOLD,
                    speaker_uncertain=getattr(segment, "speaker_basis", None) not in ("voice", "frame"),
                    boundary_reason=getattr(segment, "boundary_reason", None) or "",
                    speaker_reason=getattr(segment, "speaker_reason", None) or "",
                    speech_reason=getattr(segment, "speech_reason", None) or "",
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
            language=",".join(sorted(languages)) or "und",
            confidence_available=has_words,
            word_timestamps_available=has_words,
            speaker_segments_available=any(line.speaker != "UNK" for line in lines),
            warnings=[
                "Automatic draft: speaker labels and wording must be checked against the recording.",
            ],
            provider_metadata={
                "model_size": settings.asr_whisper_model_size,
                "language_strategy": settings.asr_language_strategy,
                "asr_model": getattr(pipeline_result, "asr_model", None),
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
