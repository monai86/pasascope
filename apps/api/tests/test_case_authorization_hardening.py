from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.api.v1.routes import evaluation
from app.core.config import Settings, get_settings
from app.main import app
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import ChildCaseCreate

THERAPIST = {"X-Mock-Role": "therapist", "X-User-Id": "therapist-demo"}
OUTSIDER = {"X-Mock-Role": "therapist", "X-User-Id": "outsider-99"}
GRANT = {"signer": "Parent", "consent_date": "2026-10-11", "confirmation_checked": True}


@pytest.fixture()
def repo():
    repository = MockRepository()
    app.dependency_overrides[get_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


@pytest.fixture()
def client(repo):
    return TestClient(app)


def _pending_case(repo: MockRepository) -> str:
    return repo.create_case(
        ChildCaseCreate(child_code="C-HARDEN-1", age_months=48, care_team_user_ids=["therapist-demo"]),
        actor_id="therapist-demo",
    ).case_id


@pytest.mark.parametrize(
    "payload",
    [
        {"care_team_user_ids": ["therapist-demo", "outsider-99"]},
        {"primary_therapist_user_id": "outsider-99"},
        {"consent_status": "granted"},
    ],
)
def test_case_patch_rejects_care_team_and_consent_fields(client, repo, payload):
    response = client.patch("/api/v1/cases/case_demo_001", json=payload, headers=THERAPIST)

    assert response.status_code == 422
    assert repo.cases["case_demo_001"].care_team_user_ids == ["therapist-demo"]
    assert client.get("/api/v1/cases/case_demo_001", headers=OUTSIDER).status_code == 403


def test_case_patch_still_updates_descriptive_fields_with_real_actor(client, repo):
    response = client.patch("/api/v1/cases/case_demo_001", json={"nickname": "Updated"}, headers=THERAPIST)

    assert response.status_code == 200
    assert response.json()["nickname"] == "Updated"
    assert repo.audit_log[-1]["action"] == "case.update"
    assert repo.audit_log[-1]["actor_id"] == "therapist-demo"


def test_grant_consent_moves_pending_to_granted_and_audits_actor(client, repo):
    case_id = _pending_case(repo)

    response = client.post(f"/api/v1/cases/{case_id}/grant-consent", json=GRANT, headers=THERAPIST)

    assert response.status_code == 200
    assert response.json()["consent_status"] == "granted"
    assert "Consent verified on 2026-10-11 by Parent." in response.json()["notes"]
    grant_events = [event for event in repo.audit_log if event["action"] == "consent.grant"]
    assert [event["actor_id"] for event in grant_events] == ["therapist-demo"]


def test_grant_consent_requires_confirmation(client, repo):
    case_id = _pending_case(repo)

    response = client.post(
        f"/api/v1/cases/{case_id}/grant-consent",
        json={**GRANT, "confirmation_checked": False},
        headers=THERAPIST,
    )

    assert response.status_code == 400
    assert repo.cases[case_id].consent_status == "pending"


def test_withdrawn_consent_cannot_be_granted_again(client, repo):
    withdrawn = client.post(
        "/api/v1/cases/case_demo_001/withdraw-consent", json={"reason": "caregiver request"}, headers=THERAPIST
    )
    assert withdrawn.status_code == 200

    regrant = client.post("/api/v1/cases/case_demo_001/grant-consent", json=GRANT, headers=THERAPIST)
    patch = client.patch("/api/v1/cases/case_demo_001", json={"nickname": "x"}, headers=THERAPIST)
    session = client.post(
        "/api/v1/cases/case_demo_001/sessions", json={"session_date": "2026-10-11"}, headers=THERAPIST
    )

    assert regrant.status_code == 409
    assert patch.status_code == 400
    assert session.status_code == 400
    assert repo.cases["case_demo_001"].consent_status == "withdrawn"


def test_grant_consent_requires_care_team_access(client, repo):
    case_id = _pending_case(repo)

    response = client.post(f"/api/v1/cases/{case_id}/grant-consent", json=GRANT, headers=OUTSIDER)

    assert response.status_code == 403
    assert repo.cases[case_id].consent_status == "pending"


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "Signed Off"},
        {"cues_acknowledged_by": "someone-else"},
        {"cues_acknowledged_at": "2020-01-01T00:00:00Z"},
    ],
)
def test_session_patch_rejects_status_and_acknowledgement_fields(client, repo, payload):
    before = repo.sessions["session_demo_001"].model_copy(deep=True)

    response = client.patch("/api/v1/sessions/session_demo_001", json=payload, headers=THERAPIST)

    assert response.status_code == 422
    assert repo.sessions["session_demo_001"] == before


