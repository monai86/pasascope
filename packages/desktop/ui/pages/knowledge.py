"""Knowledge: what each measure, cue and automatic decision in PasaScope means.

Articles are short reference pages a therapist can open while working. The
charts are drawn from this repository's own data (TalkBank reference
transcripts and the screening replication, built by
``scripts/build_knowledge_data.py``) and from the shipped boundary model, so
each number can be traced to where it came from. Nothing here turns a
measure into a probability of autism; the evidence page explains why.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QUrl
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QTextDocument
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QTextBrowser, QVBoxLayout, QWidget

from packages.desktop.core.i18n import tr
from packages.desktop.ui import theme
from packages.desktop.ui.widgets import label

DATA_PATH = Path(__file__).resolve().parents[1] / "assets" / "knowledge_data.json"
GROUP_COLORS = {"TD": theme.INK_SOFT, "LT": theme.ATTENTION, "ASD": theme.PRIMARY}


def _group_name(group: str) -> str:
    return {
        "TD": tr("พัฒนาการปกติ (TD)", "Typical development (TD)"),
        "LT": tr("พูดช้า (late talkers)", "Late talkers (LT)"),
        "ASD": tr("ออทิสติก (ASD)", "Autism (ASD)"),
    }[group]


def _data() -> dict:
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ----------------------------------------------------------------------
# Charts, drawn once into images the article embeds
# ----------------------------------------------------------------------
WIDTH, HEIGHT = 720, 300


def _canvas() -> tuple[QImage, QPainter]:
    image = QImage(WIDTH * 2, HEIGHT * 2, QImage.Format.Format_ARGB32)
    image.setDevicePixelRatio(2)
    image.fill(QColor(theme.SURFACE))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = QFont()
    font.setPixelSize(12)
    painter.setFont(font)
    return image, painter


def age_chart(measure: str, title: str, value_format: str = "{:.1f}") -> QImage:
    """Median and middle half (quartiles) of a measure by year of age, one line per group."""
    image, painter = _canvas()
    groups = _data().get("by_age", {}).get("groups", {})
    series = {g: s.get(measure, []) for g, s in groups.items()}
    points = [p for s in series.values() for p in s]
    if not points:
        painter.drawText(QRectF(0, 0, WIDTH, HEIGHT), Qt.AlignmentFlag.AlignCenter, tr("ไม่มีข้อมูล", "No data"))
        painter.end()
        return image
    plot = QRectF(56, 34, WIDTH - 280, HEIGHT - 76)
    years = sorted({p["year"] for p in points})
    top = max(p["q75"] for p in points) * 1.1 or 1
    x = lambda year: plot.left() + (year - years[0]) / max(1, years[-1] - years[0]) * plot.width()  # noqa: E731
    y = lambda value: plot.bottom() - value / top * plot.height()  # noqa: E731

    painter.setPen(QColor(theme.INK))
    painter.drawText(QRectF(0, 6, WIDTH, 20), Qt.AlignmentFlag.AlignHCenter, title)
    for fraction in (0, 0.5, 1):
        level = fraction * top
        painter.setPen(QPen(QColor(theme.LINE), 1))
        painter.drawLine(QPointF(plot.left(), y(level)), QPointF(plot.right(), y(level)))
        painter.setPen(QColor(theme.MUTED))
        painter.drawText(QRectF(0, y(level) - 8, plot.left() - 8, 16), Qt.AlignmentFlag.AlignRight, value_format.format(level))
    for year in years:
        painter.drawText(QRectF(x(year) - 20, plot.bottom() + 6, 40, 16), Qt.AlignmentFlag.AlignHCenter, str(year))
    painter.drawText(QRectF(plot.left(), plot.bottom() + 22, plot.width(), 16), Qt.AlignmentFlag.AlignHCenter,
                     tr("อายุ (ปี)", "Age (years)"))

    legend_y = plot.top()
    for group, rows in series.items():
        if not rows:
            continue
        color = QColor(GROUP_COLORS.get(group, theme.INK))
        band = QPainterPath()
        band.moveTo(QPointF(x(rows[0]["year"]), y(rows[0]["q75"])))
        for row in rows[1:]:
            band.lineTo(QPointF(x(row["year"]), y(row["q75"])))
        for row in reversed(rows):
            band.lineTo(QPointF(x(row["year"]), y(row["q25"])))
        band.closeSubpath()
        fill = QColor(color)
        fill.setAlpha(38)
        painter.fillPath(band, fill)
        line = QPainterPath()
        for index, row in enumerate(rows):
            point = QPointF(x(row["year"]), y(row["median"]))
            line.moveTo(point) if index == 0 else line.lineTo(point)
        painter.setPen(QPen(color, 2))
        painter.drawPath(line)
        painter.setBrush(color)
        for row in rows:
            painter.drawEllipse(QPointF(x(row["year"]), y(row["median"])), 3, 3)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        total = sum(row["n"] for row in rows)
        painter.fillRect(QRectF(plot.right() + 18, legend_y + 4, 14, 3), color)
        painter.setPen(QColor(theme.INK))
        painter.drawText(QRectF(plot.right() + 38, legend_y - 4, 210, 18), Qt.AlignmentFlag.AlignLeft, _group_name(group))
        painter.setPen(QColor(theme.MUTED))
        painter.drawText(QRectF(plot.right() + 38, legend_y + 12, 210, 18), Qt.AlignmentFlag.AlignLeft,
                         tr(f"{total} transcript", f"{total} transcripts"))
        legend_y += 44
    painter.end()
    return image


def screening_chart() -> QImage:
    """AUC of the replicated screening model under each check, against chance (0.5)."""
    image, painter = _canvas()
    rows = {r["check"]: r["auc"] for r in _data().get("screening", [])}
    checks = [
        ("as published", tr("ตามเปเปอร์ (MLU, turn, อายุ, เพศ)", "As published (MLU, turns, age, sex)")),
        ("age only", tr("อายุอย่างเดียว", "Age alone")),
        ("language only (MLU, MLT ratio)", tr("ภาษาอย่างเดียว", "Language measures alone")),
    ]
    plot = QRectF(240, 40, WIDTH - 360, HEIGHT - 80)
    painter.setPen(QColor(theme.INK))
    painter.drawText(QRectF(0, 6, WIDTH, 20), Qt.AlignmentFlag.AlignHCenter,
                     tr("แยกเด็กออทิสติกกับเด็กทั่วไปได้แค่ไหน (AUC)", "How well each model separates autistic from typical children (AUC)"))
    x = lambda value: plot.left() + (value - 0.4) / 0.6 * plot.width()  # noqa: E731
    for tick in (0.5, 0.75, 1.0):
        painter.setPen(QPen(QColor(theme.LINE_STRONG if tick == 0.5 else theme.LINE), 1, Qt.PenStyle.DashLine if tick == 0.5 else Qt.PenStyle.SolidLine))
        painter.drawLine(QPointF(x(tick), plot.top()), QPointF(x(tick), plot.bottom()))
        painter.setPen(QColor(theme.MUTED))
        painter.drawText(QRectF(x(tick) - 60, plot.bottom() + 6, 120, 16), Qt.AlignmentFlag.AlignHCenter,
                         f"{tick:.2f}" + (tr(" (เดาสุ่ม)", " (chance)") if tick == 0.5 else ""))
    row_height = plot.height() / len(checks)
    for index, (key, text) in enumerate(checks):
        top = plot.top() + index * row_height
        painter.setPen(QColor(theme.INK))
        painter.drawText(QRectF(0, top, plot.left() - 12, row_height), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)
        for offset, corpus in enumerate(("Nadig", "Eigsti")):
            value = rows.get(f"{corpus}: {key}")
            if value is None:
                continue
            bar = QRectF(x(0.4), top + 10 + offset * 20, x(value) - x(0.4), 15)
            painter.fillRect(bar, QColor(theme.PRIMARY if key == "age only" else theme.FAINT))
            painter.setPen(QColor(theme.INK))
            painter.drawText(QRectF(bar.right() + 6, bar.top() - 1, 120, 17), Qt.AlignmentFlag.AlignLeft, f"{corpus} {value:.2f}")
    painter.end()
    return image


def boundary_weights_chart() -> QImage:
    """The shipped utterance boundary model's feature weights."""
    from src.audio_pipeline.utterance_boundaries import FEATURE_LABELS_EN, FEATURE_LABELS_TH, BoundaryModel

    image, painter = _canvas()
    try:
        model = BoundaryModel.load()
    except (OSError, ValueError, KeyError):
        painter.drawText(QRectF(0, 0, WIDTH, HEIGHT), Qt.AlignmentFlag.AlignCenter, tr("ไม่พบโมเดล", "Model not found"))
        painter.end()
        return image
    from src.audio_pipeline.utterance_boundaries import FEATURES

    weights = sorted(zip(FEATURES, model.weights), key=lambda kv: -kv[1])
    plot = QRectF(260, 40, WIDTH - 340, HEIGHT - 70)
    painter.setPen(QColor(theme.INK))
    painter.drawText(QRectF(0, 6, WIDTH, 20), Qt.AlignmentFlag.AlignHCenter,
                     tr("สิ่งที่โมเดลใช้ตัดสินว่าขึ้นประโยคใหม่ (น้ำหนัก)", "What the boundary model weighs"))
    top = max(abs(w) for _, w in weights) or 1
    row_height = plot.height() / len(weights)
    for index, (name, weight) in enumerate(weights):
        y = plot.top() + index * row_height
        painter.setPen(QColor(theme.INK))
        text = tr(FEATURE_LABELS_TH[name], FEATURE_LABELS_EN[name])
        painter.drawText(QRectF(0, y, plot.left() - 12, row_height), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)
        bar = QRectF(plot.left(), y + row_height * 0.25, plot.width() * abs(weight) / top, row_height * 0.5)
        painter.fillRect(bar, QColor(theme.PRIMARY if weight > 0 else theme.ATTENTION))
        painter.drawText(QRectF(bar.right() + 6, y, 60, row_height), Qt.AlignmentFlag.AlignVCenter, f"{weight:+.2f}")
    painter.end()
    return image


