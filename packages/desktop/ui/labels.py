"""Wording for values the shared services return in English or as codes, in English and Thai."""

from __future__ import annotations

from typing import Any

from packages.desktop.core.i18n import Text as T, TrDict, TrList, tr

SPEAKERS = TrList([
    ("CHI", T("เด็ก (CHI)", "Child (CHI)")),
    ("INV", T("ผู้บำบัด (INV)", "Therapist (INV)")),
    ("MOT", T("แม่ (MOT)", "Mother (MOT)")),
    ("FAT", T("พ่อ (FAT)", "Father (FAT)")),
    ("UNK", T("ยังไม่ระบุ (UNK)", "Not set (UNK)")),
])
SPEAKER_LABELS = TrDict(dict(list.__iter__(SPEAKERS)))

CONSENT = TrDict({
    "granted": (T("ได้รับความยินยอม", "Consent given"), "ok"),
    "pending": (T("ยังไม่บันทึกความยินยอม", "No consent recorded"), "attention"),
    "withdrawn": (T("ถอนความยินยอมแล้ว", "Consent withdrawn"), "danger"),
})

SESSION_STATUS = TrDict({
    "Draft": T("ร่าง", "Draft"),
    "Needs Review": T("รอตรวจ", "To review"),
    "Reviewed": T("ตรวจแล้ว", "Reviewed"),
    "Ready": T("พร้อม", "Ready"),
    "Attested": T("รับรองแล้ว", "Attested"),
    "Signed Off": T("ลงนามแล้ว", "Signed"),
    "Processing": T("กำลังประมวลผล", "Processing"),
    "Failed": T("ล้มเหลว", "Failed"),
    "Withdrawn": T("ถอนความยินยอม", "Withdrawn"),
    "stale": T("ต้องทำใหม่", "Out of date"),
})

# The feature schema the app's analysis writes; older feature sets ask to be analysed again.
CURRENT_SCHEMA = "features-basic-v3"

