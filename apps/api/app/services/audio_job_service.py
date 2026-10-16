from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import (
    AsrDraftResult,
    AudioFileMetadata,
    AudioProcessRequest,
    AudioQualityReport,
    AudioUploadCompleteRequest,
    AudioUploadRequest,
    JobStatus,
    ProcessingJob,
    ReviewStatus,
    Transcript,
    utc_now,
    TranscriptionJobRequest,
    Utterance,
    QaIssue,
    QaStatus,
)
from app.services.cha_service import build_cha_text, manual_text_to_utterances
from app.services.consent_service import ensure_session_consent_active
from app.services.audio_backup_service import restore_recording
from app.services.storage_service import SupabasePrivateStorageAdapter, get_storage_adapter
from app.services.asr_providers.registry import asr_provider_registry
from app.services.asr_providers.base import TranscriptionResult



ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp4",
    "audio/x-m4a",
    "audio/webm",
    "audio/ogg",
    "video/mp4",
    "video/quicktime",
}
MAX_AUDIO_BYTES = 250 * 1024 * 1024


@dataclass(frozen=True)
class ProviderDraft:
    provider: str
    text: str
    confidence_available: bool = False
    timestamps_available: bool = False
    diarization_available: bool = False


class AsrProviderError(RuntimeError):
    pass





DIARIZED_ADULT_SPEAKERS = {"INV", "MOT", "FAT", "THER"}


def _local_audio_path(audio_file: AudioFileMetadata | None) -> Path | None:
    """Stored recording for on-device providers, or None when there is none."""
    settings = get_settings()
    if audio_file is None or not audio_file.object_key:
        return None
    if settings.storage_mode not in {"local", "local_private"}:
        return None
    storage_root = settings.resolved_local_storage_root.resolve()
    candidate = (storage_root / audio_file.object_key).resolve()
    if storage_root not in candidate.parents:
        return None
    if not candidate.is_file() and not restore_recording(audio_file.object_key, candidate):
        return None
    return candidate


def validate_audio_upload(payload: AudioUploadRequest) -> None:
    if not payload.filename.strip() or "/" in payload.filename or "\\" in payload.filename or ".." in payload.filename:
        raise ValueError("unsafe filename")
    # Browser recordings carry codec parameters, e.g. "audio/webm;codecs=opus".
    if payload.content_type.split(";")[0].strip().lower() not in ALLOWED_AUDIO_TYPES:
        raise ValueError("unsupported file")
    if payload.size_bytes > MAX_AUDIO_BYTES:
        raise ValueError("audio too long or too large")


