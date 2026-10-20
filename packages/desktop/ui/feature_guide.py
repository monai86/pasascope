"""What each language measure is and how it helps, for the Knowledge page.

One entry per measure the app computes: what it counts, what it tells the
therapist, what to watch for, and whether it is a main, supporting or
background measure (``labels.CORE_FEATURES`` holds the main ones). The
evidence behind the choice is in docs/FEATURE_GUIDE.md.
"""

from __future__ import annotations

import html

from packages.desktop.core.i18n import tr
from packages.desktop.ui import labels, theme

MAIN, SUPPORT, BACKGROUND = "main", "support", "background"

# name → (tier, (what, how it helps, watch for) in Thai, the same in English)
GUIDE: dict[str, tuple[str, tuple[str, str, str], tuple[str, str, str]]] = {
    "child_utterance_count": (MAIN, (
        "จำนวนบรรทัดที่เด็ก (CHI) พูดใน transcript",
        "บอกว่าตัวอย่างพอให้เชื่อค่าอื่นหรือไม่ ตัวอย่างสั้นทำให้ MLU และ NDW แกว่ง",
        "นับทุกบรรทัดของเด็ก รวมบรรทัดที่ฟังไม่ออก ดูคู่กับจำนวนประโยคที่ใช้คิด MLU",
    ), (
        "Lines the child (CHI) says in the transcript.",
        "Tells you whether the sample is large enough to trust the other values; short samples make MLU and NDW jump about.",
        "Counts every child line, unintelligible ones included. Read it with the utterances used for MLU.",
    )),
    "mlu_utterance_count": (MAIN, (
        "ประโยคของเด็กที่ใช้คิด MLU ตามกติกา CLAN (ไม่รวมบรรทัดที่มี xxx/yyy/www)",
        "เกณฑ์ที่ใช้กันคือ 50 ประโยคขึ้นไป ต่ำกว่านี้ให้ระวังเมื่อเทียบข้าม session",
        "ถ้าต่ำมาก ลองอัดตัวอย่างให้ยาวขึ้นหรือรวมกิจกรรมหลายแบบ",
    ), (
        "Child utterances that count towards MLU under CLAN's rules (lines with xxx/yyy/www left out).",
        "The usual minimum is 50; below that, be careful comparing sessions.",
        "If it is very low, record a longer sample or more than one activity.",
    )),
    "total_word_count": (MAIN, (
        "จำนวนคำที่เด็กพูด นับตามกติกา CLAN ไม่นับคำที่พูดซ้ำหรือแก้ [/] [//] และคำเติม",
        "เป็นฐานของตัวชี้วัดคลังคำ NDW-100 ต้องมี 100 คำ MATTR และ VOCD ต้องมี 50 คำ",
        "คำไทยตัดด้วย PyThaiNLP (ตรงกับการตัดของมนุษย์ราว 90% ของขอบคำ) ตรวจคำที่ตัดผิดในหน้า transcript",
    ), (
        "Words the child says, counted with CLAN's rules: repetitions and retracings [/] [//] and fillers are not counted.",
        "The base for the vocabulary measures: NDW-100 needs 100 words, MATTR and VOCD need 50.",
        "Thai is segmented with PyThaiNLP (about 90% of word boundaries agree with a person); check odd splits in the transcript.",
    )),
    "unintelligible_ratio": (MAIN, (
        "สัดส่วนประโยคที่มี xxx/yyy หรือทำเครื่องหมายว่าฟังไม่ออก",
        "บอกความชัดของการพูดและคุณภาพของตัวอย่าง ค่าสูงทำให้ตัวชี้วัดอื่นต่ำกว่าความจริง",
        "เสียงรบกวนหรือไมค์ไกลก็ทำให้สูงได้ ไม่ได้มาจากเด็กเสมอไป",
    ), (
        "Share of utterances with xxx/yyy or marked unclear.",
        "Speaks to intelligibility and to sample quality; a high value pulls the other measures down.",
        "Noise or a distant microphone raises it too, not only the child's speech.",
    )),
    "mean_length_of_utterance_words": (MAIN, (
        "ความยาวประโยคเฉลี่ยเป็นคำ (MLU-w) ตามกติกา CLAN",
        "บอกระดับภาษาและใช้ติดตามพัฒนาการ ตรงกับแนวทางให้ประเมินระดับก่อน แล้วขยายจากคำเป็นวลีเป็นประโยคทีละขั้น "
        "(ศิริราชเวชสาร 2566) ข้อมูล TalkBank อายุ 4 ปี ค่ามัธยฐาน TD 4.5, LT 3.4, ASD 2.1",
        "ภาษาไทยขึ้นกับการตัดคำ ค่าที่ได้เทียบกับเกณฑ์ภาษาอังกฤษตรง ๆ ไม่ได้ ใช้ดูการเปลี่ยนของเด็กคนเดียวกันดีที่สุด",
    ), (
        "Mean length of utterance in words (MLU-w), CLAN's rules.",
        "Shows the child's language level and tracks progress, in line with assessing the level first and then expanding "
        "from words to phrases to sentences (Siriraj Medical Bulletin 2023). TalkBank medians at age 4: TD 4.5, LT 3.4, ASD 2.1.",
        "Thai values depend on word segmentation and cannot be compared with English norms; best for change in one child.",
    )),
    "number_of_different_words": (MAIN, (
        "จำนวนคำที่ไม่ซ้ำกันที่เด็กใช้ (NDW)",
        "บอกความกว้างของคลังคำ บทความศิริราชระบุว่าเด็กออทิสติกมักใช้ภาษาได้หลากหลายน้อย",
        "ขึ้นกับความยาวตัวอย่าง เทียบข้าม session ให้ใช้ NDW-100 หรือ MATTR",
    ), (
        "Different words the child used (NDW).",
        "Shows the breadth of vocabulary; the Siriraj review notes that autistic children often use a narrow range of language.",
        "Grows with sample length; to compare sessions use NDW-100 or MATTR.",
    )),
    "ndw_100": (MAIN, (
        "คำไม่ซ้ำใน 100 คำแรก",
        "เทียบคลังคำข้าม session ได้ เพราะใช้จำนวนคำเท่ากันทุกครั้ง",
        "ต้องมีคำของเด็กอย่างน้อย 100 คำ",
    ), (
        "Different words in the first 100 words.",
        "Compares vocabulary across sessions, because every session uses the same number of words.",
        "Needs at least 100 child words.",
    )),
    "mattr_50": (MAIN, (
        "TTR เฉลี่ยของทุกหน้าต่าง 50 คำ (MATTR)",
        "ความหลากหลายของคำที่ไม่ขึ้นกับความยาวตัวอย่าง ใช้แทน TTR",
        "ต้องมีอย่างน้อย 50 คำ",
    ), (
        "Mean TTR over every 50-word window (MATTR).",
        "Lexical diversity that does not depend on sample length; use it instead of TTR.",
        "Needs at least 50 words.",
    )),
    "vocd_d": (MAIN, (
        "ดัชนีความหลากหลายของคำ D คำนวณแบบ CLAN VOCD",
        "มาตรฐานที่งานวิจัยใช้ ค่าของแอปตรงกับ CLAN (r = 0.9997 บน 1,755 transcript)",
        "สุ่มตัวอย่างคำ ค่าอาจต่างจาก CLAN เล็กน้อย ต้องมีอย่างน้อย 50 คำ",
    ), (
        "Lexical diversity index D, computed as CLAN VOCD does.",
        "The research standard; the app's values match CLAN (r = 0.9997 on 1,755 transcripts).",
        "It samples words at random, so it can differ slightly from CLAN. Needs at least 50 words.",
    )),
    "child_response_rate": (MAIN, (
        "สัดส่วนประโยคของผู้ใหญ่ที่เด็กพูดต่อทันที",
        "วัดการผลัดกันพูด บทความศิริราชระบุว่าเป้าหมายการฝึกสนทนาวัดจากวงรอบการสนทนาที่สมบูรณ์ ไม่ใช่ความยาวประโยค "
        "ค่านี้ให้ข้อมูลที่ MLU ไม่ได้บอก (สัมพันธ์กับ MLU เพียง ρ = 0.18) ใน TalkBank เด็ก TD 3–5 ปีอยู่ราว 0.55–0.57",
        "นับแค่ว่าเด็กพูดต่อ ไม่ได้ดูว่าตอบตรงคำถาม ขึ้นกับกิจกรรม เช่น เล่านิทานผู้ใหญ่จะพูดหลายประโยคติดกัน",
    ), (
        "Share of adult utterances the child follows straight away.",
        "Measures turn-taking. The Siriraj review measures conversation practice by complete exchanges, not sentence length. "
        "It adds what MLU does not show (ρ = 0.18 with MLU); typical children aged 3–5 in TalkBank sit around 0.55–0.57.",
        "Counts only that the child spoke next, not whether it answered; depends on the activity (story telling has long adult runs).",
    )),
    "echolalia_cue_count": (MAIN, (
        "ประโยคของเด็กที่พูดซ้ำคำของผู้ใหญ่ที่เพิ่งพูด (cue ให้ตรวจ)",
        "การพูดตามเป็นลักษณะที่พบบ่อยในเด็กออทิสติก ใน TalkBank สัดส่วนนี้ลดลงตามอายุในเด็ก TD "
        "แต่สูงขึ้นในเด็ก ASD 4–6 ปี ยืนยันหรือปัดตกทีละคู่ในหน้าตัวชี้วัด",
        "คำตอบที่ใช้คำเดียวกับคำถามอาจถูกจับได้ และการพูดตามบางครั้งมีหน้าที่สื่อสาร ต้องดูบริบท",
    ), (
        "Child utterances that repeat what an adult has just said (a cue to review).",
        "Echoing is common in autistic children; in TalkBank it falls with age in typical children and rises in autistic children "
        "aged 4–6. Confirm or dismiss each pair on the Findings tab.",
        "An answer that reuses the question's words can be caught, and echoing can be communicative; judge in context.",
    )),
    "child_response_count": (SUPPORT, (
        "จำนวนครั้งที่ผู้ใหญ่พูดแล้วเด็กพูดต่อทันที",
        "ตัวเลขจริงเบื้องหลังอัตราการตอบ ใช้อธิบายในรายงานได้ เช่น ตอบต่อ 24 ครั้งจาก 40",
        "เพิ่มตามความยาวตัวอย่าง เทียบข้าม session ให้ใช้อัตรา",
    ), (
        "Times an adult spoke and the child spoke straight after.",
        "The count behind the response rate, useful in a report: 24 responses out of 40, say.",
        "Grows with sample length; compare sessions with the rate.",
    )),
    "mlt_ratio": (SUPPORT, (
        "คำต่อรอบพูดของเด็กหารด้วยของผู้ใหญ่ (MLT ratio, Assaf et al. 2025)",
        "บอกว่าเด็กพูดยาวแค่ไหนเมื่อเทียบกับคู่สนทนา เพิ่มตามอายุชัดในเด็ก TD (ρ = 0.72)",
        "ไปด้วยกันกับ MLU มาก (ρ = 0.81) และขึ้นกับว่าผู้ใหญ่พูดมากหรือน้อย",
    ), (
        "Child words per turn over the adults' (MLT ratio, Assaf et al. 2025).",
        "How long the child's turns are next to the partner's; rises clearly with age in typical children (ρ = 0.72).",
        "Moves closely with MLU (ρ = 0.81) and depends on how much the adult talks.",
    )),
    "adult_utterance_count": (SUPPORT, (
        "จำนวนประโยคของผู้ใหญ่ทุกคน",
        "ถ้าผู้ใหญ่พูดมากกว่าเด็กมาก ตัวอย่างอาจไม่สะท้อนความสามารถของเด็ก (มี cue เตือน)",
        "ขึ้นกับรูปแบบกิจกรรม",
    ), (
        "Utterances by all adults.",
        "If the adults talk far more than the child, the sample may not show what the child can do (a cue warns of this).",
        "Depends on the activity.",
    )),
    "pronoun_reversal_cue_count": (SUPPORT, (
        "ประโยคที่อาจใช้สรรพนามสลับ เช่น ใช้ 'เธอ' แทนตัวเอง",
        "ลักษณะคลาสสิกในเด็กออทิสติกบางคน ระบบชี้จุดให้กลับไปฟัง",
        "เด็กไทยมักเรียกตัวเองว่า 'หนู' หรือใช้ชื่อตัวเอง ซึ่งไม่ใช่การสลับ กฎจับได้ไม่ครบ",
    ), (
        "Utterances that may reverse pronouns, such as 'you' for oneself.",
        "A classic sign in some autistic children; the app points to places worth listening to again.",
        "Thai children often call themselves หนู or by name, which is not reversal; the rule misses many cases.",
    )),
    "question_ratio": (SUPPORT, (
        "สัดส่วนประโยคของเด็กที่เป็นคำถาม",
        "บอกการเริ่มต้นสื่อสารและการขอข้อมูล",
        "ใน TalkBank ค่ามัธยฐานใกล้ 0 แทบทุกกลุ่ม จึงมีสัญญาณน้อย ขึ้นกับการใส่เครื่องหมาย ? ใน transcript",
    ), (
        "Share of the child's utterances that are questions.",
        "Shows the child starting exchanges and asking for information.",
        "Near zero for most children in TalkBank, so little signal; depends on ? being marked in the transcript.",
    )),
    "limited_reciprocal_question_cue": (SUPPORT, (
        "ธงเตือนเมื่อเด็กไม่ถามเลยในตัวอย่าง",
        "ชวนให้ดูว่าเด็กเริ่มต้นสื่อสารเองหรือไม่",
        "ตัวอย่างสั้นทำให้ขึ้นได้ง่าย",
    ), (
        "A flag when the child asks no questions in the sample.",
        "Prompts a look at whether the child starts exchanges.",
        "Short samples raise it easily.",
    )),
    "repetition_marker_count": (SUPPORT, (
        "คำหรือวลีที่พูดซ้ำติดกันในประโยคเดียว",
        "ชี้จุดที่อาจเป็นการพูดตะกุกตะกักหรือพูดซ้ำ ให้นักบำบัดใส่รหัส [/] ถ้าใช่",
        "การพูดซ้ำเพื่อเน้นในภาษาไทย เช่น 'เร็ว ๆ' อาจถูกนับ",
    ), (
        "A word or phrase said twice in a row in one utterance.",
        "Points to possible disfluency or repetition; code it [/] if so.",
        "Thai repetition for emphasis can be counted.",
    )),
    "coded_repetition_count": (SUPPORT, (
        "การพูดซ้ำที่นักบำบัดใส่รหัส [/]", "นับความคล่องในการพูดได้แม่นเพราะมนุษย์เป็นผู้ระบุ", "มีค่าเมื่อใส่รหัสใน transcript เท่านั้น",
    ), (
        "Repetitions the therapist coded [/].", "Accurate fluency counts, because a person marked them.", "Only has a value once the codes are in the transcript.",
    )),
    "retracing_count": (SUPPORT, (
        "การพูดแก้ที่นักบำบัดใส่รหัส [//]", "บอกการวางแผนและแก้ประโยคระหว่างพูด", "มีค่าเมื่อใส่รหัสเท่านั้น",
    ), (
        "Retracings the therapist coded [//].", "Shows the child revising a sentence while speaking.", "Only has a value once coded.",
    )),
    "word_error_count": (SUPPORT, (
        "คำผิดที่นักบำบัดใส่รหัส [*]", "ติดตามความผิดพลาดด้านคำและไวยากรณ์", "มีค่าเมื่อใส่รหัสเท่านั้น",
    ), (
        "Word errors the therapist coded [*].", "Tracks word-level and grammatical errors.", "Only has a value once coded.",
    )),
    "utterance_error_count": (SUPPORT, (
        "ประโยคที่นักบำบัดใส่รหัสผิด เช่น [+ gram]", "ติดตามความผิดพลาดระดับประโยค", "มีค่าเมื่อใส่รหัสเท่านั้น",
    ), (
        "Utterances the therapist coded as errors, such as [+ gram].", "Tracks sentence-level errors.", "Only has a value once coded.",
    )),
    "mlu50_words": (BACKGROUND, (
        "MLU จาก 50 ประโยคแรก (KIDEVAL)", "เทียบกับงานวิจัยที่ใช้ KIDEVAL ได้", "ค่ามักใกล้ MLU-w ใช้ MLU-w เป็นหลัก",
    ), (
        "MLU of the first 50 utterances (KIDEVAL).", "Comparable with research that reports KIDEVAL.", "Usually close to MLU-w; read MLU-w first.",
    )),
    "mlu_words_sd": (BACKGROUND, (
        "ส่วนเบี่ยงเบนมาตรฐานของความยาวประโยค", "บอกว่าเด็กพูดประโยคยาวสั้นปนกันแค่ไหน", "ตีความทางคลินิกยาก",
    ), (
        "Standard deviation of utterance length.", "How much the child mixes short and long utterances.", "Hard to interpret clinically.",
    )),
    "mean_length_of_utterance_morphemes": (BACKGROUND, (
        "MLU เป็นหน่วยคำ (morpheme)", "มาตรฐานภาษาอังกฤษ", "ต้องมี %mor tier ใช้กับภาษาไทยไม่ได้",
    ), (
        "MLU in morphemes.", "The English standard.", "Needs a %mor tier; not available for Thai.",
    )),
    "type_token_ratio": (BACKGROUND, (
        "คำไม่ซ้ำหารด้วยคำทั้งหมด (TTR)", "ตัวชี้วัดความหลากหลายแบบดั้งเดิม",
        "ลดลงเมื่อตัวอย่างยาวขึ้น เทียบข้าม session ไม่ได้ ใช้ MATTR หรือ NDW-100 แทน",
    ), (
        "Different words over all words (TTR).", "The traditional diversity measure.",
        "Falls as samples get longer, so sessions cannot be compared; use MATTR or NDW-100.",
    )),
    "analyzable_utterance_count": (BACKGROUND, (
        "ประโยคของเด็กที่มีคำให้นับ (KIDEVAL Total_Utts)", "ใช้ตรวจความถูกต้องเทียบกับ CLAN", "ไม่ได้ใช้ตีความโดยตรง",
    ), (
        "Child utterances with countable words (KIDEVAL Total_Utts).", "Used to check agreement with CLAN.", "Not for interpretation on its own.",
    )),
    "unknown_speaker_ratio": (BACKGROUND, (
        "สัดส่วนบรรทัดที่ยังไม่ระบุผู้พูด", "ตรวจคุณภาพ transcript ควรเป็น 0 ก่อนรับรอง", "ไม่ใช่ข้อมูลของเด็ก",
    ), (
        "Share of lines without a speaker.", "A transcript check; it should be 0 before attesting.", "Says nothing about the child.",
    )),
    "repetitive_phrase_cue": (BACKGROUND, (
        "คำเดี่ยวที่พูดซ้ำติดกัน", "ชี้จุดพูดซ้ำแบบง่าย", "ซ้ำกับจำนวนการพูดซ้ำ ใช้ตัวนั้นเป็นหลัก",
    ), (
        "A single word repeated back to back.", "A simple pointer to repetition.", "Overlaps the repetitions count; read that one first.",
    )),
    "atypical_response_cue": (BACKGROUND, (
        "การตอบไม่ตรงคำถาม", "เตือนว่าเรื่องนี้ต้องใช้การตัดสินของนักบำบัด", "ระบบคำนวณเองไม่ได้ จึงไม่มีค่า",
    ), (
        "Off-topic responses.", "A reminder that this needs the therapist's judgement.", "The app cannot compute it, so it has no value.",
    )),
}

