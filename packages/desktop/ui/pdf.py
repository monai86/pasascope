"""Lay a session report out as a formal A4 document, for the PDF and the on-screen preview.

One function, ``paint_report``, draws every page on any paged device: the
QPdfWriter that writes the PDF file and the QPrinter behind the report page's
preview, so the preview is the PDF.

The layout follows published conventions (sources in docs/REPORT_LAYOUT.md):

* Thai: the government correspondence rules (ระเบียบสำนักนายกรัฐมนตรีว่าด้วยงานสารบรรณ)
  as clinics and universities apply them: TH Sarabun at 16 pt, left margin
  3 cm, right 2 cm, first-line indent 2.5 cm. The bundled font is Google's
  Sarabun, the open (OFL) release of TH Sarabun New; its Thai letters are
  1.47 times larger at the same point size (ก is 0.586 em against 0.400 em),
  so 11 pt here prints the same size as TH Sarabun New 16 pt.
* English: Times New Roman 12 pt, 2.54 cm (1 inch) margins, block paragraphs.
* Both: three type sizes (title, body, small print); a letterhead with the
  PasaScope logo on page one and a running header (clinic, "confidential")
  on the others; a footer with the child code, session date and "page x of
  y"; the logo faint behind the text of every page; numbered sections; the
  identifying details as a table; bullets that line up with the paragraph
  indent; and a signature block. An unsigned report carries a boxed "ร่าง" /
  "DRAFT" stamp at the top of every page.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import lru_cache
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re

from PySide6.QtCore import QMarginsF, QPointF, QRectF, Qt, QUrl
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QGuiApplication,
    QImage,
    QPageLayout,
    QPageSize,
    QPagedPaintDevice,
    QPainter,
    QPdfWriter,
    QPen,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextImageFormat,
    QTextLength,
    QTextTableCellFormat,
    QTextTableFormat,
)

from packages.desktop.core.i18n import report_language

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
THAI_TIME = timezone(timedelta(hours=7))
PDF_DPI = 300

THAI_MONTHS = ("มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
               "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม")
ENGLISH_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December")

INK = QColor("#111111")
RULE = QColor("#7a7a7a")
TABLE_LINE = QColor("#9a9a9a")
LABEL_FILL = QColor(0, 0, 0, 13)  # see-through, so the background logo shows under shaded cells
DRAFT_INK = QColor("#9b2c2c")
LOGO = Path(__file__).resolve().parent / "assets" / "logo.png"
LOGO_OPACITY = 0.06
LETTERHEAD_MM = 18
# Thai letters drawn inside Times New Roman text: TH Sarabun's Thai is 0.400 em
# tall and Times' x-height 0.447 em; at 1.3 times the size the Thai sits with
# the Latin lower case as it does within TH Sarabun itself (Thai 1.17 x-heights).
THAI_IN_LATIN = 1.3
# A character TH Sarabun lacks (the arrow →) is drawn in Sarabun, whose
# letters are 1.47 times larger at the same size.
FALLBACK_SCALE = 0.68


@dataclass(frozen=True)
class Layout:
    """Page and type settings for one report language. Sizes in points, margins in millimetres."""

    families: tuple[str, ...]
    # Three sizes only: title, everything in the body (headings, tables and
    # notes included), and the small print of the running header, footer and
    # signature note. A clinic name above the title sits between the two.
    title_pt: float
    organization_pt: float
    body_pt: float
    small_pt: float
    line_height: int  # percent of the font's own line spacing
    margins_mm: tuple[float, float, float, float]  # left, top, right, bottom
    first_line_indent_mm: float
    list_marker_mm: float  # bullet position, from the left margin
    list_text_mm: float  # where a list item's text (and its wrapped lines) starts
    paragraph_after_pt: float
    heading_before_pt: float
    heading_after_pt: float
    italic_notes: bool  # Thai has no true italic, so Thai notes stay upright
    bullet: str  # Thai documents mark list items with a dash; TH Sarabun's • also sits high
    title_line_height: int  # percent, for the clinic name and title lines
    cell_padding_pt: tuple[float, float]  # top, bottom
    words: dict[str, str] = field(default_factory=dict)


THAI_FAMILIES = ("TH SarabunPSK", "TH Sarabun New", "Sarabun")

LAYOUTS = {
    "th": Layout(
        # TH SarabunPSK when the computer has it, otherwise the bundled TH
        # Sarabun New (its successor: same design and size, GPL with a font
        # exception), at the sizes Thai official documents use.
        families=THAI_FAMILIES,
        title_pt=20, organization_pt=18, body_pt=16, small_pt=14,
        line_height=92,  # about Word's single spacing for TH Sarabun
        margins_mm=(30, 25, 20, 20),
        # A 1.25 cm first-line indent (Word's default): the 2.5 cm of official
        # letters pushed short paragraphs and lists too far into the page.
        first_line_indent_mm=12.5,
        list_marker_mm=12.5, list_text_mm=18,
        paragraph_after_pt=6, heading_before_pt=12, heading_after_pt=6,
        italic_notes=False, bullet="–", title_line_height=78, cell_padding_pt=(0.5, 2.5),
        words={
            "confidential": "ข้อมูลสุขภาพส่วนบุคคล  เก็บเป็นความลับ",
            "page": "หน้า {page} จาก {pages}",
            "draft": "ร่าง",
            "child": "รหัสเด็ก",
            "session": "session วันที่",
            "sign": "ลงชื่อ",
            "role": "นักบำบัดผู้รับผิดชอบ",
            "date": "วันที่",
            "e_signed": "ลงนามอิเล็กทรอนิกส์ในโปรแกรม PasaScope",
            "draft_note": "ฉบับร่าง ยังไม่ได้ลงนาม ห้ามนำไปใช้อ้างอิง",
        },
    ),
    "en": Layout(
        families=("Times New Roman", *THAI_FAMILIES),
        title_pt=14, organization_pt=12, body_pt=12, small_pt=10,
        line_height=115,
        margins_mm=(25.4, 25.4, 25.4, 25.4),
        first_line_indent_mm=0,
        list_marker_mm=6.35, list_text_mm=12.7,
        paragraph_after_pt=6, heading_before_pt=12, heading_after_pt=6,
        italic_notes=True, bullet="•", title_line_height=100, cell_padding_pt=(2, 2),
        words={
            "confidential": "Confidential health information",
            "page": "Page {page} of {pages}",
            "draft": "DRAFT",
            "child": "Child",
            "session": "Session",
            "sign": "Signed",
            "role": "Responsible therapist",
            "date": "Date",
            "e_signed": "Signed electronically in PasaScope",
            "draft_note": "Draft, not signed. Not for use or distribution.",
        },
    ),
}

# Sections whose "- label: value" lines are identifying details, set out as a table.
DETAIL_SECTIONS = {
    "ข้อมูล session", "ที่มาของข้อมูล",
    "Session details", "Data sources", "Session Overview", "Data Sources",
}
SIGNOFF_SECTIONS = {"การลงนามของนักบำบัด", "Therapist sign-off", "Therapist Sign-off"}
# Lines the system writes into the sign-off section; the signature block replaces them.
SIGNOFF_LINES = re.compile(
    r"^(- )?(ลงนามโดย|สถานะ|เวลาลงนาม|Signed by|Status|Signed at|Sign-off status|Export timestamp)\s*:"
)
SIGNOFF_PLACEHOLDERS = {
    "รอนักบำบัดแก้ไขและลงนาม", "Awaiting therapist review and signature.", "Pending therapist edit and sign-off.",
}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")


@dataclass
class ReportMeta:
    """What the page furniture needs besides the report text."""

    title: str = ""
    organization: str = ""
    child_code: str = ""
    session_date: str = ""
    signed_by: str = ""
    signed_at: datetime | None = None
    language: str | None = None  # read from the markdown when not given

    @property
    def signed(self) -> bool:
        return bool(self.signed_by and self.signed_at)


_fonts_loaded = False


THAI_RUN = re.compile(r"[\u0e00-\u0e7f]+")
ZERO_WIDTH_SPACE = "\u200b"


@lru_cache(maxsize=4096)
def _thai_breaks(run: str) -> str:
    try:
        from pythainlp.tokenize import word_tokenize
    except ImportError:  # pragma: no cover - pythainlp ships with the app
        return run
    return ZERO_WIDTH_SPACE.join(word_tokenize(run, engine="newmm"))


def breakable(text: str) -> str:
    """Thai text with a zero-width space between words.

    Thai is written without spaces between words, and Qt on macOS breaks lines
    only at spaces, which leaves lines ending a phrase early. The marks let a
    line break between any two words; they print as nothing.
    """
    return THAI_RUN.sub(lambda match: _thai_breaks(match.group(0)), text)


def thai_family() -> str:
    """The TH Sarabun family this computer will print with (TH SarabunPSK if installed)."""
    ensure_fonts()
    available = set(QFontDatabase.families())
    return next((family for family in THAI_FAMILIES if family in available), "Sarabun")


@lru_cache(maxsize=8)
def _font_has(family: str):
    font = QFont(family)
    metrics = QFontMetricsF(font)
    return lru_cache(maxsize=1024)(lambda ch: metrics.inFontUcs4(ord(ch)))


def _missing_from(family: str, text: str) -> set[str]:
    """Characters of ``text`` (outside Thai and ASCII) that ``family`` has no glyph for."""
    if not family:
        return set()
    has = _font_has(thai_family())
    return {ch for ch in text if ord(ch) > 0x7f and not ("\u0e00" <= ch <= "\u0e7f") and ch != ZERO_WIDTH_SPACE
            and not has(ch)}


def layout_base_dpi() -> float:
    """The resolution Qt's text layout treats its pixel lengths as (Qt's qt_defaultDpiY)."""
    if QGuiApplication.testAttribute(Qt.ApplicationAttribute.AA_Use96Dpi):
        return 96.0
    screen = QGuiApplication.primaryScreen()
    return screen.logicalDotsPerInchY() if screen is not None else 100.0


def ensure_fonts() -> None:
    """Register the bundled Sarabun faces with Qt once (needs a QGuiApplication)."""
    global _fonts_loaded
    if _fonts_loaded:
        return
    for path in sorted(FONT_DIR.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(path))
    _fonts_loaded = True


def formal_date(value: date | datetime | str, language: str, *, with_time: bool = False) -> str:
    """15 ตุลาคม 2569 / 15 October 2026; with the time in Thai time when asked."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value) if "T" in value else date.fromisoformat(value[:10])
        except ValueError:
            return value
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(THAI_TIME)
        clock = f"{value:%H:%M}"
    else:
        clock = ""
    if language == "th":
        text = f"{value.day} {THAI_MONTHS[value.month - 1]} {value.year + 543}"
        return f"{text} เวลา {clock} น." if with_time and clock else text
    text = f"{value.day} {ENGLISH_MONTHS[value.month - 1]} {value.year}"
    return f"{text}, {clock}" if with_time and clock else text


