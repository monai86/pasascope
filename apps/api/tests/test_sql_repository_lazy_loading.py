"""The SQL repository reads records when they are asked for, not all of them at start-up."""
from __future__ import annotations

import gc

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import get_repository
from app.main import app
from app.repositories.lazy_table import LazyTable
from app.schemas.clinical import ChildCaseCreate, TherapySessionCreate

pytest.importorskip("sqlalchemy")

from sqlalchemy import event  # noqa: E402

from app.repositories.sqlalchemy_repository import SqlAlchemyRepository  # noqa: E402

HEADERS = {"x-mock-user-id": "clinician_a", "x-mock-role": "therapist", "x-organization-id": "org_a"}


def _url(tmp_path, name: str = "lazy.db") -> str:
    return f"sqlite:///{tmp_path / name}"


def _statements(repo: SqlAlchemyRepository) -> list[str]:
    statements: list[str] = []
    event.listen(repo.engine, "before_cursor_execute", lambda conn, cur, statement, *rest: statements.append(statement))
    return statements


def _tables(repo: SqlAlchemyRepository) -> list[LazyTable]:
    return [getattr(repo, name) for name in repo._RECORD_TABLES]


def _populated(tmp_path, cases: int = 3) -> tuple[str, list[str]]:
    url = _url(tmp_path)
    repo = SqlAlchemyRepository(url)
    case_ids = []
    for index in range(cases):
        case = repo.create_case(
            ChildCaseCreate(child_code=f"C-{index}", age_months=50, organization_id="org_a", consent_status="granted"),
            actor_id="clinician_a",
        )
        repo.create_session(
            case.case_id,
            TherapySessionCreate(session_date="2026-10-11", session_type="language_sample"),
            actor_id="clinician_a",
        )
        case_ids.append(case.case_id)
    return url, case_ids


def test_opening_a_populated_database_reads_no_records(tmp_path):
    url, _ = _populated(tmp_path)

    repo = SqlAlchemyRepository(url)

    assert all(table.loaded() == [] for table in _tables(repo))
    assert all(table.full_reads == 0 for table in _tables(repo))
    assert repo.audit_log == []


def test_a_record_is_read_once_and_handed_out_as_one_object(tmp_path):
    url, case_ids = _populated(tmp_path)
    repo = SqlAlchemyRepository(url)
    statements = _statements(repo)

    first = repo.cases[case_ids[0]]
    again = repo.cases[case_ids[0]]

    assert first is again
    assert [key for key, _ in repo.cases.loaded()] == [case_ids[0]]
    assert len([s for s in statements if "child_cases" in s]) == 1
    assert "missing" not in repo.cases
    assert repo.cases.get("missing") is None
    with pytest.raises(KeyError):
        repo.cases["missing"]


def test_find_queries_on_the_given_fields_and_reads_only_what_matches(tmp_path):
    url, case_ids = _populated(tmp_path)
    repo = SqlAlchemyRepository(url)
    statements = _statements(repo)

    sessions = repo.find("sessions", case_id=case_ids[1])

    assert [session.case_id for session in sessions] == [case_ids[1]]
    assert len(repo.sessions.loaded()) == 1
    assert any("WHERE sessions.case_id = " in statement for statement in statements)
    assert repo.sessions.full_reads == 0
    assert repo.find("sessions", case_id={case_ids[0], case_ids[2]}) != []
    assert repo.find("sessions", case_id=set()) == []


def test_find_judges_a_record_by_what_is_in_memory(tmp_path):
    url, case_ids = _populated(tmp_path)
    repo = SqlAlchemyRepository(url)
    session = repo.find("sessions", case_id=case_ids[0])[0]

    # Changed here, not saved: it no longer belongs to the first case.
    session.case_id = case_ids[1]

    assert repo.find("sessions", case_id=case_ids[0]) == []
    assert session in repo.find("sessions", case_id=case_ids[1])
    assert repo.find("sessions", case_id=case_ids[1])[0] is not None


def test_a_change_to_a_held_record_is_saved(tmp_path):
    url, case_ids = _populated(tmp_path)
    repo = SqlAlchemyRepository(url)

    repo.cases[case_ids[0]].notes = "Changed in place."
    repo.add_audit("case.update", case_ids[0], "Case updated.", actor_id="clinician_a")

    assert SqlAlchemyRepository(url).cases[case_ids[0]].notes == "Changed in place."


def test_records_beyond_the_limit_are_let_go_once_they_are_saved(tmp_path):
    url, case_ids = _populated(tmp_path, cases=6)
    repo = SqlAlchemyRepository(url)
    repo.cases._max_cached = 2

    for case_id in case_ids:
        repo.cases[case_id]
    gc.collect()

    assert len(repo.cases.loaded()) == 2


