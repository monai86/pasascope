"""Session report in Thai, filled from the reviewed data with fixed wording.

Same content rules as the English template: descriptive values only, no
norms or cutoffs, every cue shown with the therapist's decision, and the
decision-support limitations stated in the report itself.
"""

from __future__ import annotations

from typing import Any

from app.schemas.clinical import (
    ReportGenerationInput,
    ReportProviderAvailability,
    ReportProviderResult,
    ReportSection,
)
from app.services.providers.report_providers import BaseReportProvider

TITLE = "รายงานการทบทวนตัวอย่างภาษา"

THAI_LIMITATION_TEXT = (
    "รายงานนี้สร้างจากต้นแบบเครื่องมือสนับสนุนการตัดสินใจทางคลินิก ใช้สนับสนุนการตัดสินใจเท่านั้น "
    "ไม่ใช่การวินิจฉัย ระบบไม่ได้วินิจฉัยออทิสติกหรือความผิดปกติทางการพูดและภาษาใด ๆ "
    "ตัวชี้วัดเป็นค่าเชิงบรรยายจาก transcript ที่นักบำบัดตรวจแล้ว ยังไม่ได้ตรวจสอบความถูกต้องกับเด็กไทย "
    "และไม่มีเกณฑ์อ้างอิงของเด็กไทย ค่าที่คำนวณจากตัวอย่างสั้นอาจไม่เป็นตัวแทนของเด็ก "
    "ต้องให้นักบำบัดตรวจและลงนามก่อนนำรายงานไปใช้"
)

# Feature name → (Thai label, value kind)
FEATURES: list[tuple[str, str, str]] = [
    ("child_utterance_count", "จำนวนประโยคของเด็ก", "int"),
    ("adult_utterance_count", "จำนวนประโยคของผู้ใหญ่", "int"),
    ("mlu_utterance_count", "จำนวนประโยคที่ใช้คิด MLU", "int"),
    ("total_word_count", "จำนวนคำของเด็ก", "int"),
    ("number_of_different_words", "จำนวนคำที่ไม่ซ้ำ (NDW)", "int"),
    ("ndw_100", "คำไม่ซ้ำใน 100 คำแรก (NDW-100)", "int"),
    ("type_token_ratio", "ความหลากหลายของคำ (TTR)", "ratio"),
    ("mattr_50", "TTR เฉลี่ยหน้าต่าง 50 คำ (MATTR)", "ratio"),
    ("vocd_d", "ความหลากหลายของคำ (VOCD D)", "float"),
    ("mean_length_of_utterance_words", "ความยาวประโยคเฉลี่ย (MLU-w, คำ)", "float"),
    ("unintelligible_ratio", "สัดส่วนประโยคที่ฟังไม่ออก", "percent"),
    ("question_ratio", "สัดส่วนประโยคคำถามของเด็ก", "percent"),
    ("repetition_marker_count", "จำนวนการพูดซ้ำในประโยค", "int"),
    ("echolalia_cue_count", "cue การพูดตาม (echolalia)", "int"),
    ("pronoun_reversal_cue_count", "cue การใช้สรรพนามสลับ", "int"),
]
FEATURE_LABELS = {name: label for name, label, _ in FEATURES}
FEATURE_KINDS = {name: kind for name, _, kind in FEATURES}

TRACKED = [
    "child_utterance_count",
    "total_word_count",
    "number_of_different_words",
    "type_token_ratio",
    "mean_length_of_utterance_words",
]

CONSENT = {"granted": "ได้รับแล้ว", "pending": "ยังไม่บันทึก", "withdrawn": "ถอนแล้ว"}
QA = {"PASS": "ผ่าน", "WARNING": "ผ่าน มีข้อสังเกต", "FAIL": "ไม่ผ่าน (นักบำบัดรับรองโดยระบุเหตุผล)", "NOT_RUN": "ยังไม่ได้ตรวจ"}

