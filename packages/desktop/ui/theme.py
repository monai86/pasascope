"""Colours and the application style sheet.

Blue carries structure and primary actions; amber marks what needs the
therapist's attention; red is kept for withdrawal and failures. Text sizes
favour long reading sessions over density.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

INK = "#14213d"
INK_SOFT = "#4a5670"
MUTED = "#7a8499"
LINE = "#dde3ee"
SURFACE = "#ffffff"
CANVAS = "#f4f6fa"
SIDEBAR = "#eef2f8"
PRIMARY = "#1f5fbf"
PRIMARY_DARK = "#174a96"
PRIMARY_SOFT = "#e5eefb"
ATTENTION = "#b26a00"
ATTENTION_SOFT = "#fff3dd"
DANGER = "#b3261e"
DANGER_SOFT = "#fdeceb"
OK = "#1f6f8b"
OK_SOFT = "#e3f2f7"

SPEAKER_COLORS = {
    "CHI": "#1f5fbf",
    "INV": "#6b5b95",
    "MOT": "#6b5b95",
    "FAT": "#6b5b95",
    "THER": "#6b5b95",
    "UNK": "#b26a00",
}

STYLE = f"""
QWidget {{ color: {INK}; font-size: 14px; }}
QMainWindow, QDialog {{ background: {CANVAS}; }}
#Sidebar {{ background: {SIDEBAR}; border-right: 1px solid {LINE}; }}
#Brand {{ font-size: 19px; font-weight: 700; color: {PRIMARY_DARK}; }}
#BrandSub {{ color: {MUTED}; font-size: 12px; }}
#Card {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 10px; }}
#CaseTitle {{ font-size: 22px; font-weight: 700; }}
#SectionTitle {{ font-size: 16px; font-weight: 700; }}
#Muted {{ color: {MUTED}; }}
#Hint {{ color: {INK_SOFT}; }}
#EmptyTitle {{ font-size: 18px; font-weight: 600; color: {INK_SOFT}; }}
#MetricTitle {{ color: {INK_SOFT}; font-size: 13px; }}
#MetricValue {{ font-size: 26px; font-weight: 700; color: {PRIMARY_DARK}; }}
#Notice {{ border-radius: 8px; padding: 8px 12px; background: {ATTENTION_SOFT}; color: {ATTENTION}; }}
#Notice[kind="primary"] {{ background: {PRIMARY_SOFT}; color: {PRIMARY_DARK}; }}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 6px; padding: 6px 8px;
    selection-background-color: {PRIMARY_SOFT}; selection-color: {INK};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {{
    border: 1px solid {PRIMARY};
}}

QPushButton {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 6px; padding: 7px 14px;
}}
QPushButton:hover {{ border-color: {PRIMARY}; }}
QPushButton:disabled {{ color: {MUTED}; background: {CANVAS}; }}
QPushButton[role="primary"] {{ background: {PRIMARY}; color: white; border: 1px solid {PRIMARY}; font-weight: 600; }}
QPushButton[role="primary"]:hover {{ background: {PRIMARY_DARK}; }}
QPushButton[role="primary"]:disabled {{ background: #9db5dc; border-color: #9db5dc; color: #f2f5fa; }}
QPushButton[role="danger"] {{ color: {DANGER}; }}
QPushButton[role="danger"]:hover {{ border-color: {DANGER}; }}

QListWidget {{ background: transparent; border: none; outline: none; }}
QListWidget::item {{ padding: 2px; border-radius: 8px; }}
QListWidget::item:selected {{ background: {PRIMARY_SOFT}; color: {INK}; }}
QListWidget::item:hover:!selected {{ background: #e6ebf3; }}

QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    padding: 9px 18px; margin-right: 4px; border: none; border-bottom: 3px solid transparent;
    color: {INK_SOFT}; font-weight: 600; background: transparent;
}}
QTabBar::tab:selected {{ color: {PRIMARY_DARK}; border-bottom: 3px solid {PRIMARY}; }}
QTabBar::tab:disabled {{ color: #b3bac8; }}

QTableWidget, QTableView {{
    background: {SURFACE}; border: 1px solid {LINE}; border-radius: 8px; gridline-color: {LINE};
    selection-background-color: {PRIMARY_SOFT}; selection-color: {INK};
}}
QHeaderView::section {{
    background: {CANVAS}; border: none; border-bottom: 1px solid {LINE}; padding: 6px 8px;
    color: {INK_SOFT}; font-weight: 600;
}}
QProgressBar {{ border: 1px solid {LINE}; border-radius: 6px; background: {SURFACE}; height: 10px; text-align: center; }}
QProgressBar::chunk {{ background: {PRIMARY}; border-radius: 5px; }}
QStatusBar {{ background: {SURFACE}; border-top: 1px solid {LINE}; color: {INK_SOFT}; }}
QToolTip {{ background: {INK}; color: white; border: none; padding: 6px; }}
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
    fg, bg = {
        "ok": (OK, OK_SOFT),
        "attention": (ATTENTION, ATTENTION_SOFT),
        "danger": (DANGER, DANGER_SOFT),
        "primary": (PRIMARY_DARK, PRIMARY_SOFT),
    }.get(kind, (INK_SOFT, CANVAS))
    return (
        f"color: {fg}; background: {bg}; border-radius: 10px; padding: 3px 10px;"
        " font-size: 12px; font-weight: 600;"
    )
