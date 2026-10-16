"""Draw a report to PDF with Qt, which uses the system's Thai fonts."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QColor, QFont, QPageLayout, QPageSize, QPdfWriter, QTextDocument, QTextFrameFormat, QTextTable

from packages.desktop.ui import theme

THAI_FONTS = ["Sarabun", "Thonburi", "Leelawadee UI", "Noto Sans Thai", "Tahoma"]


def _style_tables(document: QTextDocument) -> None:
    for frame in document.rootFrame().childFrames():
        if isinstance(frame, QTextTable):
            fmt = frame.format()
            fmt.setBorder(1)
            fmt.setBorderBrush(QColor(theme.LINE))
            fmt.setBorderStyle(QTextFrameFormat.BorderStyle.BorderStyle_Solid)
            fmt.setCellPadding(5)
            fmt.setCellSpacing(0)
            frame.setFormat(fmt)


def write_report_pdf(markdown: str, destination: Path, title: str = "") -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    writer = QPdfWriter(str(destination))
    writer.setResolution(144)
    writer.setTitle(title)
    writer.setCreator("PasaScope")
    writer.setPageLayout(
        QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait, QMarginsF(18, 18, 18, 18), QPageLayout.Unit.Millimeter)
    )
    document = QTextDocument()
    font = QFont()
    font.setFamilies(THAI_FONTS)
    font.setPointSizeF(11)
    document.setDefaultFont(font)
    document.setDefaultStyleSheet(f"h1 {{ color: {theme.INK}; }} h2 {{ color: {theme.PRIMARY_DARK}; }}")
    document.setMarkdown(markdown)
    _style_tables(document)
    # Lay the text out on the printable area in points, so 11 pt prints as 11 pt.
    document.setPageSize(writer.pageLayout().paintRect(QPageLayout.Unit.Point).size())
    document.print_(writer)
    return destination