CUE_TITLES = {
    "insufficient_sample_size": "ตัวอย่างภาษาสั้นเกินไป",
    "adult_dominant_sample": "ผู้ใหญ่พูดมากกว่าเด็ก",
    "high_unclear_ratio": "มีประโยคที่ฟังไม่ออกมาก",
    "high_repetition_cue": "พบการพูดซ้ำ",
    "echolalia_review_cue": "อาจเป็นการพูดตาม (echolalia)",
    "pronoun_reversal_review_cue": "อาจใช้สรรพนามสลับ",
}
CUE_STATES = {"acknowledged": "นักบำบัดยืนยัน", "dismissed": "นักบำบัดปัดตก", "unreviewed": "ยังไม่ได้ตรวจ"}


def _number(value: Any, kind: str) -> str:
    if value is None or isinstance(value, str):
        return "—"
    if isinstance(value, bool):
        return "ใช่" if value else "ไม่ใช่"
    if kind == "percent":
        return f"{float(value) * 100:.0f}%"
    if kind == "int":
        return f"{int(round(float(value)))}"
    if kind == "ratio":
        return f"{float(value):.2f}"
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _source_text(source: str) -> str:
    if source.startswith("asr"):
        return "ร่างจากการถอดเสียงอัตโนมัติบนเครื่อง (Whisper) แล้วนักบำบัดตรวจแก้"
    if source.startswith("cha_upload"):
        return "นำเข้าจากไฟล์ CHAT"
    if source.startswith("manual"):
        return "นักบำบัดพิมพ์หรือวางข้อความ"
    return source


def _age_text(months: int | None) -> str | None:
    if months is None:
        return None
    years, rem = divmod(int(months), 12)
    return f"{years} ปี {rem} เดือน" if years else f"{rem} เดือน"