# ----------------------------------------------------------------------
# Articles
# ----------------------------------------------------------------------
def _topics() -> list[tuple[str, str]]:
    return [
        ("session", tr("ขั้นตอนของ session", "Working through a session")),
        ("review", tr("ตรวจร่าง transcript", "Checking the draft transcript")),
        ("codes", tr("รหัส CHAT", "CHAT codes")),
        ("mlu", tr("ความยาวประโยค (MLU)", "Utterance length (MLU)")),
        ("vocabulary", tr("คลังคำ (NDW, TTR)", "Vocabulary (NDW, TTR)")),
        ("sample", tr("ขนาดตัวอย่าง", "Sample size")),
        ("echolalia", tr("การพูดตาม (echolalia)", "Echolalia")),
        ("pronouns", tr("การใช้สรรพนามสลับ", "Pronoun reversal")),
        ("autism", tr("ตัวชี้วัดบอกอะไรเรื่องออทิสติกได้บ้าง", "What these measures say about autism")),
        ("decisions", tr("ระบบตัดสินใจอย่างไร", "How PasaScope decides")),
        ("privacy", tr("ข้อมูลและความเป็นส่วนตัว", "Data and privacy")),
    ]


def _article(topic: str) -> str:
    """The article body as simple HTML."""
    if topic == "session":
        return tr(
            """<h1>ขั้นตอนของ session</h1>
<p>หนึ่ง session คือหนึ่งตัวอย่างภาษา ทำตามลำดับ ขั้นหลังเปิดได้เมื่อขั้นก่อนเสร็จ</p>
<ol>
<li><b>เสียง</b> บันทึกจากไมโครโฟน นำเข้าไฟล์เสียง หรือนำเข้า transcript ที่มีอยู่แล้ว ไฟล์เสียงถอดด้วย Whisper บนเครื่องนี้</li>
<li><b>ตรวจ transcript</b> ฟังเทียบกับร่าง แก้คำ ระบุผู้พูด ใส่รหัส CHAT แล้วรับรอง ตัวชี้วัดคำนวณจาก transcript ที่รับรองแล้วเท่านั้น</li>
<li><b>ตัวชี้วัดและ cue</b> วิเคราะห์ แล้วยืนยันหรือปัดตก cue ทีละข้อ</li>
<li><b>รายงาน</b> แก้ร่างรายงาน ลงนาม แล้ว export เป็น PDF</li>
</ol>
<p>แก้ transcript หลังรับรองแล้ว การรับรองจะถูกยกเลิก และต้องวิเคราะห์ใหม่</p>""",
            """<h1>Working through a session</h1>
<p>A session is one language sample. The steps run in order; each opens when the one before it is done.</p>
<ol>
<li><b>Recording.</b> Record from the microphone, import an audio file, or import a transcript you already have. Audio is transcribed by Whisper on this computer.</li>
<li><b>Transcript.</b> Listen against the draft, correct words and speakers, add CHAT codes, then attest. Measures are only computed from an attested transcript.</li>
<li><b>Findings.</b> Analyse, then confirm or dismiss each cue.</li>
<li><b>Report.</b> Edit the draft report, sign it, and export a PDF.</li>
</ol>
<p>Editing an attested transcript withdraws the attestation, and the analysis has to be run again.</p>""",
        )
    if topic == "review":
        return tr(
            """<h1>ตรวจร่าง transcript</h1>
<h2>ผู้พูด</h2>
<p>ระบบแยกเสียงเด็กกับผู้ใหญ่ด้วยโมเดลของ USC SAIL ป้าย <b>?</b> หมายถึงระบบไม่แน่ใจ: ประโยคสั้นกว่าครึ่งวินาที เสียงก้ำกึ่ง หรืออายุเด็กอยู่นอกช่วงที่ตรวจแล้ว (2;6 ถึง 6;11 ปี) ป้ายที่ไม่มี ? ถูกราว 95% ในเด็กอังกฤษวัยนี้</p>
<h2>ขอบเขตประโยค</h2>
<p>ร่างภาษาอังกฤษตัดประโยคด้วยโมเดลที่อธิบายได้ เลือกประโยคแล้วดูเหตุผลในแผงด้านขวา ร่างภาษาไทยตัดเมื่อหยุดพูดเกิน 0.6 วินาที ตรวจขอบเขตประโยคเสมอ เพราะ MLU ขึ้นกับมันโดยตรง</p>
<h2>คำที่ระบบไม่มั่นใจ</h2>
<p>แถวสีส้มคือประโยคที่ความมั่นใจของการถอดเสียงต่ำกว่า 60% ฟังซ้ำก่อนรับรอง</p>""",
            """<h1>Checking the draft transcript</h1>
<h2>Speakers</h2>
<p>Child and adult voices are told apart by a model from USC SAIL. A <b>?</b> means the label is uncertain: the line is shorter than half a second, the voice is borderline, or the child's age is outside the range that was checked (2;6 to 6;11). Labels without a ? were about 95% right for English-speaking children of these ages.</p>
<h2>Utterance boundaries</h2>
<p>English drafts are cut into utterances by an explainable model; select a line to see its reasons in the side panel. Thai drafts are cut where the speaker pauses for more than 0.6 s. Always check the boundaries: MLU depends on them directly.</p>
<h2>Low-confidence words</h2>
<p>Amber rows are lines Whisper transcribed with under 60% confidence. Listen again before attesting.</p>""",
        )
    if topic == "codes":
        rows = [
            ("xxx", tr("คำที่ฟังไม่ออก ประโยคนี้ไม่ใช้คิด MLU", "Unintelligible word; the utterance is left out of MLU")),
            (tr("&lt;คำ คำ&gt; [/]", "&lt;word word&gt; [/]"), tr("พูดซ้ำ ส่วนในวงเล็บไม่ถูกนับ", "Repetition; the bracketed words are not counted")),
            ("&lt;...&gt; [//]", tr("พูดแก้ ส่วนในวงเล็บไม่ถูกนับ", "Retracing (self-correction); not counted")),
            ("&amp;-um", tr("คำเติม ไม่นับเป็นคำ", "Filler; not a word")),
            ("word [: target]", tr("คำที่พูดเพี้ยน นับเป็นคำที่ตั้งใจพูด", "Mispronounced word; the target word is counted")),
            ("word [*]", tr("คำที่ใช้ผิด นับใน word errors", "Word error; counted under word errors")),
            ("[+ exc]", tr("ตัดประโยคนี้ออกจากตัวชี้วัดทั้งหมด", "Leave the utterance out of every measure")),
        ]
        table = "".join(f"<tr><td><code>{code}</code></td><td>{meaning}</td></tr>" for code, meaning in rows)
        return tr("<h1>รหัส CHAT</h1><p>รหัสเหล่านี้กำหนดว่าคำไหนถูกนับ ตามกติกาของ CLAN</p>",
                  "<h1>CHAT codes</h1><p>These codes decide which words are counted, following CLAN's rules.</p>") + f"<table>{table}</table>"
    if topic == "mlu":
        return tr(
            """<h1>ความยาวประโยค (MLU)</h1>
<p><b>MLU-w</b> คือจำนวนคำเฉลี่ยต่อประโยคของเด็ก นับตามกติกา CLAN: ไม่นับส่วนที่พูดซ้ำหรือพูดแก้ คำเติม และไม่ใช้ประโยคที่มี xxx/yyy/www</p>
<div><img src="chart://mlu" width="{WIDTH}" height="{HEIGHT}"></div>
<p>กราฟจาก transcript TalkBank ภาษาอังกฤษตอนเล่นของเล่น (เส้นคือค่ากลาง แถบคือช่วงครึ่งกลางของเด็ก) MLU เพิ่มตามอายุ เด็กพูดช้าที่ไม่ใช่ออทิสติกก็มีค่าต่ำได้ และกลุ่มต่าง ๆ ซ้อนทับกันมาก กลุ่มเด็กแต่ละกลุ่มมาจากคนละคลังข้อมูล ซึ่งเก็บต่างกัน</p>
<p><b>ข้อจำกัด</b> ยังไม่มีค่าอ้างอิงของเด็กไทย และค่านี้ขึ้นกับตำแหน่งที่ตัดประโยค ใช้เทียบเด็กคนเดียวกันข้าม session ด้วยกิจกรรมแบบเดียวกัน</p>""",
            """<h1>Utterance length (MLU)</h1>
<p><b>MLU-w</b> is the child's average number of words per utterance, counted with CLAN's rules: repetitions, retracings and fillers are not counted, and utterances containing xxx, yyy or www are left out.</p>
<div><img src="chart://mlu" width="{WIDTH}" height="{HEIGHT}"></div>
<p>English TalkBank toy-play transcripts (line: median; band: the middle half of children). MLU rises with age. Late talkers who are not autistic can be just as low, and the groups overlap widely. Each group comes from different corpora, collected in different ways.</p>
<p><b>Limits.</b> There are no Thai reference values yet, and MLU depends on where utterances are cut. Compare the same child across sessions with the same kind of activity.</p>""",
        )
    if topic == "vocabulary":
        return tr(
            """<h1>คลังคำ</h1>
<p><b>NDW</b> จำนวนคำที่ไม่ซ้ำกัน เพิ่มตามความยาวตัวอย่าง จึงเทียบข้าม session ด้วย <b>NDW-100</b> (คำไม่ซ้ำใน 100 คำแรก) ดีกว่า</p>
<p><b>TTR</b> คำไม่ซ้ำหารด้วยคำทั้งหมด ลดลงเมื่อตัวอย่างยาวขึ้น <b>MATTR-50</b> และ <b>VOCD D</b> ไม่ขึ้นกับความยาว ต้องมีคำอย่างน้อย 50 คำ</p>
<p>ภาษาไทยตัดคำด้วย PyThaiNLP ตรวจกับ transcript ที่นักถอดเสียงตัดคำไว้: ขอบเขตคำตรงกัน F1 0.90</p>""",
            """<h1>Vocabulary</h1>
<p><b>NDW</b> counts different words. It grows with sample length, so <b>NDW-100</b> (different words in the first 100) compares sessions better.</p>
<p><b>TTR</b> is different words over all words and falls as samples get longer. <b>MATTR-50</b> and <b>VOCD D</b> do not depend on length; both need 50 words.</p>
<p>Thai is split into words with PyThaiNLP. Against transcribers' word spaces the boundaries agreed with F1 0.90.</p>""",
        )
    if topic == "sample":
        return tr(
            """<h1>ขนาดตัวอย่าง</h1>
<p>แนวทางการวิเคราะห์ตัวอย่างภาษามักให้มีประโยคของเด็กอย่างน้อย 50 ประโยค (KIDEVAL ใช้ 50 ประโยคแรกสำหรับ MLU50) ตัวอย่างที่สั้นกว่านี้ทำให้ค่าแกว่งมาก ในกราฟแนวโน้ม session ที่สั้นกว่า 50 ประโยคเป็นจุดกลวง</p>""",
            """<h1>Sample size</h1>
<p>Language-sample guidelines usually ask for at least 50 child utterances (KIDEVAL's MLU50 uses the first 50). Shorter samples make every measure swing. In trend charts, sessions under 50 utterances are drawn hollow.</p>""",
        )
    if topic == "echolalia":
        return tr(
            """<h1>การพูดตาม (echolalia)</h1>
<p>เด็กพูดซ้ำคำของผู้ใหญ่ที่เพิ่งพูด ทั้งหมด (ทันทีทุกคำ) หรือบางส่วน DSM-5-TR ยกการพูดตามเป็นตัวอย่างของการพูดซ้ำแบบเฉพาะในเกณฑ์ข้อ B1 การพูดตามก็พบในพัฒนาการปกติช่วงอายุน้อยด้วย</p>
<div><img src="chart://echolalia" width="{WIDTH}" height="{HEIGHT}"></div>
<p>สัดส่วนประโยคที่เป็นการพูดตาม ตามกฎของ PasaScope ใน transcript ชุดเดียวกับหน้า MLU ค่าของกลุ่มออทิสติกสูงกว่าตั้งแต่อายุ 4 ปี แต่กลุ่มซ้อนทับกัน และกลุ่มมาจากคนละคลังข้อมูล</p>
<p><b>กฎนี้จับอะไรได้</b> คู่ประโยคผู้ใหญ่กับเด็กที่ใช้คำซ้ำกัน คำตอบปกติที่ใช้คำเดียวกับคำถามก็ถูกจับด้วย จึงต้องยืนยันทีละคู่ ในชุดทดสอบ 40 คู่ จับ echo ได้ครบ 20 คู่ และจับผิด 4 จาก 20 คำตอบปกติ</p>""",
            """<h1>Echolalia</h1>
<p>The child repeats what an adult has just said, word for word (immediate) or in part. DSM-5-TR names echolalia as an example of stereotyped or repetitive speech under criterion B1. Young typically developing children echo too.</p>
<div><img src="chart://echolalia" width="{WIDTH}" height="{HEIGHT}"></div>
<p>The share of utterances PasaScope's rule flags as echoes, in the same transcripts as the MLU page. From age 4 the autistic group is higher, but the groups overlap and come from different corpora.</p>
<p><b>What the rule catches.</b> Adult-child pairs that share words, including ordinary answers that reuse the question's words, so each pair must be confirmed. On 40 test pairs it caught all 20 echoes and wrongly flagged 4 of 20 ordinary answers.</p>""",
        )
    if topic == "pronouns":
        return tr(
            """<h1>การใช้สรรพนามสลับ</h1>
<p>เช่น เด็กเรียกตัวเองว่า "คุณ" หรือ "เขา" มีการบรรยายในเด็กออทิสติกมาตั้งแต่ Kanner (1943) กฎของ PasaScope ตรวจเฉพาะรูปแบบง่าย ๆ ต้องดูบริบททุกครั้ง และยังไม่ได้ตรวจความแม่นยำกับข้อมูลจริง</p>""",
            """<h1>Pronoun reversal</h1>
<p>For example, a child calling themself "you". It has been described in autistic children since Kanner (1943). PasaScope's rule only checks simple patterns; read each one in context. Its accuracy has not been measured on real data.</p>""",
        )
    if topic == "autism":
        return tr(
            """<h1>ตัวชี้วัดบอกอะไรเรื่องออทิสติกได้บ้าง</h1>
<p>PasaScope ไม่บอกโอกาสเป็นออทิสติก การวินิจฉัยใช้การประเมินทางคลินิก เช่น ADOS-2 หรือ TDAS ตัวชี้วัดในโปรแกรมช่วยบรรยายภาษาของเด็กและติดตามความเปลี่ยนแปลง</p>
<h2>ทำไมไม่บอกโอกาส</h2>
<p>งานที่รายงานว่าแยกเด็กออทิสติกจาก transcript ได้แม่นมาก (Assaf et al. 2025) ใช้อายุเป็นตัวแปรด้วย เมื่อทำซ้ำกับข้อมูลชุดเดียวกัน อายุอย่างเดียวให้ผลเกือบเท่าโมเดลเต็ม ส่วนตัวชี้วัดภาษาอย่างเดียวใกล้การเดาสุ่ม</p>
<div><img src="chart://screening" width="{WIDTH}" height="{HEIGHT}"></div>
<p>โมเดลเสียงก็ใช้ข้ามบริบทไม่ได้: เปลี่ยนงานพูด F1 ลดเหลือ 0.60 ถึง 0.66 เปลี่ยนภาษาต่ำกว่าเดาสุ่ม (Rybner et al. 2022)</p>
<h2>สิ่งที่หลักฐานสนับสนุน</h2>
<ul>
<li><b>การพูดตามและการพูดซ้ำแบบเฉพาะ</b> อยู่ในเกณฑ์ DSM-5-TR ข้อ B1</li>
<li><b>ระดับเสียงสูงต่ำ</b> ช่วงและความแปรปรวนของระดับเสียงต่างจากเด็กทั่วไปในระดับปานกลาง (meta-analysis, Ma et al. 2024) โปรแกรมยังไม่วัดค่านี้</li>
<li><b>MLU และคลังคำ</b> สะท้อนระดับภาษา ไม่เฉพาะออทิสติก พบต่ำได้ในเด็กพูดช้าและเด็กที่มีความผิดปกติทางภาษา</li>
</ul>""",
            """<h1>What these measures say about autism</h1>
<p>PasaScope does not estimate how likely a child is to be autistic. Diagnosis rests on clinical assessment such as ADOS-2 or TDAS; the measures here describe a child's language and track change.</p>
<h2>Why no likelihood</h2>
<p>A study reporting high accuracy from transcripts (Assaf et al. 2025) used age as one of its inputs. Re-run on the same corpora, age alone did almost as well as the full model, and the language measures alone were close to chance.</p>
<div><img src="chart://screening" width="{WIDTH}" height="{HEIGHT}"></div>
<p>Voice models do not carry across settings either: on a different speaking task F1 fell to 0.60-0.66, and in another language below chance (Rybner et al. 2022).</p>
<h2>What the evidence does support</h2>
<ul>
<li><b>Echolalia and other stereotyped speech</b> are part of DSM-5-TR criterion B1.</li>
<li><b>Pitch</b>: pitch range and variability differ moderately from typical children (meta-analysis, Ma et al. 2024). PasaScope does not measure this yet.</li>
<li><b>MLU and vocabulary</b> reflect language level, not autism specifically; they can be low in late talkers and in developmental language disorder.</li>
</ul>""",
        )
    if topic == "decisions":
        return tr(
            """<h1>ระบบตัดสินใจอย่างไร</h1>
<h2>เด็กหรือผู้ใหญ่</h2>
<p>โมเดลของ USC SAIL ฟังทุก 20 มิลลิวินาที ถ้าคลินิกมี session ที่รับรองแล้วอย่างน้อย 4 session จากเด็ก 2 คน โปรแกรมเรียนเสียงของคลินิกเพิ่ม และใช้ก็ต่อเมื่อแม่นกว่าโมเดลพื้นฐาน แต่ละประโยคบอกโอกาสและประโยคที่รับรองแล้วที่เสียงคล้ายที่สุด</p>
<h2>ขอบเขตประโยค (ภาษาอังกฤษ)</h2>
<div><img src="chart://weights" width="{WIDTH}" height="{HEIGHT}"></div>
<p>logistic regression บนสิ่งที่มีชื่อ น้ำหนักบวกดันให้ขึ้นประโยคใหม่ เมื่อทดสอบกับเด็กที่ไม่เคยเห็น ขอบเขตตรงกับนักถอดเสียง F1 0.83 (กฎช่วงหยุดเดิม 0.66)</p>""",
            """<h1>How PasaScope decides</h1>
<h2>Child or adult</h2>
<p>A model from USC SAIL listens every 20 ms. Once the clinic has at least 4 attested sessions from 2 children, PasaScope also learns the clinic's own voices, and uses that model only when it beats the base model. Each line shows the chance it gave and the attested lines it sounds most like.</p>
<h2>Utterance boundaries (English)</h2>
<div><img src="chart://weights" width="{WIDTH}" height="{HEIGHT}"></div>
<p>A logistic regression on named features; positive weights push towards a new utterance. On children it had not seen, its boundaries matched the transcribers' with F1 0.83 (0.66 for the old pause rule).</p>""",
        )
    return tr(
        """<h1>ข้อมูลและความเป็นส่วนตัว</h1>
<p>เสียง transcript และรายงานเก็บในเครื่องนี้เท่านั้น ถอดเสียงด้วย Whisper บนเครื่อง ไม่ส่งไปที่ใด โมเดลประจำคลินิกเรียนบนเครื่อง ใช้เฉพาะเด็กที่ยังให้ความยินยอม ถอนความยินยอมแล้วข้อมูลของเด็กไม่ถูกใช้เรียนอีก</p>
<p>ไฟล์สำรองไม่เข้ารหัส เก็บไว้ในที่ที่มีแต่นักบำบัดเข้าถึงได้ ทุกการเปลี่ยนแปลงบันทึกใน audit log (เมนู Help)</p>""",
        """<h1>Data and privacy</h1>
<p>Recordings, transcripts and reports stay on this computer. Whisper runs locally and nothing is sent anywhere. The clinic's speaker model is trained on this computer from children whose consent is still in force; once consent is withdrawn, a child's data is not used again.</p>
<p>Backups are not encrypted; keep them where only therapists can reach them. Every change is recorded in the audit log (Help menu).</p>""",
    )