def test_session_patch_still_updates_notes(client, repo):
    response = client.patch("/api/v1/sessions/session_demo_001", json={"notes": "reviewed"}, headers=THERAPIST)

    assert response.status_code == 200
    assert response.json()["notes"] == "reviewed"


EVALUATION_ROUTES = sorted(f"/api/v1{route.path}" for route in evaluation.router.routes)


def test_evaluation_route_registry_is_not_empty():
    assert len(EVALUATION_ROUTES) == 5


@pytest.mark.parametrize("path", EVALUATION_ROUTES)
def test_evaluation_routes_are_closed_for_supabase_auth_even_in_mock_mode(path, tmp_path):
    staging_like = Settings(mock_mode=True, auth_mode="supabase", supabase_jwt_secret="unit-test-secret")
    app.dependency_overrides[get_settings] = lambda: staging_like
    try:
        response = TestClient(app).post(path, json={"output_dir": str(tmp_path / "out"), "dataset_dir": str(tmp_path)})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert not (tmp_path / "out").exists()


def test_case_and_session_patch_reject_stale_expected_version(client, repo):
    case_version = repo.cases["case_demo_001"].version
    session_version = repo.sessions["session_demo_001"].version

    stale_case = client.patch(
        "/api/v1/cases/case_demo_001", json={"nickname": "x", "expected_version": case_version + 5}, headers=THERAPIST
    )
    stale_session = client.patch(
        "/api/v1/sessions/session_demo_001",
        json={"notes": "x", "expected_version": session_version + 5},
        headers=THERAPIST,
    )
    current_case = client.patch(
        "/api/v1/cases/case_demo_001", json={"nickname": "y", "expected_version": case_version}, headers=THERAPIST
    )

    assert stale_case.status_code == 409
    assert stale_session.status_code == 409
    assert current_case.status_code == 200
    assert repo.cases["case_demo_001"].nickname == "y"
    assert repo.sessions["session_demo_001"].notes == ""


def test_sql_repository_mode_rejects_multiple_api_workers():
    with pytest.raises(ValueError, match="single API worker"):
        Settings(repository_mode="sql", web_concurrency=2).validate_runtime_security()
    Settings(repository_mode="json", web_concurrency=2).validate_runtime_security()


