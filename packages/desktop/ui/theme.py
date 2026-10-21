"""Colours and the application style sheet, in a light and a dark set.

A working surface laid out like a code editor's workbench: white pages in a
light grey frame, hairline dividers and grey hover fills, with colour kept
for meaning. Blue marks primary actions and the
selection; amber what needs the therapist's attention; red withdrawal and
failures. No green. The neutrals follow a code editor's 2026 light and dark
themes (frame #F8F8FA / #191A1B around a #FFFFFF / #121314 page, hairline
borders, near-black or light-grey text), with a blue accent (#0069CC) that
white text reads on.

The colour names below are module attributes that ``apply_theme`` rewrites,
so read them as ``theme.INK`` when a widget is built or painted, never copy
them into a module-level constant. Changing the theme rebuilds the main
window (``MainWindow.restyle``), which builds every widget again with the
new colours. Printed reports and the PDF keep their own black-on-white
colours in ``pdf.py``.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

LIGHT = {
    "INK": "#202020",
    "INK_SOFT": "#3f3f46",
    "MUTED": "#5f5f68",
    "FAINT": "#9a9aa2",
    "LINE": "#e7e7ea",
    "LINE_STRONG": "#d5d5da",
    "SURFACE": "#ffffff",
    "CANVAS": "#ffffff",  # the page an editor draws on
    "SIDEBAR": "#f8f8fa",  # the frame around the page: activity bar, side bar, tabs, status bar
    "HOVER": "#ececef",
    "PRESSED": "#dfdfe3",
    "ROW_ALT": "#fafafb",
    "PRIMARY": "#0069cc",
    "PRIMARY_DARK": "#005bb2",  # primary button hover
    "PRIMARY_TEXT": "#0062bf",  # blue text and marks on the page
    "PRIMARY_SOFT": "#e3eefa",
    "PRIMARY_DISABLED": "#9fc3ea",
    "PRIMARY_DISABLED_TEXT": "#ffffff",
    "ON_PRIMARY": "#ffffff",
    "LINK": "#0062bf",
    "ATTENTION": "#a85400",
    "ATTENTION_SOFT": "#fbecdc",
    "DANGER": "#c4314b",
    "DANGER_SOFT": "#fbe9ec",
    "OK": "#0062bf",
    "OK_SOFT": "#e3eefa",
    "ADULT": "#7b4fb0",
    "TOOLTIP": "#202020",
    "TOOLTIP_TEXT": "#ffffff",
    "TOAST_BORDER": "#202020",
}

DARK = {
    "INK": "#cccccc",
    "INK_SOFT": "#b4b4b6",
    "MUTED": "#9a9a9e",
    "FAINT": "#626266",
    "LINE": "#2a2b2c",
    "LINE_STRONG": "#3a3b3d",
    "SURFACE": "#121314",
    "CANVAS": "#121314",
    "SIDEBAR": "#191a1b",
    "HOVER": "#242526",
    "PRESSED": "#2e2f31",
    "ROW_ALT": "#161718",
    "PRIMARY": "#2272c3",
    "PRIMARY_DARK": "#2d80d6",
    "PRIMARY_TEXT": "#5ea6e6",
    "PRIMARY_SOFT": "#16304a",
    "PRIMARY_DISABLED": "#1d3a57",
    "PRIMARY_DISABLED_TEXT": "#7f93a8",
    "ON_PRIMARY": "#ffffff",
    "LINK": "#5ea6e6",
    "ATTENTION": "#e0914a",
    "ATTENTION_SOFT": "#3a2a1b",
    "DANGER": "#ef7470",
    "DANGER_SOFT": "#3c2324",
    "OK": "#5ea6e6",
    "OK_SOFT": "#16304a",
    "ADULT": "#b48ce0",
    "TOOLTIP": "#2e2f31",
    "TOOLTIP_TEXT": "#e6e6e6",
    "TOAST_BORDER": "#3a3b3d",
}

ASSETS = Path(__file__).resolve().parent / "assets"
CHECK_MARK = (ASSETS / "check.svg").as_posix()
MODES = ("system", "light", "dark")
SETTINGS_KEY = "appearance/theme"

# The light set until apply_theme says otherwise.
INK = INK_SOFT = MUTED = FAINT = LINE = LINE_STRONG = SURFACE = CANVAS = SIDEBAR = ""
HOVER = PRESSED = ROW_ALT = PRIMARY = PRIMARY_DARK = PRIMARY_TEXT = PRIMARY_SOFT = ""
PRIMARY_DISABLED = PRIMARY_DISABLED_TEXT = ON_PRIMARY = LINK = ""
ATTENTION = ATTENTION_SOFT = DANGER = DANGER_SOFT = OK = OK_SOFT = ADULT = TOOLTIP = TOOLTIP_TEXT = TOAST_BORDER = ""
SPEAKER_COLORS: dict[str, str] = {}
STYLE = ""
_dark = False


def build_style() -> str:
    close_icon = (ASSETS / ("close-dark.svg" if _dark else "close-light.svg")).as_posix()
    return f"""