# Feature name → (label, how to show the value, what it counts)
FEATURES = TrDict({
    "child_utterance_count": (T("จำนวนประโยคของเด็ก", "Child utterances"), "int", T("นับเฉพาะผู้พูด CHI", "Lines spoken by CHI")),
    "adult_utterance_count": (T("จำนวนประโยคของผู้ใหญ่", "Adult utterances"), "int", T("INV, MOT, FAT และผู้ใหญ่อื่น", "INV, MOT, FAT and other adults")),
    "analyzable_utterance_count": (T("จำนวนประโยคที่วิเคราะห์ได้", "Analysable utterances"), "int",
                                   T("ประโยคของเด็กที่มีคำให้นับ ตามเกณฑ์ KIDEVAL (Total_Utts)", "Child utterances with countable words (KIDEVAL Total_Utts)")),
    "mlu_utterance_count": (T("จำนวนประโยคที่ใช้คิด MLU", "Utterances in MLU"), "int",
                            T("ไม่รวมประโยคที่มี xxx/yyy/www ควรมีอย่างน้อย 50 ประโยค", "Excludes lines with xxx/yyy/www; 50 or more is recommended")),
    "total_word_count": (T("จำนวนคำของเด็ก", "Child words"), "int",
                         T("นับตามกติกา CLAN: ไม่นับส่วนที่พูดซ้ำหรือแก้ [/] [//], คำเติม &-, xxx; ตัดคำไทยด้วย PyThaiNLP",
                           "CLAN rules: repetitions and retracings [/] [//], fillers &- and xxx are not counted; Thai is word-segmented with PyThaiNLP")),
    "number_of_different_words": (T("จำนวนคำที่ไม่ซ้ำ (NDW)", "Different words (NDW)"), "int", T("คำต่างกันในคำพูดของเด็ก", "Distinct words the child used")),
    "ndw_100": (T("คำไม่ซ้ำใน 100 คำแรก (NDW-100)", "NDW in the first 100 words"), "int",
                T("เทียบข้าม session ได้ ต้องมีคำอย่างน้อย 100 คำ", "Comparable across sessions; needs 100 words")),
    "type_token_ratio": (T("ความหลากหลายของคำ (TTR)", "Type-token ratio (TTR)"), "ratio",
                         T("NDW หารด้วยจำนวนคำทั้งหมด ลดลงเมื่อตัวอย่างยาวขึ้น", "NDW over all words; falls as samples get longer")),
    "mattr_50": (T("TTR เฉลี่ยหน้าต่าง 50 คำ (MATTR)", "Moving-average TTR (MATTR-50)"), "ratio",
                 T("ไม่ขึ้นกับความยาวตัวอย่าง ต้องมีคำอย่างน้อย 50 คำ", "Not tied to sample length; needs 50 words")),
    "vocd_d": (T("ความหลากหลายของคำ (VOCD D)", "Lexical diversity (VOCD D)"), "float",
               T("วิธีเดียวกับ CLAN VOCD ต้องมีคำอย่างน้อย 50 คำ", "Same method as CLAN VOCD; needs 50 words")),
    "mean_length_of_utterance_words": (T("ความยาวประโยคเฉลี่ย (MLU-w)", "Mean length of utterance (MLU-w)"), "float",
                                       T("คำต่อประโยค ตามกติกา CLAN ไม่รวมประโยคที่มี xxx/yyy/www", "Words per utterance, CLAN rules, without lines containing xxx/yyy/www")),
    "mlu_words_sd": (T("ส่วนเบี่ยงเบนมาตรฐานของ MLU", "MLU standard deviation"), "float",
                     T("ความยาวประโยคแปรผันแค่ไหน สูตรเดียวกับ CLAN", "How much utterance length varies; CLAN formula")),
    "mlu50_words": (T("MLU50 (50 ประโยคแรก)", "MLU50 (first 50 utterances)"), "float", T("MLU จาก 50 ประโยคแรก ตาม KIDEVAL", "MLU of the first 50 utterances, as in KIDEVAL")),
    "mean_length_of_utterance_morphemes": (T("ความยาวประโยคเฉลี่ย (MLU-m)", "MLU in morphemes (MLU-m)"), "float", T("ต้องมี %mor tier", "Needs a %mor tier")),
    "unintelligible_ratio": (T("สัดส่วนประโยคที่ฟังไม่ออก", "Unintelligible utterances"), "percent",
                             T("ประโยคที่มี xxx/yyy หรือทำเครื่องหมายไว้", "Lines with xxx/yyy or marked unclear")),
    "unknown_speaker_ratio": (T("สัดส่วนประโยคที่ยังไม่ระบุผู้พูด", "Lines without a speaker"), "percent", T("ควรเป็น 0 ก่อนรับรอง", "Should be 0 before attesting")),
    "question_ratio": (T("สัดส่วนคำถามของเด็ก", "Child questions"), "percent", T("ประโยคคำถามของเด็ก", "Share of the child's utterances that are questions")),
    "repetition_marker_count": (T("จำนวนการพูดซ้ำ", "Repetitions"), "int", T("คำหรือวลีซ้ำติดกันในประโยคเดียว", "Word or phrase said twice in a row in one utterance")),
    "coded_repetition_count": (T("การพูดซ้ำที่ทำเครื่องหมาย [/]", "Coded repetitions [/]"), "int", T("นับจากรหัสที่นักบำบัดใส่ใน transcript", "From codes in the transcript")),
    "retracing_count": (T("การพูดแก้ที่ทำเครื่องหมาย [//]", "Coded retracings [//]"), "int", T("นับจากรหัสที่นักบำบัดใส่ใน transcript", "From codes in the transcript")),
    "word_error_count": (T("คำผิดที่ทำเครื่องหมาย [*]", "Coded word errors [*]"), "int", T("นับจากรหัสที่นักบำบัดใส่ใน transcript", "From codes in the transcript")),
    "utterance_error_count": (T("ประโยคผิดที่ทำเครื่องหมาย", "Coded utterance errors"), "int",
                              T("รหัส [+ gram], [+ jar], [+ es] และอื่น ๆ", "[+ gram], [+ jar], [+ es] and similar codes")),
    "thai_verbs_per_utterance": (T("คำกริยาต่อประโยค (ทดลอง)", "Verbs per utterance (experimental)"), "float",
                                 T("ติดป้ายชนิดคำด้วย PyThaiNLP ยังไม่ได้ตรวจกับเสียงเด็ก นับคุณศัพท์เป็นกริยาตามหลักภาษาไทย",
                                   "Thai word classes from PyThaiNLP, not checked on child speech; Thai adjectives count as verbs")),
    "thai_pronoun_count": (T("สรรพนาม (ทดลอง)", "Pronouns (experimental)"), "int",
                           T("รวมคำถาม เช่น อะไร ไหน ยังไม่ได้ตรวจกับเสียงเด็ก", "Includes question words; not checked on child speech")),
    "thai_particle_count": (T("คำลงท้าย ครับ/ค่ะ/นะ (ทดลอง)", "Sentence particles (experimental)"), "int", T("ยังไม่ได้ตรวจกับเสียงเด็ก", "Not checked on child speech")),
    "thai_negator_count": (T("คำปฏิเสธ (ทดลอง)", "Negators (experimental)"), "int", T("เช่น ไม่ ยังไม่ได้ตรวจกับเสียงเด็ก", "Such as ไม่; not checked on child speech")),
    "child_response_rate": (T("อัตราที่เด็กตอบต่อจากผู้ใหญ่", "Child response rate"), "percent",
                            T("ประโยคของผู้ใหญ่ที่เด็กพูดต่อทันที หารด้วยประโยคของผู้ใหญ่ทั้งหมด",
                              "Share of adult utterances the child follows straight away")),
    "child_response_count": (T("จำนวนครั้งที่เด็กตอบต่อจากผู้ใหญ่", "Child responses to adults"), "int",
                             T("นับคู่ (ผู้ใหญ่พูด → เด็กพูดต่อ) ขึ้นกับความยาวตัวอย่าง", "Adult line then child line; grows with sample length")),
    "mlt_ratio": (T("ความยาวรอบพูดของเด็กเทียบผู้ใหญ่ (MLT ratio)", "Turn length ratio, child / adult (MLT)"), "ratio",
                  T("คำต่อรอบของเด็กหารด้วยคำต่อรอบของผู้ใหญ่ ไปด้วยกันกับ MLU", "Child words per turn over the adults'; moves with MLU")),
    "pronoun_reversal_cue_count": (T("cue การใช้สรรพนามสลับ", "Pronoun reversal cues"), "int", T("ต้องตรวจในบริบท", "Check each in context")),
    "echolalia_cue_count": (T("cue การพูดตาม (echolalia)", "Echolalia cues"), "int",
                            T("เด็กพูดซ้ำคำของผู้ใหญ่ที่เพิ่งพูด ต้องยืนยันทีละคู่", "The child repeats what an adult just said; confirm each pair")),
    "limited_reciprocal_question_cue": (T("เด็กไม่ถามกลับ", "No questions from the child"), "bool", T("ไม่มีคำถามจากเด็กในตัวอย่างนี้", "The child asked no questions in this sample")),
    "repetitive_phrase_cue": (T("cue วลีซ้ำข้ามประโยค", "Repeated phrase cues"), "int", T("วลีเดียวกันในหลายประโยค", "The same phrase across utterances")),
    "atypical_response_cue": (T("cue การตอบไม่ตรงคำถาม", "Off-topic response cue"), "text", T("ระบบตัดสินเองไม่ได้ ต้องดูบริบท", "Needs the therapist's judgement in context")),
})

