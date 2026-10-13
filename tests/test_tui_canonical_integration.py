"""Integration tests connecting PasaScopeClient to the FastAPI app.

Children, consents and assessments are kept by the desktop app itself (see
``packages/tui/adapters/canonical_store.py``), so these tests check that the
live client keeps them locally and asks the API nothing for them, and that the
audio routes it does call still answer.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

# Ensure apps/api is resolvable regardless of PYTHONPATH setting
_apps_api_dir = str(Path(__file__).resolve().parents[1] / "apps" / "api")
if _apps_api_dir not in sys.path:
    sys.path.insert(0, _apps_api_dir)

import pytest
from fastapi.testclient import TestClient

from app.main import app
from packages.tui.client import (
    PasaScopeClient,
    PasaScopeApiError,
    PasaScopeConflictError,
    PasaScopeValidationError,
)


class FastAPITransportHandler(urllib.request.BaseHandler):
    """Urllib transport handler that dispatches directly to FastAPI TestClient."""

    handler_order = 100

    def __init__(self, client: TestClient):
        self.client = client

    def default_open(self, req: urllib.request.Request):
        url = req.full_url
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path
        if parsed.query:
            path += f"?{parsed.query}"
        method = req.get_method()
        headers = {k: v for k, v in req.headers.items()}
        data = req.data
        resp = self.client.request(
            method=method,
            url=path,
            headers=headers,
            content=data,
            follow_redirects=False,
        )
        fp = io.BytesIO(resp.content)
        res = urllib.response.addinfourl(fp, resp.headers, url, resp.status_code)
        res.code = resp.status_code
        res.msg = resp.reason_phrase
        if resp.status_code >= 400:
            raise urllib.error.HTTPError(
                url=url,
                code=resp.status_code,
                msg=resp.reason_phrase,
                hdrs=resp.headers,
                fp=fp,
            )
        return res


@pytest.fixture
def canonical_client():
    """A live-mode client whose transport is the FastAPI app, and a log of the requests it made."""
    with TestClient(app) as test_client:
        client = PasaScopeClient(base_url="http://testserver/api/v1", mock_mode=False)
        handler = FastAPITransportHandler(test_client)
        requests: list[str] = []
        original_open = handler.default_open

        def recording_open(req):
            requests.append(f"{req.get_method()} {urllib.parse.urlsplit(req.full_url).path}")
            return original_open(req)

        handler.default_open = recording_open
        client._opener = urllib.request.build_opener(handler)
        yield client, requests


def test_child_consent_and_assessment_lifecycle_is_local_and_survives_a_new_client(canonical_client, isolated_desktop_records):
    """The whole child → consent → assessment path works in live mode without one request to the API."""
    client, requests = canonical_client

    child = client.create_child("LL-LIVE-01", 2021, 6, {"primary": "TH", "additional": ["en"]})
    assert child["language_context"] == {"primary": "th", "additional": ["en"]}
    assert client.get_child(child["id"]) == child
    assert client.list_children() == [child]

    # No consent yet: an assessment is refused, and nothing is created.
    with pytest.raises(PasaScopeConflictError):
        client.create_assessment(child["id"])
    assert client.list_assessments(child["id"]) == []

    consent = client.record_consent(child["id"], purpose="clinical_assessment", status="active")
    assert consent["version"] == 1 and consent["withdrawn_at"] is None
    assessment = client.create_assessment(child["id"], purpose="initial")
    assert assessment["state"] == "draft" and assessment["child_id"] == child["id"]
    assert assessment["assigned_clinician_id"] == "therapist-local"
    assert client.get_assessment(assessment["id"]) == assessment

    # Withdrawing consent closes the gate again.
    withdrawn = client.record_consent(child["id"], purpose="clinical_assessment", status="withdrawn")
    assert withdrawn["version"] == 2 and withdrawn["withdrawn_at"] is not None
    assert client.get_active_consent(child["id"]) is None
    with pytest.raises(PasaScopeConflictError):
        client.create_assessment(child["id"])

    with pytest.raises(PasaScopeApiError):
        client.get_assessment("asmt-missing")
    assert requests == []

    # The records are on disk: a client started later reads the same ones.
    assert isolated_desktop_records.is_file()
    later = PasaScopeClient(base_url="http://testserver/api/v1", mock_mode=False)
    assert later.list_children() == [child]
    assert [item["version"] for item in later.list_consents(child["id"])] == [2, 1]
    assert later.list_assessments(child["id"]) == [assessment]


def test_a_damaged_records_file_is_reported_and_left_as_it_is(isolated_desktop_records):
    isolated_desktop_records.write_text("{ not json", encoding="utf-8")
    client = PasaScopeClient(base_url="http://testserver/api/v1", mock_mode=False)

    with pytest.raises(PasaScopeApiError, match="could not be read"):
        client.list_children()
    with pytest.raises(PasaScopeApiError, match="could not be read"):
        client.create_child("LL-01", 2021, 5)

    assert isolated_desktop_records.read_text(encoding="utf-8") == "{ not json"


def test_client_create_child_validation_error_fails_closed_zero_dispatch(canonical_client, monkeypatch):
    """Client-side validation rejects invalid intake input immediately with PasaScopeValidationError and zero network dispatch."""
    client, requests = canonical_client

    # Spy on transport dispatch to prove zero HTTP requests are dispatched
    http_calls = []
    real_http_request = client._http_request

    def spy_http_request(*args, **kwargs):
        http_calls.append((args, kwargs))
        return real_http_request(*args, **kwargs)

    monkeypatch.setattr(client, "_http_request", spy_http_request)

    # Invalid birth month (13) must raise PasaScopeValidationError specifically
    with pytest.raises(PasaScopeValidationError) as exc_info:
        client.create_child("INV-01", birth_year=2021, birth_month=13)

    assert exc_info.value.__class__ is PasaScopeValidationError
    assert str(exc_info.value) == "birth_month must be between 1 and 12"

    # Verify zero network transport dispatch (zero POST calls)
    assert len(http_calls) == 0

    # Neither the demo data nor the local records gained a child
    assert len(client._mock_data.get("children", [])) == 0
    assert client.list_children() == []


def test_canonical_consent_versioning_per_purpose_and_child_isolation(canonical_client) -> None:
    """Verify consent version increment per purpose, active consent derivation, and child isolation."""
    client, requests = canonical_client
    child_1 = client.create_child("LL-SEQ-01", 2021, 6)["id"]
    child_2 = client.create_child("LL-SEQ-02", 2021, 7)["id"]

    # 1. Child 1: clinical active -> version 1
    c1 = client.record_consent(child_1, purpose="clinical_assessment", status="active")
    assert c1["version"] == 1
    assert c1["purpose"] == "clinical_assessment"

    # 2. Child 1: research active -> version 1 (isolated by purpose!)
    c2 = client.record_consent(child_1, purpose="research_reuse", status="active")
    assert c2["version"] == 1
    assert c2["purpose"] == "research_reuse"

    # 3. Child 1: clinical withdrawn -> version 2
    c3 = client.record_consent(child_1, purpose="clinical_assessment", status="withdrawn")
    assert c3["version"] == 2
    assert c3["purpose"] == "clinical_assessment"

    # Active clinical consent should now be None
    assert client.get_active_consent(child_1) is None

    # 4. Child 1: clinical active -> version 3
    c4 = client.record_consent(child_1, purpose="clinical_assessment", status="active")
    assert c4["version"] == 3
    assert c4["purpose"] == "clinical_assessment"

    # Active consent derivation
    active = client.get_active_consent(child_1)
    assert active is not None
    assert active["version"] == 3
    assert active["status"] == "active"

    # Child 2 isolation: Child 2 gets clinical active -> version 1
    c2_1 = client.record_consent(child_2, purpose="clinical_assessment", status="active")
    assert c2_1["version"] == 1
    assert c2_1["child_id"] == child_2


def test_client_audio_waveform_peaks_and_playback_grant_in_memory():
    """Verify in-memory client adapter handles peaks and playback grant with validation."""
    client = PasaScopeClient(mock_mode=True, seed_demo=True)

    # 1. Waveform peaks returns 50 bytes of binary samples
    peaks = client.get_waveform_peaks("sess-demo-101")
    assert isinstance(peaks, bytes)
    assert len(peaks) == 50

    # 2. Playback grant returns time-limited payload
    grant = client.get_playback_grant("sess-demo-101")
    assert isinstance(grant, dict)
    assert grant["playback_url"].startswith("/api/v1/audio/")
    assert "expires_at" in grant
    assert grant["audio_sha256"].startswith("mock_sha256_")

    # 3. Nonexistent session raises error
    with pytest.raises(PasaScopeApiError) as exc_info:
        client.get_playback_grant("nonexistent_session")
    assert "not found" in str(exc_info.value).lower()


def test_client_audio_waveform_peaks_and_playback_grant_canonical(canonical_client, tmp_path, monkeypatch):
    """Verify canonical HTTP client adapter fetches binary waveform peaks and playback grant."""
    np = pytest.importorskip("numpy")
    soundfile = pytest.importorskip("soundfile")
    pytest.importorskip("faster_whisper")
    from app.core.config import Settings
    from app.services import audio_job_service

    client, _ = canonical_client
    from app.api.v1.dependencies import get_repository
    from app.repositories.mock_repository import MockRepository
    from app.schemas.clinical import AudioFileMetadata

    repo = MockRepository()
    audio = AudioFileMetadata(
        audio_file_id="audio_demo_001",
        organization_id="pilot_org_001",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="sample.wav",
        content_type="audio/wav",
        size_bytes=10240,
        storage_mode="local_private",
        object_key="pilot_org_001/case_demo_001/session_demo_001/audio_demo_001.wav",
        upload_status="uploaded",
        duration_seconds=120.0,
        sample_rate_hz=16000,
        channels=2,
        checksum_sha256="4a7d1ed414474e4033ac29ccb8653d9b",
    )
    repo.audio_files[audio.audio_file_id] = audio
    # The waveform is computed from the stored recording, so store one second of tone.
    recording = tmp_path / audio.object_key
    recording.parent.mkdir(parents=True)
    soundfile.write(str(recording), (0.5 * np.sin(np.arange(16000) / 8)).astype("float32"), 16000)
    monkeypatch.setattr(audio_job_service, "get_settings", lambda: Settings(local_storage_root=str(tmp_path)))
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        # Set authenticated session
        client.set_session(access_token="therapist-token", organization_id="pilot_org_001")

        # 1. Binary waveform peaks
        peaks = client.get_waveform_peaks("session_demo_001")
        assert isinstance(peaks, bytes)
        assert len(peaks) == 50

        # 2. Playback grant
        grant = client.get_playback_grant("session_demo_001")
        assert isinstance(grant, dict)
        assert grant["playback_url"] == "/api/v1/audio/audio_demo_001/file"
        assert grant["audio_sha256"] == "4a7d1ed414474e4033ac29ccb8653d9b"
        assert "expires_at" in grant
    finally:
        app.dependency_overrides.pop(get_repository, None)



