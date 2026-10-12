"""Public sign-up and open review gates: opt-in settings for a public app.

Defaults stay strict; these tests turn the settings on per test.
"""
from __future__ import annotations

import time
import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.api.v1.routes import features as features_route
from app.auth.supabase_auth import authenticate_supabase_bearer
from app.core.config import Settings, get_settings
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.services import feature_service, report_service

SECRET = "test-secret-with-at-least-thirty-two-bytes"
ISSUER = "https://example.supabase.co/auth/v1"


def _settings(**overrides) -> Settings:
    return get_settings().model_copy(
        update={
            "auth_mode": "supabase",
            "supabase_jwt_verification_mode": "hs256_shared_secret",
            "supabase_jwt_secret": SECRET,
            "supabase_jwt_issuer": ISSUER,
            "supabase_jwt_audience": "authenticated",
            "supabase_require_mfa": False,
            "supabase_require_invitation": False,
            **overrides,
        }
    )


def _token(sub: str, **claims) -> str:
    payload = {
        "sub": sub,
        "aud": "authenticated",
        "iss": ISSUER,
        "exp": int(time.time()) + 600,
        "email": f"{sub}@example.test",
        **claims,
    }
    return "Bearer " + jwt.encode(payload, SECRET, algorithm="HS256")


def test_new_user_without_organization_claims_is_rejected_by_default():
    with pytest.raises(HTTPException) as error:
        authenticate_supabase_bearer(_token("user-a"), _settings())
    assert error.value.status_code == 401


def test_public_signup_gives_a_new_user_a_personal_workspace():
    principal = authenticate_supabase_bearer(_token("user-a"), _settings(public_signup=True))

    assert principal.user_id == "user-a"
    assert principal.organization_id == "personal_user-a"
    assert principal.role == "therapist"
    assert principal.membership_active is True
    assert principal.display_name == "user-a@example.test"


def test_public_signup_ignores_organization_claims_in_the_token():
    token = _token("user-a", app_metadata={"organization_id": "someone_elses_org", "role": "org_admin"})

    principal = authenticate_supabase_bearer(token, _settings(public_signup=True))

    assert principal.organization_id == "personal_user-a"
    assert principal.role == "therapist"


def test_public_signup_still_rejects_a_token_signed_with_another_key():
    forged = "Bearer " + jwt.encode(
        {"sub": "user-a", "aud": "authenticated", "iss": ISSUER, "exp": int(time.time()) + 600},
        "a-different-secret-with-at-least-thirty-two-bytes",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as error:
        authenticate_supabase_bearer(forged, _settings(public_signup=True))
    assert error.value.status_code == 401


def test_public_signup_cannot_be_combined_with_required_mfa_or_invitation():
    with pytest.raises(ValueError):
        get_settings().model_copy(update={"public_signup": True, "supabase_require_mfa": True}).validate_runtime_security()


def test_review_gates_must_be_a_known_value():
    with pytest.raises(ValueError):
        get_settings().model_copy(update={"review_gates": "sometimes"}).validate_runtime_security()


# --- personal workspaces are isolated, and the open workflow runs end to end -------------


def _headers(user_id: str) -> dict[str, str]:
    # Mock auth with the organization a public sign-up principal would get.
    return {"x-mock-user-id": user_id, "x-mock-role": "therapist", "x-organization-id": f"personal_{user_id}"}


@pytest.fixture()
def client():
    repo = MockRepository()
    app.dependency_overrides[get_repository] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def open_gates(monkeypatch):
    opened = get_settings().model_copy(update={"review_gates": "open"})
    for module in (features_route, feature_service, report_service):
        monkeypatch.setattr(module, "get_settings", lambda: opened)


def _case_with_transcript(client: TestClient, headers: dict[str, str]) -> dict:
    case = client.post("/api/v1/cases", headers=headers, json={"child_code": "C-PUBLIC", "age_months": 54}).json()
    session = client.post(
        f"/api/v1/cases/{case['case_id']}/sessions",
        headers=headers,
        json={"session_date": "2026-10-12", "session_type": "therapy_session"},
    ).json()
    transcript = client.post(
        f"/api/v1/sessions/{session['session_id']}/transcripts/manual",
        headers=headers,
        json={"text": "THER: what do you see\nCHI: i see a big blue car\nCHI: the car goes fast", "language": "English"},
    ).json()
    return {"case": case, "session": session, "transcript": transcript}


def test_one_users_case_is_not_visible_to_another_user(client):
    mine = _case_with_transcript(client, _headers("user-a"))

    other = _headers("user-b")
    assert client.get(f"/api/v1/cases/{mine['case']['case_id']}", headers=other).status_code == 404
    assert client.get(f"/api/v1/sessions/{mine['session']['session_id']}/transcript", headers=other).status_code == 404
    listed = client.get("/api/v1/cases", headers=other).json()
    assert mine["case"]["case_id"] not in [item["case_id"] for item in listed]


def test_strict_gates_still_block_analysis_without_attestation(client):
    headers = _headers("user-a")
    record = _case_with_transcript(client, headers)

    response = client.post(f"/api/v1/transcripts/{record['transcript']['transcript_id']}/extract-features", headers=headers, json={})

    assert response.status_code == 400


def test_open_gates_analyse_and_export_without_attestation_or_sign_off(client, open_gates):
    headers = _headers("user-a")
    record = _case_with_transcript(client, headers)
    transcript_id = record["transcript"]["transcript_id"]
    session_id = record["session"]["session_id"]

    features = client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", headers=headers, json={})
    assert features.status_code == 200, features.text

    # The automatic attestation is recorded as automatic, not as a therapist's own statement.
    transcript = client.get(f"/api/v1/sessions/{session_id}/transcript", headers=headers).json()
    assert transcript["therapist_attested"] is True
    assert "automatically" in transcript["attestation_reason"]

    report = client.post(f"/api/v1/sessions/{session_id}/reports/draft", headers=headers, json={})
    assert report.status_code == 200, report.text

    exported = client.get(f"/api/v1/reports/{report.json()['report_id']}/export?format=markdown", headers=headers)
    assert exported.status_code == 200, exported.text
    assert exported.json()["content"].strip()


def test_strict_gates_still_block_export_of_an_unsigned_report(client, open_gates, monkeypatch):
    headers = _headers("user-a")
    record = _case_with_transcript(client, headers)
    client.post(f"/api/v1/transcripts/{record['transcript']['transcript_id']}/extract-features", headers=headers, json={})
    report = client.post(f"/api/v1/sessions/{record['session']['session_id']}/reports/draft", headers=headers, json={}).json()

    monkeypatch.setattr(report_service, "get_settings", lambda: get_settings().model_copy(update={"review_gates": "strict"}))
    response = client.get(f"/api/v1/reports/{report['report_id']}/export?format=markdown", headers=headers)

    assert response.status_code == 400


# --- recordings survive a wiped disk when a backup target is configured -----------------


class _FakeBucket:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}


