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
    "analyzable_utterance_count": ("จำนวนประโยคที่วิเคราะห์ได้", "int", "ประโยคของเด็กที่มีคำให้นับ ตามเกณฑ์ KIDEVAL (Total_Utts)"),
    "mlu_utterance_count": ("จำนวนประโยคที่ใช้คิด MLU", "int", "ไม่รวมประโยคที่มี xxx/yyy/www ควรมีอย่างน้อย 50 ประโยค"),
    "total_word_count": ("จำนวนคำของเด็ก", "int", "นับตามกติกา CLAN: ไม่นับส่วนที่พูดซ้ำหรือแก้ [/] [//], คำเติม &-, xxx; ตัดคำไทยด้วย PyThaiNLP"),
    "number_of_different_words": ("จำนวนคำที่ไม่ซ้ำ (NDW)", "int", "คำต่างกันในคำพูดของเด็ก"),
    "ndw_100": ("คำไม่ซ้ำใน 100 คำแรก (NDW-100)", "int", "เทียบข้าม session ได้ ต้องมีคำอย่างน้อย 100 คำ"),
    "type_token_ratio": ("ความหลากหลายของคำ (TTR)", "ratio", "NDW หารด้วยจำนวนคำทั้งหมด ลดลงเมื่อตัวอย่างยาวขึ้น"),
    "mattr_50": ("TTR เฉลี่ยหน้าต่าง 50 คำ (MATTR)", "ratio", "ไม่ขึ้นกับความยาวตัวอย่าง ต้องมีคำอย่างน้อย 50 คำ"),
    "vocd_d": ("ความหลากหลายของคำ (VOCD D)", "float", "วิธีเดียวกับ CLAN VOCD ต้องมีคำอย่างน้อย 50 คำ"),
    "mean_length_of_utterance_words": ("ความยาวประโยคเฉลี่ย (MLU-w)", "float", "คำต่อประโยค ตามกติกา CLAN ไม่รวมประโยคที่มี xxx/yyy/www"),
    "mlu_words_sd": ("ส่วนเบี่ยงเบนมาตรฐานของ MLU", "float", "ความยาวประโยคแปรผันแค่ไหน สูตรเดียวกับ CLAN"),
    "mlu50_words": ("MLU50 (50 ประโยคแรก)", "float", "MLU จาก 50 ประโยคแรก ตาม KIDEVAL"),
    "mean_length_of_utterance_morphemes": ("ความยาวประโยคเฉลี่ย (MLU-m)", "float", "ต้องมี %mor tier"),
    "unintelligible_ratio": ("สัดส่วนประโยคที่ฟังไม่ออก", "percent", "ประโยคที่มี xxx/yyy หรือทำเครื่องหมายไว้"),
    "unknown_speaker_ratio": ("สัดส่วนประโยคที่ยังไม่ระบุผู้พูด", "percent", "ควรเป็น 0 ก่อนรับรอง"),
    "question_ratio": ("สัดส่วนคำถามของเด็ก", "percent", "ประโยคคำถามของเด็ก"),
    "repetition_marker_count": ("จำนวนการพูดซ้ำ", "int", "คำหรือวลีซ้ำติดกันในประโยคเดียว"),
    "coded_repetition_count": ("การพูดซ้ำที่ทำเครื่องหมาย [/]", "int", "นับจากรหัสที่นักบำบัดใส่ใน transcript"),
    "retracing_count": ("การพูดแก้ที่ทำเครื่องหมาย [//]", "int", "นับจากรหัสที่นักบำบัดใส่ใน transcript"),
    "word_error_count": ("คำผิดที่ทำเครื่องหมาย [*]", "int", "นับจากรหัสที่นักบำบัดใส่ใน transcript"),
    "utterance_error_count": ("ประโยคผิดที่ทำเครื่องหมาย", "int", "รหัส [+ gram], [+ jar], [+ es] และอื่น ๆ"),
    "thai_verbs_per_utterance": ("คำกริยาต่อประโยค (ทดลอง)", "float", "ติดป้ายชนิดคำด้วย PyThaiNLP ยังไม่ได้ตรวจกับเสียงเด็ก นับคุณศัพท์เป็นกริยาตามหลักภาษาไทย"),
    "thai_pronoun_count": ("สรรพนาม (ทดลอง)", "int", "รวมคำถาม เช่น อะไร ไหน ยังไม่ได้ตรวจกับเสียงเด็ก"),
    "thai_particle_count": ("คำลงท้าย ครับ/ค่ะ/นะ (ทดลอง)", "int", "ยังไม่ได้ตรวจกับเสียงเด็ก"),
    "thai_negator_count": ("คำปฏิเสธ (ทดลอง)", "int", "เช่น ไม่ ยังไม่ได้ตรวจกับเสียงเด็ก"),
    "pronoun_reversal_cue_count": ("cue การใช้สรรพนามสลับ", "int", "ต้องตรวจในบริบท"),
    "echolalia_cue_count": ("cue การพูดตาม (echolalia)", "int", "เด็กพูดซ้ำคำของผู้ใหญ่ที่เพิ่งพูด ต้องยืนยันทีละคู่"),
    "limited_reciprocal_question_cue": ("เด็กไม่ถามกลับ", "bool", "ไม่มีคำถามจากเด็กในตัวอย่างนี้"),
    "repetitive_phrase_cue": ("cue วลีซ้ำข้ามประโยค", "int", "วลีเดียวกันในหลายประโยค"),
    "atypical_response_cue": ("cue การตอบไม่ตรงคำถาม", "text", "ระบบตัดสินเองไม่ได้ ต้องดูบริบท"),
}

