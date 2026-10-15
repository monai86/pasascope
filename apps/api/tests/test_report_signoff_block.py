"""Signing a report fills its sign-off sections without dropping the therapist's text."""

from datetime import datetime, timezone

from app.services.report_service import apply_signoff_block

SIGNED_AT = datetime(2026, 10, 16, 9, 30, tzinfo=timezone.utc)
DRAFT = """# Session Review Report

## Clinical Interpretation Notes
- Add therapist interpretation here.

## Therapist Sign-off
Pending therapist edit and sign-off.

## Export Timestamp
- Pending until therapist sign-off.
"""


def test_signoff_replaces_placeholders():
    signed = apply_signoff_block(DRAFT, "Therapist A", SIGNED_AT)
    assert "Pending therapist edit and sign-off." not in signed
    assert "Pending until therapist sign-off." not in signed
    assert "- Signed by: Therapist A" in signed
    assert f"- {SIGNED_AT.isoformat()}" in signed


def test_note_typed_at_the_end_survives_signoff():
    edited = DRAFT + "\nเด็กตอบคำถามได้ดีขึ้นเมื่อเทียบกับครั้งก่อน\n"
    signed = apply_signoff_block(edited, "Therapist A", SIGNED_AT)
    assert "เด็กตอบคำถามได้ดีขึ้นเมื่อเทียบกับครั้งก่อน" in signed


def test_resigning_does_not_stack_generated_lines():
    once = apply_signoff_block(DRAFT, "Therapist A", SIGNED_AT)
    later = datetime(2026, 10, 17, 9, 30, tzinfo=timezone.utc)
    twice = apply_signoff_block(once, "Therapist B", later)
    assert twice.count("- Signed by:") == 1
    assert "Therapist A" not in twice
    assert twice.count("- 2026-10-1") == 1


def test_missing_sections_are_added():
    signed = apply_signoff_block("# Report\n\nBody", "Therapist A", SIGNED_AT)
    assert "## Therapist Sign-off" in signed and "## Export Timestamp" in signed