HEADLINE_FEATURES = TrDict({
    "mean_length_of_utterance_words": T("ความยาวประโยค (MLU-w)", "MLU-w"),
    "number_of_different_words": T("คำไม่ซ้ำ (NDW)", "Different words (NDW)"),
    "child_response_rate": T("เด็กตอบต่อจากผู้ใหญ่", "Child response rate"),
    "mlu_utterance_count": T("ประโยคที่ใช้คิด MLU", "Utterances in MLU"),
})

# The measures a therapist reads first (docs/FEATURE_GUIDE.md explains the choice);
# the rest appear with "Show all measures".
CORE_FEATURES = {
    "child_utterance_count", "mlu_utterance_count", "total_word_count", "unintelligible_ratio",
    "mean_length_of_utterance_words",
    "number_of_different_words", "ndw_100", "mattr_50", "vocd_d",
    "child_response_rate",
    "echolalia_cue_count",
}

FEATURE_GROUPS = TrList([
    (T("ขนาดตัวอย่าง", "Sample size"), [
        "child_utterance_count", "mlu_utterance_count", "total_word_count", "unintelligible_ratio",
        "adult_utterance_count", "analyzable_utterance_count", "unknown_speaker_ratio",
    ]),
    (T("ความยาวประโยค", "Utterance length"), [
        "mean_length_of_utterance_words", "mlu50_words", "mlu_words_sd", "mean_length_of_utterance_morphemes",
    ]),
    (T("คลังคำ", "Vocabulary"), ["number_of_different_words", "ndw_100", "mattr_50", "vocd_d", "type_token_ratio"]),
    (T("การผลัดกันพูด", "Turn-taking"), ["child_response_rate", "child_response_count", "mlt_ratio"]),
    (T("cue ที่ควรตรวจ", "Review cues"), [
        "echolalia_cue_count", "pronoun_reversal_cue_count", "question_ratio", "limited_reciprocal_question_cue",
        "repetition_marker_count", "repetitive_phrase_cue", "atypical_response_cue",
    ]),
    (T("ชนิดคำภาษาไทย (ทดลอง)", "Thai word classes (experimental)"), [
        "thai_verbs_per_utterance", "thai_pronoun_count", "thai_particle_count", "thai_negator_count",
    ]),
    (T("รหัส CHAT ที่นักบำบัดใส่", "CHAT codes added by the therapist"), [
        "coded_repetition_count", "retracing_count", "word_error_count", "utterance_error_count",
    ]),
])
CODED_GROUP_FEATURES = {"coded_repetition_count", "retracing_count", "word_error_count", "utterance_error_count"}

