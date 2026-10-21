"""The parts of the window, laid out the way a code editor's workbench is.

An activity bar of icons on the far left picks what the side bar shows; the
side bar lists cases (or Knowledge topics); the editor area holds tabs for
Home, cases, sessions and Knowledge; a status bar runs along the bottom; and
a command palette (Ctrl/Cmd+Shift+P) finds any case, session or command by
typing. Sizes follow the same conventions: a 48 px activity bar, 35 px
headers and tabs, a 22 px status bar. The icons are drawn here, in the
theme's colours, rather than taken from any icon set.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
import sys

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.core.i18n import tr
from packages.desktop.ui import motion, theme

MOD = "⌘" if sys.platform == "darwin" else "Ctrl+"
SHIFT = "⇧" if sys.platform == "darwin" else "Shift+"


# ----------------------------------------------------------------------
# Icons, drawn as lines on a 24-unit grid
# ----------------------------------------------------------------------
def _draw(name: str, painter: QPainter, colour: QColor) -> None:
    pen = QPen(colour, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if name == "home":
        path = QPainterPath()
        path.moveTo(4, 11)
        path.lineTo(12, 4)
        path.lineTo(20, 11)
        painter.drawPath(path)
        painter.drawRect(QRectF(6.5, 10.5, 11, 9))
        painter.drawRect(QRectF(10.5, 14, 3, 5.5))
    elif name == "cases":
        painter.drawEllipse(QPointF(9, 8.5), 3, 3)
        arc = QPainterPath()
        arc.moveTo(3.5, 19.5)
        arc.cubicTo(3.5, 14.5, 14.5, 14.5, 14.5, 19.5)
        painter.drawPath(arc)
        painter.drawEllipse(QPointF(16, 9.5), 2.5, 2.5)
        arc2 = QPainterPath()
        arc2.moveTo(16, 14.2)
        arc2.cubicTo(18.5, 14.2, 20.5, 15.8, 20.5, 19)
        painter.drawPath(arc2)
    elif name == "knowledge":
        book = QPainterPath()
        book.moveTo(12, 7)
        book.cubicTo(9.5, 5.2, 6.5, 5, 4, 5.5)
        book.lineTo(4, 18.5)
        book.cubicTo(6.5, 18, 9.5, 18.2, 12, 20)
        book.cubicTo(14.5, 18.2, 17.5, 18, 20, 18.5)
        book.lineTo(20, 5.5)
        book.cubicTo(17.5, 5, 14.5, 5.2, 12, 7)
        book.lineTo(12, 20)
        painter.drawPath(book)
    elif name == "search":
        painter.drawEllipse(QPointF(10.5, 10.5), 5.5, 5.5)
        painter.drawLine(QPointF(14.6, 14.6), QPointF(19.5, 19.5))
    elif name == "settings":
        path = QPainterPath()
        teeth = 8
        for index in range(teeth * 2):
            angle = math.pi * index / teeth
            radius = 8.2 if index % 2 == 0 else 6.4
            for offset in (-0.17, 0.17):
                point = QPointF(12 + radius * math.cos(angle + offset), 12 + radius * math.sin(angle + offset))
                path.lineTo(point) if path.elementCount() else path.moveTo(point)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawEllipse(QPointF(12, 12), 2.6, 2.6)
    elif name == "add":
        painter.drawLine(QPointF(12, 6), QPointF(12, 18))
        painter.drawLine(QPointF(6, 12), QPointF(18, 12))
    elif name == "collapse":
        for top in (8.0, 13.0):
            chevron = QPainterPath()
            chevron.moveTo(7, top + 4)
            chevron.lineTo(12, top)
            chevron.lineTo(17, top + 4)
            painter.drawPath(chevron)
    elif name == "refresh":
        arc = QPainterPath()
        arc.arcMoveTo(QRectF(5.5, 5.5, 13, 13), 60)
        arc.arcTo(QRectF(5.5, 5.5, 13, 13), 60, 280)
        painter.drawPath(arc)
        head = QPainterPath()
        head.moveTo(15.2, 4.2)
        head.lineTo(15.4, 7.4)
        head.lineTo(18.6, 7.0)
        painter.drawPath(head)


def icon(name: str, colour: str | None = None, checked_colour: str | None = None, size: int = 24) -> QIcon:
    """A line icon in the theme's colours; ``checked_colour`` draws the checked state too."""
    result = QIcon()
    for state, hex_colour in ((QIcon.State.Off, colour or theme.MUTED), (QIcon.State.On, checked_colour or colour or theme.MUTED)):
        for scale in (1, 2):
            pixmap = QPixmap(size * scale, size * scale)
            pixmap.setDevicePixelRatio(scale)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(size / 24, size / 24)
            _draw(name, painter, QColor(hex_colour))
            painter.end()
            result.addPixmap(pixmap, QIcon.Mode.Normal, state)
    return result