def test_a_record_that_is_not_saved_yet_is_never_let_go(tmp_path):
    url, case_ids = _populated(tmp_path, cases=6)
    repo = SqlAlchemyRepository(url)
    repo.cases._max_cached = 2

    repo.cases[case_ids[0]].notes = "Not saved yet."
    for case_id in case_ids[1:]:
        repo.cases[case_id]
    gc.collect()

    assert repo.cases[case_ids[0]].notes == "Not saved yet."
    repo.save()
    assert SqlAlchemyRepository(url).cases[case_ids[0]].notes == "Not saved yet."


def test_a_record_let_go_while_a_caller_holds_it_is_still_saved(tmp_path):
    url, case_ids = _populated(tmp_path, cases=6)
    repo = SqlAlchemyRepository(url)
    repo.cases._max_cached = 2

    held = repo.cases[case_ids[0]]
    for case_id in case_ids[1:]:
        repo.cases[case_id]
    gc.collect()
    held.notes = "Changed after it left the recent set."
    repo.save()

    assert repo.cases[case_ids[0]] is held
    assert SqlAlchemyRepository(url).cases[case_ids[0]].notes == "Changed after it left the recent set."


def test_reading_a_whole_table_still_works_and_is_counted(tmp_path):
    url, case_ids = _populated(tmp_path)
    repo = SqlAlchemyRepository(url)

    assert set(case_ids) <= set(repo.cases)
    assert repo.cases.full_reads == 1


def test_stored_audit_events_are_read_from_the_table(tmp_path):
    url, case_ids = _populated(tmp_path)
    repo = SqlAlchemyRepository(url)

    events = repo.audit_events(action="case.create")

    assert {event["target_id"] for event in events} >= set(case_ids)
    assert repo.audit_log == []


def test_the_audit_list_in_memory_stays_short(tmp_path):
    repo = SqlAlchemyRepository(_url(tmp_path))
    repo._AUDIT_TAIL = 5

    for index in range(12):
        repo.add_audit("job.cancel", "case_demo_001", f"Event {index}.", actor_id="clinician_a")

    assert len(repo.audit_log) == 5
    assert len(repo.audit_events(action="job.cancel")) == 12


def test_a_session_from_start_to_report_never_reads_a_whole_table(tmp_path):
    """Every route a therapist's session goes through asks for the records it needs by field."""
    url, _ = _populated(tmp_path)
    repo = SqlAlchemyRepository(url)
    app.dependency_overrides[get_repository] = lambda: repo
    client = TestClient(app)
    try:
        case = client.post("/api/v1/cases", headers=HEADERS, json={"child_code": "C-FLOW", "age_months": 54, "consent_status": "granted"}).json()
        case_id = case["case_id"]
        session = client.post(
            f"/api/v1/cases/{case_id}/sessions",
            headers=HEADERS,
            json={"session_date": "2026-10-12", "session_type": "therapy_session"},
        ).json()
        session_id = session["session_id"]
        transcript = client.post(
            f"/api/v1/sessions/{session_id}/transcripts/manual",
            headers=HEADERS,
            json={"text": "THER: what is this\nCHI: it is a red ball\nCHI: the ball goes up", "language": "English"},
        ).json()
        transcript_id = transcript["transcript_id"]
        responses = [
            client.post(f"/api/v1/transcripts/{transcript_id}/qa", headers=HEADERS),
            client.post(f"/api/v1/transcripts/{transcript_id}/extract-features", headers=HEADERS, json={}),
            client.post(f"/api/v1/sessions/{session_id}/reports/draft", headers=HEADERS, json={}),
            client.post(f"/api/v1/cases/{case_id}/goals", headers=HEADERS, json={"title": "Goal", "target": "Target"}),
            client.get("/api/v1/cases", headers=HEADERS),
            client.get(f"/api/v1/cases/{case_id}", headers=HEADERS),
            client.get(f"/api/v1/cases/{case_id}/timeline", headers=HEADERS),
            client.get(f"/api/v1/cases/{case_id}/goals", headers=HEADERS),
            client.get(f"/api/v1/cases/{case_id}/feature-trend", headers=HEADERS),
            client.get(f"/api/v1/sessions/{session_id}", headers=HEADERS),
            client.get(f"/api/v1/sessions/{session_id}/status", headers=HEADERS),
            client.get(f"/api/v1/sessions/{session_id}/transcript", headers=HEADERS),
            client.get(f"/api/v1/sessions/{session_id}/features", headers=HEADERS),
            client.get(f"/api/v1/sessions/{session_id}/audio", headers=HEADERS),
            client.get("/api/v1/reports", headers=HEADERS),
            client.get("/api/v1/dashboard/summary", headers=HEADERS),
            client.post(f"/api/v1/cases/{case_id}/withdraw-consent", headers=HEADERS, json={"reason": "Family request."}),
        ]
    finally:
        app.dependency_overrides.clear()

    assert [(response.request.url.path, response.status_code) for response in responses if response.status_code >= 400] == []
    assert {table.kind: table.full_reads for table in _tables(repo) if table.full_reads} == {}
