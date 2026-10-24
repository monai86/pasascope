"""Build cases and sessions the way the desktop program does, without HTTP."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date

from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import ChildCaseCreate, ConsentGrantRequest, TherapySessionCreate
from app.services.consent_service import grant_consent

USER_ID = "therapist-demo"
ORGANIZATION_ID = "pilot_org_001"


def new_case(repo: MockRepository, child_code: str, *, age_months: int = 48, consent: bool = True):
    case = repo.create_case(
        ChildCaseCreate(
            child_code=child_code,
            nickname="Test",
            age_months=age_months,
            organization_id=ORGANIZATION_ID,
            care_team_user_ids=[USER_ID],
            primary_therapist_user_id=USER_ID,
            consent_status="pending",
        ),
        actor_id="system",
        audit_actor_id=USER_ID,
    )
    if consent:
        grant_consent(
            repo,
            case.case_id,
            ConsentGrantRequest(signer="Parent", consent_date=date(2026, 6, 1), confirmation_checked=True),
            actor_id=USER_ID,
        )
    return repo.cases[case.case_id]


def new_session(repo: MockRepository, child_code: str, *, age_months: int = 48):
    case = new_case(repo, child_code, age_months=age_months)
    return repo.create_session(
        case.case_id, TherapySessionCreate(session_date="2026-06-29"), actor_id=USER_ID
    )


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_reference_artifact(tmp_path):
    """Minimal valid reference-evidence artifact (TD row, age 60-71, toyplay)."""
    artifact_dir = tmp_path / "reference-evidence"
    artifact_dir.mkdir()
    cells_path = artifact_dir / "reference_cells.csv"
    fieldnames = [
        "language",
        "age_band_12mo",
        "task_type",
        "original_group",
        "presentation_group",
        "participant_count",
        "corpus_count",
        "supported",
        "reason_code",
    ]
    for feature in (
        "total_utterances",
        "total_words",
        "ttr",
        "mluw",
        "unintelligible_ratio",
        "question_ratio",
        "echolalia_count",
        "pronoun_reversal_count",
    ):
        fieldnames.extend([f"{feature}_q1", f"{feature}_median", f"{feature}_q3"])
    row = {
        "language": "eng",
        "age_band_12mo": "60-71",
        "task_type": "toyplay",
        "original_group": "TD",
        "presentation_group": "TD",
        "participant_count": 32,
        "corpus_count": 2,
        "supported": "true",
        "reason_code": "",
    }
    for feature in (
        "total_utterances",
        "total_words",
        "ttr",
        "mluw",
        "unintelligible_ratio",
        "question_ratio",
        "echolalia_count",
        "pronoun_reversal_count",
    ):
        row[f"{feature}_q1"] = 1.0
        row[f"{feature}_median"] = 2.0
        row[f"{feature}_q3"] = 3.0
    with cells_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)
    manifest = {
        "artifact_type": "ml_reference_evidence",
        "artifact_version": "test-v1",
        "dataset_hash": "test-dataset-hash",
        "feature_schema_version": "reference-core-14-v1",
        "supported_language": "eng",
        "gate1": {"status": "research_only"},
        "files": {
            "reference_cells": {
                "filename": cells_path.name,
                "sha256": _sha256(cells_path),
                "size_bytes": cells_path.stat().st_size,
            }
        },
    }
    (artifact_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return artifact_dir

AUTH_HEADERS = {
    "X-Mock-User-Id": "therapist-demo",
    "X-Mock-Role": "therapist",
    "X-Organization-Id": "pilot_org_001",
}
