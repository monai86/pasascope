"""The Thai report template, its sign-off, and Thai wording in the safety check."""

from datetime import datetime, timezone

from app.schemas.clinical import FeatureValue, ReportGenerationInput, ReviewCue, ReviewCueState
from app.services.providers.report_registry import report_provider_registry
from app.services.report_safety_validator import ReportSafetyValidator
from app.services.report_service import apply_signoff_block, assemble_report_markdown


def _input(**overrides) -> ReportGenerationInput:
    data = dict(
        transcript_id="tr1",
        case_code="TH-001",
        session_date="2026-10-16",
        consent_status="granted",
        transcript_source="asr_draft:local_whisper",
        qa_status="PASS",
        therapist_attested=True,
        child_age_months=50,
        features=[
            FeatureValue(name="child_utterance_count", value=12, session_id="s2"),
            FeatureValue(name="type_token_ratio", value=0.6125, session_id="s2"),
            FeatureValue(name="mean_length_of_utterance_words", value=3.5, session_id="s2"),
            FeatureValue(name="mean_length_of_utterance_morphemes", value="not_available", session_id="s2"),
        ],
        previous_features=[FeatureValue(name="mean_length_of_utterance_words", value=2.5, session_id="s1")],
        review_cues=[
            ReviewCue(
                cue_code="echolalia_review_cue", severity="review", title="Possible echoed-language cue",
                explanation="x", recommended_next_review_step="y",
                evidence=[{"adult_utterance_id": "a", "child_utterance_id": "c"}],
                review_state=ReviewCueState(status="dismissed", therapist_note="เป็นคำตอบ ไม่ใช่การพูดตาม"),
            )
        ],
    )
    data.update(overrides)
    return ReportGenerationInput(**data)


def _markdown(**overrides) -> str:
    provider = report_provider_registry.get("template_th")
    return assemble_report_markdown(provider.generate_report(_input(**overrides), {}), "Session Review Report")


def test_thai_report_reads_in_thai_with_named_values():
    markdown = _markdown()
    assert markdown.startswith("# รายงานการทบทวนตัวอย่างภาษา")
    assert "| ความหลากหลายของคำ (TTR) | 0.61 |" in markdown
    assert "type_token_ratio" not in markdown
    assert "MLU-m" not in markdown  # a value that could not be computed is left out
    assert "2.5 → 3.5 (เพิ่มขึ้น 1 จากครั้งก่อน)" in markdown
    assert "นักบำบัดปัดตก — เป็นคำตอบ ไม่ใช่การพูดตาม" in markdown
    assert "4 ปี 2 เดือน" in markdown
    assert "## Therapist Sign-off" not in markdown


def test_thai_report_passes_the_safety_check():
    result = ReportSafetyValidator().validate_report(_markdown(), source="finalization")
    assert result.status == "passed", result.issues


def test_thai_diagnostic_wording_blocks_signoff():
    markdown = _markdown() + "\nสรุป: ตรวจพบออทิสติกในเด็กรายนี้\n"
    result = ReportSafetyValidator().validate_report(markdown, source="finalization")
    assert result.finalization_blocked
    assert any(issue.rule_id == "RULE_TH_DETECTED" for issue in result.issues)


def test_thai_signoff_keeps_thai_headings_and_notes():
    markdown = _markdown() + "\nหมายเหตุ: ผู้ปกครองให้ข้อมูลเพิ่ม\n"
    signed = apply_signoff_block(markdown, "กานดา ใจดี", datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc))
    assert "- ลงนามโดย: กานดา ใจดี" in signed
    assert "รอนักบำบัดแก้ไขและลงนาม" not in signed and "- รอการลงนาม" not in signed
    assert "หมายเหตุ: ผู้ปกครองให้ข้อมูลเพิ่ม" in signed
    assert "## Therapist Sign-off" not in signed and "## Export Timestamp" not in signed
    assert "- เวลาลงนาม: 16/10/2569 16:00 น. (เวลาประเทศไทย)" in signed
    resigned = apply_signoff_block(signed, "กานดา ใจดี", datetime(2026, 10, 17, 2, 0, tzinfo=timezone.utc))
    assert resigned.count("- เวลาลงนาม:") == 1 and "17/10/2569 09:00" in resigned
