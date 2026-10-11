from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.report_transcript_review_time import review_times  # noqa: E402


def _event(action: str, target_id: str, timestamp: str) -> dict:
    return {"action": action, "target_id": target_id, "timestamp": timestamp}


def _repository(audit_log: list[dict]) -> dict:
    return {
        "jobs": {
            "job_1": {
                "details": {
                    "audio_file_id": "aud_1",
                    "asr_draft": {"transcript_id": "tr_1", "provider": "local_whisper", "utterance_count": 12},
                }
            },
            "job_failed": {"details": {"audio_file_id": "aud_2"}},
        },
        "audio_files": {"aud_1": {"duration_seconds": 120}},
        "audit_log": audit_log,
    }


def test_review_time_runs_from_draft_ready_to_first_attestation():
    rows = review_times(
        _repository(
            [
                _event("audio.process", "job_1", "2026-10-11T10:00:00+00:00"),
                _event("transcript.patch", "tr_1", "2026-10-11T10:04:00+00:00"),
                _event("transcript.attest", "tr_1", "2026-10-11T10:09:00+00:00"),
                _event("transcript.attest", "tr_1", "2026-10-11T11:00:00+00:00"),
            ]
        )
    )

    assert rows == [
        {
            "job_id": "job_1",
            "transcript_id": "tr_1",
            "provider": "local_whisper",
            "audio_seconds": 120,
            "utterance_count": 12,
            "review_minutes": 9.0,
            "review_minutes_per_audio_minute": 4.5,
        }
    ]


def test_drafts_that_were_never_attested_are_left_out():
    rows = review_times(_repository([_event("audio.process", "job_1", "2026-10-11T10:00:00+00:00")]))

    assert rows == []