# ----------------------------------------------------------------------
# Activity bar
# ----------------------------------------------------------------------
class ActivityBar(QFrame):
    """The column of icons on the far left. Views are exclusive; actions just fire."""

    view_selected = Signal(str)

    WIDTH = 48

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ActivityBar")
        self.setFixedWidth(self.WIDTH)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 4, 0, 6)
        self._layout.setSpacing(0)
        self._bottom = QVBoxLayout()
        self._bottom.setSpacing(0)
        self._layout.addStretch(1)
        self._layout.addLayout(self._bottom)
        self._top_count = 0
        self.views: dict[str, QToolButton] = {}

    def _button(self, icon_name: str, tooltip: str) -> QToolButton:
        item = QToolButton()
        item.setObjectName("ActivityItem")
        item.setIcon(icon(icon_name, theme.MUTED, theme.INK))
        item.setIconSize(QSize(24, 24))
        item.setFixedSize(self.WIDTH, self.WIDTH)
        item.setToolTip(tooltip)
        item.setAccessibleName(tooltip.split("(")[0].strip())
        item.setCursor(Qt.CursorShape.PointingHandCursor)
        return item

    def add_view(self, key: str, icon_name: str, tooltip: str) -> QToolButton:
        item = self._button(icon_name, tooltip)
        item.setCheckable(True)
        item.setProperty("kind", "view")
        item.clicked.connect(lambda: self.view_selected.emit(key))
        self._layout.insertWidget(self._top_count, item)
        self._top_count += 1
        self.views[key] = item
        return item

    def add_action(self, icon_name: str, tooltip: str, callback: Callable[[], None], bottom: bool = False,
                   checkable: bool = False) -> QToolButton:
        item = self._button(icon_name, tooltip)
        item.setCheckable(checkable)
        item.setProperty("kind", "action")
        item.clicked.connect(lambda: callback())
        if bottom:
            self._bottom.addWidget(item)
        else:
            self._layout.insertWidget(self._top_count, item)
            self._top_count += 1
        return item

    def set_current_view(self, key: str | None) -> None:
        for name, item in self.views.items():
            item.setChecked(name == key)