THAI_EXPERIMENTAL = {
    "thai_verbs_per_utterance": ("คำกริยาต่อประโยค", "Verbs per utterance"),
    "thai_pronoun_count": ("สรรพนาม", "Pronouns"),
    "thai_particle_count": ("คำลงท้าย ครับ/ค่ะ/นะ", "Sentence particles"),
    "thai_negator_count": ("คำปฏิเสธ", "Negators"),
}
for _name, (_th, _en) in THAI_EXPERIMENTAL.items():
    GUIDE[_name] = (BACKGROUND, (
        f"{_th} ในประโยคของเด็ก ติดป้ายชนิดคำด้วย PyThaiNLP",
        "อาจช่วยดูไวยากรณ์ภาษาไทยในอนาคต",
        "ทดลอง ยังไม่ได้ตรวจกับเสียงเด็ก อย่าใช้ตีความ",
    ), (
        f"{_en} in the child's Thai, tagged by PyThaiNLP.",
        "May help with Thai grammar in future.",
        "Experimental and not checked on child speech; do not interpret.",
    ))


def tier_name(tier: str) -> str:
    return {
        MAIN: tr("ตัวหลัก", "Main"),
        SUPPORT: tr("ตัวเสริม", "Supporting"),
        BACKGROUND: tr("ข้อมูลเบื้องหลัง", "Background"),
    }[tier]


