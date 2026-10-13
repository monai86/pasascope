"""Children, consent records and assessments kept by the desktop app itself.

The API no longer has these records, so the TUI and the desktop GUI hold them
locally. In mock mode the store works on the adapter's in-memory data; in live
mode it is backed by one JSON file on this machine and survives a restart.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

STORE_PATH_ENV = "PASASCOPE_DESKTOP_RECORDS_PATH"
_SECTIONS = ("children", "consents", "assessments")


def default_store_path() -> Path:
    """Where live mode keeps the records unless the environment names another file."""
    configured = os.environ.get(STORE_PATH_ENV, "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".pasascope" / "desktop" / "records.json"


class LocalCanonicalStore:
    """The same rules for children, consents and assessments in mock and live mode."""

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        *,
        path: Path | None = None,
        clock: Optional[Callable[[], datetime]] = None,
        default_clinician_id: str = "therapist-mock",
    ) -> None:
        self._path = path
        self._clock = clock
        self._default_clinician_id = default_clinician_id
        self._data: dict[str, Any] = data if data is not None else {}
        if path is not None and data is None:
            self._data = self._read()

    def _now(self) -> datetime:
        return self._clock() if self._clock else datetime.now(timezone.utc)

    def _read(self) -> dict[str, Any]:
        from packages.tui.client import PasaScopeApiError

        assert self._path is not None
        if not self._path.is_file() or self._path.stat().st_size == 0:
            return {}
        try:
            loaded = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            # A damaged file is reported, never replaced by an empty one.
            raise PasaScopeApiError("The desktop records file could not be read.") from exc
        if not isinstance(loaded, dict):
            raise PasaScopeApiError("The desktop records file could not be read.")
        return {section: loaded[section] for section in _SECTIONS if section in loaded}

    def _save(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {section: self._data[section] for section in _SECTIONS if section in self._data}
        # Written beside the file and moved into place, so a crash cannot leave half a file.
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self._path.parent, prefix=self._path.name, suffix=".tmp", delete=False
        )
        try:
            with handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(handle.name, self._path)
        finally:
            if os.path.exists(handle.name):
                os.unlink(handle.name)

    def create_child(
        self,
        display_code: str,
        birth_year: int,
        birth_month: int,
        language_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from packages.tui.validation import validate_child_input
        from packages.tui.client import PasaScopeValidationError
        try:
            norm = validate_child_input(display_code, birth_year, birth_month, language_context)
        except ValueError as exc:
            raise PasaScopeValidationError(str(exc)) from exc

        if "children" not in self._data:
            self._data["children"] = []
        new_child = {
            "id": f"child-local-{len(self._data['children']) + 1:04d}",
            "display_code": norm["display_code"],
            "birth_year": norm["birth_year"],
            "birth_month": norm["birth_month"],
            "language_context": norm["language_context"],
            "version": 1,
        }
        self._data["children"].append(new_child)
        self._save()
        return new_child

    def get_child(self, child_id: str) -> dict[str, Any]:
        from packages.tui.client import PasaScopeApiError
        for c in self._data.get("children", []):
            if c.get("id") == child_id or c.get("display_code") == child_id:
                return c
        raise PasaScopeApiError(f"Child '{child_id}' not found.")

    def list_children(self) -> list[dict[str, Any]]:
        return list(self._data.get("children", []))

    def record_consent(
        self,
        child_id: str,
        purpose: str = "clinical_assessment",
        scope_version: str = "2026.1",
        status: str = "active",
    ) -> dict[str, Any]:
        from packages.tui.validation import validate_consent_input
        from packages.tui.client import PasaScopeValidationError
        try:
            norm = validate_consent_input(child_id, purpose, scope_version, status)
        except ValueError as exc:
            raise PasaScopeValidationError(str(exc)) from exc

        clean_child_id = norm["child_id"]
        # A consent belongs to a child that exists.
        self.get_child(clean_child_id)

        if "consents" not in self._data:
            self._data["consents"] = {}
        if clean_child_id not in self._data["consents"]:
            self._data["consents"][clean_child_id] = []

        now_iso = self._now().strftime("%Y-%m-%dT%H:%M:%SZ")
        purpose_consents = [
            c for c in self._data["consents"][clean_child_id]
            if c.get("purpose") == norm["purpose"]
        ]
        version_num = max((c.get("version", 0) for c in purpose_consents), default=0) + 1
        new_consent = {
            "id": f"consent-local-{version_num:04d}",
            "child_id": clean_child_id,
            "purpose": norm["purpose"],
            "scope_version": norm["scope_version"],
            "status": norm["status"],
            "granted_at": now_iso,
            "withdrawn_at": None if norm["status"] == "active" else now_iso,
            "version": version_num,
        }
        self._data["consents"][clean_child_id].append(new_consent)
        self._save()
        return new_consent

    def list_consents(self, child_id: str) -> list[dict[str, Any]]:
        consents = list(self._data.get("consents", {}).get(child_id, []))
        return sorted(consents, key=lambda c: c.get("version", 0), reverse=True)

    def get_active_consent(self, child_id: str) -> dict[str, Any] | None:
        consents = self.list_consents(child_id)
        if not consents:
            return None
        matching = [c for c in consents if c.get("purpose") == "clinical_assessment"]
        if not matching:
            return None
        sorted_consents = sorted(
            enumerate(matching),
            key=lambda item: (item[1].get("version", 0), item[0]),
            reverse=True,
        )
        latest = sorted_consents[0][1]
        if latest.get("status") == "active":
            return latest
        return None

    def create_assessment(
        self,
        child_id: str,
        purpose: str = "initial",
        assigned_clinician_id: str | None = None,
    ) -> dict[str, Any]:
        from packages.tui.validation import (
            calculate_age_in_months,
            validate_assessment_input,
        )
        from packages.tui.client import (
            PasaScopeApiError,
            PasaScopeConflictError,
            PasaScopeValidationError,
        )

        try:
            norm = validate_assessment_input(child_id, purpose, assigned_clinician_id)
        except ValueError as exc:
            raise PasaScopeValidationError(str(exc)) from exc

        clean_child_id = norm["child_id"]
        child = self.get_child(clean_child_id)

        active_consent = self.get_active_consent(clean_child_id)
        if not active_consent:
            raise PasaScopeConflictError("Active clinical-assessment consent is required.")

        try:
            age_months = calculate_age_in_months(
                child["birth_year"], child["birth_month"], current_date=self._now()
            )
        except ValueError as exc:
            raise PasaScopeApiError(str(exc)) from exc

        child_lang = child.get("language_context")
        if isinstance(child_lang, dict):
            lang_ctx = dict(child_lang)
        else:
            lang_ctx = {"primary": "th", "additional": []}

        if "assessments" not in self._data:
            self._data["assessments"] = {}
        if clean_child_id not in self._data["assessments"]:
            self._data["assessments"][clean_child_id] = []

        new_asmt = {
            "id": f"asmt-local-{len(self._data['assessments'][clean_child_id]) + 1:04d}",
            "child_id": clean_child_id,
            "purpose": norm["purpose"],
            "state": "draft",
            "age_months": age_months,
            "language_context": lang_ctx,
            "assigned_clinician_id": norm["assigned_clinician_id"] or self._default_clinician_id,
            "version": 1,
        }
        self._data["assessments"][clean_child_id].append(new_asmt)
        self._save()
        return new_asmt

    def list_assessments(self, child_id: str) -> list[dict[str, Any]]:
        return list(self._data.get("assessments", {}).get(child_id, []))

    def get_assessment(self, assessment_id: str) -> dict[str, Any]:
        from packages.tui.client import PasaScopeApiError
        for child_asmts in self._data.get("assessments", {}).values():
            for a in child_asmts:
                if a.get("id") == assessment_id:
                    return a
        raise PasaScopeApiError(f"Assessment '{assessment_id}' not found.")
