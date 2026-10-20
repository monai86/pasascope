"""The clinic's own child/adult voice model.

Learned from this computer's attested, Whisper-drafted sessions and used
in place of the base model once there is enough of them.

Part of :class:`packages.desktop.core.service.DesktopService`."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
import shutil

from packages.desktop.core.i18n import tr
from packages.desktop.core.workspace import LOCAL_ORGANIZATION_ID, LOCAL_USER_ID
from packages.desktop.core.workflow.common import ProgressCallback, WorkflowError, _day


class ClinicSpeakerMixin:
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
