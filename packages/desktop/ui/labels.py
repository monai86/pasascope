"""Thai wording for values the shared services return in English or as codes."""

from __future__ import annotations

from typing import Any

SPEAKERS = [
    ("CHI", "เด็ก (CHI)"),
    ("INV", "ผู้บำบัด (INV)"),
    ("MOT", "แม่ (MOT)"),
    ("FAT", "พ่อ (FAT)"),
    ("UNK", "ยังไม่ระบุ (UNK)"),
]
SPEAKER_LABELS = dict(SPEAKERS)

CONSENT = {
    "granted": ("ได้รับความยินยอม", "ok"),
    "pending": ("ยังไม่บันทึกความยินยอม", "attention"),
    "withdrawn": ("ถอนความยินยอมแล้ว", "danger"),
}

SESSION_STATUS = {
    "Draft": "ร่าง",
    "Needs Review": "รอตรวจ",
    "Reviewed": "ตรวจแล้ว",
    "Ready": "พร้อม",
    "Attested": "รับรองแล้ว",
    "Signed Off": "ลงนามแล้ว",
    "Processing": "กำลังประมวลผล",
    "Failed": "ล้มเหลว",
    "Withdrawn": "ถอนความยินยอม",
    "stale": "ต้องทำใหม่",
}

# Feature name → (Thai label, how to show the value, short explanation)
FEATURES: dict[str, tuple[str, str, str]] = {
    "child_utterance_count": ("จำนวนประโยคของเด็ก", "int", "นับเฉพาะผู้พูด CHI"),
    "adult_utterance_count": ("จำนวนประโยคของผู้ใหญ่", "int", "INV, MOT, FAT และผู้ใหญ่อื่น"),
    "total_word_count": ("จำนวนคำของเด็ก", "int", "ตัดคำภาษาไทยด้วย PyThaiNLP"),
    "number_of_different_words": ("จำนวนคำที่ไม่ซ้ำ (NDW)", "int", "คำต่างกันในคำพูดของเด็ก"),
    "type_token_ratio": ("ความหลากหลายของคำ (TTR)", "ratio", "NDW หารด้วยจำนวนคำทั้งหมด ขึ้นกับความยาวตัวอย่าง"),
    "mean_length_of_utterance_words": ("ความยาวประโยคเฉลี่ย (MLU-w)", "float", "คำต่อประโยคของเด็ก"),
    "mean_length_of_utterance_morphemes": ("ความยาวประโยคเฉลี่ย (MLU-m)", "float", "ต้องมี %mor tier"),
    "unintelligible_ratio": ("สัดส่วนประโยคที่ฟังไม่ออก", "percent", "ประโยคที่มี xxx/yyy หรือทำเครื่องหมายไว้"),
    "unknown_speaker_ratio": ("สัดส่วนประโยคที่ยังไม่ระบุผู้พูด", "percent", "ควรเป็น 0 ก่อนรับรอง"),
    "question_ratio": ("สัดส่วนคำถามของเด็ก", "percent", "ประโยคคำถามของเด็ก"),
    "repetition_marker_count": ("จำนวนการพูดซ้ำ", "int", "คำหรือวลีซ้ำติดกันในประโยคเดียว"),
    "pronoun_reversal_cue_count": ("cue การใช้สรรพนามสลับ", "int", "ต้องตรวจในบริบท"),
    "echolalia_cue_count": ("cue การพูดตาม (echolalia)", "int", "เด็กพูดซ้ำคำของผู้ใหญ่ที่เพิ่งพูด ต้องยืนยันทีละคู่"),
    "limited_reciprocal_question_cue": ("เด็กไม่ถามกลับ", "bool", "ไม่มีคำถามจากเด็กในตัวอย่างนี้"),
    "repetitive_phrase_cue": ("cue วลีซ้ำข้ามประโยค", "int", "วลีเดียวกันในหลายประโยค"),
    "atypical_response_cue": ("cue การตอบไม่ตรงคำถาม", "text", "ระบบตัดสินเองไม่ได้ ต้องดูบริบท"),
}