class ThaiTemplateReportProvider(BaseReportProvider):
    @property
    def provider_id(self) -> str:
        return "template_th"

    @property
    def provider_name(self) -> str:
        return "ThaiTemplateReportProvider"

    @property
    def provider_version(self) -> str:
        return "1.0.0"

    def check_availability(self) -> ReportProviderAvailability:
        return ReportProviderAvailability(
            provider_id=self.provider_id,
            available=True,
            reason="Deterministic Thai template is always available.",
            requires_external_service=False,
        )

    def generate_report(self, input_data: ReportGenerationInput, config: dict[str, Any]) -> ReportProviderResult:
        values = {f.name: f.value for f in input_data.features}
        sections = [
            self._overview(input_data),
            self._sources(input_data),
            self._features(input_data, values),
            self._progress(input_data, values),
            self._cues(input_data),
            ReportSection(
                section_id="clinical_interpretation",
                title="การแปลผลของนักบำบัด",
                content=(input_data.therapist_notes or "").strip()
                or "- (นักบำบัดเขียนการแปลผลและข้อสังเกตจากการบำบัดที่นี่ ก่อนลงนาม)",
            ),
            self._goals(input_data),
            ReportSection(section_id="limitations", title="ข้อจำกัด", content=THAI_LIMITATION_TEXT),
            ReportSection(
                section_id="therapist_signoff",
                title="การลงนามของนักบำบัด",
                content="รอนักบำบัดแก้ไขและลงนาม",
            ),
        ]
        return ReportProviderResult(
            status="completed",
            sections=sections,
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            metadata={"title": TITLE, "language": "th"},
        )

    # ------------------------------------------------------------------
    def _overview(self, data: ReportGenerationInput) -> ReportSection:
        lines = [f"- รหัสเด็ก: {data.case_code}", f"- วันที่ session: {data.session_date}"]
        age = _age_text(data.child_age_months)
        if age:
            lines.append(f"- อายุเมื่อเปิดเคส: {age}")
        lines.append(f"- ความยินยอมของผู้ปกครอง: {CONSENT.get(data.consent_status, data.consent_status)}")
        return ReportSection(section_id="session_overview", title="ข้อมูล session", content="\n".join(lines))

    def _sources(self, data: ReportGenerationInput) -> ReportSection:
        lines = [
            f"- transcript: {_source_text(data.transcript_source)}",
            f"- การตรวจรูปแบบ transcript: {QA.get(data.qa_status, data.qa_status)}",
            f"- การรับรอง transcript: {'นักบำบัดรับรองแล้ว' if data.therapist_attested else 'ยังไม่รับรอง'}",
        ]
        return ReportSection(section_id="data_sources", title="ที่มาของข้อมูล", content="\n".join(lines))

    def _features(self, data: ReportGenerationInput, values: dict) -> ReportSection:
        if not data.features:
            return ReportSection(section_id="feature_summary", title="ตัวชี้วัดจากตัวอย่างภาษา", content="- ยังไม่ได้คำนวณตัวชี้วัด")
        rows = ["| ตัวชี้วัด | ค่า |", "|---|---:|"]
        for name, label, kind in FEATURES:
            if name in values and values[name] not in (None, "not_available"):
                rows.append(f"| {label} | {_number(values[name], kind)} |")
        rows.append("")
        rows.append("ค่าทั้งหมดเป็นค่าเชิงบรรยายของ session นี้ ยังไม่มีเกณฑ์อ้างอิงของเด็กไทย จึงไม่ได้ระบุว่าสูงหรือต่ำกว่าปกติ")
        return ReportSection(section_id="feature_summary", title="ตัวชี้วัดจากตัวอย่างภาษา", content="\n".join(rows))

    def _progress(self, data: ReportGenerationInput, values: dict) -> ReportSection:
        title = "เปรียบเทียบกับ session ก่อนหน้า"
        if not data.previous_features:
            return ReportSection(
                section_id="progress_comparison", title=title,
                content="- ต้องมีอย่างน้อย 2 session ที่วิเคราะห์แล้วจึงจะเปรียบเทียบได้",
            )
        by_session: dict[str, dict[str, float]] = {}
        for item in data.previous_features:
            if isinstance(item.value, (int, float)) and not isinstance(item.value, bool):
                by_session.setdefault(item.session_id or "_", {})[item.name] = float(item.value)
        series_sessions = list(by_session.values())
        lines = []
        for name in TRACKED:
            current = values.get(name)
            if not isinstance(current, (int, float)) or isinstance(current, bool):
                continue
            history = [s[name] for s in series_sessions if name in s]
            if not history:
                continue
            kind = FEATURE_KINDS[name]
            path = " → ".join(_number(v, kind) for v in [*history, float(current)])
            delta = float(current) - history[-1]
            if abs(delta) < 1e-9:
                change = "เท่าเดิม"
            else:
                change = f"{'เพิ่มขึ้น' if delta > 0 else 'ลดลง'} {_number(abs(delta), kind)} จากครั้งก่อน"
            lines.append(f"- {FEATURE_LABELS[name]}: {path} ({change})")
        if not lines:
            lines.append("- ไม่มีตัวชี้วัดที่เทียบกันได้ระหว่าง session")
        lines.append(f"- เทียบ {len(series_sessions) + 1} session เรียงจากเก่าไปใหม่ เป็นการบรรยายการเปลี่ยนแปลง ต้องให้นักบำบัดแปลผล")
        return ReportSection(section_id="progress_comparison", title=title, content="\n".join(lines))

    def _cues(self, data: ReportGenerationInput) -> ReportSection:
        title = "Cue ที่ระบบให้ตรวจ และการตัดสินของนักบำบัด"
        if not data.review_cues:
            return ReportSection(section_id="ml_review_cues", title=title, content="- ไม่มี cue จากกฎใน session นี้")
        lines = []
        for cue in data.review_cues:
            state = cue.review_state.status if cue.review_state else "unreviewed"
            line = f"- {CUE_TITLES.get(cue.cue_code, cue.title)}: {CUE_STATES.get(state, state)}"
            note = (cue.review_state.therapist_note or "").strip() if cue.review_state else ""
            if note:
                line += f" — {note}"
            if cue.evidence:
                line += f" ({len(cue.evidence)} จุดในบทสนทนา)"
            lines.append(line)
        lines.append("- cue มาจากกฎที่โปร่งใสบน transcript ไม่ใช่ผลวินิจฉัย")
        return ReportSection(section_id="ml_review_cues", title=title, content="\n".join(lines))

    def _goals(self, data: ReportGenerationInput) -> ReportSection:
        if data.therapy_goals:
            lines = [f"- {g.title}: {g.status}" + (f" — {g.target}" if g.target else "") for g in data.therapy_goals]
        else:
            lines = ["- ยังไม่ได้บันทึกเป้าหมายการบำบัดของเคสนี้"]
        return ReportSection(section_id="therapy_focus_areas", title="เป้าหมายการบำบัด", content="\n".join(lines))
