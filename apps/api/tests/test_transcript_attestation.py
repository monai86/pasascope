import pytest
from fastapi import HTTPException

from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import Transcript, TranscriptReviewUpdate, Utterance
from app.services import transcript_service


@pytest.fixture
def repo_with_transcript():
    repo = MockRepository()
    session = repo.sessions["session_demo_001"]
    transcript = Transcript(
        transcript_id="trans_demo_001",
        session_id=session.session_id,
        case_id=session.case_id,
        source="manual",
        version=3,
        raw_text="*CHI: รถ สี แดง\n*INV: ใช่แล้ว",
        utterances=[
            Utterance(utterance_id="u1", speaker="CHI", text="รถ สี แดง", start_ms=1000, end_ms=2500),
            Utterance(utterance_id="u2", speaker="INV", text="ใช่แล้ว", start_ms=2800, end_ms=3500),
        ],
    )
    repo.transcripts[transcript.transcript_id] = transcript
    session.transcript_id = transcript.transcript_id
    return repo


def test_transcript_update_optimistic_concurrency_conflict(repo_with_transcript):
    # Base version is 3; base_version=2 is a conflict
    payload = TranscriptReviewUpdate.model_validate({
        "base_version": 2,
        "lines": [
            {"line_id": "L1", "speaker": "CHI", "start_ms": 1000, "end_ms": 2500, "text": "รถ สี แดง"}
        ],
        "review_status": "IN_REVIEW",
    })
    with pytest.raises(HTTPException) as caught:
        transcript_service.update_reviewed_transcript(repo_with_transcript, "session_demo_001", payload)
    assert caught.value.status_code == 409
    assert "conflict" in caught.value.detail.lower()


def test_transcript_update_sets_downstream_stale_and_increments_version(repo_with_transcript):
    payload = TranscriptReviewUpdate.model_validate({
        "base_version": 3,
        "lines": [
            {"line_id": "L1", "speaker": "CHI", "start_ms": 1000, "end_ms": 2600, "text": "รถ สี แดง คัน ใหญ่"},
            {"line_id": "L2", "speaker": "INV", "start_ms": 2800, "end_ms": 3500, "text": "ใช่แล้ว"},
        ],
        "review_status": "IN_REVIEW",
    })
    updated = transcript_service.update_reviewed_transcript(repo_with_transcript, "session_demo_001", payload)
    assert updated.version == 4
    assert repo_with_transcript.sessions["session_demo_001"].findings_stale is True
