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

from packages.desktop.core.i18n import language as current_language, report_language, tr
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


class DesktopService:
    def __init__(self, workspace: Workspace, *, repository: Any | None = None) -> None:
        self.workspace = workspace
        if repository is None:
            from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

            repository = SqlAlchemyRepository(workspace.database_url, create_schema=True, seed_demo=False)
        self.repo = repository
        from packages.desktop.core.models import use_downloaded_thai_model

        use_downloaded_thai_model()
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
            raise WorkflowError(tr("กรุณาใส่ชื่อนักบำบัด", "Enter the therapist's name."))
        if len(name) > 120:
            raise WorkflowError(tr("ชื่อยาวเกิน 120 ตัวอักษร", "The name is longer than 120 characters."))
        profile = self.workspace.read_profile()
        profile["display_name"] = name
        self.workspace.write_profile(profile)

    @property
    def organization(self) -> str:
        """The clinic or organisation printed at the top of each report page; may be empty."""
        return str(self.workspace.read_profile().get("organization") or "").strip()

    def set_organization(self, name: str) -> None:
        name = name.strip()
        if len(name) > 120:
            raise WorkflowError(tr("ชื่อยาวเกิน 120 ตัวอักษร", "The name is longer than 120 characters."))
        profile = self.workspace.read_profile()
        profile["organization"] = name
        self.workspace.write_profile(profile)

    @property
    def language(self) -> str:
        """The interface language saved for this workspace ("en" or "th"); English unless chosen."""
        from packages.desktop.core.i18n import LANGUAGES

        code = str(self.workspace.read_profile().get("language") or "en")
        return code if code in LANGUAGES else "en"

    def set_language(self, code: str) -> None:
        """Remember the interface language; the window uses it from the next start."""
        from packages.desktop.core.i18n import LANGUAGES

        if code not in LANGUAGES:
            raise WorkflowError(f"Unknown language {code}")
        profile = self.workspace.read_profile()
        profile["language"] = code
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
            raise WorkflowError(tr(f"ไม่รู้จักโหมด {mode}", f"Unknown mode {mode}"))
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
                        "name": f"{case.child_code} {_day(session.session_date)}",
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
                progress(index / (len(sessions) + 1), tr(f"อ่านเสียง session {index}/{len(sessions)}", f"Reading session {index} of {len(sessions)}"))
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
            progress(len(sessions) / (len(sessions) + 1), tr("กำลังเทรนและทดสอบโมเดล", "Training and testing the model"))
        result = train_clinic_head(labelled)
        names = [f"{s['name']} {int(start // 60):02d}:{int(start % 60):02d}" for s in sessions for start, _ in s["spans"]]
        result.examples = (np.vstack([item.design for item in labelled]), np.concatenate([item.is_child for item in labelled]), names)
        return result

    def save_clinic_speaker_result(self, result) -> dict:
        """Keep the newest result, record it in the audit log, and use the model if it was adopted."""
        from src.audio_pipeline.clinic_speaker_model import examples_path, save_examples, save_result

        if result.reason == "not_enough_sessions":
            return self.clinic_speaker_status()
        save_result(self.clinic_speaker_model_path, result, trained_at=datetime.now().astimezone().isoformat(timespec="seconds"))
        if result.head is not None and result.examples is not None:
            save_examples(self.clinic_speaker_model_path, result.head, *result.examples)
        else:
            examples_path(self.clinic_speaker_model_path).unlink(missing_ok=True)
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
        from src.audio_pipeline.clinic_speaker_model import examples_path

        self.clinic_speaker_model_path.unlink(missing_ok=True)
        examples_path(self.clinic_speaker_model_path).unlink(missing_ok=True)
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
            raise WorkflowError(tr("ตั้งชื่อนักบำบัดก่อน (เมนู ตั้งค่า) เพราะชื่อนี้จะอยู่ในการรับรองและการลงนาม", "Set the therapist name first (Settings); it appears on attestations and signatures."))
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
            raise WorkflowError(tr("ไม่พบเคสนี้", "Case not found."))
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
            raise WorkflowError(tr(f"มีเคสรหัส {child_code} อยู่แล้ว", f"A case with code {child_code} already exists."))
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
            raise WorkflowError(tr("กรุณาระบุเหตุผลที่ถอนความยินยอม", "Enter the reason for withdrawing consent."))
        result = withdraw_consent(
            self.repo, case_id, reason.strip(), True, actor_id=LOCAL_USER_ID, requester_role="therapist"
        )
        self._save()
        return result

    def update_case(self, case_id: str, *, nickname: str, age_months: int, language: str, notes: str):
        """Change a case's nickname, age at intake, language and notes; the code stays (it is on every record)."""
        from pydantic import ValidationError

        from app.schemas.clinical import ChildCaseUpdate

        case = self.get_case(case_id)
        try:
            patch = ChildCaseUpdate(
                nickname=nickname.strip() or None, age_months=age_months,
                language=language.strip() or case.language, notes=notes.strip(),
            )
            updated = self.repo.update_case(case_id, patch, expected_version=None, actor_id=LOCAL_USER_ID)
        except ValidationError as exc:
            raise WorkflowError(_validation_message(exc)) from exc
        self._save()
        return updated

    def deletion_summary(self, case_id: str, session_id: str | None = None) -> dict[str, int]:
        """What deleting a case (or one of its sessions) would remove, for the confirmation dialog."""
        self.get_case(case_id)
        if session_id is not None and self.get_session(session_id).case_id != case_id:
            raise WorkflowError(tr("ไม่พบ session นี้", "Session not found."))
        records = self.repo.case_records(case_id, session_id=session_id)
        return {
            "sessions": len(records["sessions"]),
            "recordings": len(records["audio_files"]),
            "transcripts": len(records["transcripts"]),
            "reports": len(records["reports"]),
            "signed_reports": sum(1 for report in records["reports"] if report.status == "Signed Off"),
        }

    def delete_case(self, case_id: str, typed_code: str) -> dict[str, int]:
        """Delete a case with its sessions, recordings, transcripts, findings and reports.

        The therapist types the child's code to confirm. The audit log keeps
        one event with counts only, and exported files and backups outside the
        data folder are not touched.
        """
        case = self.get_case(case_id)
        if typed_code.strip() != case.child_code:
            raise WorkflowError(tr(f"พิมพ์รหัส {case.child_code} ให้ตรงเพื่อยืนยันการลบ", f"Type {case.child_code} exactly to confirm."))
        return self._delete_records(case_id, None)

    def delete_session(self, session_id: str) -> dict[str, int]:
        """Delete one session with its recording, transcript, findings and report."""
        session = self.get_session(session_id)
        return self._delete_records(session.case_id, session_id)

    def _delete_records(self, case_id: str, session_id: str | None) -> dict[str, int]:
        root = self.workspace.storage_root.resolve()
        audio = self.repo.case_records(case_id, session_id=session_id)["audio_files"]
        removed = self.repo.delete_case_records(case_id, actor_id=LOCAL_USER_ID, session_id=session_id)
        # Files go after the records: a failure here leaves a file without a record, never the reverse.
        for audio_file in audio:
            for path in (
                root / str(audio_file.object_key or ""),
                root / "playback" / f"{audio_file.audio_file_id}.wav",
                root / "playback" / f"{audio_file.audio_file_id}.full.wav",
            ):
                path = path.resolve()
                if root in path.parents and path.is_file():
                    path.unlink(missing_ok=True)
        self._save()
        return removed

    def consent_active(self, case_id: str) -> bool:
        return self.get_case(case_id).consent_status == "granted"

    def _ensure(self, check: Callable[..., None], *args: Any) -> None:
        """The API's consent gate: nothing changes on a case whose consent was withdrawn."""
        try:
            check(self.repo, *args)
        except ValueError as exc:
            raise WorkflowError(tr("ผู้ปกครองถอนความยินยอมของเคสนี้แล้ว จึงเพิ่มหรือแก้ข้อมูลไม่ได้", "Consent for this case was withdrawn, so its data cannot be added to or changed.")) from exc

    def _require_granted(self, case_id: str) -> None:
        """New sessions and recordings need consent that was actually recorded, not just pending."""
        status = self.get_case(case_id).consent_status
        if status == "withdrawn":
            raise WorkflowError(tr("ผู้ปกครองถอนความยินยอมของเคสนี้แล้ว จึงเพิ่มหรือแก้ข้อมูลไม่ได้", "Consent for this case was withdrawn, so its data cannot be added to or changed."))
        if status != "granted":
            raise WorkflowError(tr("บันทึกความยินยอมของผู้ปกครองก่อน แล้วจึงเริ่ม session หรือบันทึกเสียง", "Record the parent's consent before starting a session or recording."))

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
            raise WorkflowError(tr("ไม่พบ session นี้", "Session not found."))
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
        # The provider's own message about a missing Thai model names a
        # developer script; point the therapist to the download instead.
        if not availability and self.transcription_mode == "accurate" and not self.thai_model_status()["installed"]:
            return False, tr("ต้องดาวน์โหลดโมเดลภาษาไทยก่อน (ตั้งค่า → ดาวน์โหลดโมเดลถอดเสียง)",
                             "Download the Thai model first (Settings, Download speech models)")
        return bool(availability), availability.reason or ""

    # ------------------------------------------------------------------
    # Updates
    # ------------------------------------------------------------------
    @property
    def auto_update_check(self) -> bool:
        return bool(self.workspace.read_profile().get("auto_update_check", True))

    def set_auto_update_check(self, enabled: bool) -> None:
        profile = self.workspace.read_profile()
        profile["auto_update_check"] = bool(enabled)
        self.workspace.write_profile(profile)

    def update_check_due(self, now: datetime | None = None) -> bool:
        """Automatic checks run at most once a day, and only when switched on."""
        if not self.auto_update_check:
            return False
        last = self.workspace.read_profile().get("last_update_check")
        if not last:
            return True
        try:
            then = datetime.fromisoformat(str(last))
        except ValueError:
            return True
        now = now or datetime.now(timezone.utc)
        return (now - then).total_seconds() >= 24 * 3600

    def check_for_update(self, current_version: str):
        """The newer release on GitHub, or None; remembers when it last looked."""
        from packages.desktop.core.updates import check_for_update

        release = check_for_update(current_version)
        profile = self.workspace.read_profile()
        profile["last_update_check"] = datetime.now(timezone.utc).isoformat()
        self.workspace.write_profile(profile)
        return release

    def download_update(self, release, progress=None, cancelled=None) -> Path:
        """Download and check the release's installer for this platform into the Downloads folder."""
        from packages.desktop.core.updates import download_release

        def report(done: int, total: int) -> None:
            if progress:
                progress(done / total if total else 0.0, tr("ดาวน์โหลดรุ่นใหม่", "Downloading the new version"))

        path = download_release(release, Path.home() / "Downloads", report, cancelled=cancelled)
        self.repo.add_audit("app.update_downloaded", release.version, f"Downloaded {path.name} (SHA-256 checked).",
                            actor_id=LOCAL_USER_ID)
        self._save()
        return path

    def thai_model_status(self) -> dict:
        """Whether the Thai Whisper model is on this computer, where, and its download size."""
        from packages.desktop.core.models import THAI_WHISPER, use_downloaded_thai_model

        folder = use_downloaded_thai_model()
        return {"installed": folder is not None, "path": folder, "size": THAI_WHISPER.size}

    def download_speech_models(self, progress=None, cancelled=None) -> Path:
        """Download and check the Thai Whisper model, then fetch the smaller models used on first transcription."""
        from packages.desktop.core.models import THAI_WHISPER, download, prefetch_others, use_downloaded_thai_model

        def report(done: int, total: int) -> None:
            if progress:
                progress(done / total * 0.95, tr("ดาวน์โหลดโมเดลภาษาไทย", "Downloading the Thai model"))

        if not self.thai_model_status()["installed"]:
            download(THAI_WHISPER, report, cancelled=cancelled)
        if progress:
            progress(0.96, tr("ดาวน์โหลดโมเดลแยกเสียงและภาษา", "Downloading the voice and language models"))
        prefetch_others()
        folder = use_downloaded_thai_model()
        self.repo.add_audit("models.download", "speech_models", f"Speech models ready at {folder}.", actor_id=LOCAL_USER_ID)
        self._save()
        return folder

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
            raise WorkflowError(tr("ไม่มีข้อความให้นำเข้า", "There is no text to import."))
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
            raise WorkflowError(tr("session นี้ยังไม่มี transcript", "This session has no transcript yet."))
        if not transcript.therapist_attested:
            raise WorkflowError(tr("รับรอง transcript ก่อน แล้วจึงวิเคราะห์", "Attest the transcript before analysing."))
        self._ensure(ensure_transcript_consent_active, transcript.transcript_id)
        try:
            features = extract_features(
                self.repo, transcript.transcript_id, FeatureExtractionRequest(), actor_id=LOCAL_USER_ID
            )
            cues = create_ml_review(
                self.repo, transcript.transcript_id, MLReviewRequest(force_regenerate=True), actor_id=LOCAL_USER_ID
            )
        except MLReadinessError as exc:
            raise WorkflowError("; ".join(exc.readiness.reasons) or tr("ยังสร้าง cue ไม่ได้", "Cues could not be created yet.")) from exc
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
            raise WorkflowError(tr("ไม่พบผลการทบทวนนี้", "Review result not found."))
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

    def work_queue(self) -> list[dict]:
        """Everything waiting for the therapist, most urgent first.

        One row per unfinished session of a consented child (``step`` 0-3 as in
        ``session_step``) and one per child still waiting for consent
        (``step`` "consent"). ``waiting_days`` counts from the last change.
        """
        now = datetime.now(timezone.utc)
        rows = []
        for case in self.list_cases():
            if case.consent_status == "pending":
                rows.append({"case": case, "session": None, "step": "consent",
                             "waiting_days": (now - _utc(case.updated_at)).days})
                continue
            if case.consent_status != "granted":
                continue
            for session in self.list_sessions(case.case_id):
                step = self.session_step(session)
                if step < 4:
                    rows.append({"case": case, "session": session, "step": step,
                                 "waiting_days": (now - _utc(session.updated_at)).days})
        order = {"consent": 0, 1: 1, 3: 2, 2: 3, 0: 4}  # review and sign-off first; they block the rest
        return sorted(rows, key=lambda r: (order[r["step"]], -r["waiting_days"]))

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

    def report_language(self, report) -> str:
        """"th" or "en": the language a report was drafted in, read from its headings."""
        return report_language(report.markdown if report is not None else "")

    def draft_report(self, session_id: str, *, therapist_notes: str = "", language: str | None = None):
        """Draft (or redraft) the session report in ``language``.

        Without a language, a redraft keeps the current report's language and a
        first draft uses the interface language in use.
        """
        from app.schemas.clinical import ReportGenerationRequest
        from app.services.consent_service import ensure_session_consent_active
        from app.services.report_service import draft_report

        self.get_session(session_id)
        self._ensure(ensure_session_consent_active, session_id)
        existing = self.get_report(session_id)
        if language is None:
            language = self.report_language(existing) if existing is not None else current_language()
        if language not in REPORT_PROVIDERS:
            raise WorkflowError(f"Unknown report language {language}")
        try:
            report = draft_report(
                self.repo,
                session_id,
                ReportGenerationRequest(
                    provider_id=REPORT_PROVIDERS[language],
                    therapist_notes=therapist_notes or None,
                    replace_existing=existing is not None,
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
            raise WorkflowError(tr("ไม่พบรายงานนี้", "Report not found."))
        if _status_value(report.status) == "stale":
            raise WorkflowError(tr("transcript หรือตัวชี้วัดเปลี่ยนหลังทำรายงานนี้ สร้างร่างใหม่ก่อน export", "The transcript or findings changed after this report; redraft it before exporting."))
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
            raise WorkflowError(tr(f"ไม่รองรับรูปแบบ {export_format}", f"Unsupported format {export_format}"))
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