def test_case_creation_cannot_start_with_consent_outside_demo_mode(client, repo):
    production_like = Settings(mock_mode=False, auth_mode="mock")
    app.dependency_overrides[get_settings] = lambda: production_like
    try:
        created = client.post(
            "/api/v1/cases",
            json={"child_code": "C-PROD-1", "age_months": 48, "consent_status": "granted"},
            headers=THERAPIST,
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert created.status_code == 200
    assert created.json()["consent_status"] == "pending"
    assert repo.cases[created.json()["case_id"]].consent_status == "pending"


@pytest.mark.parametrize("consent_status", ["withdrawn", "whatever", ""])
def test_case_creation_rejects_unknown_initial_consent(client, consent_status):
    response = client.post(
        "/api/v1/cases",
        json={"child_code": "C-BAD", "age_months": 48, "consent_status": consent_status},
        headers=THERAPIST,
    )

    assert response.status_code == 422


def test_withdrawal_reason_is_kept_on_a_privacy_record_not_in_the_audit_log(client, repo):
    reason = "Caregiver asked to stop participation."

    response = client.post(
        "/api/v1/cases/case_demo_001/withdraw-consent", json={"reason": reason}, headers=THERAPIST
    )

    assert response.status_code == 200
    records = [item for item in repo.privacy_operations.values() if item.operation_type == "consent_withdrawal"]
    assert [(item.reason, item.status, item.requested_by) for item in records] == [
        (reason, "completed", "therapist-demo")
    ]
    assert records[0].completed_at is not None
    assert all(reason not in event["message"] for event in repo.audit_log)


def test_v1_audio_upload_reports_unavailable_storage_instead_of_failing(client, repo, monkeypatch):
    monkeypatch.setenv("PASASCOPE_STORAGE_MODE", "supabase_private")
    get_settings.cache_clear()
    try:
        response = client.post(
            "/api/v1/sessions/session_demo_001/audio/upload",
            json={"filename": "a.wav", "content_type": "audio/wav", "size_bytes": 10},
            headers=THERAPIST,
        )
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Audio upload is unavailable for the configured storage mode."
    assert repo.audio_files == {}


ADMIN = {"X-Mock-Role": "org_admin", "X-User-Id": "admin-first", "X-Organization-Id": "org_fresh"}


def _membership(user_id: str, role: str) -> dict:
    return {"user_id": user_id, "display_name": "Name", "role": role}


def test_first_org_admin_can_record_their_own_membership_once(client, repo):
    denied_before = client.get("/api/v1/organizations/current/memberships", headers=ADMIN)

    bootstrap = client.post(
        "/api/v1/organizations/current/memberships", json=_membership("admin-first", "org_admin"), headers=ADMIN
    )
    listed = client.get("/api/v1/organizations/current/memberships", headers=ADMIN)
    add_therapist = client.post(
        "/api/v1/organizations/current/memberships", json=_membership("t-1", "therapist"), headers=ADMIN
    )

    assert denied_before.status_code == 403
    assert bootstrap.status_code == 200
    assert listed.status_code == 200
    assert add_therapist.status_code == 200
    assert [event["actor_id"] for event in repo.audit_log if event["action"] == "membership.bootstrap"] == [
        "admin-first"
    ]


@pytest.mark.parametrize(
    ("headers", "payload"),
    [
        # Not an org admin by identity.
        ({**ADMIN, "X-Mock-Role": "therapist"}, _membership("admin-first", "org_admin")),
        # Bootstrapping someone else, or a non-admin role, is not a bootstrap.
        (ADMIN, _membership("someone-else", "org_admin")),
        (ADMIN, _membership("admin-first", "therapist")),
    ],
)
def test_bootstrap_is_limited_to_the_callers_own_admin_membership(client, repo, headers, payload):
    response = client.post("/api/v1/organizations/current/memberships", json=payload, headers=headers)

    assert response.status_code == 403
    assert repo.memberships == {}


def test_bootstrap_closes_once_the_organization_has_an_admin(client, repo):
    assert client.post(
        "/api/v1/organizations/current/memberships", json=_membership("admin-first", "org_admin"), headers=ADMIN
    ).status_code == 200

    second = client.post(
        "/api/v1/organizations/current/memberships",
        json=_membership("admin-second", "org_admin"),
        headers={**ADMIN, "X-User-Id": "admin-second"},
    )

    assert second.status_code == 403


@pytest.mark.parametrize("role", ["platform_operator", "superuser", ""])
def test_membership_roles_are_restricted_to_organization_roles(client, role):
    assert client.post(
        "/api/v1/organizations/current/memberships", json=_membership("admin-first", "org_admin"), headers=ADMIN
    ).status_code == 200

    response = client.post("/api/v1/organizations/current/memberships", json=_membership("x", role), headers=ADMIN)

    assert response.status_code == 422