def build_opaque_audio_object_key(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    safe_suffix = suffix if suffix and len(suffix) <= 10 else ""
    return f"audio/{new_id('obj')}{safe_suffix}"


def create_audio_upload_job(repo: MockRepository, session_id: str, payload: AudioUploadRequest, *, actor_id: str = "system") -> ProcessingJob:
    validate_audio_upload(payload)
    session = repo.sessions[session_id]
    storage_adapter = get_storage_adapter()
    if isinstance(storage_adapter, SupabasePrivateStorageAdapter):
        # This workflow has no managed-storage upload path; recordings for
        # Supabase storage go through the assessment (v2) capture flow.
        raise ValueError("Audio upload is unavailable for the configured storage mode.")
    audio_file = AudioFileMetadata(
        audio_file_id=new_id("aud"),
        organization_id=session.organization_id,
        session_id=session_id,
        case_id=session.case_id,
        original_filename=payload.filename,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        storage_mode=storage_adapter.storage_mode,
        object_key=build_opaque_audio_object_key(payload.filename),
        duration_seconds=payload.duration_seconds,
        sample_rate_hz=payload.sample_rate_hz,
        channels=payload.channels,
        estimated_noise_level=payload.estimated_noise_level,
        silence_ratio=payload.silence_ratio,
    )
    upload_intent = storage_adapter.create_upload_intent(audio_file)
    repo.audio_files[audio_file.audio_file_id] = audio_file
    quality = analyze_audio_quality(
        duration_seconds=payload.duration_seconds,
        sample_rate_hz=payload.sample_rate_hz,
        channels=payload.channels,
        estimated_noise_level=payload.estimated_noise_level,
        silence_ratio=payload.silence_ratio,
    )
    job = ProcessingJob(
        job_id=new_id("job"),
        organization_id=session.organization_id,
        session_id=session_id,
        status=JobStatus.queued,
        message="Audio metadata accepted. Processing is experimental and requires therapist transcript review.",
        details={
            "quality": quality.model_dump(mode="json"),
            "audio_file": audio_file.model_dump(mode="json"),
            "upload_intent": upload_intent.model_dump(mode="json"),
            "status_history": [JobStatus.queued.value],
        },
    )
    repo.jobs[job.job_id] = job
    repo.add_audit("audio.upload", job.job_id, "Experimental audio processing job queued.", actor_id=actor_id)
    return repo.clone(job)


def complete_audio_upload(repo: MockRepository, audio_file_id: str, payload: AudioUploadCompleteRequest, *, actor_id: str = "system") -> AudioFileMetadata:
    if audio_file_id not in repo.audio_files:
        raise ValueError("Audio file not found.")
    audio_file = repo.audio_files[audio_file_id]
    if not audio_file.retained:
        raise ValueError("Audio file is no longer retained.")
    storage_adapter = get_storage_adapter()
    if audio_file.upload_status == "pending" and audio_file.storage_mode == "supabase_private":
        if storage_adapter.storage_mode != audio_file.storage_mode:
            raise ValueError("Audio upload storage mode no longer matches the configured adapter.")
        if not storage_adapter.verify_upload_completion(audio_file, payload.size_bytes):
            raise ValueError("Uploaded audio object could not be verified.")
        audio_file.upload_status = "pending_verification"
    if audio_file.upload_status != "pending_verification":
        raise ValueError("Audio upload must be re-issued with a new upload intent before completion verification.")
    if payload.size_bytes is not None and payload.size_bytes != audio_file.size_bytes:
        raise ValueError("Uploaded audio size does not match upload intent metadata.")
    # Bytes received by this API were hashed on arrival; that server-side digest
    # is the integrity record. A client-declared checksum is only kept when the
    # object went straight to external storage.
    if not audio_file.checksum_sha256:
        audio_file.checksum_sha256 = payload.checksum_sha256
    audio_file.uploaded_at = utc_now()
    audio_file.upload_status = "uploaded"
    repo.add_audit("audio.upload_complete", audio_file.audio_file_id, "Audio upload metadata marked complete.", actor_id=actor_id)
    return repo.clone(audio_file)


def process_audio(repo: MockRepository, session_id: str, payload: AudioProcessRequest | TranscriptionJobRequest, *, actor_id: str = "system") -> ProcessingJob:
    job = create_audio_processing_job(repo, session_id, payload, actor_id=actor_id)
    return repo.clone(job)


def _resolve_audio_file_id_for_job(
    repo: MockRepository,
    session_id: str,
    payload: AudioProcessRequest | TranscriptionJobRequest,
) -> str | None:
    audio_file_id = getattr(payload, "audio_id", None)
    if audio_file_id:
        if audio_file_id not in repo.audio_files:
            raise ValueError("Audio file not found.")
        audio_file = repo.audio_files[audio_file_id]
        if audio_file.session_id != session_id or not audio_file.retained:
            raise ValueError("Audio file is not available for this session.")
        if audio_file.upload_status != "uploaded":
            raise ValueError("Audio processing requires a verified uploaded audio artifact.")
        return audio_file_id
    uploaded_files = [
        audio_file.audio_file_id
        for audio_file in repo.find("audio_files", session_id=session_id)
        if audio_file.retained
        and audio_file.upload_status == "uploaded"
    ]
    if len(uploaded_files) == 1:
        return uploaded_files[0]
    return None


def _ensure_no_active_job_for_audio_artifact(
    repo: MockRepository,
    *,
    session_id: str,
    audio_file_id: str | None,
) -> None:
    if not audio_file_id:
        return
    active_statuses = {
        JobStatus.queued.value,
        JobStatus.processing.value,
        JobStatus.transcription_completed.value,
    }
    for job in repo.find("jobs", session_id=session_id):
        if job.details.get("audio_file_id") != audio_file_id:
            continue
        status_value = job.status.value if hasattr(job.status, "value") else str(job.status)
        if status_value in active_statuses:
            raise ValueError("Only one active processing job is allowed per audio artifact.")


def create_audio_processing_job(repo: MockRepository, session_id: str, payload: AudioProcessRequest | TranscriptionJobRequest, *, actor_id: str = "system") -> ProcessingJob:
    session = repo.sessions[session_id]
    audio_file_id = _resolve_audio_file_id_for_job(repo, session_id, payload)
    _ensure_no_active_job_for_audio_artifact(
        repo,
        session_id=session_id,
        audio_file_id=audio_file_id,
    )
    try:
        provider = asr_provider_registry.get(payload.provider)
    except KeyError:
        raise ValueError(f"ASR provider '{payload.provider}' is not registered.")
    
    # Synthetic ASR text must never be attached to a recording outside local
    # demo mode, either directly or as a fallback.
    mock_output_allowed = get_settings().mock_mode
    if payload.provider == "mock" and not mock_output_allowed:
        raise ValueError("The mock transcription provider is available in local demo mode only.")

    avail = provider.check_availability()
    
    # Fallback logic — explicit, never silent
    actual_provider = payload.provider
    fallback_reason = None
    
    allow_fallback = False
    if hasattr(payload, "config") and payload.config is not None:
        allow_fallback = getattr(payload.config, "allow_fallback_to_mock", False)
    else:
        allow_fallback = getattr(payload, "allow_fallback_to_mock", False)
        
    if not avail:
        if allow_fallback and mock_output_allowed:
            actual_provider = "mock"
            fallback_reason = f"Provider '{payload.provider}' unavailable: {avail.reason}. Fell back to mock."
        else:
            job = ProcessingJob(
                job_id=new_id("job"),
                organization_id=session.organization_id,
                session_id=session_id,
                status=JobStatus.failed,
                message=f"Provider '{payload.provider}' is unavailable: {avail.reason}",
                error_code="provider_unavailable",
                details={
                    "audio_file_id": audio_file_id,
                    "requested_provider": payload.provider,
                    "actual_provider": None,
                    "fallback_reason": None,
                    "provider_error": avail.reason,
                    "status_history": [JobStatus.failed.value],
                },
            )
            repo.jobs[job.job_id] = job
            repo.add_audit("transcription.provider_unavailable", job.job_id,
                           f"Provider '{payload.provider}' unavailable; job failed immediately.", actor_id=actor_id)
            return job

    job = ProcessingJob(
        job_id=new_id("job"),
        organization_id=session.organization_id,
        session_id=session_id,
        status=JobStatus.queued,
        message="Transcription job queued.",
        details={
            "queued_payload": payload.model_dump(mode="json"),
            "audio_file_id": audio_file_id,
            "requested_provider": payload.provider,
            "actual_provider": actual_provider,
            "fallback_reason": fallback_reason,
            "status_history": [JobStatus.queued.value],
        },
    )
    repo.jobs[job.job_id] = job
    repo.add_audit("audio.process_queued", job.job_id, "Experimental audio processing job queued.", actor_id=actor_id)
    return job


def run_audio_processing_job(
    repo: MockRepository,
    job_id: str,
    *,
    actor_id: str = "worker",
    progress_callback: Callable[[float, str], None] | None = None,
) -> ProcessingJob:
    """Run a queued transcription job.

    ``progress_callback`` receives (fraction, stage) from an on-device
    provider; the desktop app shows it, the API worker passes none.
    """
    if job_id not in repo.jobs:
        raise ValueError("Job not found.")
    job = repo.jobs[job_id]
    
    queued_payload = job.details.get("queued_payload", {})
    if "config" in queued_payload:
        payload = TranscriptionJobRequest.model_validate(queued_payload)
    else:
        payload = AudioProcessRequest.model_validate(queued_payload)
        
    session_id = job.session_id
    if job.status == JobStatus.cancelled:
        # Cancelled while queued: leave it cancelled instead of running it.
        return repo.clone(job)
    if job.details.get("consent_withdrawn"):
        job.status = JobStatus.cancelled
        job.message = "Audio processing cancelled because case consent was withdrawn."
        job.error_code = "consent_withdrawn"
        append_job_status(job, JobStatus.cancelled)
        repo.add_audit("audio.process_cancelled", job.job_id, "Audio processing cancelled after consent withdrawal.", actor_id=actor_id)
        return repo.clone(job)
        
    try:
        ensure_session_consent_active(repo, session_id)
    except ValueError:
        job.status = JobStatus.cancelled
        job.message = "Audio processing cancelled because case consent was withdrawn."
        job.error_code = "consent_withdrawn"
        job.details = {**job.details, "consent_withdrawn": True}
        append_job_status(job, JobStatus.cancelled)
        repo.add_audit("audio.process_cancelled", job.job_id, "Audio processing cancelled after consent withdrawal.", actor_id=actor_id)
        return repo.clone(job)
        
    actual_provider_id = job.details.get("actual_provider") or payload.provider
    
    try:
        provider = asr_provider_registry.get(actual_provider_id)
    except KeyError:
        raise ValueError(f"ASR provider '{actual_provider_id}' is not registered.")
        
    job.status = JobStatus.processing
    job.message = "Audio processing job is running."
    append_job_status(job, JobStatus.processing)
    repo.add_audit("audio.process_started", job.job_id, "Experimental audio processing job started.", actor_id=actor_id)
    
    audio_file_id = job.details.get("audio_file_id") or (payload.audio_id if hasattr(payload, "audio_id") else None)
    audio_file = None
    if audio_file_id and audio_file_id in repo.audio_files:
        audio_file = repo.audio_files[audio_file_id]
        
    duration_seconds = getattr(payload, "duration_seconds", None)
    sample_rate_hz = getattr(payload, "sample_rate_hz", None)
    channels = getattr(payload, "channels", None)
    estimated_noise_level = getattr(payload, "estimated_noise_level", None)
    silence_ratio = getattr(payload, "silence_ratio", None)
    
    if audio_file:
        duration_seconds = duration_seconds or audio_file.duration_seconds
        sample_rate_hz = sample_rate_hz or audio_file.sample_rate_hz
        channels = channels or audio_file.channels
        estimated_noise_level = estimated_noise_level or audio_file.estimated_noise_level
        silence_ratio = silence_ratio or audio_file.silence_ratio
        
    quality = analyze_audio_quality(
        duration_seconds=duration_seconds,
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        estimated_noise_level=estimated_noise_level,
        silence_ratio=silence_ratio,
    )
    
    if quality.status == "failed":
        job.status = JobStatus.failed
        job.message = "Audio quality checks failed before ASR draft generation."
        job.error_code = "audio_quality_failed"
        job.details = {**job.details, "quality": quality.model_dump(mode="json")}
        append_job_status(job, JobStatus.failed)
        repo.add_audit("audio.process_failed", job.job_id, "Audio processing failed quality checks.", actor_id=actor_id)
        return repo.clone(job)

    try:
        transcribe_config = {}
        if hasattr(payload, "config") and payload.config is not None:
            transcribe_config = payload.config.model_dump()
        if hasattr(payload, "draft_text") and payload.draft_text:
            transcribe_config["draft_text"] = payload.draft_text
        local_audio_path = _local_audio_path(audio_file)
        if local_audio_path is not None:
            transcribe_config["audio_path"] = str(local_audio_path)
            transcribe_config["child_age_months"] = repo.cases[repo.sessions[session_id].case_id].age_months
            if progress_callback is not None:
                transcribe_config["progress_callback"] = progress_callback

        result: TranscriptionResult = provider.transcribe(
            audio_ref=audio_file_id or "",
            config=transcribe_config,
        )
    except Exception as exc:
        job.status = JobStatus.failed
        job.message = str(exc)
        job.error_code = "asr_failed"
        job.details = {**job.details, "quality": quality.model_dump(mode="json"), "provider_error": str(exc)}
        append_job_status(job, JobStatus.failed)
        repo.add_audit("audio.process_failed", job.job_id, "ASR provider failed before draft transcript generation.", actor_id=actor_id)
        return repo.clone(job)
        
    if result.status != "completed":
        job.status = JobStatus.failed
        job.message = result.error_message or "Provider returned non-completed status."
        job.error_code = "asr_failed"
        job.details = {**job.details, "quality": quality.model_dump(mode="json"), "provider_error": result.error_message}
        append_job_status(job, JobStatus.failed)
        repo.add_audit("audio.process_failed", job.job_id, f"ASR provider failed: {result.error_message}", actor_id=actor_id)
        return repo.clone(job)
        
    draft_warnings = []
    utterance_count = len(result.transcript_lines)
    if utterance_count < 2:
        draft_warnings.append("transcript too short")
    if not any(line.speaker == "CHI" for line in result.transcript_lines):
        draft_warnings.append("no child speech detected")
    if not result.speaker_segments_available:
        draft_warnings.append("diarization failed")
        
    job.status = JobStatus.transcription_completed
    job.message = "ASR draft transcription completed; preparing reviewable transcript."
    append_job_status(job, JobStatus.transcription_completed)
    
    transcript = create_draft_transcript_from_result(repo, session_id, result, audio_file_id=audio_file_id)
    
    asr_draft_result = AsrDraftResult(
        provider=result.provider_id,
        transcript_id=transcript.transcript_id,
        utterance_count=len(transcript.utterances),
        confidence_available=result.confidence_available,
        timestamps_available=result.word_timestamps_available,
        diarization_available=result.speaker_segments_available,
        warnings=draft_warnings + result.warnings,
        quality=quality,
    )
    
    job.status = JobStatus.needs_review
    job.message = "Draft transcript generated. Therapist correction and attestation are required before features."
    job.details = {**job.details, "asr_draft": asr_draft_result.model_dump(mode="json")}
    append_job_status(job, JobStatus.needs_review)
    repo.add_audit("audio.process", job.job_id, "Experimental audio-to-draft-CHA processing completed.", actor_id=actor_id)
    return repo.clone(job)

_CHAT_LANGUAGE_CODES = {"th": "tha", "en": "eng"}


def _chat_languages(detected: str) -> list[str]:
    """CHAT @Languages codes for the languages a provider reported hearing."""
    codes = [_CHAT_LANGUAGE_CODES.get(part.strip().lower()) for part in (detected or "").split(",")]
    return [code for code in dict.fromkeys(codes) if code]


def create_draft_transcript_from_result(
    repo: MockRepository,
    session_id: str,
    result: TranscriptionResult,
    audio_file_id: str | None = None,
) -> Transcript:
    """
    Create a draft Transcript from a TranscriptionResult.
    - Maps TranscriptLine -> Utterance (preserving timestamps)
    - source = "mock_asr_draft:{id}" or "asr_draft:{id}"
    - Adds ASR warning QaIssue
    - therapist_attested=False locks feature extraction
    """
    session = repo.sessions[session_id]

    utterances: list[Utterance] = []
    for line in result.transcript_lines:
        speaker_code = line.speaker
        # Adult labels are kept only when the provider actually separated
        # speakers; otherwise they are placeholders for the therapist to set.
        if speaker_code != "CHI" and not (
            result.speaker_segments_available and speaker_code in DIARIZED_ADULT_SPEAKERS
        ):
            speaker_code = "UNK"
        utt = Utterance(
            utterance_id=new_id("utt"),
            speaker=speaker_code,
            text=line.text,
            start_ms=line.start_ms,
            end_ms=line.end_ms,
            confidence=line.confidence,
            unintelligible=line.unclear,
            speaker_uncertain=getattr(line, "speaker_uncertain", False),
            source=line.source,
            notes="ASR draft — therapist review required." if (line.unclear or speaker_code == "UNK") else "",
            review_status="draft",
        )
        utterances.append(utt)

    is_mock = result.provider_id == "mock"
    source_label = (
        f"mock_asr_draft:{result.provider_id}" if is_mock
        else f"asr_draft:{result.provider_id}"
    )

    asr_warning = QaIssue(
        code="ASR_DRAFT_REVIEW_REQUIRED",
        severity="warning",
        message="ASR draft transcript — therapist must listen to the audio and correct all content before feature extraction.",
        blocking=False,
        fix_suggestion="Review all utterances, correct speaker labels, and attest when satisfied.",
        source="asr_pipeline",
    )
    qa_issues = [asr_warning]
    if is_mock:
        qa_issues.append(QaIssue(
            code="MOCK_ASR_OUTPUT",
            severity="warning",
            message="MOCK PROVIDER: Synthetic placeholder output, not real ASR. Replace all content.",
            blocking=False,
            source="asr_pipeline",
        ))

    chat_languages = _chat_languages(result.language)
    raw_text = build_cha_text(
        utterances,
        media_name=f"{session_id}_audio",
        **({"language": ", ".join(chat_languages)} if chat_languages else {}),
    )
    transcript = Transcript(
        transcript_id=new_id("tr"),
        session_id=session_id,
        case_id=session.case_id,
        source=source_label,
        raw_text=raw_text,
        utterances=utterances,
        review_status=ReviewStatus.needs_review,
        therapist_attested=False,
        qa_status=QaStatus.warning,
        qa_issues=qa_issues,
        chat_metadata={
            "asr_provider": result.provider_id,
            "asr_provider_version": result.provider_version,
            "is_mock": is_mock,
            "audio_file_id": audio_file_id,
            "word_timestamps_available": result.word_timestamps_available,
            **({"languages": chat_languages} if chat_languages else {}),
        },
    )
    repo.transcripts[transcript.transcript_id] = transcript
    session.transcript_id = transcript.transcript_id
    session.status = ReviewStatus.needs_review
    return transcript



def analyze_audio_quality(
    *,
    duration_seconds: float | None,
    sample_rate_hz: int | None,
    channels: int | None,
    estimated_noise_level: float | None,
    silence_ratio: float | None,
) -> AudioQualityReport:
    warnings: list[str] = []
    status = "pass"
    if duration_seconds is not None and duration_seconds > 3600:
        warnings.append("audio too long")
        status = "failed"
    if sample_rate_hz is not None and sample_rate_hz < 16000:
        warnings.append("sample rate below 16 kHz")
        status = "warning" if status == "pass" else status
    if channels is not None and channels < 1:
        warnings.append("missing audio channel")
        status = "failed"
    if estimated_noise_level is not None and estimated_noise_level > 0.7:
        warnings.append("audio too noisy")
        status = "warning" if status == "pass" else status
    if silence_ratio is not None and silence_ratio > 0.8:
        warnings.append("high silence ratio")
        status = "warning" if status == "pass" else status
    return AudioQualityReport(
        duration_seconds=duration_seconds,
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        estimated_noise_level=estimated_noise_level,
        silence_ratio=silence_ratio,
        status=status,
        warnings=warnings,
    )







def recover_interrupted_jobs(repo: MockRepository, queue) -> dict[str, int]:
    """Settle transcription jobs left over by a process that kept its queue in memory.

    A job that was still waiting is queued again. A job that had started is
    marked failed: its work stopped with the process, it would otherwise block
    a new job for the same recording for good, and running it again unasked
    could transcribe a recording twice. The therapist can start it again.
    """
    requeued = 0
    failed = 0
    unfinished = {JobStatus.queued, JobStatus.processing, JobStatus.transcription_completed}
    for job in repo.find("jobs", status=unfinished):
        if "queued_payload" not in job.details:
            continue  # an upload record, not a transcription job
        if job.status == JobStatus.queued:
            queue.enqueue(job.job_id)
            requeued += 1
        elif job.status in {JobStatus.processing, JobStatus.transcription_completed}:
            job.status = JobStatus.failed
            job.message = "Transcription was interrupted by a restart. Start it again."
            job.error_code = "interrupted"
            append_job_status(job, JobStatus.failed)
            repo.add_audit(
                "audio.process_failed",
                job.job_id,
                "Audio processing was interrupted by a restart.",
                actor_id="worker",
                outcome="failure",
            )
            failed += 1
    return {"requeued": requeued, "failed": failed}


def append_job_status(job: ProcessingJob, status: JobStatus) -> None:
    history = list(job.details.get("status_history", []))
    if not history or history[-1] != status.value:
        history.append(status.value)
    job.details = {**job.details, "status_history": history}


def draft_quality_warnings(draft: ProviderDraft) -> list[str]:
    utterances = manual_text_to_utterances(draft.text)
    warnings: list[str] = []
    if len(utterances) < 2:
        warnings.append("transcript too short")
    if not any(str(utterance.speaker).upper() == "CHI" for utterance in utterances):
        warnings.append("no child speech detected")
    if not draft.diarization_available:
        warnings.append("diarization failed")
    return warnings