# ----------------------------------------------------------------------
# Markdown → sections
# ----------------------------------------------------------------------
@dataclass
class Section:
    heading: str
    lines: list[str]


def split_sections(markdown: str) -> tuple[str, list[str], list[Section]]:
    """(title, lines before the first section, sections)."""
    title, preamble, sections = "", [], []
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("# ") and not title and not sections:
            title = line[2:].strip()
        elif line.startswith("## "):
            sections.append(Section(line[3:].strip(), []))
        elif sections:
            sections[-1].lines.append(line)
        else:
            preamble.append(line)
    return title, preamble, sections


def _table_rows(lines: list[str]) -> tuple[list[list[str]], list[str]]:
    """Cells of a pipe table and each column's alignment ("left"/"right"/"center")."""
    rows, aligns = [], []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            aligns = ["right" if c.endswith(":") and not c.startswith(":") else "center" if c.startswith(":") and c.endswith(":") else "left" for c in cells]
            continue
        rows.append(cells)
    return rows, aligns


def _blocks(lines: list[str]) -> list[tuple[str, object]]:
    """Group a section's lines into ("para", text), ("list", [items]), ("table", rows) and ("sub", text)."""
    blocks: list[tuple[str, object]] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append(("para", " ".join(paragraph)))
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            flush()
        elif line.startswith("|"):
            flush()
            table = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table.append(lines[index])
                index += 1
            blocks.append(("table", _table_rows(table)))
            continue
        elif line.startswith(("- ", "* ")):
            flush()
            if blocks and blocks[-1][0] == "list":
                blocks[-1][1].append(line[2:].strip())
            else:
                blocks.append(("list", [line[2:].strip()]))
        elif line.startswith("#"):
            flush()
            blocks.append(("sub", line.lstrip("#").strip()))
        else:
            paragraph.append(line)
        index += 1
    flush()
    return blocks