QWidget {{ color: {INK}; font-size: 14px; }}
QMainWindow, QDialog {{ background: {CANVAS}; }}
#Sidebar {{ background: {SIDEBAR}; border-right: 1px solid {LINE}; }}
#Brand {{ font-size: 15px; font-weight: 600; color: {INK}; }}
#BrandSub {{ color: {MUTED}; font-size: 12px; }}
#Card {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 6px; }}
#Metric {{ background: transparent; border: none; border-left: 1px solid {LINE_STRONG}; }}
#Article {{ border: none; background: {SURFACE}; }}
#Panel {{ background: {SIDEBAR}; border: none; border-radius: 6px; }}
#CaseTitle {{ font-size: 24px; font-weight: 700; }}
#SectionTitle {{ font-size: 15px; font-weight: 600; }}
#Muted {{ color: {MUTED}; }}
#Hint {{ color: {MUTED}; font-size: 13px; }}
#EmptyTitle {{ font-size: 16px; font-weight: 600; color: {INK}; }}
#MetricTitle {{ color: {MUTED}; font-size: 12px; }}
#MetricValue {{ font-size: 22px; font-weight: 600; color: {INK}; }}
#Notice {{ border-radius: 4px; padding: 8px 12px; background: {ATTENTION_SOFT}; color: {INK}; }}
#Notice[kind="primary"] {{ background: {PRIMARY_SOFT}; color: {INK}; }}
#Chip {{
    border-radius: 3px; padding: 2px 7px; font-size: 12px; font-weight: 500; color: {INK_SOFT}; background: {HOVER};
}}
#Chip[kind="ok"] {{ color: {OK}; background: {OK_SOFT}; }}
#Chip[kind="attention"] {{ color: {ATTENTION}; background: {ATTENTION_SOFT}; }}
#Chip[kind="danger"] {{ color: {DANGER}; background: {DANGER_SOFT}; }}
#Chip[kind="primary"] {{ color: {PRIMARY_TEXT}; background: {PRIMARY_SOFT}; }}
#ErrorText {{ color: {DANGER}; }}
#AttentionText {{ color: {ATTENTION}; }}
#Step[state="done"] {{ color: {FAINT}; text-decoration: line-through; }}
#Step[state="current"] {{ color: {INK}; font-weight: 600; }}
#Step[state="todo"] {{ color: {MUTED}; }}
#Evidence {{ background: {SIDEBAR}; border-radius: 4px; }}
#EvidenceChild {{ color: {PRIMARY_TEXT}; font-weight: 600; }}
#RecordTime {{ font-size: 28px; font-weight: 700; color: {INK}; }}
#ReportText {{ font-family: 'Sarabun'; font-size: 15px; }}
#PreviewBackdrop, #PreviewBackdrop QGraphicsView {{ background: {SIDEBAR}; border: none; }}
#OnboardingSide {{ background: {SIDEBAR}; border-right: 1px solid {LINE}; }}
#WelcomeTitle {{ font-size: 22px; font-weight: 600; color: {INK}; }}
#StepItem {{ padding: 6px 8px; border-radius: 4px; color: {MUTED}; }}
#StepItem[state="current"] {{ background: {PRESSED}; color: {INK}; font-weight: 600; }}
#StepItem[state="done"] {{ color: {INK_SOFT}; }}
#FeatureTile {{ background: {SIDEBAR}; border: 1px solid {LINE}; border-radius: 6px; }}
#NoteItem {{ border: none; border-left: 2px solid {PRIMARY}; }}
QPushButton[role="segment"] {{ padding: 3px 10px; color: {INK_SOFT}; }}
QPushButton[role="segment"]:checked {{ background: {PRIMARY_SOFT}; color: {PRIMARY_TEXT}; border-color: {PRIMARY}; }}
#InspectorKey {{ color: {MUTED}; font-size: 12px; }}
#InspectorValue {{ color: {INK}; }}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit {{
    background: {SURFACE}; border: 1px solid {LINE_STRONG}; border-radius: 4px; padding: 5px 8px;
    selection-background-color: {PRIMARY_SOFT}; selection-color: {INK};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {{
    border: 1px solid {PRIMARY};
}}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {LINE}; selection-background-color: {HOVER}; selection-color: {INK};
}}
#Sidebar QLineEdit {{ background: {HOVER}; border: 1px solid transparent; }}
#Sidebar QLineEdit:focus {{ background: {SURFACE}; border: 1px solid {PRIMARY}; }}