# Findings page: headline cards, then the full list in groups.
HEADLINE_FEATURES = {
    "mean_length_of_utterance_words": "ความยาวประโยค (MLU-w)",
    "number_of_different_words": "คำไม่ซ้ำ (NDW)",
    "type_token_ratio": "ความหลากหลายของคำ (TTR)",
    "mlu_utterance_count": "ประโยคที่ใช้คิด MLU",
}

FEATURE_GROUPS: list[tuple[str, list[str]]] = [
    ("ขนาดตัวอย่าง", [
        "child_utterance_count", "adult_utterance_count", "analyzable_utterance_count",
        "mlu_utterance_count", "total_word_count", "unintelligible_ratio", "unknown_speaker_ratio",
    ]),
    ("ความยาวประโยค", [
        "mean_length_of_utterance_words", "mlu_words_sd", "mlu50_words", "mean_length_of_utterance_morphemes",
    ]),
    ("คลังคำ", ["number_of_different_words", "ndw_100", "type_token_ratio", "mattr_50", "vocd_d"]),
    ("การโต้ตอบและ cue", [
        "question_ratio", "repetition_marker_count", "echolalia_cue_count", "pronoun_reversal_cue_count",
        "limited_reciprocal_question_cue", "repetitive_phrase_cue", "atypical_response_cue",
    ]),
    ("ชนิดคำภาษาไทย (ทดลอง)", [
        "thai_verbs_per_utterance", "thai_pronoun_count", "thai_particle_count", "thai_negator_count",
    ]),
    ("รหัส CHAT ที่นักบำบัดใส่", [
        "coded_repetition_count", "retracing_count", "word_error_count", "utterance_error_count",
    ]),
]
CODED_GROUP = "รหัส CHAT ที่นักบำบัดใส่"

# Measures that need a minimum sample: name → (what is counted, minimum, unit).
MINIMUM_SAMPLE = {
    "ndw_100": ("total_word_count", 100, "คำ"),
    "mattr_50": ("total_word_count", 50, "คำ"),
    "vocd_d": ("total_word_count", 50, "คำ"),
    "mlu_words_sd": ("mlu_utterance_count", 2, "ประโยค"),
}
RECOMMENDED_MLU_UTTERANCES = 50


def missing_reason(name: str, values: dict[str, Any]) -> str:
    """Why a measure has no value, in words a therapist can act on."""
    if name in MINIMUM_SAMPLE:
        source, minimum, unit = MINIMUM_SAMPLE[name]
        have = values.get(source)
        have_text = f" (มี {int(have)})" if isinstance(have, (int, float)) else ""
        return f"ต้องมี ≥ {minimum} {unit}{have_text}"
    if name == "mean_length_of_utterance_morphemes":
        return "ต้องมี %mor tier"
    if name.startswith("thai_"):
        return "ต้องมีคำพูดภาษาไทยของเด็ก"
    return "ไม่มีข้อมูล"


TREND_FEATURES = [
    "mean_length_of_utterance_words",
    "type_token_ratio",
    "mattr_50",
    "number_of_different_words",
    "ndw_100",
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


def clinic_speaker_text(status: dict) -> str:
    """One paragraph on whether the clinic's own child/adult model is in use, and why."""
    def pct(value: Any) -> str:
        return f"{value * 100:.0f}%" if isinstance(value, (int, float)) else "-"

    if not status.get("trained"):
        needed = []
        if status.get("sessions_needed"):
            needed.append(f"session ที่รับรองแล้วและมีไฟล์เสียงอีก {status['sessions_needed']} session")
        if status.get("children_needed"):
            needed.append(f"เด็กอีก {status['children_needed']} คน")
        text = "ยังเรียนไม่ได้: ต้องการ" + " และ".join(needed) if needed else "ยังไม่ได้เรียน กด ‘เรียนตอนนี้’"
    elif status.get("adopted"):
        text = (
            f"เรียนจาก {status.get('trained_sessions')} session (เด็ก {status.get('trained_children')} คน). "
            f"ทดสอบกับ session ของคลินิกโดยกันเด็กทีละคน: แยกถูกเฉลี่ยเด็กกับผู้ใหญ่ {pct(status.get('model_balanced'))} "
            f"เทียบโมเดลพื้นฐาน {pct(status.get('frame_balanced'))}"
        )
        text = ("ใช้อยู่ · " if status.get("enabled") else "ปิดอยู่ (ใช้โมเดลพื้นฐาน) · ") + text
    else:
        text = (
            f"ยังใช้โมเดลพื้นฐาน: โมเดลประจำคลินิกแยกถูกเฉลี่ยเด็กกับผู้ใหญ่ {pct(status.get('model_balanced'))} "
            f"ไม่ดีกว่าโมเดลพื้นฐาน ({pct(status.get('frame_balanced'))}) "
            f"จาก {status.get('trained_sessions')} session"
        )
    if status.get("trained") and status.get("stale"):
        text += f" · มี session ที่รับรองแล้ว {status.get('eligible_sessions')} session ยังไม่ได้เรียนรอบล่าสุด"
    return text
