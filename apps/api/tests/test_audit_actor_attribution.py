from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.mock_repository import MockRepository

ACTOR = "clinician-audit-1"
HEADERS = {"x-mock-user-id": ACTOR, "x-mock-role": "therapist", "x-organization-id": "pilot_org_001"}
PLACEHOLDER_ACTORS = {"system", "therapist", "worker"}
CHA = "@UTF8\n@Begin\n@Languages:\teng\n@Participants:\tCHI Child, THER Therapist\n*THER:\thello .\n*CHI:\thi there .\n@End"

# Every audited action a clinician can trigger through the v1 routes below.
EXPECTED_ACTIONS = {
    "case.create",
    "case.update",
    "consent.grant",
    "session.create",
    "session.patch",
    "cues_acknowledged",
    "therapy_goal.create",
    "therapy_goal.patch",
    "transcript.manual",
    "transcript.patch",
    "transcript.qa",
    "transcript.attest",
    "features.extract",
    "report.draft",
    "report.patch",
    "report.sign_off",
    "audio.upload",
    "job.cancel",
    "consent.withdraw",
}


@pytest.fixture()
def repo():
    repository = MockRepository()
    app.dependency_overrides[get_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


def _ok(response):
    assert response.status_code == 200, f"{response.request.method} {response.request.url.path}: {response.text}"
    return response.json()


def test_route_driven_audit_events_name_the_authenticated_user(repo):
    client = TestClient(app, headers=HEADERS)
    start = len(repo.audit_log)

    case = _ok(client.post("/api/v1/cases", json={"child_code": "C-AUDIT-1", "age_months": 60}))
    case_id = case["case_id"]
    _ok(client.patch(f"/api/v1/cases/{case_id}", json={"nickname": "A"}))
    _ok(
        client.post(
            f"/api/v1/cases/{case_id}/grant-consent",
            json={"signer": "Parent", "consent_date": "2026-10-11", "confirmation_checked": True},
        )
    )
    session_id = _ok(client.post(f"/api/v1/cases/{case_id}/sessions", json={"session_date": "2026-10-11"}))["session_id"]
    _ok(client.patch(f"/api/v1/sessions/{session_id}", json={"notes": "n"}))
    _ok(client.post(f"/api/v1/sessions/{session_id}/acknowledge-cues"))
    goal = _ok(client.post(f"/api/v1/cases/{case_id}/goals", json={"title": "Goal"}))
    _ok(client.patch(f"/api/v1/goals/{goal['goal_id']}", json={"title": "Goal 2"}))
    transcript = _ok(client.post(f"/api/v1/sessions/{session_id}/transcripts/manual", json={"text": CHA}))
    transcript_id = transcript["transcript_id"]
    _ok(client.patch(f"/api/v1/transcripts/{transcript_id}", json={"reviewer_note": "checked"}))
    _ok(client.post(f"/api/v1/transcripts/{transcript_id}/qa"))
    _ok(client.post(f"/api/v1/transcripts/{transcript_id}/attest", json={"override_qa_failure": True}))
    _ok(client.post(f"/api/v1/transcripts/{transcript_id}/extract-features"))
    report = _ok(client.post(f"/api/v1/sessions/{session_id}/reports/draft"))
    _ok(client.patch(f"/api/v1/reports/{report['report_id']}", json={"therapist_notes": "note"}))
    _ok(client.post(f"/api/v1/reports/{report['report_id']}/sign-off", json={"confirmation_checked": True}))
    job = _ok(
        client.post(
            f"/api/v1/sessions/{session_id}/audio/upload",
            json={"filename": "a.wav", "content_type": "audio/wav", "size_bytes": 10},
        )
    )
    _ok(client.post(f"/api/v1/jobs/{job['job_id']}/cancel"))
    _ok(client.post(f"/api/v1/cases/{case_id}/withdraw-consent", json={"reason": "caregiver request"}))

    events = repo.audit_log[start:]
    actions = {event["action"] for event in events}
    placeholder = sorted({event["action"] for event in events if event["actor_id"] in PLACEHOLDER_ACTORS})

    assert EXPECTED_ACTIONS <= actions, sorted(EXPECTED_ACTIONS - actions)
    assert placeholder == []
    assert {event["actor_id"] for event in events} == {ACTOR}