QPushButton {{
    background: {SURFACE}; border: 1px solid {LINE_STRONG}; border-radius: 4px; padding: 5px 12px; color: {INK};
}}
QPushButton:hover {{ background: {HOVER}; }}
QPushButton:pressed {{ background: {PRESSED}; }}
QPushButton:disabled {{ color: {FAINT}; background: {SURFACE}; border-color: {LINE}; }}
QPushButton[role="primary"] {{ background: {PRIMARY}; color: {ON_PRIMARY}; border: 1px solid {PRIMARY}; font-weight: 500; }}
QPushButton[role="primary"]:hover {{ background: {PRIMARY_DARK}; border-color: {PRIMARY_DARK}; }}
QPushButton[role="primary"]:disabled {{
    background: {PRIMARY_DISABLED}; border-color: {PRIMARY_DISABLED}; color: {PRIMARY_DISABLED_TEXT};
}}
QPushButton[role="danger"] {{ color: {DANGER}; }}
QPushButton[role="danger"]:hover {{ background: {DANGER_SOFT}; border-color: {DANGER_SOFT}; }}
QPushButton[role="ghost"] {{ background: transparent; border: 1px solid transparent; color: {INK_SOFT}; text-align: left; padding: 5px 8px; }}
QPushButton[role="ghost"]:hover {{ background: {HOVER}; }}
QPushButton[role="nav"] {{ background: transparent; border: none; color: {INK_SOFT}; text-align: left; padding: 6px 8px; font-weight: 500; }}
QPushButton[role="nav"]:hover {{ background: {HOVER}; }}
QPushButton[role="nav"]:checked {{ background: {PRESSED}; color: {INK}; }}
#SidebarHeading {{ color: {MUTED}; font-size: 12px; font-weight: 500; }}
#SidebarRule {{ background: {LINE}; border: none; }}
#TherapistName {{ color: {INK}; font-weight: 500; }}
#Sidebar QPushButton[role="ghost"] {{ color: {PRIMARY_TEXT}; padding: 4px 8px; }}

QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px; border: 1px solid {FAINT}; border-radius: 3px; background: {SURFACE};
}}
QCheckBox::indicator:hover {{ border-color: {MUTED}; }}
QCheckBox::indicator:checked {{ background: {PRIMARY}; border-color: {PRIMARY}; image: url("{CHECK_MARK}"); }}
QCheckBox::indicator:disabled {{ border-color: {LINE_STRONG}; background: {HOVER}; }}
QCheckBox:disabled {{ color: {FAINT}; }}

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
    selection-background-color: {PRIMARY_SOFT}; selection-color: {INK}; alternate-background-color: {ROW_ALT};
}}
QHeaderView::section {{
    background: {SURFACE}; border: none; border-bottom: 1px solid {LINE}; padding: 6px 8px;
    color: {MUTED}; font-weight: 500; font-size: 13px;
}}
QTableCornerButton::section {{ background: {SURFACE}; border: none; }}
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
QMenu::item:disabled {{ color: {FAINT}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 4px 6px; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: {LINE}; }}
/* The workbench: activity bar, side bar, editor tabs, breadcrumbs, palette, status bar */
#ActivityBar {{ background: {SIDEBAR}; border-right: 1px solid {LINE}; }}
QToolButton#ActivityItem {{ border: none; border-left: 2px solid transparent; background: transparent; }}
QToolButton#ActivityItem:hover {{ background: {HOVER}; }}
QToolButton#ActivityItem:checked {{ border-left: 2px solid {PRIMARY}; }}
#SideBar {{ background: {SIDEBAR}; border-right: 1px solid {LINE}; }}
#SideBarHeader {{ background: transparent; }}
#SideBarTitle {{ color: {INK_SOFT}; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }}
#SideBarSection {{ color: {INK_SOFT}; font-size: 11px; font-weight: 700; padding: 4px 20px; }}
QToolButton#HeaderAction {{ border: none; border-radius: 4px; background: transparent; }}
QToolButton#HeaderAction:hover {{ background: {HOVER}; }}
#SideBar QLineEdit {{ background: {SURFACE}; border: 1px solid {LINE_STRONG}; margin: 0 12px; }}
#SideBar QLineEdit:focus {{ border: 1px solid {PRIMARY}; }}
QTreeWidget#CaseTree, QListWidget#TopicList {{ background: transparent; border: none; outline: none; }}
QTreeWidget#CaseTree::item, QListWidget#TopicList::item {{ height: 24px; padding: 0 4px; color: {INK}; border: none; }}
QListWidget#TopicList::item {{ padding-left: 20px; }}
QTreeWidget#CaseTree::item:hover, QListWidget#TopicList::item:hover {{ background: {HOVER}; }}
QTreeWidget#CaseTree::item:selected, QListWidget#TopicList::item:selected {{ background: {PRESSED}; color: {INK}; }}
#SideBarFooter {{ border-top: 1px solid {LINE}; }}
QSplitter#Workbench::handle {{ background: {LINE}; }}
#EditorTabsRow {{ background: {SIDEBAR}; border-bottom: 1px solid {LINE}; }}
QTabBar#EditorTabs {{ background: transparent; }}
QTabBar#EditorTabs::tab {{
    height: 34px; padding: 0 6px 0 12px; margin: 0; border: none; border-right: 1px solid {LINE};
    border-top: 2px solid transparent; background: {SIDEBAR}; color: {MUTED}; font-weight: 400;
}}
QTabBar#EditorTabs::tab:hover {{ color: {INK}; }}
QTabBar#EditorTabs::tab:selected {{ background: {CANVAS}; color: {INK}; border-top: 2px solid {PRIMARY}; }}
QTabBar#EditorTabs::close-button {{ image: url("{close_icon}"); subcontrol-position: right; width: 16px; height: 16px; border-radius: 3px; margin-left: 4px; }}
QTabBar#EditorTabs::close-button:hover {{ background: {PRESSED}; }}
QTabBar#EditorTabs QToolButton {{ background: {SIDEBAR}; border: none; }}
#EditorStack, #Watermark {{ background: {CANVAS}; }}
#WatermarkText {{ color: {MUTED}; font-size: 13px; }}
#Keycap {{ color: {INK_SOFT}; background: {HOVER}; border: 1px solid {LINE_STRONG}; border-radius: 3px; padding: 1px 6px; font-size: 12px; }}
#Breadcrumbs {{ background: {CANVAS}; }}
QToolButton#Crumb {{ border: none; padding: 1px 3px; color: {MUTED}; font-size: 12px; background: transparent; }}
QToolButton#Crumb:hover {{ color: {INK}; background: {HOVER}; border-radius: 3px; }}
QToolButton#Crumb[last="true"] {{ color: {INK}; }}
QToolButton#Crumb:disabled {{ color: {MUTED}; }}
#CrumbSeparator {{ color: {FAINT}; font-size: 12px; }}
#CommandPalette {{ background: {SIDEBAR}; border: 1px solid {LINE_STRONG}; border-radius: 8px; }}
QLineEdit#PaletteInput {{ background: {SURFACE}; border: 1px solid {PRIMARY}; padding: 5px 8px; font-size: 13px; }}
QListWidget#PaletteList {{ background: transparent; border: none; outline: none; font-size: 13px; }}
QListWidget#PaletteList::item {{ height: 26px; padding: 0 8px; border-radius: 4px; }}
QListWidget#PaletteList::item:selected {{ background: {PRIMARY_SOFT}; color: {INK}; }}
#EditorHeader {{ background: {CANVAS}; }}
QStatusBar {{ font-size: 12px; padding: 0; }}  /* 22 px high, set by the window */
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ padding: 0 8px; color: {MUTED}; font-size: 12px; }}
#StatusBadge {{ background: {PRIMARY}; color: {ON_PRIMARY}; padding: 0 10px; }}
#Toast {{
    background: {TOOLTIP}; color: {TOOLTIP_TEXT}; border: 1px solid {TOAST_BORDER}; border-radius: 8px;
    padding: 9px 16px; font-size: 13px;
}}
QToolTip {{ background: {TOOLTIP}; color: {TOOLTIP_TEXT}; border: none; padding: 6px 8px; }}
"""


def _use_tokens(dark: bool) -> None:
    global _dark, STYLE
    _dark = dark
    globals().update(DARK if dark else LIGHT)
    SPEAKER_COLORS.clear()
    SPEAKER_COLORS.update({
        "CHI": PRIMARY_TEXT,
        "INV": ADULT,
        "MOT": ADULT,
        "FAT": ADULT,
        "THER": ADULT,
        "UNK": ATTENTION,
    })
    STYLE = build_style()


_use_tokens(False)


def saved_mode() -> str:
    """``system`` (follow the computer), ``light`` or ``dark``."""
    mode = QSettings().value(SETTINGS_KEY, "system")
    return mode if mode in MODES else "system"


def save_mode(mode: str) -> None:
    if mode not in MODES:
        raise ValueError(f"unknown theme {mode!r}")
    QSettings().setValue(SETTINGS_KEY, mode)


def is_dark() -> bool:
    """Whether the colours in use are the dark set."""
    return _dark


def wants_dark(app: QApplication, mode: str | None = None) -> bool:
    """Whether ``mode`` (the saved one by default) means the dark set right now.

    Also tells Qt which scheme the app uses, so on macOS and Windows the title
    bar and the system's own dialogs match the window.
    """
    mode = mode or saved_mode()
    hints = app.styleHints()
    scheme = {"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}.get(mode, Qt.ColorScheme.Unknown)
    if hasattr(hints, "setColorScheme"):  # Qt 6.8 and later
        hints.setColorScheme(scheme)
    if mode == "system":
        return hints.colorScheme() == Qt.ColorScheme.Dark
    return mode == "dark"


def _palette(app: QApplication, dark: bool) -> QPalette:
    roles = QPalette.ColorRole
    # Light keeps Fusion's own palette with the few roles it always changed;
    # dark has to set every role Fusion draws with (check boxes, arrows, frames).
    palette = app.style().standardPalette()
    pairs = [
        (roles.Window, CANVAS), (roles.Base, SURFACE), (roles.Text, INK), (roles.WindowText, INK),
        (roles.Highlight, PRIMARY_SOFT), (roles.HighlightedText, INK), (roles.Link, LINK),
    ]
    if dark:
        pairs += [
            (roles.AlternateBase, ROW_ALT), (roles.Button, SURFACE), (roles.ButtonText, INK),
            (roles.BrightText, ON_PRIMARY), (roles.ToolTipBase, TOOLTIP), (roles.ToolTipText, TOOLTIP_TEXT),
            (roles.PlaceholderText, FAINT), (roles.LinkVisited, LINK), (roles.Light, PRESSED),
            (roles.Midlight, HOVER), (roles.Mid, LINE_STRONG), (roles.Dark, "#0f0f0f"), (roles.Shadow, "#000000"),
        ]
        if hasattr(roles, "Accent"):
            pairs.append((roles.Accent, PRIMARY))
    for role, colour in pairs:
        palette.setColor(role, QColor(colour))
    if dark:
        for role in (roles.WindowText, roles.Text, roles.ButtonText):
            palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(FAINT))
    return palette


def apply_theme(app: QApplication, mode: str | None = None) -> bool:
    """Use the light or dark set that ``mode`` (the saved one by default) asks for; returns whether it is dark."""
    dark = wants_dark(app, mode)
    _use_tokens(dark)
    app.setStyle("Fusion")
    app.setPalette(_palette(app, dark))
    font = QFont()
    font.setPointSize(13)
    app.setFont(font)
    app.setStyleSheet(STYLE)
    return dark