ARTICLE_STYLE = f"""
body {{ color: {theme.INK}; font-size: 14px; }}
h1 {{ font-size: 24px; font-weight: 700; margin: 4px 0 12px 0; }}
h2 {{ font-size: 16px; font-weight: 600; margin: 18px 0 6px 0; }}
p, li {{ line-height: 150%; }}
td {{ padding: 6px 14px 6px 0; border-bottom: 1px solid {theme.LINE}; }}
code {{ background: {theme.HOVER}; }}
"""


class KnowledgePage(QWidget):
    """Topics on the left, the article on the right."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(24, 22, 12, 16)
        side_layout.addWidget(label(tr("ความรู้", "Knowledge"), "CaseTitle"))
        self.topics = QListWidget()
        self.topics.setFixedWidth(280)
        self.topics.setWordWrap(True)
        self.topics.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for key, title in _topics():
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.topics.addItem(item)
        self.topics.currentItemChanged.connect(lambda item, _: item and self._show(item.data(Qt.ItemDataRole.UserRole)))
        side_layout.addWidget(self.topics, 1)
        layout.addWidget(side)

        self.article = QTextBrowser()
        self.article.setOpenExternalLinks(False)
        self.article.setFrameShape(QTextBrowser.Shape.NoFrame)
        self.article.setObjectName("Article")
        self.article.document().setDocumentMargin(28)
        self.article.document().setDefaultStyleSheet(ARTICLE_STYLE)
        layout.addWidget(self.article, 1)
        self._charts_ready = False
        self.topics.setCurrentRow(0)

    def _add_charts(self) -> None:
        if self._charts_ready:
            return
        document = self.article.document()
        for name, image in (
            ("mlu", age_chart("mlu_words", tr("MLU-w ตามอายุ", "MLU-w by age"))),
            ("echolalia", age_chart("echolalia_ratio", tr("สัดส่วนการพูดตามตามอายุ", "Echolalia by age"), "{:.2f}")),
            ("screening", screening_chart()),
            ("weights", boundary_weights_chart()),
        ):
            document.addResource(QTextDocument.ResourceType.ImageResource, QUrl(f"chart://{name}"), image)
        self._charts_ready = True

    def _show(self, topic: str) -> None:
        if topic in ("mlu", "echolalia", "autism", "decisions"):
            self._add_charts()
        self.article.setHtml(_article(topic).replace("{WIDTH}", str(WIDTH)).replace("{HEIGHT}", str(HEIGHT)))

    def open_topic(self, topic: str) -> None:
        for row in range(self.topics.count()):
            if self.topics.item(row).data(Qt.ItemDataRole.UserRole) == topic:
                self.topics.setCurrentRow(row)
                return
