"""Report how long therapists took to correct ASR drafts, from the local audit log.

For each transcription job that produced a draft, this measures the wall-clock
time between the draft becoming available (``audio.process``) and the first
attestation of that transcript (``transcript.attest``). It is elapsed time, so
it includes any pause the reviewer took; treat it as an upper bound on effort.

Reads the local JSON repository only. The output carries opaque record ids and
timings, never transcript text or child identifiers.

Usage:
    python scripts/report_transcript_review_time.py
    python scripts/report_transcript_review_time.py --repository path/to/repository.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPOSITORY = PROJECT_ROOT / "apps" / "api" / ".local" / "lingualens-app-repository.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "metrics" / "transcript_review_time.csv"

CSV_COLUMNS = [
    "job_id",
    "transcript_id",
    "provider",
    "audio_seconds",
    "utterance_count",
    "review_minutes",
    "review_minutes_per_audio_minute",
]


def _first_timestamp(audit_log: list[dict], action: str, target_id: str, *, after: datetime | None = None) -> datetime | None:
    stamps = sorted(
        datetime.fromisoformat(event["timestamp"])
        for event in audit_log
        if event.get("action") == action and event.get("target_id") == target_id
    )
    for stamp in stamps:
        if after is None or stamp >= after:
            return stamp
    return None


def review_times(repository: dict) -> list[dict]:
    audit_log = repository.get("audit_log", [])
    audio_files = repository.get("audio_files", {})
    rows = []
    for job_id, job in sorted(repository.get("jobs", {}).items()):
        details = job.get("details", {})
        draft = details.get("asr_draft") or {}
        transcript_id = draft.get("transcript_id")
        if not transcript_id:
            continue
        ready_at = _first_timestamp(audit_log, "audio.process", job_id)
        if ready_at is None:
            continue
        attested_at = _first_timestamp(audit_log, "transcript.attest", transcript_id, after=ready_at)
        if attested_at is None:
            continue
        minutes = (attested_at - ready_at).total_seconds() / 60
        audio_seconds = (audio_files.get(details.get("audio_file_id") or "") or {}).get("duration_seconds")
        rows.append(
            {
                "job_id": job_id,
                "transcript_id": transcript_id,
                "provider": draft.get("provider"),
                "audio_seconds": audio_seconds,
                "utterance_count": draft.get("utterance_count"),
                "review_minutes": round(minutes, 2),
                "review_minutes_per_audio_minute": (
                    round(minutes / (audio_seconds / 60), 2) if audio_seconds else None
                ),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repository", type=Path, default=DEFAULT_REPOSITORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.repository.exists():
        print(f"No local repository at {args.repository}. Run the app and review a draft first.")
        return 1
    rows = review_times(json.loads(args.repository.read_text(encoding="utf-8")))
    if not rows:
        print("No attested ASR drafts found yet.")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(f"{row['job_id']}: {row['review_minutes']} min to review ({row['provider']})")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