# ----------------------------------------------------------------------
# Side bar
# ----------------------------------------------------------------------
class SideBarHeader(QFrame):
    """The 35 px title row of a side bar view: an upper-case name and small icon actions."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SideBarHeader")
        self.setFixedHeight(35)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 8, 0)
        layout.setSpacing(2)
        self.title = QLabel(title.upper())
        self.title.setObjectName("SideBarTitle")
        layout.addWidget(self.title, 1)
        self._actions = layout

    def add_action(self, icon_name: str, tooltip: str, callback: Callable[[], None]) -> QToolButton:
        item = QToolButton()
        item.setObjectName("HeaderAction")
        item.setIcon(icon(icon_name, theme.INK_SOFT, size=16))
        item.setIconSize(QSize(16, 16))
        item.setFixedSize(24, 24)
        item.setToolTip(tooltip)
        item.setAccessibleName(tooltip)
        item.setCursor(Qt.CursorShape.PointingHandCursor)
        item.clicked.connect(lambda: callback())
        self._actions.addWidget(item)
        return item


# ----------------------------------------------------------------------
# Editor area: tabs over a stack, with a watermark when nothing is open
# ----------------------------------------------------------------------
class EditorArea(QWidget):
    """Tabs for open editors. Each editor is a widget under a string key ("home", "session:…")."""

    current_changed = Signal(str)
    close_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("EditorArea")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.bar = QTabBar()
        self.bar.setObjectName("EditorTabs")
        self.bar.setDocumentMode(True)
        self.bar.setTabsClosable(True)
        self.bar.setMovable(True)
        self.bar.setExpanding(False)
        self.bar.setElideMode(Qt.TextElideMode.ElideNone)  # full names; scroll buttons when they do not fit
        self.bar.setUsesScrollButtons(True)
        self.bar.setDrawBase(False)
        self.bar.currentChanged.connect(self._on_current)
        self.bar.tabCloseRequested.connect(lambda index: self.close_requested.emit(self.key_at(index)))
        self.bar.installEventFilter(self)
        bar_row = QFrame()
        bar_row.setObjectName("EditorTabsRow")
        bar_row.setFixedHeight(36)  # tabs are 34 px plus their 2 px top line; fixed so an empty bar keeps its place
        self.bar.setFixedHeight(36)
        bar_layout = QHBoxLayout(bar_row)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)
        bar_layout.addWidget(self.bar)
        bar_layout.addStretch(1)
        layout.addWidget(bar_row)
        self.stack = QStackedWidget()
        self.stack.setObjectName("EditorStack")
        layout.addWidget(self.stack, 1)
        self.watermark = Watermark()
        self.stack.addWidget(self.watermark)
        self.editors: dict[str, QWidget] = {}
        self._titles: dict[str, str] = {}
        self._dirty: set[str] = set()

    # ------------------------------------------------------------------
    def key_at(self, index: int) -> str:
        return self.bar.tabData(index) or ""

    def index_of(self, key: str) -> int:
        return next((i for i in range(self.bar.count()) if self.bar.tabData(i) == key), -1)

    def current_key(self) -> str | None:
        index = self.bar.currentIndex()
        return self.key_at(index) if index >= 0 else None

    def current_editor(self) -> QWidget | None:
        key = self.current_key()
        return self.editors.get(key) if key else None

    def keys(self) -> list[str]:
        return [self.key_at(i) for i in range(self.bar.count())]

    def open_editor(self, key: str, editor: QWidget, title: str, tooltip: str = "", closable: bool = True) -> QWidget:
        """Show ``key``'s editor, adding its tab after the current one when it is new."""
        if key not in self.editors:
            self.editors[key] = editor
            self.stack.addWidget(editor)
            # The bar reports the new current tab while inserting, before it carries its key.
            self.bar.blockSignals(True)
            index = self.bar.insertTab(self.bar.currentIndex() + 1, title)
            self.bar.setTabData(index, key)
            self.bar.blockSignals(False)
            self._titles[key] = title
            if not closable:
                self.bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, None)
                self.bar.setTabButton(index, QTabBar.ButtonPosition.LeftSide, None)
        self.set_title(key, title, tooltip)
        index = self.index_of(key)
        if self.bar.currentIndex() != index:
            self.bar.setCurrentIndex(index)  # reports the change itself
        elif self.stack.currentWidget() is not self.editors[key]:
            self._on_current(index)
        return self.editors[key]

    def close_editor(self, key: str) -> QWidget | None:
        index = self.index_of(key)
        editor = self.editors.pop(key, None)
        self._titles.pop(key, None)
        self._dirty.discard(key)
        if index >= 0:
            self.bar.removeTab(index)
        if editor is not None:
            self.stack.removeWidget(editor)
        if self.bar.count() == 0:
            self.stack.setCurrentWidget(self.watermark)
            self.current_changed.emit("")
        return editor

    def set_title(self, key: str, title: str, tooltip: str = "") -> None:
        index = self.index_of(key)
        if index < 0:
            return
        self._titles[key] = title
        self.bar.setTabText(index, ("● " if key in self._dirty else "") + title)
        if tooltip:
            self.bar.setTabToolTip(index, tooltip)

    def set_dirty(self, key: str, dirty: bool) -> None:
        if (key in self._dirty) == dirty:
            return
        (self._dirty.add if dirty else self._dirty.discard)(key)
        self.set_title(key, self._titles.get(key, ""))

    def _on_current(self, index: int) -> None:
        key = self.key_at(index) if index >= 0 else ""
        editor = self.editors.get(key)
        if editor is not None and self.stack.currentWidget() is not editor:
            self.stack.setCurrentWidget(editor)
            motion.fade_in(editor)
        self.current_changed.emit(key)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt override
        try:
            return self._handle_event(watched, event)
        except RuntimeError:  # the window is being torn down at quit
            return False

    def _handle_event(self, watched: QObject, event: QEvent) -> bool:
        # A middle click closes a tab, as in browsers and editors.
        if watched is self.bar and event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.MiddleButton:
            index = self.bar.tabAt(event.position().toPoint())
            if index >= 0:
                self.close_requested.emit(self.key_at(index))
                return True
        return False