# Measures that need a minimum sample: name → (what is counted, minimum, unit).
MINIMUM_SAMPLE = TrDict({
    "ndw_100": ("total_word_count", 100, T("คำ", "words")),
    "mattr_50": ("total_word_count", 50, T("คำ", "words")),
    "vocd_d": ("total_word_count", 50, T("คำ", "words")),
    "mlu_words_sd": ("mlu_utterance_count", 2, T("ประโยค", "utterances")),
})
RECOMMENDED_MLU_UTTERANCES = 50


def missing_reason(name: str, values: dict[str, Any]) -> str:
    """Why a measure has no value, in words a therapist can act on."""
    if name in MINIMUM_SAMPLE:
        source, minimum, unit = MINIMUM_SAMPLE[name]
        have = values.get(source)
        have_text = tr(f" (มี {int(have)})", f" (has {int(have)})") if isinstance(have, (int, float)) else ""
        return tr(f"ต้องมี ≥ {minimum} {unit}{have_text}", f"Needs {minimum}+ {unit}{have_text}")
    if name == "mean_length_of_utterance_morphemes":
        return tr("ต้องมี %mor tier", "Needs a %mor tier")
    if name.startswith("thai_"):
        return tr("ต้องมีคำพูดภาษาไทยของเด็ก", "Needs Thai speech from the child")
    return tr("ไม่มีข้อมูล", "No data")