TREND_FEATURES = [
    "mean_length_of_utterance_words",
    "type_token_ratio",
    "number_of_different_words",
    "child_utterance_count",
]

CUE_SEVERITY = {
    "info": ("ข้อมูล", "primary"),
    "review": ("ควรตรวจ", "attention"),
    "caution": ("ระวัง", "danger"),
}

# Cue code → (title, what the rule saw, what to check next)
CUES: dict[str, tuple[str, str, str]] = {
    "insufficient_sample_size": (
        "ตัวอย่างภาษาสั้นเกินไป",
        "เด็กพูดน้อยกว่า 3 ประโยค ระบบจึงไม่สร้าง cue อื่น",
        "เก็บตัวอย่างภาษาที่ยาวขึ้นและเป็นตัวแทนของเด็ก",
    ),
    "adult_dominant_sample": (
        "ผู้ใหญ่พูดมากกว่าเด็ก",
        "จำนวนประโยคของผู้ใหญ่มากกว่าของเด็กในตัวอย่างนี้",
        "ดูว่ากิจกรรมเปิดโอกาสให้เด็กพูดพอหรือไม่",
    ),
    "high_unclear_ratio": (
        "มีประโยคที่ฟังไม่ออกมาก",
        "สัดส่วนประโยคที่ฟังไม่ออกเกินเกณฑ์ทางวิศวกรรม 20% (ไม่ใช่เกณฑ์ทางคลินิก)",
        "ฟังช่วงที่ฟังไม่ออกซ้ำเทียบกับเสียงก่อนแปลผล",
    ),
    "high_repetition_cue": (
        "พบการพูดซ้ำ",
        "กฎจาก transcript พบคำหรือวลีซ้ำ",
        "ดูการพูดซ้ำในบริบทของบทสนทนา",
    ),
    "echolalia_review_cue": (
        "อาจเป็นการพูดตาม (echolalia)",
        "เด็กพูดคำของผู้ใหญ่ที่เพิ่งพูดซ้ำทั้งหมดหรือบางส่วน คำตอบปกติที่ใช้คำเดียวกันก็ถูกจับได้",
        "ตรวจทีละคู่ประโยคด้านล่างว่าเป็นการพูดตามจริงหรือเป็นคำตอบ",
    ),
    "pronoun_reversal_review_cue": (
        "อาจใช้สรรพนามสลับ",
        "กฎจาก transcript พบสรรพนามที่อาจใช้สลับบุคคล",
        "ตรวจสรรพนามแต่ละจุดในบริบท",
    ),
}

CUE_STATE = {
    "unreviewed": "ยังไม่ตรวจ",
    "acknowledged": "ยืนยันแล้ว",
    "dismissed": "ปัดตก",
}

ECHO_CATEGORY = {
    "immediate_verbatim": "พูดตามทันทีทุกคำ",
    "mitigated": "พูดตามบางส่วน",
}


def feature_value_text(name: str, value: Any, unit: str = "") -> str:
    if value is None or value == "not_available":
        return "—"
    kind = FEATURES.get(name, ("", "", ""))[1]
    if isinstance(value, bool) or kind == "bool":
        return "ใช่" if value in (True, "true", "True") else "ไม่ใช่"
    if isinstance(value, (int, float)):
        if kind == "percent":
            return f"{float(value) * 100:.0f}%"
        if kind == "int":
            return f"{int(round(float(value)))}"
        if kind == "ratio":
            return f"{float(value):.2f}"
        return f"{float(value):.2f}".rstrip("0").rstrip(".")
    if value == "needs_context":
        return "ต้องดูบริบท"
    return str(value)


def status_text(status: Any) -> str:
    value = status.value if hasattr(status, "value") else str(status)
    return SESSION_STATUS.get(value, value)


def age_text(months: int) -> str:
    years, rem = divmod(int(months), 12)
    if years and rem:
        return f"{years} ปี {rem} เดือน"
    if years:
        return f"{years} ปี"
    return f"{rem} เดือน"
