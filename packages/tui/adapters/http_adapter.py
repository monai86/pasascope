"""HTTP Transport Adapter implementing ClinicalDataPort for live API server."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from packages.tui.adapters.canonical_store import LocalCanonicalStore, default_store_path

if TYPE_CHECKING:
    from packages.tui.client import PasaScopeClient


# Recording types the API accepts, keyed by file extension.
AUDIO_CONTENT_TYPES = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/x-m4a",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
}
AUDIO_UPLOAD_TIMEOUT_SECONDS = 300.0
AUDIO_JOB_POLL_SECONDS = 1.0
# On-device Whisper runs slower than real time on a laptop CPU.
AUDIO_JOB_TIMEOUT_SECONDS = 2 * 60 * 60
AUDIO_JOB_FINISHED = {"needs_review", "failed", "cancelled"}


def _to_local_transcript_shape(transcript: dict[str, Any]) -> dict[str, Any]:
    """Add the keys the TUI/GUI read (seconds, ``id``, ``attested``) to an API transcript."""
    transcript.setdefault("attested", bool(transcript.get("therapist_attested")))
    for utterance in transcript.get("utterances") or []:
        if not isinstance(utterance, dict):
            continue
        utterance.setdefault("id", utterance.get("utterance_id"))
        for seconds_key, ms_key in (("start_time", "start_ms"), ("end_time", "end_ms")):
            if seconds_key not in utterance and utterance.get(ms_key) is not None:
                utterance[seconds_key] = utterance[ms_key] / 1000.0
        utterance.setdefault("qa_flags", [])
    return transcript


class HttpClinicalAdapter:
    """Clinical data adapter delegating all calls to live PasaScope FastAPI endpoints."""

    def __init__(self, client: PasaScopeClient) -> None:
        self._client = client
        # Opened on first use, so a client that never touches these records reads no file.
        self._canonical_store: LocalCanonicalStore | None = None

    def check_health(self) -> bool:
        """Check if backend API is reachable."""
        try:
            self._client._http_request("GET", "/cases")
            return True
        except Exception:
            return False

    def list_cases(self) -> list[dict[str, Any]]:
        return self._client._http_request("GET", "/cases")

    def create_case(
        self,
        child_code: str | None = None,
        age_months: int | str | None = None,
        language: str = "th",
        notes: str = "",
        *,
        child_id: str | None = None,
        birth_year_month: str | None = None,
        primary_language: str | None = None,
    ) -> dict[str, Any]:
        from packages.tui.client import PasaScopeApiError, PasaScopeUnsupportedOperationError

        legacy_shape = (
            child_id is not None
            or birth_year_month is not None
            or primary_language is not None
            or isinstance(age_months, str)
        )
        if legacy_shape:
            legacy_child_id = child_id if child_id is not None else child_code
            legacy_birth_month = birth_year_month if birth_year_month is not None else age_months
            legacy_language = primary_language if primary_language is not None else language
            if not isinstance(legacy_child_id, str) or not isinstance(legacy_birth_month, str):
                raise PasaScopeApiError(
                    "Legacy case creation requires child_id and birth_year_month; no age conversion was performed."
                )
            legacy_child_id = legacy_child_id.strip()
            legacy_birth_month = legacy_birth_month.strip()
            if not legacy_child_id:
                raise PasaScopeApiError("Case creation requires a non-empty child_code.")

            calc_age: int
            if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", legacy_birth_month):
                from packages.tui.validation import calculate_age_in_months
                by_str, bm_str = legacy_birth_month.split("-")
                calc_age = calculate_age_in_months(int(by_str), int(bm_str), current_date=self._client._get_now())
            elif legacy_birth_month.isdigit():
                calc_age = int(legacy_birth_month)
                if not 0 <= calc_age <= 240:
                    raise PasaScopeApiError("Case creation requires age_months as an integer from 0 through 240.")
            else:
                raise PasaScopeApiError(
                    "Invalid birth_year_month; expected YYYY-MM with a month from 01 through 12."
                )

            return self.create_case(
                child_code=legacy_child_id,
                age_months=calc_age,
                language=legacy_language or "th",
                notes=notes,
            )

        if not isinstance(child_code, str) or not child_code.strip():
            raise PasaScopeApiError("Case creation requires a non-empty child_code.")
        if not isinstance(age_months, int) or isinstance(age_months, bool) or not 0 <= age_months <= 240:
            raise PasaScopeApiError("Case creation requires age_months as an integer from 0 through 240.")
        if not isinstance(language, str) or not language.strip():
            raise PasaScopeApiError("Case creation requires a non-empty language.")
        if not isinstance(notes, str):
            raise PasaScopeApiError("Case creation notes must be text.")

        payload = {
            "child_code": child_code,
            "age_months": age_months,
            "language": language,
            "notes": notes,
        }
        return self._client._http_request("POST", "/cases", payload)

    def get_session_detail(self, session_id: str) -> dict[str, Any]:
        from packages.tui.client import PasaScopeApiError
        sess = self._client._http_request("GET", f"/sessions/{session_id}")
        if not isinstance(sess, dict) or "session_id" not in sess:
            raise PasaScopeApiError("Malformed API response: invalid session detail object.")
        return sess

    def list_sessions(self, case_id: str) -> list[dict[str, Any]]:
        from packages.tui.client import PasaScopeApiError
        timeline = self._client._http_request("GET", f"/cases/{case_id}/timeline")
        if not isinstance(timeline, list):
            raise PasaScopeApiError("Malformed API response: expected list from case timeline.")
        sessions = []
        for idx, event in enumerate(timeline, 1):
            if not isinstance(event, dict) or "target_id" not in event:
                continue
            session_id = event["target_id"]
            sess = self.get_session_detail(session_id)
            sess_copy = dict(sess)
            sess_copy.setdefault("session_number", idx)
            sessions.append(sess_copy)
        return sessions

    def create_session(self, case_id: str, session_date: str, notes: str = "") -> dict[str, Any]:
        payload = {"session_date": session_date, "session_type": "therapy_session", "notes": notes}
        return self._client._http_request("POST", f"/cases/{case_id}/sessions", payload)

    def get_session_transcript(self, session_id: str) -> dict[str, Any] | None:
        from packages.tui.client import PasaScopeApiError
        sess = self.get_session_detail(session_id)
        tr_id = sess.get("transcript_id") if isinstance(sess, dict) else None
        if not tr_id:
            return None
        try:
            transcript = self._client._http_request("GET", f"/sessions/{session_id}/transcript")
            return _to_local_transcript_shape(transcript) if isinstance(transcript, dict) else transcript
        except PasaScopeApiError as exc:
            if "404" in str(exc):
                return None
            raise

    def ingest_transcript_text(self, session_id: str, text: str) -> dict[str, Any]:
        return self._client._http_request("POST", f"/sessions/{session_id}/transcript", {"text": text})

    def ingest_audio_file(
        self,
        session_id: str,
        audio_path: str,
        progress_callback: Optional[Any] = None,
    ) -> dict[str, Any]:
        from packages.tui.client import PasaScopeApiError

        def _progress(fraction: float, message: str) -> None:
            if progress_callback is not None:
                progress_callback(fraction, message)

        path = Path(audio_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Audio/video file not found at: {audio_path}")
        content_type = AUDIO_CONTENT_TYPES.get(path.suffix.lower())
        if content_type is None:
            raise PasaScopeApiError(
                f"Unsupported recording type '{path.suffix}'. Use one of: {', '.join(sorted(AUDIO_CONTENT_TYPES))}."
            )
        size_bytes = path.stat().st_size
        # The API rejects path-like names; the stored object gets its own opaque key.
        filename = re.sub(r"\.{2,}", ".", path.name).replace("/", "_").replace("\\", "_")

        _progress(0.02, "Registering recording with the backend...")
        upload_job = self._client._http_request(
            "POST",
            f"/sessions/{session_id}/audio/upload",
            {"filename": filename, "content_type": content_type, "size_bytes": size_bytes},
        )
        audio_file = (upload_job.get("details") or {}).get("audio_file") if isinstance(upload_job, dict) else None
        audio_file_id = audio_file.get("audio_file_id") if isinstance(audio_file, dict) else None
        if not audio_file_id:
            raise PasaScopeApiError("Malformed API response: upload intent has no audio file id.")

        _progress(0.05, "Uploading recording to the backend...")
        with path.open("rb") as handle:
            self._client._http_request(
                "PUT",
                f"/audio/{audio_file_id}/upload-file",
                body=handle,
                content_type=content_type,
                content_length=size_bytes,
                timeout=AUDIO_UPLOAD_TIMEOUT_SECONDS,
            )
        self._client._http_request(
            "POST", f"/audio/{audio_file_id}/complete-upload", {"size_bytes": size_bytes}
        )

        _progress(0.15, "Queueing on-device transcription...")
        job = self._client._http_request(
            "POST",
            f"/sessions/{session_id}/audio/process",
            {
                "audio_id": audio_file_id,
                "provider": "local_whisper",
                "config": {
                    "language": "th",
                    "return_word_timestamps": True,
                    "return_speaker_segments": True,
                    "allow_fallback_to_mock": False,
                },
            },
        )
        deadline = time.monotonic() + AUDIO_JOB_TIMEOUT_SECONDS
        started = time.monotonic()
        while isinstance(job, dict) and job.get("status") not in AUDIO_JOB_FINISHED:
            if time.monotonic() > deadline:
                raise PasaScopeApiError("Timed out waiting for the backend to finish transcription.")
            elapsed = int(time.monotonic() - started)
            # The backend reports no percentage; creep towards 95% so the bar keeps moving.
            _progress(
                0.15 + 0.80 * (1 - 1 / (1 + elapsed / 120)),
                f"Backend is transcribing ({job.get('status', 'queued')}, {elapsed // 60}:{elapsed % 60:02d} elapsed)...",
            )
            time.sleep(AUDIO_JOB_POLL_SECONDS)
            job = self._client._http_request("GET", f"/jobs/{job['job_id']}")

        if not isinstance(job, dict) or job.get("status") != "needs_review":
            message = job.get("message") if isinstance(job, dict) else None
            raise PasaScopeApiError(f"Audio transcription failed: {message or 'no reason reported by the backend'}")

        _progress(0.97, "Loading draft transcript...")
        transcript = self.get_session_transcript(session_id)
        if not transcript:
            raise PasaScopeApiError("Transcription finished but no transcript was returned for this session.")
        _progress(1.0, "Draft transcript ready for review.")
        return transcript

    def update_utterance(
        self,
        transcript_id: str,
        utterance_id: str,
        new_text: str,
        new_speaker: str,
    ) -> dict[str, Any]:
        from packages.tui.client import PasaScopeUnsupportedOperationError
        raise PasaScopeUnsupportedOperationError(
            "In-place utterance editing is unsupported in live thin-client mode."
        )

    def auto_refine_speakers(self, transcript_id: str) -> dict[str, Any]:
        from packages.tui.client import PasaScopeUnsupportedOperationError
        raise PasaScopeUnsupportedOperationError(
            "Speaker auto-refinement is unsupported in live thin-client mode."
        )

    def swap_speakers(self, transcript_id: str, spk1: str = "CHI", spk2: str = "INV") -> dict[str, Any]:
        from packages.tui.client import PasaScopeUnsupportedOperationError
        raise PasaScopeUnsupportedOperationError(
            "Speaker swapping is unsupported in live thin-client mode."
        )

    def attest_transcript(self, transcript_id: str, therapist_name: str) -> dict[str, Any]:
        payload = {"attested_by": therapist_name, "notes": "Attested via PasaScope TUI"}
        return self._client._http_request("POST", f"/transcripts/{transcript_id}/attest", payload)

    def get_findings(self, session_id: str) -> dict[str, Any]:
        from packages.tui.client import PasaScopeApiError
        try:
            res = self._client._http_request("GET", f"/sessions/{session_id}/features")
        except PasaScopeApiError as exc:
            if getattr(exc, "status_code", None) == 404 or "not found" in str(exc).lower():
                return {
                    "session_id": session_id,
                    "has_data": False,
                    "metrics": {},
                    "guideline_links": [],
                }
            raise

        if not isinstance(res, dict):
            return {
                "session_id": session_id,
                "has_data": False,
                "metrics": {},
                "guideline_links": [],
            }
        features_list = res.get("features", [])
        metrics: dict[str, Any] = {}
        if isinstance(features_list, list):
            for f in features_list:
                if isinstance(f, dict):
                    name = f.get("name")
                    val = f.get("value")
                    if name:
                        metrics[name] = val

        has_data = bool(metrics) and not res.get("insufficient_data", False)
        guideline_links = res.get("guideline_links", [])
        if not guideline_links and metrics:
            mlu = metrics.get("mlu_words", 0.0)
            ttr = metrics.get("ttr", 0.0)
            turns = metrics.get("turn_taking_ratio", 0.0)
            echo = metrics.get("echolalia_count", 0)
            f0 = metrics.get("f0_median_hz")
            guideline_links = [
                {
                    "construct": "1. Expressive Phrase Length (ไวยากรณ์และความยาวประโยค)",
                    "status": "Measured",
                    "description": f"MLU-w อยู่ที่ {mlu} คำ/ประโยค",
                },
                {
                    "construct": "2. Lexical & Vocabulary Diversity (ความหลากหลายของคำศัพท์)",
                    "status": "Measured",
                    "description": f"TTR {ttr}",
                },
                {
                    "construct": "3. Pragmatic Turn-Taking (การผลัดกันพูดในบทสนทนา)",
                    "status": "Measured",
                    "description": f"Turn-taking ratio {turns}",
                },
                {
                    "construct": "4. Echolalia & Repetition (การพูดตาม/พูดซ้ำ)",
                    "status": "Not observed" if echo == 0 else f"Observed {echo} — review in context",
                    "description": f"พบ Echolalia {echo} ครั้ง",
                },
                {
                    "construct": "5. Acoustic Prosody & Pitch (ระดับเสียงและน้ำเสียง)",
                    "status": f"F0 {f0} Hz" if f0 else "N/A (Text-only - No Audio)",
                    "description": "วิเคราะห์จากสัญญาณเสียงพูด" if f0 else "จำเป็นต้องมีไฟล์เสียงเพื่อวัด F0",
                },
            ]

        return {
            "session_id": session_id,
            "has_data": has_data,
            "metrics": metrics,
            "guideline_links": guideline_links,
            "raw": res,
        }

    def draft_report(self, session_id: str, prompt_notes: str = "") -> dict[str, Any]:
        payload = {"notes": prompt_notes}
        return self._client._http_request("POST", f"/sessions/{session_id}/reports/draft", payload)

    def sign_off_report(self, report_id: str, therapist_name: str) -> dict[str, Any]:
        payload = {
            "confirmation_checked": True,
            "therapist_name": therapist_name,
            "signed_by": therapist_name,
        }
        return self._client._http_request("POST", f"/reports/{report_id}/sign-off", payload)

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        return self._client._http_request("GET", f"/reports/{report_id}")

    def get_session_report(self, session_id: str) -> dict[str, Any] | None:
        sess = self.get_session_detail(session_id)
        rep_id = sess.get("report_id") if isinstance(sess, dict) else None
        if rep_id:
            return self.get_report(rep_id)
        return None

    def _canonical(self) -> LocalCanonicalStore:
        """Children, consents and assessments live in a file on this machine, not in the API."""
        if self._canonical_store is None:
            self._canonical_store = LocalCanonicalStore(
                path=default_store_path(), default_clinician_id="therapist-local"
            )
        return self._canonical_store

    def create_child(
        self,
        display_code: str,
        birth_year: int,
        birth_month: int,
        language_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._canonical().create_child(display_code, birth_year, birth_month, language_context)

    def get_child(self, child_id: str) -> dict[str, Any]:
        return self._canonical().get_child(child_id)

    def list_children(self) -> list[dict[str, Any]]:
        return self._canonical().list_children()

    def record_consent(
        self,
        child_id: str,
        purpose: str = "clinical_assessment",
        scope_version: str = "2026.1",
        status: str = "active",
    ) -> dict[str, Any]:
        return self._canonical().record_consent(child_id, purpose, scope_version, status)

    def list_consents(self, child_id: str) -> list[dict[str, Any]]:
        return self._canonical().list_consents(child_id)

    def get_active_consent(self, child_id: str) -> dict[str, Any] | None:
        return self._canonical().get_active_consent(child_id)

    def create_assessment(
        self,
        child_id: str,
        purpose: str = "initial",
        assigned_clinician_id: str | None = None,
    ) -> dict[str, Any]:
        return self._canonical().create_assessment(child_id, purpose, assigned_clinician_id)

    def list_assessments(self, child_id: str) -> list[dict[str, Any]]:
        return self._canonical().list_assessments(child_id)

    def get_assessment(self, assessment_id: str) -> dict[str, Any]:
        return self._canonical().get_assessment(assessment_id)

    def get_waveform_peaks(self, session_id: str) -> bytes:
        return self._client._http_request_bytes("GET", f"/sessions/{session_id}/audio/waveform-peaks")

    def get_playback_grant(self, session_id: str) -> dict[str, Any]:
        return self._client._http_request("POST", f"/sessions/{session_id}/audio/playback-grant")

