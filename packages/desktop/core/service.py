"""The clinical workflow the desktop UI drives.

Each method does what the matching ``/api/v1`` route does, minus HTTP: the
same consent checks, the same service call, the same audit event. Records
are written to the workspace's SQLite file as they change.

Flow: case → consent → session → recording or transcript → review and
attest → features and review cues → report draft → sign-off → export.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone
from hashlib import sha256
import mimetypes
from pathlib import Path
import shutil
import subprocess
import threading
from typing import Any

from packages.desktop.core.workspace import LOCAL_ORGANIZATION_ID, LOCAL_USER_ID, Workspace

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
        super().__init__("transcript ไม่ผ่านการตรวจรูปแบบ ต้องระบุเหตุผลจึงจะรับรองได้")
        self.issues = issues


class TranscriptionCancelled(Exception):
    """Raised from the progress callback to stop a running transcription."""


def _utc(value: datetime | None) -> datetime:
    """Records read back from SQLite carry naive UTC times; new ones are aware."""
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _status_value(status: Any) -> str:
    return status.value if hasattr(status, "value") else str(status)


class DesktopService:
    def __init__(self, workspace: Workspace, *, repository: Any | None = None) -> None:
        self.workspace = workspace
        if repository is None:
            from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

            repository = SqlAlchemyRepository(workspace.database_url, create_schema=True, seed_demo=False)
        self.repo = repository
        self._apply_transcription_mode()
        self._apply_clinic_speaker_model()

    # ------------------------------------------------------------------
    # Therapist on this computer
    # ------------------------------------------------------------------
    @property
    def therapist_name(self) -> str:
        return str(self.workspace.read_profile().get("display_name") or "").strip()

    def set_therapist_name(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise WorkflowError("กรุณาใส่ชื่อนักบำบัด")
        if len(name) > 120:
            raise WorkflowError("ชื่อยาวเกิน 120 ตัวอักษร")
        profile = self.workspace.read_profile()
        profile["display_name"] = name
        self.workspace.write_profile(profile)

    # Transcription modes the therapist can pick. On six scripted Thai
    # dialogues the Thai model had CER 1.2% at ~4.8x the audio length, the
    # multilingual model 5.2% at ~0.9x (reports/metrics/asr_desktop_tuning.md).
    TRANSCRIPTION_MODES = {
        "accurate": "thai_specialized",
        "fast": "thai",
    }

    @property
    def transcription_mode(self) -> str:
        mode = str(self.workspace.read_profile().get("transcription_mode") or "accurate")
        return mode if mode in self.TRANSCRIPTION_MODES else "accurate"

    def set_transcription_mode(self, mode: str) -> None:
        if mode not in self.TRANSCRIPTION_MODES:
            raise WorkflowError(f"ไม่รู้จักโหมด {mode}")
        profile = self.workspace.read_profile()
        profile["transcription_mode"] = mode
        self.workspace.write_profile(profile)
        self._apply_transcription_mode()

    def _apply_transcription_mode(self) -> None:
        import os

        from app.core.config import get_settings

        strategy = self.TRANSCRIPTION_MODES[self.transcription_mode]
        if os.environ.get("PASASCOPE_ASR_LANGUAGE_STRATEGY") != strategy:
            os.environ["PASASCOPE_ASR_LANGUAGE_STRATEGY"] = strategy
            get_settings.cache_clear()

    # ------------------------------------------------------------------
    # The clinic's own child/adult model
    # ------------------------------------------------------------------
    # Learned from this computer's attested, Whisper-drafted sessions and used
    # for new drafts only when it beats the frame model on those sessions
    # (src/audio_pipeline/clinic_speaker_model.py).

    @property
    def clinic_speaker_model_path(self) -> Path:
        return self.workspace.root / "models" / "clinic_speaker_model.json"

    @property
    def _speaker_feature_cache(self) -> Path:
        return self.workspace.root / ".cache" / "speaker_features"  # left out of backups

    @property
    def clinic_speaker_enabled(self) -> bool:
        return bool(self.workspace.read_profile().get("clinic_speaker_model", True))

    def set_clinic_speaker_enabled(self, enabled: bool) -> None:
        profile = self.workspace.read_profile()
        profile["clinic_speaker_model"] = bool(enabled)
        self.workspace.write_profile(profile)
        self._apply_clinic_speaker_model()
        self.repo.add_audit(
            "speaker_model.enable" if enabled else "speaker_model.disable", "clinic_speaker_model",
            "Therapist turned the clinic speaker model " + ("on." if enabled else "off."), actor_id=LOCAL_USER_ID,
        )
        self._save()

    def _apply_clinic_speaker_model(self) -> None:
        import os

        from src.audio_pipeline.clinic_speaker_model import CLINIC_MODEL_ENV, read_result

        data = read_result(self.clinic_speaker_model_path)
        if self.clinic_speaker_enabled and data and data.get("adopted"):
            os.environ[CLINIC_MODEL_ENV] = str(self.clinic_speaker_model_path)
        else:
            os.environ.pop(CLINIC_MODEL_ENV, None)

    def clinic_speaker_training_sessions(self) -> list[dict]:
        """Attested sessions drafted by Whisper whose recording is on this computer.

        Only children whose consent is still granted are used. Lines without
        times or with an unknown speaker are left out.
        """
        sessions = []
        for case in self.repo.find("cases", organization_id=LOCAL_ORGANIZATION_ID):
            if case.consent_status != "granted":
                continue
            for session in self.list_sessions(case.case_id):
                transcript = self.get_transcript(session.session_id)
                if not transcript or not transcript.therapist_attested or not str(transcript.source).startswith("asr_draft"):
                    continue
                audio = self.session_audio(session.session_id)
                if audio is None:
                    continue
                try:
                    path = self.audio_path(audio)
                except WorkflowError:
                    continue
                spans, labels = [], []
                for u in transcript.utterances:
                    speaker = str(u.speaker)
                    if u.start_ms is None or u.end_ms is None or u.end_ms <= u.start_ms or speaker in ("", "UNK"):
                        continue
                    spans.append((u.start_ms / 1000, u.end_ms / 1000))
                    labels.append(speaker == "CHI")
                if spans:
                    sessions.append({
                        "session_id": session.session_id, "child_id": case.case_id, "audio_file_id": audio.audio_file_id,
                        "audio_path": str(path), "spans": spans, "labels": labels,
                    })
        return sessions

    def train_clinic_speaker_model(self, sessions: list[dict], progress: ProgressCallback | None = None):
        """Read each session's recording and train; touches only files, so it can run in a worker thread."""
        import json

        import numpy as np

        from src.audio_pipeline.clinic_speaker_model import (
            MIN_CHILDREN, MIN_SESSIONS, LabelledSession, train_clinic_head, utterance_features,
        )

        children = {s["child_id"] for s in sessions}
        if len(sessions) < MIN_SESSIONS or len(children) < MIN_CHILDREN:
            return train_clinic_head(
                LabelledSession(s["session_id"], s["child_id"], np.zeros((len(s["labels"]), 0)), np.asarray(s["labels"], int))
                for s in sessions
            )
        model = None
        labelled = []
        self._speaker_feature_cache.mkdir(parents=True, exist_ok=True)
        for index, s in enumerate(sessions, start=1):
            if progress is not None:
                progress(index / (len(sessions) + 1), f"อ่านเสียง session {index}/{len(sessions)}")
            key = sha256(json.dumps([s["audio_file_id"], s["spans"]]).encode()).hexdigest()[:24]
            cached = self._speaker_feature_cache / f"{key}.npy"
            try:
                design = np.load(cached)
            except (OSError, ValueError):
                import librosa

                from src.audio_pipeline.child_adult_frames import SAMPLE_RATE, ChildAdultFrameModel

                model = model or ChildAdultFrameModel()
                audio, _ = librosa.load(s["audio_path"], sr=SAMPLE_RATE, mono=True)
                design = utterance_features(*model.frame_outputs(audio), s["spans"])
                np.save(cached, design)
            labelled.append(LabelledSession(s["session_id"], s["child_id"], design, np.asarray(s["labels"], int)))
        if progress is not None:
            progress(len(sessions) / (len(sessions) + 1), "กำลังเทรนและทดสอบโมเดล")
        return train_clinic_head(labelled)

    def save_clinic_speaker_result(self, result) -> dict:
        """Keep the newest result, record it in the audit log, and use the model if it was adopted."""
        from src.audio_pipeline.clinic_speaker_model import save_result

        if result.reason == "not_enough_sessions":
            return self.clinic_speaker_status()
        save_result(self.clinic_speaker_model_path, result, trained_at=datetime.now().astimezone().isoformat(timespec="seconds"))
        if result.model_accuracy is not None:
            outcome = "adopted" if result.adopted else "kept the frame model"
            message = (
                f"Clinic speaker model trained on {result.sessions} attested sessions ({result.children} children): "
                f"held-out balanced accuracy {result.model_balanced:.1%} vs frame model {result.frame_balanced:.1%} "
                f"(accuracy {result.model_accuracy:.1%} vs {result.frame_accuracy:.1%}); {outcome}."
            )
        else:
            message = f"Clinic speaker model not trained: {result.reason}."
        self.repo.add_audit("speaker_model.train", "clinic_speaker_model", message, actor_id=LOCAL_USER_ID)
        self._save()
        self._apply_clinic_speaker_model()
        return self.clinic_speaker_status()

    def update_clinic_speaker_model(self, progress: ProgressCallback | None = None) -> dict:
        return self.save_clinic_speaker_result(self.train_clinic_speaker_model(self.clinic_speaker_training_sessions(), progress))

    def reset_clinic_speaker_model(self) -> None:
        self.clinic_speaker_model_path.unlink(missing_ok=True)
        shutil.rmtree(self._speaker_feature_cache, ignore_errors=True)
        self._apply_clinic_speaker_model()
        self.repo.add_audit("speaker_model.reset", "clinic_speaker_model", "Therapist cleared the clinic speaker model.", actor_id=LOCAL_USER_ID)
        self._save()

    def clinic_speaker_status(self) -> dict:
        from src.audio_pipeline.clinic_speaker_model import MIN_CHILDREN, MIN_SESSIONS, read_result

        eligible = self.clinic_speaker_training_sessions()
        children = len({s["child_id"] for s in eligible})
        data = read_result(self.clinic_speaker_model_path) or {}
        return {
            "enabled": self.clinic_speaker_enabled,
            "in_use": self.clinic_speaker_enabled and bool(data.get("adopted")),
            "trained": bool(data),
            "adopted": bool(data.get("adopted")),
            "eligible_sessions": len(eligible),
            "eligible_children": children,
            "sessions_needed": max(0, MIN_SESSIONS - len(eligible)),
            "children_needed": max(0, MIN_CHILDREN - children),
            "trained_sessions": data.get("sessions"),
            "trained_children": data.get("children"),
            "model_accuracy": data.get("model_accuracy"),
            "frame_accuracy": data.get("frame_accuracy"),
            "model_balanced": data.get("model_balanced"),
            "frame_balanced": data.get("frame_balanced"),
            "trained_at": data.get("trained_at"),
            "stale": bool(data) and data.get("sessions") != len(eligible),
        }

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------
    BACKUP_REMINDER_DAYS = 7

    @property
    def last_backup_at(self):
        """When this workspace was last backed up, or None."""
        value = self.workspace.read_profile().get("last_backup_at")
        try:
            return datetime.fromisoformat(value) if value else None
        except ValueError:
            return None

    def backup_due(self) -> bool:
        """True when there is real data and no backup in the last week."""
        if (self.workspace.root / "pasascope-demo.json").exists() or not self.list_cases():
            return False
        last = self.last_backup_at
        return last is None or (datetime.now(last.tzinfo) - last).days >= self.BACKUP_REMINDER_DAYS

    def create_backup(self, destination, app_version: str = ""):
        from packages.desktop.core.backup import create_backup

        self._save()
        cases = self.list_cases()
        counts = {
            "cases": len(cases),
            "sessions": sum(len(self.list_sessions(case.case_id)) for case in cases),
            "recordings": sum(1 for path in self.workspace.storage_root.rglob("*") if path.is_file()),
        }
        info = create_backup(self.workspace, Path(destination), counts=counts, app_version=app_version)
        profile = self.workspace.read_profile()
        profile["last_backup_at"] = info.created_at
        profile["last_backup_path"] = str(info.path)
        self.workspace.write_profile(profile)
        return info

    def close(self) -> None:
        """Release the database file, e.g. before a restore replaces it."""
        engine = getattr(self.repo, "engine", None)
        if engine is not None:
            engine.dispose()

    @property
    def user(self):
        from app.core.security import CurrentUser

        return CurrentUser(
            user_id=LOCAL_USER_ID,
            role="therapist",
            display_name=self.therapist_name or "Therapist",
            organization_id=LOCAL_ORGANIZATION_ID,
        )

    def _require_signer(self) -> str:
        name = self.therapist_name
        if not name:
            raise WorkflowError("ตั้งชื่อนักบำบัดก่อน (เมนู ตั้งค่า) เพราะชื่อนี้จะอยู่ในการรับรองและการลงนาม")
        return name

    def _save(self) -> None:
        if hasattr(self.repo, "save"):
            self.repo.save()

    # ------------------------------------------------------------------
    # Cases and consent
    # ------------------------------------------------------------------
    def list_cases(self, search: str = "") -> list:
        cases = self.repo.find("cases", organization_id=LOCAL_ORGANIZATION_ID)
        needle = search.strip().lower()
        if needle:
            cases = [
                c for c in cases
                if needle in c.child_code.lower() or needle in (c.nickname or "").lower()
            ]
        return sorted(cases, key=lambda c: _utc(c.updated_at), reverse=True)

    def get_case(self, case_id: str):
        case = self.repo.cases.get(case_id)
        if case is None or case.organization_id != LOCAL_ORGANIZATION_ID:
            raise WorkflowError("ไม่พบเคสนี้")
        return case

    def create_case(
        self,
        child_code: str,
        age_months: int,
        *,
        nickname: str = "",
        language: str = "Thai",
        notes: str = "",
    ):
        from pydantic import ValidationError

        from app.schemas.clinical import ChildCaseCreate

        child_code = child_code.strip()
        if any(c.child_code == child_code for c in self.list_cases()):
            raise WorkflowError(f"มีเคสรหัส {child_code} อยู่แล้ว")
        try:
            payload = ChildCaseCreate(
                child_code=child_code,
                nickname=nickname.strip() or None,
                age_months=age_months,
                language=language,
                notes=notes,
                organization_id=LOCAL_ORGANIZATION_ID,
                care_team_user_ids=[LOCAL_USER_ID],
                primary_therapist_user_id=LOCAL_USER_ID,
                consent_status="pending",
            )
        except ValidationError as exc:
            raise WorkflowError(_validation_message(exc)) from exc
        case = self.repo.create_case(payload, actor_id="system", audit_actor_id=LOCAL_USER_ID)
        self._save()
        return case

    def grant_consent(self, case_id: str, signer: str, consent_date: date, notes: str = ""):
        from pydantic import ValidationError

        from app.schemas.clinical import ConsentGrantRequest
        from app.services.consent_service import grant_consent

        self.get_case(case_id)
        try:
            payload = ConsentGrantRequest(
                signer=signer, consent_date=consent_date, notes=notes, confirmation_checked=True
            )
            case = grant_consent(self.repo, case_id, payload, actor_id=LOCAL_USER_ID)
        except ValidationError as exc:
            raise WorkflowError(_validation_message(exc)) from exc
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return case

    def withdraw_consent(self, case_id: str, reason: str):
        from app.services.consent_service import withdraw_consent

        self.get_case(case_id)
        if not reason.strip():
            raise WorkflowError("กรุณาระบุเหตุผลที่ถอนความยินยอม")
        result = withdraw_consent(
            self.repo, case_id, reason.strip(), True, actor_id=LOCAL_USER_ID, requester_role="therapist"
        )
        self._save()
        return result

    def consent_active(self, case_id: str) -> bool:
        return self.get_case(case_id).consent_status == "granted"

    def _ensure(self, check: Callable[..., None], *args: Any) -> None:
        """The API's consent gate: nothing changes on a case whose consent was withdrawn."""
        try:
            check(self.repo, *args)
        except ValueError as exc:
            raise WorkflowError("ผู้ปกครองถอนความยินยอมของเคสนี้แล้ว จึงเพิ่มหรือแก้ข้อมูลไม่ได้") from exc

    def _require_granted(self, case_id: str) -> None:
        """New sessions and recordings need consent that was actually recorded, not just pending."""
        status = self.get_case(case_id).consent_status
        if status == "withdrawn":
            raise WorkflowError("ผู้ปกครองถอนความยินยอมของเคสนี้แล้ว จึงเพิ่มหรือแก้ข้อมูลไม่ได้")
        if status != "granted":
            raise WorkflowError("บันทึกความยินยอมของผู้ปกครองก่อน แล้วจึงเริ่ม session หรือบันทึกเสียง")

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------
    def list_sessions(self, case_id: str) -> list:
        self.get_case(case_id)
        sessions = self.repo.find("sessions", case_id=case_id)
        return sorted(sessions, key=lambda s: (s.session_date, _utc(s.created_at)), reverse=True)

    def get_session(self, session_id: str):
        session = self.repo.sessions.get(session_id)
        if session is None or session.organization_id != LOCAL_ORGANIZATION_ID:
            raise WorkflowError("ไม่พบ session นี้")
        return session

    def create_session(self, case_id: str, session_date: date, *, session_type: str = "therapy_session", notes: str = ""):
        from app.schemas.clinical import TherapySessionCreate
        from app.services.consent_service import ensure_case_consent_active

        self._require_granted(case_id)
        self._ensure(ensure_case_consent_active, case_id)
        session = self.repo.create_session(
            case_id,
            TherapySessionCreate(session_date=session_date.isoformat(), session_type=session_type, notes=notes),
            actor_id=LOCAL_USER_ID,
        )
        self._save()
        return session

    # ------------------------------------------------------------------
    # Recordings
    # ------------------------------------------------------------------
    def transcription_availability(self) -> tuple[bool, str]:
        """Whether on-device Whisper can run, and why not when it cannot."""
        from app.services.asr_providers.registry import asr_provider_registry

        availability = asr_provider_registry.get("local_whisper").check_availability()
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
            raise WorkflowError("ไม่พบไฟล์เสียงของ session นี้ในเครื่อง")
        return path

    def playback_path(self, audio_file) -> Path:
        """A WAV copy of the recording that the player can read."""
        source = self.audio_path(audio_file)
        if source.suffix.lower() == ".wav":
            return source
        target = self.workspace.storage_root / "playback" / f"{audio_file.audio_file_id}.wav"
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            from src.audio_pipeline.pipeline import decode_to_wav

            try:
                decode_to_wav(source, target)
            except (OSError, subprocess.SubprocessError) as exc:
                raise WorkflowError("แปลงไฟล์เสียงเพื่อเล่นไม่สำเร็จ (ต้องมี ffmpeg)") from exc
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
            raise WorkflowError(f"ไม่พบไฟล์ {source.name}")
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
            raise WorkflowError("ตำแหน่งเก็บไฟล์เสียงไม่ถูกต้อง")
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
            raise WorkflowError(f"ถอดเสียงบนเครื่องไม่ได้: {reason}")

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
            raise WorkflowError("ยกเลิกการถอดเสียงแล้ว")
        if _status_value(job.status) != "needs_review":
            self._save()
            raise WorkflowError(f"ถอดเสียงไม่สำเร็จ: {job.message}")
        self._save()
        return self.get_transcript(session_id)

    # ------------------------------------------------------------------
    # Transcript
    # ------------------------------------------------------------------
    def get_transcript(self, session_id: str):
        session = self.get_session(session_id)
        if not session.transcript_id:
            return None
        return self.repo.transcripts.get(session.transcript_id)

    def import_transcript_text(self, session_id: str, text: str, *, filename: str = "transcript.cha"):
        """Add a transcript typed or loaded from a file: CHAT when it looks like CHAT, plain lines otherwise."""
        from app.schemas.clinical import TranscriptManualCreate, TranscriptUploadCha
        from app.services import transcript_service
        from app.services.consent_service import ensure_session_consent_active

        self.get_session(session_id)
        self._ensure(ensure_session_consent_active, session_id)
        if not text.strip():
            raise WorkflowError("ไม่มีข้อความให้นำเข้า")
        replace = self.get_transcript(session_id) is not None
        try:
            if _looks_like_chat(text):
                transcript = transcript_service.create_from_cha(
                    self.repo,
                    session_id,
                    TranscriptUploadCha(filename=_safe_filename(filename), cha_text=text, replace_existing=replace),
                    actor_id=LOCAL_USER_ID,
                )
            else:
                transcript = transcript_service.create_from_manual(
                    self.repo,
                    session_id,
                    TranscriptManualCreate(text=text, language="Thai", replace_existing=replace),
                    actor_id=LOCAL_USER_ID,
                )
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return transcript

    def save_utterances(self, transcript_id: str, utterances: list, *, note: str = ""):
        from app.schemas.clinical import TranscriptPatch
        from app.services import transcript_service
        from app.services.consent_service import ensure_transcript_consent_active

        self._ensure(ensure_transcript_consent_active, transcript_id)
        try:
            transcript = transcript_service.patch_transcript(
                self.repo,
                transcript_id,
                TranscriptPatch(utterances=utterances, reviewer_note=note),
                actor_id=LOCAL_USER_ID,
            )
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return transcript

    def attest(self, transcript_id: str, *, override_reason: str = ""):
        """Attest the transcript. A transcript that failed QA needs the therapist's reason to override."""
        from app.schemas.clinical import AttestationRequest
        from app.services import transcript_service
        from app.services.consent_service import ensure_transcript_consent_active

        signer = self._require_signer()
        self._ensure(ensure_transcript_consent_active, transcript_id)
        try:
            transcript = transcript_service.attest(
                self.repo,
                transcript_id,
                AttestationRequest(
                    attested_by=signer,
                    reason=override_reason.strip() or "Therapist reviewed the transcript against the recording.",
                    override_qa_failure=bool(override_reason.strip()),
                ),
                actor_id=LOCAL_USER_ID,
                attested_by=signer,
            )
        except ValueError as exc:
            if "failed QA" in str(exc):
                raise QaOverrideRequired(self.repo.transcripts[transcript_id].qa_issues) from exc
            raise WorkflowError(str(exc)) from exc
        self._save()
        return transcript

    def qa_issues(self, transcript_id: str) -> list:
        from app.services import transcript_service

        report = transcript_service.run_qa(self.repo, transcript_id, actor_id=LOCAL_USER_ID)
        self._save()
        return list(report.issues) if hasattr(report, "issues") else []

    def export_cha(self, transcript_id: str) -> str:
        from app.services import transcript_service

        return transcript_service.export_cha(self.repo, transcript_id).cha_text

    # ------------------------------------------------------------------
    # Features and review cues
    # ------------------------------------------------------------------
    def analyze(self, session_id: str):
        """Extract features from the attested transcript, then generate review cues."""
        from app.schemas.clinical import FeatureExtractionRequest, MLReviewRequest
        from app.services.consent_service import ensure_transcript_consent_active
        from app.services.feature_service import extract_features
        from app.services.ml_review_service import MLReadinessError, create_ml_review

        transcript = self.get_transcript(session_id)
        if transcript is None:
            raise WorkflowError("session นี้ยังไม่มี transcript")
        if not transcript.therapist_attested:
            raise WorkflowError("รับรอง transcript ก่อน แล้วจึงวิเคราะห์")
        self._ensure(ensure_transcript_consent_active, transcript.transcript_id)
        try:
            features = extract_features(
                self.repo, transcript.transcript_id, FeatureExtractionRequest(), actor_id=LOCAL_USER_ID
            )
            cues = create_ml_review(
                self.repo, transcript.transcript_id, MLReviewRequest(force_regenerate=True), actor_id=LOCAL_USER_ID
            )
        except MLReadinessError as exc:
            raise WorkflowError("; ".join(exc.readiness.reasons) or "ยังสร้าง cue ไม่ได้") from exc
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return features, cues

    def get_features(self, session_id: str):
        session = self.get_session(session_id)
        return self.repo.features.get(session.feature_set_id) if session.feature_set_id else None

    def get_cues(self, session_id: str):
        session = self.get_session(session_id)
        return self.repo.ml_results.get(session.ml_result_id) if session.ml_result_id else None

    def set_cue_state(self, result_id: str, cue_code: str, status: str, note: str = ""):
        from app.schemas.clinical import ReviewCuePatch
        from app.services.consent_service import ensure_session_consent_active
        from app.services.ml_review_service import patch_cue_state

        self._require_signer()
        result = self.repo.ml_results.get(result_id)
        if result is None:
            raise WorkflowError("ไม่พบผลการทบทวนนี้")
        self._ensure(ensure_session_consent_active, result.session_id)
        try:
            updated = patch_cue_state(
                self.repo, result_id, cue_code, ReviewCuePatch(status=status, therapist_note=note), self.user
            )
        except (KeyError, PermissionError, ValueError) as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return updated

    def session_step(self, session) -> int:
        """Where a session stands: 0 needs a transcript, 1 review, 2 analysis, 3 sign-off, 4 done."""
        transcript = self.get_transcript(session.session_id)
        if transcript is None:
            return 0
        if not transcript.therapist_attested:
            return 1
        if self.get_features(session.session_id) is None or session.findings_stale:
            return 2
        report = self.get_report(session.session_id)
        status = getattr(getattr(report, "status", None), "value", getattr(report, "status", None))
        return 4 if status == "Signed Off" else 3

    def session_summaries(self, case_id: str, names: list[str]) -> list[dict]:
        """One row per session, newest first: its step, open cues and feature values."""
        rows = []
        for session in self.list_sessions(case_id):
            features = self.get_features(session.session_id)
            cues = self.get_cues(session.session_id)
            values = {}
            if features is not None and not session.findings_stale:
                values = {f.name: f.value for f in features.features if f.name in names}
            pending = sum(
                1 for cue in (cues.cues if cues else [])
                if (cue.review_state.status if cue.review_state else "unreviewed") == "unreviewed"
            )
            rows.append({
                "session": session,
                "step": self.session_step(session),
                "values": values,
                "pending_cues": pending,
                "schema_version": getattr(features, "schema_version", None),
            })
        return rows

    def feature_trend(self, case_id: str, names: list[str]) -> list[tuple[str, dict[str, float]]]:
        """Each session's value for the named features, oldest session first."""
        rows: list[tuple[str, dict[str, float]]] = []
        for session in reversed(self.list_sessions(case_id)):
            features = self.get_features(session.session_id)
            if features is None:
                continue
            values = {
                f.name: float(f.value)
                for f in features.features
                if f.name in names and isinstance(f.value, (int, float)) and not isinstance(f.value, bool)
            }
            if values:
                rows.append((session.session_date, values))
        return rows

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    def get_report(self, session_id: str):
        session = self.get_session(session_id)
        return self.repo.reports.get(session.report_id) if session.report_id else None

    def draft_report(self, session_id: str, *, therapist_notes: str = ""):
        from app.schemas.clinical import ReportGenerationRequest
        from app.services.consent_service import ensure_session_consent_active
        from app.services.report_service import draft_report

        self.get_session(session_id)
        self._ensure(ensure_session_consent_active, session_id)
        try:
            report = draft_report(
                self.repo,
                session_id,
                ReportGenerationRequest(
                    provider_id="template_th",
                    therapist_notes=therapist_notes or None,
                    replace_existing=self.get_report(session_id) is not None,
                ),
                actor_id=LOCAL_USER_ID,
            )
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return report

    def update_report(self, report_id: str, markdown: str):
        from app.schemas.clinical import ReportPatch
        from app.services.consent_service import ensure_report_consent_active
        from app.services.report_service import patch_report, revise_finalized_report

        self._ensure(ensure_report_consent_active, report_id)
        report = self.repo.reports[report_id]
        try:
            if _status_value(report.status) == "Signed Off":
                updated = revise_finalized_report(self.repo, report_id, ReportPatch(markdown=markdown), actor_id=LOCAL_USER_ID)
            else:
                updated = patch_report(self.repo, report_id, ReportPatch(markdown=markdown), actor_id=LOCAL_USER_ID)
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return updated

    def sign_off(self, report_id: str):
        from app.services.consent_service import ensure_report_consent_active
        from app.services.report_service import sign_off_report

        signer = self._require_signer()
        self._ensure(ensure_report_consent_active, report_id)
        try:
            report = sign_off_report(self.repo, report_id, signer, signed_by_user_id=LOCAL_USER_ID)
        except ValueError as exc:
            raise WorkflowError(str(exc)) from exc
        self._save()
        return report

    def report_for_export(self, report_id: str):
        """The report, when it may be exported now (consent active, not stale)."""
        from app.services.consent_service import ensure_report_consent_active

        self._ensure(ensure_report_consent_active, report_id)
        report = self.repo.reports.get(report_id)
        if report is None:
            raise WorkflowError("ไม่พบรายงานนี้")
        if _status_value(report.status) == "stale":
            raise WorkflowError("transcript หรือตัวชี้วัดเปลี่ยนหลังทำรายงานนี้ สร้างร่างใหม่ก่อน export")
        return report

    def record_export(self, report_id: str, export_format: str) -> None:
        self.repo.add_audit(
            "report.export", report_id, f"Report exported as {export_format} from the desktop app.", actor_id=LOCAL_USER_ID
        )
        self._save()

    def export_report(self, report_id: str, export_format: str, destination: Path) -> Path:
        """Write the report as markdown or html. PDF is drawn by the UI, which has the fonts."""
        from packages.desktop.core.rendering import report_html

        report = self.report_for_export(report_id)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if export_format == "html":
            destination.write_text(report_html(report.markdown, report.title), encoding="utf-8")
        elif export_format == "markdown":
            destination.write_text(report.markdown, encoding="utf-8")
        else:
            raise WorkflowError(f"ไม่รองรับรูปแบบ {export_format}")
        self.record_export(report_id, export_format)
        return destination

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------
    def audit_events(self, limit: int = 200) -> list[dict]:
        if hasattr(self.repo, "audit_events"):
            events = self.repo.audit_events()
        else:
            events = list(self.repo.audit_log)
        return events[-limit:]


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
        "unsupported file": "ไฟล์ชนิดนี้ใช้ไม่ได้ ใช้ .wav .mp3 .m4a .mp4 .webm หรือ .ogg",
        "audio too long or too large": "ไฟล์เสียงใหญ่เกิน 250 MB",
        "unsafe filename": "ชื่อไฟล์ใช้ไม่ได้",
    }.get(reason, reason)


def _validation_message(exc: Exception) -> str:
    errors = getattr(exc, "errors", lambda: [])()
    if not errors:
        return str(exc)
    first = errors[0]
    field = ".".join(str(part) for part in first.get("loc", ()))
    return f"{field}: {first.get('msg', 'ค่าไม่ถูกต้อง')}"
