"""The therapist's name, clinic name, interface language and transcription mode.

Part of :class:`packages.desktop.core.service.DesktopService`."""

from __future__ import annotations

from packages.desktop.core.i18n import tr
from packages.desktop.core.workflow.common import WorkflowError


class SettingsMixin:
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
