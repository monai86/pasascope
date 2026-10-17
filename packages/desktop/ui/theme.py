"""Colours and the application style sheet.

A quiet working surface in the manner of Notion's desktop app: white pages,
a warm grey sidebar, near-black warm text, hairline dividers and grey hover
fills, with colour kept for meaning. Blue marks primary actions and the
selection; amber what needs the therapist's attention; red withdrawal and
failures. No green. Tokens follow those in Notion's desktop shell (text
rgb(55,53,47), dividers at 9% of it, hover at 8%, accent #2383E2).
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

INK = "#37352f"
INK_SOFT = "#5f5e5b"
MUTED = "#787774"
FAINT = "#a5a29d"
LINE = "#e9e9e7"
LINE_STRONG = "#d9d8d5"
SURFACE = "#ffffff"
CANVAS = "#ffffff"
SIDEBAR = "#f7f7f5"
HOVER = "#efefee"
PRESSED = "#e3e2e0"
PRIMARY = "#2383e2"
PRIMARY_DARK = "#1b6ec2"
PRIMARY_SOFT = "#e7f3f8"
ATTENTION = "#c4650a"
ATTENTION_SOFT = "#fbecdd"
DANGER = "#d44c47"
DANGER_SOFT = "#fdebec"
OK = "#337ea9"
OK_SOFT = "#e7f3f8"
ADULT = "#9065b0"

SPEAKER_COLORS = {
    "CHI": PRIMARY_DARK,
    "INV": ADULT,
    "MOT": ADULT,
    "FAT": ADULT,
    "THER": ADULT,
    "UNK": ATTENTION,
}

STYLE = f"""
QWidget {{ color: {INK}; font-size: 14px; }}
QMainWindow, QDialog {{ background: {CANVAS}; }}
#Sidebar {{ background: {SIDEBAR}; border-right: 1px solid {LINE}; }}
#Brand {{ font-size: 15px; font-weight: 600; color: {INK}; }}
#BrandSub {{ color: {MUTED}; font-size: 12px; }}
#Card {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 6px; }}
#Panel {{ background: {SIDEBAR}; border: none; border-radius: 6px; }}
#CaseTitle {{ font-size: 24px; font-weight: 700; }}
#SectionTitle {{ font-size: 15px; font-weight: 600; }}
#Muted {{ color: {MUTED}; }}
#Hint {{ color: {MUTED}; font-size: 13px; }}
#EmptyTitle {{ font-size: 16px; font-weight: 600; color: {INK}; }}
#MetricTitle {{ color: {MUTED}; font-size: 12px; }}
#MetricValue {{ font-size: 24px; font-weight: 600; color: {INK}; }}
#Notice {{ border-radius: 4px; padding: 8px 12px; background: {ATTENTION_SOFT}; color: {INK}; }}
#Notice[kind="primary"] {{ background: {PRIMARY_SOFT}; color: {INK}; }}
#InspectorKey {{ color: {MUTED}; font-size: 12px; }}
#InspectorValue {{ color: {INK}; }}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit {{
    background: {SURFACE}; border: 1px solid {LINE_STRONG}; border-radius: 4px; padding: 5px 8px;
    selection-background-color: {PRIMARY_SOFT}; selection-color: {INK};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {{
    border: 1px solid {PRIMARY};
}}
#Sidebar QLineEdit {{ background: {HOVER}; border: 1px solid transparent; }}
#Sidebar QLineEdit:focus {{ background: {SURFACE}; border: 1px solid {PRIMARY}; }}

QPushButton {{
    background: {SURFACE}; border: 1px solid {LINE_STRONG}; border-radius: 4px; padding: 5px 12px; color: {INK};
}}
QPushButton:hover {{ background: {HOVER}; }}
QPushButton:pressed {{ background: {PRESSED}; }}
QPushButton:disabled {{ color: {FAINT}; background: {SURFACE}; border-color: {LINE}; }}
QPushButton[role="primary"] {{ background: {PRIMARY}; color: white; border: 1px solid {PRIMARY}; font-weight: 500; }}
QPushButton[role="primary"]:hover {{ background: {PRIMARY_DARK}; border-color: {PRIMARY_DARK}; }}
QPushButton[role="primary"]:disabled {{ background: #a7cdf2; border-color: #a7cdf2; color: white; }}
QPushButton[role="danger"] {{ color: {DANGER}; }}
QPushButton[role="danger"]:hover {{ background: {DANGER_SOFT}; border-color: {DANGER_SOFT}; }}
QPushButton[role="ghost"] {{ background: transparent; border: 1px solid transparent; color: {INK_SOFT}; text-align: left; }}
QPushButton[role="ghost"]:hover {{ background: {HOVER}; }}

QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 4px 6px; border-radius: 4px; color: {INK}; }}
QListWidget::item:selected {{ background: {PRESSED}; color: {INK}; }}
QListWidget::item:hover:!selected {{ background: {HOVER}; }}

QTabWidget::pane {{ border: none; border-top: 1px solid {LINE}; }}
QTabBar::tab {{
    padding: 7px 14px; margin-right: 2px; border: none; border-bottom: 2px solid transparent;
    color: {MUTED}; font-weight: 500; background: transparent;
}}
QTabBar::tab:hover {{ color: {INK}; }}
QTabBar::tab:selected {{ color: {INK}; border-bottom: 2px solid {INK}; }}
QTabBar::tab:disabled {{ color: {FAINT}; }}

QTableWidget, QTableView {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 4px; gridline-color: {LINE};
    selection-background-color: {PRIMARY_SOFT}; selection-color: {INK}; alternate-background-color: #fbfbfa;
}}
QHeaderView::section {{
    background: {SURFACE}; border: none; border-bottom: 1px solid {LINE}; padding: 6px 8px;
    color: {MUTED}; font-weight: 500; font-size: 13px;
}}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {LINE_STRONG}; border-radius: 4px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {FAINT}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {LINE_STRONG}; border-radius: 4px; min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QProgressBar {{ border: none; border-radius: 3px; background: {HOVER}; height: 6px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {PRIMARY}; border-radius: 3px; }}
QStatusBar {{ background: {SIDEBAR}; border-top: 1px solid {LINE}; color: {MUTED}; font-size: 12px; }}
QMenuBar {{ background: {SIDEBAR}; }}
QMenu {{ background: {SURFACE}; border: 1px solid {LINE}; padding: 4px; }}
QMenu::item {{ padding: 5px 18px; border-radius: 4px; }}
QMenu::item:selected {{ background: {HOVER}; color: {INK}; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: {LINE}; }}
QToolTip {{ background: {INK}; color: white; border: none; padding: 6px 8px; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(CANVAS))
    palette.setColor(QPalette.ColorRole.Base, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.Text, QColor(INK))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(INK))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(PRIMARY_SOFT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(INK))
    app.setPalette(palette)
    font = QFont()
    font.setPointSize(13)
    app.setFont(font)
    app.setStyleSheet(STYLE)


def chip_style(kind: str) -> str:
    """A Notion-style tag: tinted background, coloured text, small radius."""
    fg, bg = {
        "ok": (OK, OK_SOFT),
        "attention": (ATTENTION, ATTENTION_SOFT),
        "danger": (DANGER, DANGER_SOFT),
        "primary": (PRIMARY_DARK, PRIMARY_SOFT),
    }.get(kind, (INK_SOFT, HOVER))
    return (
        f"color: {fg}; background: {bg}; border-radius: 3px; padding: 2px 7px;"
        " font-size: 12px; font-weight: 500;"
    )