TREND_FEATURES = [
    "mean_length_of_utterance_words",
    "child_response_rate",
    "type_token_ratio",
    "mattr_50",
    "number_of_different_words",
    "ndw_100",
    "child_utterance_count",
]

CUE_SEVERITY = TrDict({
    "info": (T("ข้อมูล", "Note"), "primary"),
    "review": (T("ควรตรวจ", "Review"), "attention"),
    "caution": (T("ระวัง", "Caution"), "danger"),
})

# Cue code → (title, what the rule saw, what to check next)
CUES = TrDict({
    "insufficient_sample_size": (
        T("ตัวอย่างภาษาสั้นเกินไป", "Sample too short"),
        T("เด็กพูดน้อยกว่า 3 ประโยค ระบบจึงไม่สร้าง cue อื่น", "Fewer than 3 child utterances, so no other cues were raised."),
        T("เก็บตัวอย่างภาษาที่ยาวขึ้นและเป็นตัวแทนของเด็ก", "Collect a longer, more representative sample."),
    ),
    "adult_dominant_sample": (
        T("ผู้ใหญ่พูดมากกว่าเด็ก", "Adults talk more than the child"),
        T("จำนวนประโยคของผู้ใหญ่มากกว่าของเด็กในตัวอย่างนี้", "There are more adult than child utterances."),
        T("ดูว่ากิจกรรมเปิดโอกาสให้เด็กพูดพอหรือไม่", "Check whether the activity gave the child room to talk."),
    ),
    "high_unclear_ratio": (
        T("มีประโยคที่ฟังไม่ออกมาก", "Many unintelligible lines"),
        T("สัดส่วนประโยคที่ฟังไม่ออกเกินเกณฑ์ทางวิศวกรรม 20% (ไม่ใช่เกณฑ์ทางคลินิก)", "More than 20% unintelligible (an engineering limit, not a clinical one)."),
        T("ฟังช่วงที่ฟังไม่ออกซ้ำเทียบกับเสียงก่อนแปลผล", "Listen to those lines again before reading the measures."),
    ),
    "high_repetition_cue": (
        T("พบการพูดซ้ำ", "Repetitions found"),
        T("กฎจาก transcript พบคำหรือวลีซ้ำ", "The transcript has repeated words or phrases."),
        T("ดูการพูดซ้ำในบริบทของบทสนทนา", "Look at each repetition in context."),
    ),
    "echolalia_review_cue": (
        T("อาจเป็นการพูดตาม (echolalia)", "Possible echolalia"),
        T("เด็กพูดคำของผู้ใหญ่ที่เพิ่งพูดซ้ำทั้งหมดหรือบางส่วน คำตอบปกติที่ใช้คำเดียวกันก็ถูกจับได้",
          "The child repeats all or part of what an adult just said. Ordinary answers that reuse the adult's words are caught too."),
        T("ตรวจทีละคู่ประโยคด้านล่างว่าเป็นการพูดตามจริงหรือเป็นคำตอบ", "Decide for each pair below: echo or answer."),
    ),
    "pronoun_reversal_review_cue": (
        T("อาจใช้สรรพนามสลับ", "Possible pronoun reversal"),
        T("กฎจาก transcript พบสรรพนามที่อาจใช้สลับบุคคล", "A pronoun may refer to the wrong person."),
        T("ตรวจสรรพนามแต่ละจุดในบริบท", "Check each pronoun in context."),
    ),
})

CUE_STATE = TrDict({
    "unreviewed": T("ยังไม่ตรวจ", "Not reviewed"),
    "acknowledged": T("ยืนยันแล้ว", "Confirmed"),
    "dismissed": T("ปัดตก", "Dismissed"),
})

ECHO_CATEGORY = TrDict({
    "immediate_verbatim": T("พูดตามทันทีทุกคำ", "Immediate, word for word"),
    "mitigated": T("พูดตามบางส่วน", "Partial"),
})