class Watermark(QWidget):
    """What the editor area shows with every tab closed: the shortcuts that open things."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Watermark")
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        rows = [
            (tr("ค้นหาคำสั่งทั้งหมด", "Show all commands"), f"{SHIFT}{MOD}P"),
            (tr("เปิดเคสหรือ session", "Open a case or session"), f"{MOD}P"),
            (tr("เพิ่มเคส", "New case"), f"{MOD}N"),
            (tr("หน้าแรก", "Home"), f"{SHIFT}{MOD}H"),
            (tr("ความรู้", "Knowledge"), "F1"),
        ]
        for text, keys in rows:
            row = QHBoxLayout()
            row.addStretch(1)
            name = QLabel(text)
            name.setObjectName("WatermarkText")
            name.setFixedWidth(220)
            name.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(name)
            row.addSpacing(14)
            key = QLabel(keys)
            key.setObjectName("Keycap")
            row.addWidget(key)
            row.addStretch(1)
            spacer = QWidget()
            spacer.setFixedWidth(120)
            row.addWidget(spacer)
            layout.addLayout(row)
        layout.addStretch(2)


# ----------------------------------------------------------------------
# Breadcrumbs
# ----------------------------------------------------------------------
class Breadcrumbs(QFrame):
    """``Case › Session › Step``: where an editor is, each part clickable when it leads somewhere."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Breadcrumbs")
        self.setFixedHeight(26)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(14, 0, 14, 0)
        self._layout.setSpacing(2)
        self.parts: list[QWidget] = []

    def set_parts(self, parts: list[tuple[str, Callable[[], None] | None]]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.parts = []
        for index, (text, action) in enumerate(parts):
            if index:
                sep = QLabel("›")
                sep.setObjectName("CrumbSeparator")
                self._layout.addWidget(sep)
            part = QToolButton()
            part.setObjectName("Crumb")
            part.setText(text)
            part.setProperty("last", "true" if index == len(parts) - 1 else "false")
            part.setAutoRaise(True)
            part.setEnabled(action is not None or index == len(parts) - 1)
            if action is not None:
                part.setCursor(Qt.CursorShape.PointingHandCursor)
                part.clicked.connect(lambda _=False, a=action: a())
            self._layout.addWidget(part)
            self.parts.append(part)
        self._layout.addStretch(1)


# ----------------------------------------------------------------------
# Command palette
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Command:
    label: str
    run: Callable[[], None]
    detail: str = ""
    group: str = ""
    shortcut: str = ""


def match_score(query: str, text: str) -> int | None:
    """How well ``query`` matches ``text``: higher is better, None when it does not match.

    Every typed word must appear, as a substring or as letters in order;
    substrings at the start of a word score highest.
    """
    text_lower = text.lower()
    score = 0
    for word in query.lower().split():
        position = text_lower.find(word)
        if position >= 0:
            score += 30 if position == 0 or not text_lower[position - 1].isalnum() else 20
            continue
        at = 0
        for char in word:
            at = text_lower.find(char, at)
            if at < 0:
                return None
            at += 1
        score += 5
    return score


class CommandPalette(QFrame):
    """A box at the top of the window: type to find a case, session or command, Enter to run it."""

    WIDTH = 600

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.setObjectName("CommandPalette")
        self.host = host
        self.commands: list[Command] = []
        self.shown: list[Command] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        self.input = QLineEdit()
        self.input.setObjectName("PaletteInput")
        self.input.textChanged.connect(self._filter)
        self.input.installEventFilter(self)
        layout.addWidget(self.input)
        self.list = QListWidget()
        self.list.setObjectName("PaletteList")
        self.list.setUniformItemSizes(True)
        self.list.itemActivated.connect(self._run_item)
        self.list.itemClicked.connect(self._run_item)
        layout.addWidget(self.list)
        self.hide()
        host.installEventFilter(self)

    def open(self, commands: list[Command], placeholder: str, text: str = "") -> None:
        self.commands = commands
        self.input.setPlaceholderText(placeholder)
        self.input.setText(text)
        self._filter(text)
        self._place()
        self.show()
        self.raise_()
        self.input.setFocus()
        self.input.selectAll()

    def _place(self) -> None:
        width = min(self.WIDTH, self.host.width() - 40)
        rows = min(12, max(1, self.list.count()))
        height = 44 + rows * 26 + 12
        self.setFixedSize(width, height)
        top = self.host.menuWidget().height() if hasattr(self.host, "menuWidget") and self.host.menuWidget() else 0
        self.move((self.host.width() - width) // 2, top + 8)

    def _filter(self, text: str) -> None:
        if text.strip():
            scored = [(match_score(text, f"{c.group} {c.label} {c.detail}"), i, c) for i, c in enumerate(self.commands)]
            ranked = sorted(((s, i, c) for s, i, c in scored if s is not None), key=lambda t: (-t[0], t[1]))
            self.shown = [c for _, _, c in ranked][:60]
        else:
            self.shown = self.commands[:60]
        self.list.clear()
        for command in self.shown:
            prefix = f"{command.group}: " if command.group else ""
            text_line = prefix + command.label + (f"      {command.detail}" if command.detail else "")
            item = QListWidgetItem(text_line)
            if command.shortcut:
                item.setToolTip(command.shortcut)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)
        if self.isVisible():
            self._place()

    def _run_item(self, item: QListWidgetItem) -> None:
        row = self.list.row(item)
        if 0 <= row < len(self.shown):
            command = self.shown[row]
            self.hide()
            command.run()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt override
        try:
            return self._handle_event(watched, event)
        except RuntimeError:  # the window is being torn down at quit
            return False

    def _handle_event(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                row = self.list.currentRow() + (1 if key == Qt.Key.Key_Down else -1)
                self.list.setCurrentRow(max(0, min(self.list.count() - 1, row)))
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self.list.currentItem()
                if item is not None:
                    self._run_item(item)
                return True
            if key == Qt.Key.Key_Escape:
                self.hide()
                return True
        if watched is self.input and event.type() == QEvent.Type.FocusOut and self.isVisible():
            focus = self.host.focusWidget() if hasattr(self.host, "focusWidget") else None
            if focus is not self.list:
                self.hide()
        if watched is self.host and event.type() == QEvent.Type.Resize and self.isVisible():
            self._place()
        return False


def shortcut_text(sequence: QKeySequence) -> str:
    return sequence.toString(QKeySequence.SequenceFormat.NativeText)


def spacer(width: int = 0) -> QWidget:
    widget = QWidget()
    widget.setSizePolicy(QSizePolicy.Policy.Expanding if not width else QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
    if width:
        widget.setFixedWidth(width)
    return widget
