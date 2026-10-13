from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.schemas.clinical import ChildCaseCreate


def test_create_case_route_uses_transactional_sql_repository_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'case-route-create.db'}")

    def fail_snapshot_save() -> None:
        raise AssertionError("case route create must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        response = TestClient(app).post(
            "/api/v1/cases",
            json={"child_code": "C-ROUTE-001", "age_months": 48, "language": "English"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    case_id = response.json()["case_id"]
    with repo.SessionLocal() as db:
        row = db.get(ChildCaseRecord, case_id)
        audit = db.query(AuditLogRecord).filter_by(action="case.create", target_id=case_id).one()

    assert row is not None
    assert row.child_code == "C-ROUTE-001"
    assert row.consent_status == "pending"
    assert response.json()["consent_status"] == "pending"
    assert row.version == 1
    assert audit.actor_id == "therapist-demo"


def test_create_case_route_rejects_blank_case_code():
    response = TestClient(app).post(
        "/api/v1/cases",
        json={"child_code": "   ", "age_months": 48, "language": "Thai"},
    )

    assert response.status_code == 422


def test_update_case_route_uses_transactional_sql_repository_without_snapshot_save(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    repo = SqlAlchemyRepository(f"sqlite:///{tmp_path / 'case-route-update.db'}")
    case = repo.create_case(ChildCaseCreate(child_code="C-ROUTE-002", age_months=48), actor_id="user_tx")

    def fail_snapshot_save() -> None:
        raise AssertionError("case route update must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        response = TestClient(app).patch(
            f"/api/v1/cases/{case.case_id}",
            headers={"x-mock-user-id": "user_tx", "x-organization-id": case.organization_id},
            json={"notes": "Route update."},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    with repo.SessionLocal() as db:
        row = db.get(ChildCaseRecord, case.case_id)
        audit = db.query(AuditLogRecord).filter_by(action="case.update", target_id=case.case_id).one()

    assert body["version"] == case.version + 1
    assert row is not None
    assert row.notes == "Route update."
    assert row.version == case.version + 1
    assert audit.actor_id == "user_tx"


def _delete(repo, case_id: str, headers: dict[str, str] | None = None):
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        return TestClient(app).delete(f"/api/v1/cases/{case_id}", headers=headers or {})
    finally:
        app.dependency_overrides.clear()


def test_an_empty_case_is_deleted_and_the_deletion_is_audited(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from app.db.models import AuditLogRecord, ChildCaseRecord
    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    url = f"sqlite:///{tmp_path / 'case-route-delete.db'}"
    repo = SqlAlchemyRepository(url)
    case = repo.create_case(
        ChildCaseCreate(child_code="C-MISTAKE", age_months=48, language="Thai", care_team_user_ids=["therapist-demo"]),
        actor_id="therapist-demo",
    )

    def fail_snapshot_save() -> None:
        raise AssertionError("case deletion must not use snapshot save")

    monkeypatch.setattr(repo, "save", fail_snapshot_save)
    response = _delete(repo, case.case_id)

    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "case_id": case.case_id}
    assert case.case_id not in repo.cases
    with repo.SessionLocal() as db:
        assert db.get(ChildCaseRecord, case.case_id) is None
        audit = db.query(AuditLogRecord).filter_by(action="case.delete", target_id=case.case_id).one()
        # The record of the case being created is kept too.
        assert db.query(AuditLogRecord).filter_by(action="case.create", target_id=case.case_id).count() == 1
    assert audit.outcome == "success"
    assert "C-MISTAKE" not in audit.message

    monkeypatch.undo()
    reloaded = SqlAlchemyRepository(url)
    assert case.case_id not in reloaded.cases
    assert _delete(repo, case.case_id).status_code == 404


def test_a_case_with_a_session_is_not_deleted():
    from app.repositories.mock_repository import MockRepository

    repo = MockRepository()  # seeded with a case that has one session
    response = _delete(repo, "case_demo_001")

    assert response.status_code == 409
    assert "has sessions" in response.json()["detail"]
    assert "case_demo_001" in repo.cases
    assert not [item for item in repo.audit_log if item["action"] == "case.delete"]


def test_a_case_whose_consent_was_withdrawn_is_kept():
    from app.repositories.mock_repository import MockRepository

    repo = MockRepository(seed_demo=False)
    case = repo.create_case(
        ChildCaseCreate(child_code="C-WITHDRAWN", age_months=40, language="Thai", care_team_user_ids=["therapist-demo"]),
        actor_id="therapist-demo",
    )
    repo.cases[case.case_id].consent_status = "withdrawn"

    response = _delete(repo, case.case_id)

    assert response.status_code == 409
    assert case.case_id in repo.cases


def test_another_workspace_cannot_delete_a_case():
    from app.repositories.mock_repository import MockRepository

    repo = MockRepository(seed_demo=False)
    case = repo.create_case(
        ChildCaseCreate(child_code="C-OTHER", age_months=40, language="Thai", care_team_user_ids=["therapist-demo"]),
        actor_id="therapist-demo",
    )

    response = _delete(repo, case.case_id, {"x-mock-user-id": "someone-else", "x-organization-id": "another_org"})

    assert response.status_code == 404
    assert case.case_id in repo.cases