# ----------------------------------------------------------------------
# Building the document
# ----------------------------------------------------------------------
class _Builder:
    def __init__(self, device: QPagedPaintDevice, layout: Layout, page: QRectF, body: QRectF, language: str) -> None:
        self.layout = layout
        self.language = language
        self.dpi = device.logicalDpiY()
        self.base_dpi = layout_base_dpi()
        self.body_width = body.width()
        self.document = QTextDocument()
        self.document.documentLayout().setPaintDevice(device)
        # Whole sheets with the margins on the root frame: Qt then keeps every
        # line inside one sheet's text area, and the Thai marks above a page's
        # first line fall in that page's own top margin.
        frame = self.document.rootFrame().frameFormat()
        frame.setLeftMargin(self.from_device(body.left()))
        frame.setTopMargin(self.from_device(body.top()))
        frame.setRightMargin(self.from_device(page.right() - body.right()))
        frame.setBottomMargin(self.from_device(page.bottom() - body.bottom()))
        frame.setPadding(0)
        frame.setBorder(0)
        self.document.rootFrame().setFrameFormat(frame)
        self.document.setPageSize(page.size())
        self.document.setDefaultFont(self.font(layout.body_pt))
        self.cursor = QTextCursor(self.document)
        self.first_block = True
        self.headings: list[int] = []  # block numbers of section headings
        self.heading_names: dict[str, int] = {}  # section heading text → block number
        self.tables: list = []  # bordered tables, kept on one page with their heading

    # units ---------------------------------------------------------
    # Qt's text layout reads margins, padding, borders and indents as pixels
    # at the platform's base resolution (72 dpi on macOS, 96 elsewhere) and
    # scales them to the device itself; page size is in device pixels.
    def pt(self, points: float) -> float:
        return points * self.base_dpi / 72

    def mm(self, millimetres: float) -> float:
        return millimetres * self.base_dpi / 25.4

    def from_device(self, pixels: float) -> float:
        return pixels * self.base_dpi / self.dpi

    def font(self, size: float, *, bold: bool = False, italic: bool = False) -> QFont:
        font = QFont()
        font.setFamilies(list(self.layout.families))
        font.setPointSizeF(size)
        font.setBold(bold)
        font.setItalic(italic)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        return font

    def char(self, size: float | None = None, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setFont(self.font(size or self.layout.body_pt, bold=bold, italic=italic))
        fmt.setForeground(QBrush(INK))
        return fmt

    def block(self, *, align=Qt.AlignmentFlag.AlignLeft, before: float = 0, after: float | None = None,
              indent_mm: float = 0, left: float = 0) -> QTextBlockFormat:
        fmt = QTextBlockFormat()
        fmt.setAlignment(align)
        fmt.setTopMargin(self.pt(before))
        fmt.setBottomMargin(self.pt(self.layout.paragraph_after_pt if after is None else after))
        fmt.setTextIndent(indent_mm * self.dpi / 25.4)  # the one length Qt takes in device pixels
        fmt.setLeftMargin(left)
        fmt.setLineHeight(self.layout.line_height, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        return fmt

    # pieces --------------------------------------------------------
    def new_block(self, fmt: QTextBlockFormat, char: QTextCharFormat) -> None:
        if self.first_block:
            self.cursor.setBlockFormat(fmt)
            self.cursor.setBlockCharFormat(char)
            self.first_block = False
        else:
            self.cursor.insertBlock(fmt, char)

    def inline(self, text: str, base: QTextCharFormat) -> None:
        """Text with **bold**, *italic* and `code` spans."""
        for piece in INLINE.split(text):
            if not piece:
                continue
            fmt = QTextCharFormat(base)
            if piece.startswith("**") and piece.endswith("**"):
                piece = piece[2:-2]
                fmt.setFontWeight(QFont.Weight.Bold)
            elif piece.startswith("`") and piece.endswith("`"):
                piece = piece[1:-1]
            elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
                piece = piece[1:-1]
                fmt.setFontItalic(self.layout.italic_notes)
            self.text(piece, fmt)

    def text(self, text: str, fmt: QTextCharFormat) -> None:
        """Insert text; in an English report Thai runs are set in TH Sarabun at a matching size."""
        if self.language == "th" or not THAI_RUN.search(text):
            self._plain(breakable(text), fmt)
            return
        position = 0
        for match in THAI_RUN.finditer(text):
            if match.start() > position:
                self.cursor.insertText(text[position:match.start()], fmt)
            thai = QTextCharFormat(fmt)
            thai.setFontFamilies(list(THAI_FAMILIES))
            thai.setFontPointSize(fmt.font().pointSizeF() * THAI_IN_LATIN)
            thai.setFontItalic(False)
            self.cursor.insertText(_thai_breaks(match.group(0)), thai)
            position = match.end()
        if position < len(text):
            self.cursor.insertText(text[position:], fmt)

    def _plain(self, text: str, fmt: QTextCharFormat) -> None:
        """Insert text, drawing any character the TH Sarabun fonts lack in Sarabun at a matching size."""
        missing = _missing_from(self.layout.families[0] if self.language == "th" else "", text)
        if not missing:
            self.cursor.insertText(text, fmt)
            return
        run = ""
        for ch in text:
            if ch in missing:
                if run:
                    self.cursor.insertText(run, fmt)
                    run = ""
                other = QTextCharFormat(fmt)
                other.setFontFamilies(["Sarabun"])
                other.setFontPointSize(fmt.font().pointSizeF() * FALLBACK_SCALE)
                self.cursor.insertText(ch, other)
            else:
                run += ch
        if run:
            self.cursor.insertText(run, fmt)

    def paragraph(self, text: str, *, size: float | None = None, indent: bool = True, **kwargs) -> None:
        self.new_block(self.block(indent_mm=self.layout.first_line_indent_mm if indent else 0, **kwargs), self.char(size))
        self.inline(text, self.char(size))

    def title(self, organization: str, title: str) -> None:
        """The letterhead on page one: the logo, the clinic, and the report title, centred."""
        center = Qt.AlignmentFlag.AlignHCenter
        logo = QImage(str(LOGO))
        if not logo.isNull():
            self.document.addResource(QTextDocument.ResourceType.ImageResource, QUrl("pasascope-logo"), logo)
            self.new_block(self.block(align=center, after=4), self.char())
            image = QTextImageFormat()
            image.setName("pasascope-logo")
            image.setWidth(self.mm(LETTERHEAD_MM))
            image.setHeight(self.mm(LETTERHEAD_MM))
            self.cursor.insertImage(image)
        # The letterhead lines sit close together; the font's own spacing leaves
        # room for stacked Thai marks that a one-line heading does not need.
        tight = self.layout.title_line_height
        if organization:
            block = self.block(align=center, after=0)
            block.setLineHeight(tight, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            self.new_block(block, self.char(self.layout.organization_pt, bold=True))
            self.text(organization, self.char(self.layout.organization_pt, bold=True))
        block = self.block(align=center, after=10)
        block.setLineHeight(tight, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        self.new_block(block, self.char(self.layout.title_pt, bold=True))
        self.text(title, self.char(self.layout.title_pt, bold=True))

    def heading(self, number: int | None, text: str) -> None:
        label = f"{number}. {text}" if number else text
        fmt = self.block(before=self.layout.heading_before_pt, after=self.layout.heading_after_pt)
        fmt.setNonBreakableLines(True)
        self.new_block(fmt, self.char(bold=True))
        self.headings.append(self.cursor.block().blockNumber())
        self.heading_names[text] = self.cursor.block().blockNumber()
        self.text(label, self.char(bold=True))

    def subheading(self, text: str) -> None:
        self.new_block(self.block(before=self.layout.paragraph_after_pt, after=2), self.char(bold=True))
        self.text(text, self.char(bold=True))

    def bullets(self, items: list[str]) -> None:
        """A bullet list with every line of an item starting at the same place.

        Drawn as a borderless table: the bullet sits at ``list_marker_mm`` (the
        paragraph indent in Thai) and the text, wrapped lines included, at
        ``list_text_mm``.
        """
        marker = self.layout.list_marker_mm
        gap = self.layout.list_text_mm - marker
        fmt = QTextTableFormat()
        fmt.setBorder(0)
        fmt.setBorderStyle(QTextTableFormat.BorderStyle.BorderStyle_None)
        fmt.setCellSpacing(0)
        fmt.setCellPadding(0)
        fmt.setLeftMargin(self.mm(marker))
        fmt.setTopMargin(0)
        fmt.setBottomMargin(self.pt(self.layout.paragraph_after_pt))
        # Qt counts the left margin inside a table's fixed width.
        fmt.setWidth(QTextLength(QTextLength.Type.FixedLength, self.from_device(self.body_width)))
        fmt.setColumnWidthConstraints([
            QTextLength(QTextLength.Type.FixedLength, self.mm(gap)),
            QTextLength(QTextLength.Type.VariableLength, 0),
        ])
        if self.first_block:
            self.first_block = False
        table = self.cursor.insertTable(len(items), 2, fmt)
        for row, item in enumerate(items):
            for column, text in ((0, self.layout.bullet), (1, item)):
                cell = table.cellAt(row, column)
                cell_format = QTextTableCellFormat(cell.format().toTableCellFormat())
                cell_format.setBottomPadding(self.pt(2) if row < len(items) - 1 else 0)
                cell.setFormat(cell_format)
                cursor = cell.firstCursorPosition()
                block = QTextBlockFormat()
                block.setLineHeight(self.layout.line_height, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
                cursor.setBlockFormat(block)
                saved, self.cursor = self.cursor, cursor
                self.inline(text, self.char())
                self.cursor = saved
        self.cursor.movePosition(QTextCursor.MoveOperation.End)

    def _table(self, rows: int, columns: int, widths: list[float], *, header: bool) -> object:
        fmt = QTextTableFormat()
        fmt.setBorder(1)
        fmt.setBorderBrush(QBrush(TABLE_LINE))
        fmt.setBorderStyle(QTextTableFormat.BorderStyle.BorderStyle_Solid)
        fmt.setBorderCollapse(True)
        fmt.setCellSpacing(0)
        fmt.setCellPadding(self.pt(3))
        self._cell_top_padding = self.pt(self.layout.cell_padding_pt[0])
        self._cell_bottom_padding = self.pt(self.layout.cell_padding_pt[1])
        fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
        fmt.setColumnWidthConstraints([QTextLength(QTextLength.Type.PercentageLength, w) for w in widths])
        fmt.setTopMargin(self.pt(2))
        fmt.setBottomMargin(self.pt(self.layout.paragraph_after_pt))
        if header:
            fmt.setHeaderRowCount(1)
        if self.first_block:
            self.first_block = False
        table = self.cursor.insertTable(rows, columns, fmt)
        self.tables.append(table)
        return table

    def _cell(self, table, row: int, column: int, text: str, *, bold: bool = False, fill: QColor | None = None,
              align=Qt.AlignmentFlag.AlignLeft) -> None:
        cell = table.cellAt(row, column)
        cell_format = QTextTableCellFormat(cell.format().toTableCellFormat())
        cell_format.setTopPadding(self._cell_top_padding)
        cell_format.setBottomPadding(self._cell_bottom_padding)
        if fill is not None:
            cell_format.setBackground(QBrush(fill))
        cell.setFormat(cell_format)
        cursor = cell.firstCursorPosition()
        block = QTextBlockFormat()
        block.setAlignment(align)
        block.setLineHeight(self.layout.line_height, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        cursor.setBlockFormat(block)
        saved, self.cursor = self.cursor, cursor
        self.inline(text, self.char(bold=bold))
        self.cursor = saved

    def details(self, pairs: list[tuple[str, str]]) -> None:
        table = self._table(len(pairs), 2, [34, 66], header=False)
        for row, (key, value) in enumerate(pairs):
            if ISO_DATE.match(value):
                value = formal_date(value, self.language)
            self._cell(table, row, 0, key, bold=True, fill=LABEL_FILL)
            self._cell(table, row, 1, value)
        self.cursor.movePosition(QTextCursor.MoveOperation.End)

    def data_table(self, rows: list[list[str]], aligns: list[str]) -> None:
        if not rows:
            return
        columns = max(len(r) for r in rows)
        widths = [72] + [28 / (columns - 1)] * (columns - 1) if columns > 1 else [100]
        table = self._table(len(rows), columns, widths, header=True)
        for r, cells in enumerate(rows):
            for c in range(columns):
                text = cells[c] if c < len(cells) else ""
                align = {"right": Qt.AlignmentFlag.AlignRight, "center": Qt.AlignmentFlag.AlignHCenter}.get(
                    aligns[c] if c < len(aligns) else "left", Qt.AlignmentFlag.AlignLeft)
                self._cell(table, r, c, text, bold=r == 0, fill=LABEL_FILL if r == 0 else None,
                           align=Qt.AlignmentFlag.AlignHCenter if r == 0 else align)
        self.cursor.movePosition(QTextCursor.MoveOperation.End)

    def signature(self, meta: ReportMeta) -> int:
        """The signature block on the right half; returns its first block number."""
        words = self.layout.words
        left = self.from_device(self.body_width * 0.42)
        center = Qt.AlignmentFlag.AlignHCenter
        dots = "." * 44
        self.new_block(self.block(align=center, before=self.layout.heading_before_pt * 2, after=2, left=left), self.char())
        first = self.cursor.block().blockNumber()
        if meta.signed:
            self.text(f"{words['sign']}  ", self.char())
            name = self.char(italic=self.layout.italic_notes)
            name.setUnderlineStyle(QTextCharFormat.UnderlineStyle.DotLine)
            self.text(f"  {meta.signed_by}  ", name)
        else:
            self.text(f"{words['sign']} {dots}", self.char())
        lines = [f"( {meta.signed_by} )" if meta.signed_by else f"( {dots} )", words["role"]]
        if meta.signed:
            lines.append(f"{words['date']} {formal_date(meta.signed_at, self.language, with_time=True)}")
        else:
            lines.append(f"{words['date']} {'.' * 36}")
        for line in lines:
            self.new_block(self.block(align=center, after=2, left=left), self.char())
            self.text(line, self.char())
        note = words["e_signed"] if meta.signed else words["draft_note"]
        note_format = self.char(self.layout.small_pt, italic=self.layout.italic_notes)
        self.new_block(self.block(align=center, before=4, after=0, left=left), note_format)
        self.text(note, note_format)
        return first


def build_document(device: QPagedPaintDevice, markdown: str, meta: ReportMeta, layout: Layout, page: QRectF,
                   body: QRectF, language: str) -> tuple[QTextDocument, list[int], int | None]:
    """The report as a QTextDocument paginated on ``page`` sheets with text in ``body``; also heading and signature block numbers."""
    builder = _Builder(device, layout, page, body, language)
    title, preamble, sections = split_sections(markdown)
    builder.title(meta.organization, title or meta.title)
    for kind, value in _blocks(preamble):
        _add_block(builder, kind, value)
    number = 0
    signoff_extra: list[str] | None = None
    for section in sections:
        if section.heading in SIGNOFF_SECTIONS:
            signoff_extra = [
                line for line in section.lines
                if line.strip() and not SIGNOFF_LINES.match(line.strip()) and line.strip() not in SIGNOFF_PLACEHOLDERS
            ]
            continue
        number += 1
        builder.heading(number, section.heading)
        pairs = _detail_pairs(section)
        if pairs is not None:
            builder.details(pairs)
            continue
        for kind, value in _blocks(section.lines):
            _add_block(builder, kind, value)
    for kind, value in _blocks(signoff_extra or []):
        _add_block(builder, kind, value)
    signature = builder.signature(meta)
    builder.document.setProperty("heading_names", builder.heading_names)
    builder.document.setProperty("table_spans", [
        (table.firstCursorPosition().block().blockNumber(), table.lastCursorPosition().block().blockNumber())
        for table in builder.tables
    ])
    return builder.document, builder.headings, signature


def _detail_pairs(section: Section) -> list[tuple[str, str]] | None:
    """The section's "- label: value" lines, when it is a details section made only of them."""
    if section.heading not in DETAIL_SECTIONS:
        return None
    pairs = []
    for line in section.lines:
        text = line.strip()
        if not text:
            continue
        match = re.match(r"^[-*] ([^:]{1,60}):\s*(.*)$", text)
        if not match:
            return None
        pairs.append((match.group(1).strip(), match.group(2).strip()))
    return pairs or None


def _add_block(builder: _Builder, kind: str, value) -> None:
    if kind == "para":
        builder.paragraph(value)
    elif kind == "list":
        builder.bullets(value)
    elif kind == "table":
        rows, aligns = value
        builder.data_table(rows, aligns)
    elif kind == "sub":
        builder.subheading(value)


# ----------------------------------------------------------------------
# Pagination
# ----------------------------------------------------------------------
def _block_page(document: QTextDocument, block_number: int, page_height: float) -> tuple[int, float]:
    """(page index, offset from that page's top) of a block's first line."""
    block = document.findBlockByNumber(block_number)
    rect = document.documentLayout().blockBoundingRect(block)
    return int(rect.top() // page_height), rect.top() % page_height


def breaks_needed(document: QTextDocument, headings: list[int], signature: int | None, page: QRectF, body: QRectF,
                  min_after_heading: float, breaks: set[int] = frozenset()) -> set[int]:
    """Blocks to start a new page at, so that pages read as whole pieces.

    * a heading never sits alone at the foot of a page;
    * a table that fits on one page is not split: it moves, with its
      section heading, to the next page;
    * the signature block stays on the page where the report text ends,
      taking the last section (the limitations) with it when it has to move.
    """
    needed = set()
    page_height = page.height()

    def page_of(number: int) -> int:
        return _block_page(document, number, page_height)[0]

    def heading_before(number: int) -> int | None:
        earlier = [h for h in headings if h < number]
        return earlier[-1] if earlier else None

    for number in headings:
        _, offset = _block_page(document, number, page_height)
        if body.bottom() - offset < min_after_heading and offset > body.top() + 1:
            needed.add(number)

    layout = document.documentLayout()
    for first, last in document.property("table_spans") or []:
        if page_of(first) == page_of(last):
            continue
        top = layout.blockBoundingRect(document.findBlockByNumber(first)).top()
        bottom = layout.blockBoundingRect(document.findBlockByNumber(last)).bottom()
        anchor = heading_before(first)
        if bottom - top < body.height() * 0.9 and anchor is not None:
            needed.add(anchor)

    if signature is not None:
        signature_page = page_of(signature)
        text_page = page_of(signature - 1) if signature > 0 else signature_page
        split = page_of(document.blockCount() - 1) != signature_page
        if split or signature_page != text_page:
            last_heading = heading_before(signature)
            if last_heading is not None and last_heading not in breaks:
                needed.add(last_heading)
            else:
                needed.add(signature)
    return needed


def _break_before(document: QTextDocument, block_number: int) -> None:
    block = document.findBlockByNumber(block_number)
    cursor = QTextCursor(block)
    fmt = block.blockFormat()
    fmt.setPageBreakPolicy(QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore)
    fmt.setTopMargin(0)
    cursor.setBlockFormat(fmt)


def _paint_furniture(painter: QPainter, page: QRectF, body: QRectF, meta: ReportMeta, layout: Layout,
                     language: str, index: int, pages: int, mm, pt) -> None:
    words = layout.words
    small = QFont()
    small.setFamilies(list(layout.families))
    small.setPointSizeF(layout.small_pt)
    painter.setFont(small)
    painter.setPen(QPen(INK))
    line_gap = mm(2.5)
    text_height = pt(layout.small_pt * 1.6)

    # Page one carries the letterhead instead of the running header.
    if index > 0:
        header_line = body.top() - mm(6)
        header = QRectF(body.left(), header_line - line_gap - text_height, body.width(), text_height)
        left_text = painter.fontMetrics().elidedText(meta.organization or meta.title, Qt.TextElideMode.ElideRight,
                                                     int(body.width() * 0.4))
        painter.drawText(header, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, left_text)
        painter.drawText(header, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, words["confidential"])
        painter.setPen(QPen(RULE, pt(0.5)))
        painter.drawLine(QPointF(body.left(), header_line), QPointF(body.right(), header_line))
    else:
        painter.setPen(QPen(RULE, pt(0.5)))

    footer_line = body.bottom() + mm(5)
    painter.drawLine(QPointF(body.left(), footer_line), QPointF(body.right(), footer_line))
    footer = QRectF(body.left(), footer_line + line_gap, body.width(), text_height)
    painter.setPen(QPen(INK))
    bits = []
    if meta.child_code:
        bits.append(f"{words['child']} {meta.child_code}")
    if meta.session_date:
        bits.append(f"{words['session']} {formal_date(meta.session_date, language)}")
    painter.drawText(footer, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "   ·   ".join(bits))
    painter.drawText(footer, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
                     words["page"].format(page=index + 1, pages=pages))
    if index == 0:
        confidential = QRectF(body.left(), footer.bottom(), body.width(), text_height)
        painter.drawText(confidential, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, words["confidential"])


def _paint_logo(painter: QPainter, body: QRectF, mm) -> None:
    """The PasaScope mark, faint and centred behind the text of every page."""
    logo = QImage(str(LOGO))
    if logo.isNull():
        return
    side = min(body.width(), mm(120))
    target = QRectF(body.center().x() - side / 2, body.center().y() - side / 2, side, side)
    painter.save()
    painter.setOpacity(LOGO_OPACITY)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawImage(target, logo)
    painter.restore()


def _paint_draft_stamp(painter: QPainter, page: QRectF, body: QRectF, layout: Layout, mm, pt) -> None:
    """A boxed "ร่าง" / "DRAFT" at the top centre of the page, as Thai draft documents are marked."""
    font = QFont()
    font.setFamilies(list(layout.families))
    font.setPointSizeF(layout.body_pt)
    font.setBold(True)
    painter.save()
    painter.setFont(font)
    text = layout.words["draft"]
    width = painter.fontMetrics().horizontalAdvance(text) + mm(8)
    height = mm(7.5)
    box = QRectF(page.center().x() - width / 2, mm(9), width, height)
    painter.setPen(QPen(DRAFT_INK, pt(0.9)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(box, mm(1), mm(1))
    painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
    painter.restore()


def paint_report(device: QPagedPaintDevice, markdown: str, meta: ReportMeta, *, outline: dict | None = None) -> int:
    """Draw the report on ``device`` (zero page margins, A4); returns the number of pages.

    ``outline``, when given, is filled with each section heading's page number
    (from 1), the first and last page of each table (``"__tables__"``) and the
    signature block's first and last page with the page of the text before it
    (``"__signature__"``).
    """
    ensure_fonts()
    if not meta.title:
        meta = replace(meta, title=split_sections(markdown)[0])
    language = meta.language or report_language(markdown)
    layout = LAYOUTS.get(language, LAYOUTS["en"])
    dpi = device.logicalDpiY()

    def mm(value: float) -> float:
        return value * dpi / 25.4

    def pt(value: float) -> float:
        return value * dpi / 72

    page = QRectF(0, 0, device.width(), device.height())
    left, top, right, bottom = (mm(v) for v in layout.margins_mm)
    body = QRectF(left, top, page.width() - left - right, page.height() - top - bottom)

    # Qt lays text out lazily and loses track when a format changes after a
    # query, so page breaks are found on one build and applied to a fresh one.
    # One break at a time, earliest first: a break moves everything after it,
    # so later problems are judged again on the new layout.
    breaks: set[int] = set()
    for _ in range(12):
        document, headings, signature = build_document(device, markdown, meta, layout, page, body, language)
        for number in sorted(breaks):
            _break_before(document, number)
        needed = breaks_needed(document, headings, signature, page, body, pt(layout.body_pt * 4), breaks) - breaks
        if not needed:
            break
        breaks.add(min(needed))
    # Count pages from where the text ends: Qt's own count includes the last
    # page's bottom margin and can add a blank page when the text ends low.
    last = document.documentLayout().blockBoundingRect(document.lastBlock())
    pages = max(1, min(document.pageCount(), int((last.bottom() - 1) // page.height()) + 1))
    if outline is not None:
        def page_of(number: int) -> int:
            return _block_page(document, number, page.height())[0] + 1

        for name, number in (document.property("heading_names") or {}).items():
            outline[name] = page_of(number)
        # Where the pieces that must not break landed, for checks and tests.
        outline["__tables__"] = [(page_of(a), page_of(b)) for a, b in document.property("table_spans") or []]
        if signature is not None:
            outline["__signature__"] = (page_of(signature), page_of(document.blockCount() - 1), page_of(signature - 1))

    painter = QPainter(device)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    for index in range(pages):
        if index:
            device.newPage()
        _paint_logo(painter, body, mm)
        _paint_furniture(painter, page, body, meta, layout, language, index, pages, mm, pt)
        painter.save()
        painter.translate(0, -index * page.height())
        document.drawContents(painter, QRectF(0, index * page.height(), page.width(), page.height()))
        painter.restore()
        if not meta.signed:
            _paint_draft_stamp(painter, page, body, layout, mm, pt)
    painter.end()
    return pages


def a4_layout() -> QPageLayout:
    return QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0),
                       QPageLayout.Unit.Millimeter)


def write_report_pdf(markdown: str, destination: Path, meta: ReportMeta | None = None, *, title: str = "") -> Path:
    """Write the report as an A4 PDF at ``destination``."""
    meta = meta or ReportMeta(title=title)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = QPdfWriter(str(destination))
    writer.setResolution(PDF_DPI)
    writer.setTitle(meta.title or title or split_sections(markdown)[0])
    writer.setCreator("PasaScope")
    writer.setPageLayout(a4_layout())
    paint_report(writer, markdown, meta)
    return destination