@pytest.fixture()
def supabase_backup(monkeypatch, tmp_path):
    import httpx

    from app.services import audio_backup_service

    bucket = _FakeBucket()
    configured = get_settings().model_copy(
        update={
            "audio_backup_mode": "supabase",
            "supabase_storage_url": "https://exampleproject.supabase.co",
            "supabase_storage_bucket": "audio-recordings",
            "supabase_storage_service_role_key": "sb_secret_" + "k" * 40,
        }
    )
    monkeypatch.setattr(audio_backup_service, "get_settings", lambda: configured)
    assert audio_backup_service.backup_enabled() is True
    configured.validate_runtime_security()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"].startswith("Bearer sb_secret_")
        key = request.url.path.split("/storage/v1/object/audio-recordings/", 1)[1]
        if request.method == "POST":
            bucket.objects[key] = request.read()
            return httpx.Response(200, json={"Key": key})
        if request.method == "GET":
            return httpx.Response(200, content=bucket.objects[key]) if key in bucket.objects else httpx.Response(404)
        if request.method == "DELETE":
            return httpx.Response(200 if bucket.objects.pop(key, None) is not None else 404)
        return httpx.Response(405)

    monkeypatch.setattr(audio_backup_service, "_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    return bucket, audio_backup_service, tmp_path


def test_recording_is_backed_up_restored_and_deleted(supabase_backup):
    bucket, service, tmp_path = supabase_backup
    recording = tmp_path / "org" / "case" / "take.webm"
    recording.parent.mkdir(parents=True)
    recording.write_bytes(b"synthetic audio bytes")

    service.backup_recording("org/case/take.webm", recording, "audio/webm")
    assert bucket.objects == {"org/case/take.webm": b"synthetic audio bytes"}

    recording.unlink()  # the host's disk was wiped
    assert service.restore_recording("org/case/take.webm", recording) is True
    assert recording.read_bytes() == b"synthetic audio bytes"

    assert service.delete_backup("org/case/take.webm") is True
    assert bucket.objects == {}
    recording.unlink()
    assert service.restore_recording("org/case/take.webm", recording) is False
    assert not recording.exists()


def test_backup_does_nothing_when_no_target_is_configured(tmp_path):
    from app.services import audio_backup_service

    missing = tmp_path / "missing.webm"
    assert audio_backup_service.backup_enabled() is False
    assert audio_backup_service.restore_recording("org/case/missing.webm", missing) is False
    assert audio_backup_service.delete_backup("org/case/missing.webm") is True