def anchor(name: str) -> str:
    return f"feature-{name}"


def guide_html() -> str:
    """The guide as one article, grouped as on the Findings tab, one anchored entry per measure."""
    parts = [
        tr("<h1>ตัวชี้วัดแต่ละตัว</h1>", "<h1>Each measure</h1>"),
        tr(
            "<p>ตัวชี้วัดทุกตัวเป็นค่าเชิงบรรยายของตัวอย่างภาษาหนึ่งครั้ง ไม่มีตัวไหนบอกว่าเด็กเป็นหรือไม่เป็นออทิสติก "
            "เมื่อทดลองกับข้อมูล TalkBank การใช้ MLU และความยาวรอบพูดอย่างเดียวแยกกลุ่มได้ใกล้การเดาสุ่ม (AUC 0.53–0.56) "
            "ใช้ตัวชี้วัดเพื่อบอกระดับภาษา ติดตามความเปลี่ยนแปลงของเด็กคนเดียวกัน และหาจุดที่ควรกลับไปฟัง</p>"
            "<p><b>ตัวหลัก</b> แสดงในหน้าตัวชี้วัดและรายงาน <b>ตัวเสริม</b> ช่วยอธิบายเพิ่ม "
            "<b>ข้อมูลเบื้องหลัง</b> ใช้ตรวจคุณภาพหรือยังเป็นการทดลอง ติ๊ก 'แสดงตัวชี้วัดทั้งหมด' เพื่อดูทุกตัว</p>",
            "<p>Every measure describes one language sample. None says whether a child is autistic: on TalkBank data, MLU "
            "and turn length alone separated the groups at about chance (AUC 0.53–0.56). Use them to see the child's language "
            "level, follow change in the same child, and find places worth listening to again.</p>"
            "<p><b>Main</b> measures are on the Findings tab and in the report, <b>supporting</b> ones add detail, and "
            "<b>background</b> ones check quality or are experimental. Tick 'Show all measures' to see every one.</p>",
        ),
    ]
    for group, names in labels.FEATURE_GROUPS:
        parts.append(f"<h2>{html.escape(group)}</h2>")
        for name in names:
            if name not in GUIDE or name not in labels.FEATURES:
                continue
            tier, thai, english = GUIDE[name]
            what, helps, caution = thai if tr("th", "en") == "th" else english
            title = labels.FEATURES[name][0]
            parts.append(
                f'<a name="{anchor(name)}"></a><h3>{html.escape(title)} '
                f'<span style="font-weight: 400; color: {theme.MUTED};">· {tier_name(tier)}</span></h3>'
                f"<p><b>{tr('คืออะไร', 'What it is')}</b> {html.escape(what)}<br>"
                f"<b>{tr('ช่วยอย่างไร', 'How it helps')}</b> {html.escape(helps)}<br>"
                f"<b>{tr('ข้อควรระวัง', 'Watch for')}</b> {html.escape(caution)}</p>"
            )
    parts.append(tr(
        "<p>แหล่งอ้างอิง: ภัทธาลดา จตุรวิธวงศ์ ภาษาและการพูดในเด็กที่มีภาวะออทิสติก ศิริราชเวชสาร 2566; "
        "Assaf et al. 2025, Scientific Reports 15:34134; ผลตรวจของโครงการใน reports/metrics</p>",
        "<p>Sources: Speech and language in children with autism spectrum disorders, Siriraj Medical Bulletin 16(1), 2023; "
        "Assaf et al. 2025, Scientific Reports 15:34134; the project's own checks in reports/metrics.</p>",
    ))
    return "\n".join(parts)
