"""Clinic session report in Thai or English, filled from the reviewed data with fixed wording.

Same content rules as the web template: descriptive values only, no norms or
cutoffs, every cue shown with the therapist's decision, and the
decision-support limitations stated in the report itself. Both languages have
the same sections in the same order, so a report reads the same either way.
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

# Feature name → (Thai label, value kind). The report lists the main measures
# (docs/FEATURE_GUIDE.md); every measure is still in the app's Findings tab.
FEATURES: list[tuple[str, str, str]] = [
    ("child_utterance_count", "จำนวนประโยคของเด็ก", "int"),
    ("mlu_utterance_count", "จำนวนประโยคที่ใช้คิด MLU", "int"),
    ("total_word_count", "จำนวนคำของเด็ก", "int"),
    ("mean_length_of_utterance_words", "ความยาวประโยคเฉลี่ย (MLU-w, คำ)", "float"),
    ("number_of_different_words", "จำนวนคำที่ไม่ซ้ำ (NDW)", "int"),
    ("ndw_100", "คำไม่ซ้ำใน 100 คำแรก (NDW-100)", "int"),
    ("mattr_50", "TTR เฉลี่ยหน้าต่าง 50 คำ (MATTR)", "ratio"),
    ("vocd_d", "ความหลากหลายของคำ (VOCD D)", "float"),
    ("child_response_rate", "อัตราที่เด็กตอบต่อจากผู้ใหญ่", "percent"),
    ("unintelligible_ratio", "สัดส่วนประโยคที่ฟังไม่ออก", "percent"),
    ("echolalia_cue_count", "cue การพูดตาม (echolalia)", "int"),
]
FEATURE_LABELS = {name: label for name, label, _ in FEATURES}
FEATURE_KINDS = {name: kind for name, _, kind in FEATURES}

TRACKED = [
    "child_utterance_count",
    "total_word_count",
    "number_of_different_words",
    "mean_length_of_utterance_words",
    "child_response_rate",
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


ENGLISH_LIMITATION_TEXT = (
    "This report comes from a prototype clinical decision-support tool and is for decision-support only. "
    "It is not diagnostic: the system does not diagnose autism or any speech or language disorder. "
    "The measures describe a transcript the therapist reviewed. They have not been validated with Thai "
    "children and there are no Thai reference norms. Values from a short sample may not represent the child. "
    "Therapist review required: a therapist must review and sign this report before it is used."
)

ENGLISH_FEATURE_LABELS = {
    "child_utterance_count": "Child utterances",
    "mlu_utterance_count": "Utterances used for MLU",
    "total_word_count": "Child words",
    "mean_length_of_utterance_words": "Mean length of utterance (MLU-w, words)",
    "number_of_different_words": "Number of different words (NDW)",
    "ndw_100": "Different words in the first 100 (NDW-100)",
    "mattr_50": "Moving-average TTR, 50-word window (MATTR)",
    "vocd_d": "Lexical diversity (VOCD D)",
    "child_response_rate": "Child response rate",
    "unintelligible_ratio": "Unintelligible utterances",
    "echolalia_cue_count": "Echolalia cues",
}

WORDING: dict[str, dict[str, Any]] = {
    "th": {
        "title": TITLE,
        "feature_labels": FEATURE_LABELS,
        "consent": CONSENT,
        "qa": QA,
        "cue_titles": CUE_TITLES,
        "cue_states": CUE_STATES,
        "yes": "ใช่", "no": "ไม่ใช่",
        "overview": "ข้อมูล session",
        "child_code": "รหัสเด็ก", "session_date": "วันที่ session", "age": "อายุเมื่อเปิดเคส",
        "consent_label": "ความยินยอมของผู้ปกครอง",
        "sources": "ที่มาของข้อมูล",
        "transcript": "transcript", "qa_label": "การตรวจรูปแบบ transcript", "attest_label": "การรับรอง transcript",
        "attested": "นักบำบัดรับรองแล้ว", "not_attested": "ยังไม่รับรอง",
        "source_asr": "ร่างจากการถอดเสียงอัตโนมัติบนเครื่อง (Whisper) แล้วนักบำบัดตรวจแก้",
        "source_cha": "นำเข้าจากไฟล์ CHAT", "source_manual": "นักบำบัดพิมพ์หรือวางข้อความ",
        "features": "ตัวชี้วัดจากตัวอย่างภาษา",
        "no_features": "- ยังไม่ได้คำนวณตัวชี้วัด",
        "table_head": "| ตัวชี้วัด | ค่า |",
        "features_note": "ค่าทั้งหมดเป็นค่าเชิงบรรยายของ session นี้ ยังไม่มีเกณฑ์อ้างอิงของเด็กไทย จึงไม่ได้ระบุว่าสูงหรือต่ำกว่าปกติ",
        "progress": "เปรียบเทียบกับ session ก่อนหน้า",
        "progress_needs_two": "- ต้องมีอย่างน้อย 2 session ที่วิเคราะห์แล้วจึงจะเปรียบเทียบได้",
        "same": "เท่าเดิม", "up": "เพิ่มขึ้น", "down": "ลดลง", "from_last": "จากครั้งก่อน",
        "no_comparable": "- ไม่มีตัวชี้วัดที่เทียบกันได้ระหว่าง session",
        "progress_note": "- เทียบ {n} session เรียงจากเก่าไปใหม่ เป็นการบรรยายการเปลี่ยนแปลง ต้องให้นักบำบัดแปลผล",
        "cues": "Cue ที่ระบบให้ตรวจ และการตัดสินของนักบำบัด",
        "no_cues": "- ไม่มี cue จากกฎใน session นี้",
        "cue_points": "({n} จุดในบทสนทนา)",
        "cue_note": "- cue มาจากกฎที่โปร่งใสบน transcript ไม่ใช่ผลวินิจฉัย",
        "interpretation": "การแปลผลของนักบำบัด",
        "interpretation_placeholder": "- (นักบำบัดเขียนการแปลผลและข้อสังเกตจากการบำบัดที่นี่ ก่อนลงนาม)",
        "goals": "เป้าหมายการบำบัด",
        "no_goals": "- ยังไม่ได้บันทึกเป้าหมายการบำบัดของเคสนี้",
        "limitations": "ข้อจำกัด", "limitation_text": THAI_LIMITATION_TEXT,
        "signoff": "การลงนามของนักบำบัด", "signoff_placeholder": "รอนักบำบัดแก้ไขและลงนาม",
    },
    "en": {
        "title": "Language Sample Review Report",
        "feature_labels": ENGLISH_FEATURE_LABELS,
        "consent": {"granted": "granted", "pending": "not recorded", "withdrawn": "withdrawn"},
        "qa": {"PASS": "passed", "WARNING": "passed with notes", "FAIL": "did not pass (attested by the therapist with a reason)", "NOT_RUN": "not checked"},
        "cue_titles": {
            "insufficient_sample_size": "Sample too short",
            "adult_dominant_sample": "Adult talk dominates the sample",
            "high_unclear_ratio": "Many unintelligible utterances",
            "high_repetition_cue": "Repetitions",
            "echolalia_review_cue": "Possible echolalia",
            "pronoun_reversal_review_cue": "Possible pronoun reversal",
        },
        "cue_states": {"acknowledged": "confirmed by the therapist", "dismissed": "dismissed by the therapist", "unreviewed": "not reviewed"},
        "yes": "yes", "no": "no",
        "overview": "Session details",
        "child_code": "Child code", "session_date": "Session date", "age": "Age at intake",
        "consent_label": "Caregiver consent",
        "sources": "Data sources",
        "transcript": "Transcript", "qa_label": "Transcript format check", "attest_label": "Transcript attestation",
        "attested": "attested by the therapist", "not_attested": "not attested",
        "source_asr": "drafted by on-device speech recognition (Whisper), then corrected by the therapist",
        "source_cha": "imported from a CHAT file", "source_manual": "typed or pasted by the therapist",
        "features": "Language sample measures",
        "no_features": "- Measures have not been calculated.",
        "table_head": "| Measure | Value |",
        "features_note": "All values describe this session only. There are no Thai reference norms, so no value is labelled high or low.",
        "progress": "Comparison with earlier sessions",
        "progress_needs_two": "- At least two analysed sessions are needed for a comparison.",
        "same": "unchanged", "up": "up", "down": "down", "from_last": "from the last session",
        "no_comparable": "- No measure can be compared across sessions.",
        "progress_note": "- {n} sessions, oldest first. This describes change; the therapist interprets it.",
        "cues": "Review cues and the therapist's decisions",
        "no_cues": "- No rule-based cues in this session.",
        "cue_points": "({n} places in the transcript)",
        "cue_note": "- Cues come from transparent rules applied to the transcript. They are not diagnostic findings.",
        "interpretation": "Therapist's interpretation",
        "interpretation_placeholder": "- (Write your interpretation and clinical observations here before signing.)",
        "goals": "Therapy goals",
        "no_goals": "- No therapy goals are recorded for this case.",
        "limitations": "Limitations", "limitation_text": ENGLISH_LIMITATION_TEXT,
        "signoff": "Therapist sign-off", "signoff_placeholder": "Awaiting therapist review and signature.",
    },
}


def _number(value: Any, kind: str, words: dict | None = None) -> str:
    words = words or WORDING["th"]
    if value is None or isinstance(value, str):
        return "—"
    if isinstance(value, bool):
        return words["yes"] if value else words["no"]
    if kind == "percent":
        return f"{float(value) * 100:.0f}%"
    if kind == "int":
        return f"{int(round(float(value)))}"
    if kind == "ratio":
        return f"{float(value):.2f}"
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _source_text(source: str, words: dict | None = None) -> str:
    words = words or WORDING["th"]
    if source.startswith("asr"):
        return words["source_asr"]
    if source.startswith("cha_upload"):
        return words["source_cha"]
    if source.startswith("manual"):
        return words["source_manual"]
    return source


def _age_text(months: int | None, language: str = "th") -> str | None:
    if months is None:
        return None
    years, rem = divmod(int(months), 12)
    if language == "en":
        return f"{years} years {rem} months" if years else f"{rem} months"
    return f"{years} ปี {rem} เดือน" if years else f"{rem} เดือน"


class ThaiTemplateReportProvider(BaseReportProvider):
    """The clinic report in Thai. ``EnglishClinicReportProvider`` writes the same report in English."""

    language = "th"

    @property
    def words(self) -> dict[str, Any]:
        return WORDING[self.language]

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
            reason="Deterministic clinic template is always available.",
            requires_external_service=False,
        )

    def generate_report(self, input_data: ReportGenerationInput, config: dict[str, Any]) -> ReportProviderResult:
        w = self.words
        values = {f.name: f.value for f in input_data.features}
        sections = [
            self._overview(input_data),
            self._sources(input_data),
            self._features(input_data, values),
            self._progress(input_data, values),
            self._cues(input_data),
            ReportSection(
                section_id="clinical_interpretation",
                title=w["interpretation"],
                content=(input_data.therapist_notes or "").strip() or w["interpretation_placeholder"],
            ),
            self._goals(input_data),
            ReportSection(section_id="limitations", title=w["limitations"], content=w["limitation_text"]),
            ReportSection(section_id="therapist_signoff", title=w["signoff"], content=w["signoff_placeholder"]),
        ]
        return ReportProviderResult(
            status="completed",
            sections=sections,
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            metadata={"title": w["title"], "language": self.language},
        )

    # ------------------------------------------------------------------
    def _overview(self, data: ReportGenerationInput) -> ReportSection:
        w = self.words
        lines = [f"- {w['child_code']}: {data.case_code}", f"- {w['session_date']}: {data.session_date}"]
        age = _age_text(data.child_age_months, self.language)
        if age:
            lines.append(f"- {w['age']}: {age}")
        lines.append(f"- {w['consent_label']}: {w['consent'].get(data.consent_status, data.consent_status)}")
        return ReportSection(section_id="session_overview", title=w["overview"], content="\n".join(lines))

    def _sources(self, data: ReportGenerationInput) -> ReportSection:
        w = self.words
        lines = [
            f"- {w['transcript']}: {_source_text(data.transcript_source, w)}",
            f"- {w['qa_label']}: {w['qa'].get(data.qa_status, data.qa_status)}",
            f"- {w['attest_label']}: {w['attested'] if data.therapist_attested else w['not_attested']}",
        ]
        return ReportSection(section_id="data_sources", title=w["sources"], content="\n".join(lines))

    def _features(self, data: ReportGenerationInput, values: dict) -> ReportSection:
        w = self.words
        if not data.features:
            return ReportSection(section_id="feature_summary", title=w["features"], content=w["no_features"])
        rows = [w["table_head"], "|---|---:|"]
        for name, _, kind in FEATURES:
            if name in values and values[name] not in (None, "not_available"):
                rows.append(f"| {w['feature_labels'][name]} | {_number(values[name], kind, w)} |")
        rows.append("")
        rows.append(w["features_note"])
        return ReportSection(section_id="feature_summary", title=w["features"], content="\n".join(rows))

    def _progress(self, data: ReportGenerationInput, values: dict) -> ReportSection:
        w = self.words
        if not data.previous_features:
            return ReportSection(section_id="progress_comparison", title=w["progress"], content=w["progress_needs_two"])
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
            path = " → ".join(_number(v, kind, w) for v in [*history, float(current)])
            delta = float(current) - history[-1]
            if abs(delta) < 1e-9:
                change = w["same"]
            else:
                change = f"{w['up'] if delta > 0 else w['down']} {_number(abs(delta), kind, w)} {w['from_last']}"
            lines.append(f"- {w['feature_labels'][name]}: {path} ({change})")
        if not lines:
            lines.append(w["no_comparable"])
        lines.append(w["progress_note"].format(n=len(series_sessions) + 1))
        return ReportSection(section_id="progress_comparison", title=w["progress"], content="\n".join(lines))

    def _cues(self, data: ReportGenerationInput) -> ReportSection:
        w = self.words
        if not data.review_cues:
            return ReportSection(section_id="ml_review_cues", title=w["cues"], content=w["no_cues"])
        lines = []
        for cue in data.review_cues:
            state = cue.review_state.status if cue.review_state else "unreviewed"
            line = f"- {w['cue_titles'].get(cue.cue_code, cue.title)}: {w['cue_states'].get(state, state)}"
            note = (cue.review_state.therapist_note or "").strip() if cue.review_state else ""
            if note:
                line += f" — {note}"
            if cue.evidence:
                line += " " + w["cue_points"].format(n=len(cue.evidence))
            lines.append(line)
        lines.append(w["cue_note"])
        return ReportSection(section_id="ml_review_cues", title=w["cues"], content="\n".join(lines))

    def _goals(self, data: ReportGenerationInput) -> ReportSection:
        w = self.words
        if data.therapy_goals:
            lines = [f"- {g.title}: {g.status}" + (f" — {g.target}" if g.target else "") for g in data.therapy_goals]
        else:
            lines = [w["no_goals"]]
        return ReportSection(section_id="therapy_focus_areas", title=w["goals"], content="\n".join(lines))


class EnglishClinicReportProvider(ThaiTemplateReportProvider):
    """The clinic report in English: the Thai report's sections, wording and rules."""

    language = "en"

    @property
    def provider_id(self) -> str:
        return "template_clinic_en"

    @property
    def provider_name(self) -> str:
        return "EnglishClinicReportProvider"
