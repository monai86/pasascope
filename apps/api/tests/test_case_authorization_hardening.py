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