def feature_value_text(name: str, value: Any, unit: str = "") -> str:
    if value is None or value == "not_available":
        return "—"
    kind = FEATURES.get(name, ("", "", ""))[1]
    if isinstance(value, bool) or kind == "bool":
        return tr("ใช่", "Yes") if value in (True, "true", "True") else tr("ไม่ใช่", "No")
    if isinstance(value, (int, float)):
        if kind == "percent":
            return f"{float(value) * 100:.0f}%"
        if kind == "int":
            return f"{int(round(float(value)))}"
        if kind == "ratio":
            return f"{float(value):.2f}"
        return f"{float(value):.2f}".rstrip("0").rstrip(".")
    if value == "needs_context":
        return tr("ต้องดูบริบท", "Needs context")
    return str(value)


def status_text(status: Any) -> str:
    value = status.value if hasattr(status, "value") else str(status)
    return SESSION_STATUS.get(value, value)


def age_text(months: int) -> str:
    years, rem = divmod(int(months), 12)
    if years and rem:
        return tr(f"{years} ปี {rem} เดือน", f"{years} y {rem} m")
    if years:
        return tr(f"{years} ปี", f"{years} years")
    return tr(f"{rem} เดือน", f"{rem} months")


def clinic_speaker_text(status: dict) -> str:
    """One paragraph on whether the clinic's own child/adult model is in use, and why."""
    def pct(value: Any) -> str:
        return f"{value * 100:.0f}%" if isinstance(value, (int, float)) else "-"

    sessions, children = status.get("trained_sessions"), status.get("trained_children")
    model, frame = pct(status.get("model_balanced")), pct(status.get("frame_balanced"))
    if not status.get("trained"):
        needed = []
        if status.get("sessions_needed"):
            n = status["sessions_needed"]
            needed.append(tr(f"session ที่รับรองแล้วและมีไฟล์เสียงอีก {n} session", f"{n} more attested sessions with recordings"))
        if status.get("children_needed"):
            n = status["children_needed"]
            needed.append(tr(f"เด็กอีก {n} คน", f"{n} more children"))
        if needed:
            text = tr("ยังเรียนไม่ได้: ต้องการ", "Not trained yet. Needs ") + tr(" และ", " and ").join(needed) + tr("", ".")
        else:
            text = tr("ยังไม่ได้เรียน กด ‘เรียนตอนนี้’", "Not trained yet. Choose Train now.")
    elif status.get("adopted"):
        text = tr(
            f"เรียนจาก {sessions} session (เด็ก {children} คน) ทดสอบกับ session ของคลินิกโดยกันเด็กทีละคน: "
            f"แยกถูกเฉลี่ยเด็กกับผู้ใหญ่ {model} เทียบโมเดลพื้นฐาน {frame}",
            f"Learned from {sessions} sessions ({children} children). Tested on this clinic's sessions, one child held out "
            f"at a time: balanced accuracy {model} against {frame} for the base model.",
        )
        text = (tr("ใช้อยู่ ", "In use. ") if status.get("enabled") else tr("ปิดอยู่ (ใช้โมเดลพื้นฐาน) ", "Turned off (base model in use). ")) + text
    else:
        text = tr(
            f"ยังใช้โมเดลพื้นฐาน: โมเดลประจำคลินิกแยกถูกเฉลี่ยเด็กกับผู้ใหญ่ {model} ไม่ดีกว่าโมเดลพื้นฐาน ({frame}) จาก {sessions} session",
            f"Base model still in use: the clinic model reached {model} balanced accuracy, no better than the base model ({frame}), "
            f"on {sessions} sessions.",
        )
    if status.get("trained") and status.get("stale"):
        n = status.get("eligible_sessions")
        text += tr(f" มี session ที่รับรองแล้ว {n} session ยังไม่ได้เรียนรอบล่าสุด", f" {n} attested sessions are newer than the last training.")
    return text
