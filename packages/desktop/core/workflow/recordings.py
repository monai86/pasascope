"""Recordings: storing, playing back and transcribing them.

Part of :class:`packages.desktop.core.service.DesktopService`."""

from __future__ import annotations

from hashlib import sha256
import mimetypes
from pathlib import Path
import threading

from packages.desktop.core.i18n import tr
from packages.desktop.core.workspace import LOCAL_USER_ID
from packages.desktop.core.workflow.common import (
    ProgressCallback,
    AUDIO_SUFFIXES,
    WorkflowError,
    TranscriptionCancelled,
    _utc,
    _status_value,
    _safe_filename,
    _audio_duration,
    _upload_message,
    _decode_for_listening,
)


class RecordingsMixin:
    def transcription_availability(self) -> tuple[bool, str]:
        """Whether on-device Whisper can run, and why not when it cannot."""
        from app.services.asr_providers.registry import asr_provider_registry

        availability = asr_provider_registry.get("local_whisper").check_availability()
        # The provider's own message about a missing Thai model names a
        # developer script; point the therapist to the download instead.
        if not availability and self.transcription_mode == "accurate" and not self.thai_model_status()["installed"]:
            return False, tr("ต้องดาวน์โหลดโมเดลภาษาไทยก่อน (ตั้งค่า → ดาวน์โหลดโมเดลถอดเสียง)",
                             "Download the Thai model first (Settings, Download speech models)")
        return bool(availability), availability.reason or ""

    def session_audio(self, session_id: str):
        """The session's most recent stored recording, or None."""
        files = [
            f for f in self.repo.find("audio_files", session_id=session_id)
            if f.retained and f.upload_status == "uploaded"
        ]
        return max(files, key=lambda f: _utc(f.created_at)) if files else None

    def audio_path(self, audio_file) -> Path:
        root = self.workspace.storage_root.resolve()
        path = (root / audio_file.object_key).resolve()
        if root not in path.parents or not path.is_file():
            raise WorkflowError(tr("ไม่พบไฟล์เสียงของ session นี้ในเครื่อง", "This session's recording is not on this computer."))
        return path

    def playback_path(self, audio_file) -> Path:
        """The recording at its own quality, in a form the player can read.

        WAV, MP3, FLAC and Ogg are played as they are. Other containers (M4A,
        MP4, WebM) are decoded once to a WAV copy at the recording's own sample
        rate and channels: the 16 kHz mono copy transcription uses loses
        everything above 8 kHz and is hard to listen to.
        """
        import soundfile

        source = self.audio_path(audio_file)
        try:
            soundfile.info(str(source))
            return source
        except (RuntimeError, soundfile.LibsndfileError):
            pass
        target = self.workspace.storage_root / "playback" / f"{audio_file.audio_file_id}.full.wav"
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                _decode_for_listening(source, target)
            except Exception as exc:  # noqa: BLE001 - any decoder failure is reported the same way
                target.unlink(missing_ok=True)
                raise WorkflowError(tr("แปลงไฟล์เสียงเพื่อเล่นไม่สำเร็จ", "Could not convert the recording for playback.")) from exc
        return target

    def store_recording(self, session_id: str, source: Path):
        """Copy a recording into the workspace and register it with the session."""
        from app.schemas.clinical import AudioUploadCompleteRequest, AudioUploadRequest
        from app.services.audio_job_service import complete_audio_upload, create_audio_upload_job
        from app.services.consent_service import ensure_session_consent_active

        source = Path(source)
        self._require_granted(self.get_session(session_id).case_id)
        self._ensure(ensure_session_consent_active, session_id)
        if not source.is_file():
            raise WorkflowError(tr(f"ไม่พบไฟล์ {source.name}", f"File not found: {source.name}"))
        content_type = AUDIO_SUFFIXES.get(source.suffix.lower()) or mimetypes.guess_type(source.name)[0] or ""
        size = source.stat().st_size
        duration = _audio_duration(source)
        try:
            job = create_audio_upload_job(
                self.repo,
                session_id,
                AudioUploadRequest(
                    filename=_safe_filename(source.name),
                    content_type=content_type,
                    size_bytes=size,
                    duration_seconds=duration,
                ),
                actor_id=LOCAL_USER_ID,
            )
        except ValueError as exc:
            raise WorkflowError(_upload_message(str(exc))) from exc
        audio_file_id = job.details["audio_file"]["audio_file_id"]
        audio_file = self.repo.audio_files[audio_file_id]
        root = self.workspace.storage_root.resolve()
        destination = (root / audio_file.object_key).resolve()
        if root not in destination.parents:
            raise WorkflowError(tr("ตำแหน่งเก็บไฟล์เสียงไม่ถูกต้อง", "Invalid storage location for the recording."))
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = sha256()
        with source.open("rb") as reader, destination.open("wb") as writer:
            for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                digest.update(chunk)
                writer.write(chunk)
        audio_file.checksum_sha256 = digest.hexdigest()
        audio_file.upload_status = "pending_verification"
        stored = complete_audio_upload(
            self.repo, audio_file_id, AudioUploadCompleteRequest(size_bytes=size), actor_id=LOCAL_USER_ID
        )
        self._save()
        return stored

    def transcribe(
        self,
        session_id: str,
        audio_file_id: str,
        *,
        progress: ProgressCallback | None = None,
        cancel: threading.Event | None = None,
    ):
        """Draft a transcript from a stored recording with on-device Whisper.

        Runs for minutes; call it from a worker thread. Setting ``cancel``
        stops it at the next progress step.
        """
        from app.schemas.clinical import JobStatus, TranscriptionJobConfig, TranscriptionJobRequest
        from app.services.audio_job_service import append_job_status, create_audio_processing_job, run_audio_processing_job
        from app.services.consent_service import ensure_session_consent_active

        self.get_session(session_id)
        self._ensure(ensure_session_consent_active, session_id)
        available, reason = self.transcription_availability()
        if not available:
            raise WorkflowError(tr(f"ถอดเสียงบนเครื่องไม่ได้: {reason}", f"Transcription unavailable: {reason}"))

        def on_progress(fraction: float, stage: str) -> None:
            if cancel is not None and cancel.is_set():
                raise TranscriptionCancelled()
            if progress is not None:
                progress(fraction, stage)

        try:
            job = create_audio_processing_job(
                self.repo,
                session_id,
                TranscriptionJobRequest(
                    audio_id=audio_file_id,
                    provider="local_whisper",
                    config=TranscriptionJobConfig(language="th"),
                ),
                actor_id=LOCAL_USER_ID,
            )
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        if _status_value(job.status) == "failed":
            self._save()
            raise WorkflowError(job.message)
        job = run_audio_processing_job(
            self.repo, job.job_id, actor_id=LOCAL_USER_ID, progress_callback=on_progress
        )
        if cancel is not None and cancel.is_set():
            stored = self.repo.jobs[job.job_id]
            stored.status = JobStatus.cancelled
            stored.message = "Transcription cancelled by therapist."
            append_job_status(stored, JobStatus.cancelled)
            self.repo.add_audit("job.cancel", job.job_id, "Transcription job cancelled by therapist.", actor_id=LOCAL_USER_ID)
            raise WorkflowError(tr("ยกเลิกการถอดเสียงแล้ว", "Transcription cancelled."))
        if _status_value(job.status) != "needs_review":
            self._save()
            raise WorkflowError(tr(f"ถอดเสียงไม่สำเร็จ: {job.message}", f"Transcription failed: {job.message}"))
        self._save()
        return self.get_transcript(session_id)
