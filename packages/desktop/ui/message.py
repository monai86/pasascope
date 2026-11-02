"""Alerts and confirmations drawn in PasaScope's own style.

``QMessageBox`` looks like the operating system (a macOS alert with its
title bar and system icons), not like the rest of the app. ``MessageBox`` is
a frameless card in the theme's colours: a tinted icon badge, the title as a
heading, the message, and the app's own buttons with the main one in blue (or
red when it removes something). The window behind it dims while it is open.

The module functions take the same arguments as ``QMessageBox``'s static
methods and return the same ``QMessageBox.StandardButton`` values, so a call
reads ``message.question(self, title, text)``. Tests replace these functions
(``monkeypatch.setattr(message, "question", ...)``) instead of opening a box.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from packages.desktop.core.i18n import tr
from packages.desktop.ui import motion, theme

Button = QMessageBox.StandardButton
KINDS = ("info", "warning", "critical", "question")

# The buttons that agree, in the order a caller would prefer as the default.
_AFFIRMATIVE = (Button.Yes, Button.Save, Button.Ok, Button.Open, Button.Retry, Button.YesToAll, Button.Apply)
# The buttons Escape and the window's close stand for, in order.
_ESCAPE = (Button.Cancel, Button.No, Button.Close, Button.Abort, Button.Ignore, Button.NoToAll, Button.Ok)
# Left-hand side, apart from the rest (macOS puts "Don't save" there).
_APART = (Button.Discard,)
# Every standard button a call can ask for, in the order they are added.
_ORDER = (
    Button.Discard, Button.Cancel, Button.No, Button.NoToAll, Button.Abort, Button.Ignore, Button.Close,
    Button.Open, Button.Retry, Button.Apply, Button.YesToAll, Button.Yes, Button.Save, Button.Ok,
)


def _label(button: Button) -> str:
    return {
        Button.Ok: tr("ตกลง", "OK"),
        Button.Yes: tr("ใช่", "Yes"),
        Button.No: tr("ไม่", "No"),
        Button.Cancel: tr("ยกเลิก", "Cancel"),
        Button.Save: tr("บันทึก", "Save"),
        Button.Discard: tr("ไม่บันทึก", "Don't save"),
        Button.Close: tr("ปิด", "Close"),
        Button.Open: tr("เปิด", "Open"),
        Button.Retry: tr("ลองอีกครั้ง", "Try again"),
        Button.Abort: tr("หยุด", "Stop"),
        Button.Ignore: tr("ข้าม", "Skip"),
        Button.Apply: tr("ใช้", "Apply"),
        Button.YesToAll: tr("ใช่ทั้งหมด", "Yes to all"),
        Button.NoToAll: tr("ไม่ทั้งหมด", "No to all"),
    }.get(button, button.name or "")


def _badge(kind: str, size: int = 36) -> QPixmap:
    """A round tinted badge with i, !, or ? in the kind's colour."""
    fill, ink, glyph = {
        "info": (theme.PRIMARY_SOFT, theme.PRIMARY_TEXT, "i"),
        "question": (theme.PRIMARY_SOFT, theme.PRIMARY_TEXT, "?"),
        "warning": (theme.ATTENTION_SOFT, theme.ATTENTION, "!"),
        "critical": (theme.DANGER_SOFT, theme.DANGER, "!"),
    }[kind]
    ratio = 2.0
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(fill))
    painter.drawEllipse(QRectF(0, 0, size, size))
    font = QFont()
    font.setPixelSize(int(size * 0.5))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(ink))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, glyph)
    painter.end()
    return pixmap


class _Scrim(QWidget):
    """A soft dark veil over the window while a message is open."""

    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(window.rect())
        self.raise_()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt name
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90 if theme.is_dark() else 46))


class MessageBox(QDialog):
    """A themed alert: icon, title, message, optional details, and buttons.

    Add buttons with ``add_standard`` or ``add_button``, call ``exec()``, then
    read ``clicked`` (the button pressed) or ``result_button`` (its standard
    value, or ``NoButton`` for a custom one).
    """

    def __init__(self, kind: str, title: str, text: str, parent: QWidget | None = None,
                 informative: str = "", detail: str = "") -> None:
        if kind not in KINDS:
            raise ValueError(f"unknown message kind {kind!r}")
        super().__init__(parent)
        self.kind = kind
        self.clicked: QPushButton | None = None
        self.result_button = Button.NoButton
        self._standard: dict[QPushButton, Button] = {}
        self._escape: QPushButton | None = None
        self._default: QPushButton | None = None
        self._drag: QPoint | None = None
        self._scrim: _Scrim | None = None
        self.setObjectName("MessageBox")
        self.setWindowTitle(title or "PasaScope")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 34)  # room for the shadow
        card = QFrame()
        card.setObjectName("MessageCard")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 120 if theme.is_dark() else 48))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        body = QVBoxLayout(card)
        body.setContentsMargins(22, 22, 22, 18)
        body.setSpacing(18)
        top = QHBoxLayout()
        top.setSpacing(14)
        icon = QLabel()
        icon.setObjectName("MessageIcon")
        icon.setPixmap(_badge(kind))
        icon.setFixedSize(36, 36)
        top.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        words = QVBoxLayout()
        words.setSpacing(6)
        # A short title over a longer text reads as heading + message; when the
        # text is the whole message (the old macOS boxes hid the title), the
        # text becomes the heading.
        heading_text, message_text = (title, text) if title else (text, "")
        self.heading = self._text(heading_text, "MessageTitle")
        words.addWidget(self.heading)
        self.message = self._text(message_text, "MessageText")
        self.message.setVisible(bool(message_text))
        words.addWidget(self.message)
        self.informative = self._text(informative, "MessageInfo")
        self.informative.setVisible(bool(informative))
        words.addWidget(self.informative)
        top.addLayout(words, 1)
        body.addLayout(top)

        self.details = QPlainTextEdit(detail)
        self.details.setObjectName("MessageDetails")
        self.details.setReadOnly(True)
        self.details.setFixedHeight(150)
        self.details.hide()
        body.addWidget(self.details)

        self.button_row = QHBoxLayout()
        self.button_row.setSpacing(8)
        self._left = QHBoxLayout()
        self._left.setSpacing(8)
        self._right = QHBoxLayout()
        self._right.setSpacing(8)
        self.button_row.addLayout(self._left)
        self.button_row.addStretch(1)
        self.button_row.addLayout(self._right)
        body.addLayout(self.button_row)
        if detail:
            toggle = QPushButton(tr("แสดงรายละเอียด", "Show details"))
            toggle.setProperty("role", "ghost")
            toggle.setAutoDefault(False)
            toggle.clicked.connect(lambda: self._toggle_details(toggle))
            self._left.addWidget(toggle)

        width = 460 if len(heading_text) + len(message_text) + len(informative) < 260 else 540
        card.setFixedWidth(width)

    @staticmethod
    def _text(text: str, name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(name)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.AutoText)
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        return label

    def _toggle_details(self, toggle: QPushButton) -> None:
        shown = not self.details.isVisible()
        self.details.setVisible(shown)
        toggle.setText(tr("ซ่อนรายละเอียด", "Hide details") if shown else tr("แสดงรายละเอียด", "Show details"))
        self.adjustSize()

    # --- buttons ---------------------------------------------------------

    def add_button(self, text: str, role: str = "secondary", *, escape: bool = False,
                   default: bool = False, apart: bool = False) -> QPushButton:
        """Add a button; ``role`` is ``primary``, ``destructive`` or ``secondary``."""
        button = QPushButton(text)
        button.setObjectName("MessageButton")
        if role != "secondary":
            button.setProperty("role", role)
        button.setMinimumWidth(84)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self._finish(button))
        if apart:
            self._left.addWidget(button)
        elif role == "secondary":
            self._right.insertWidget(0, button)  # secondary buttons sit left of the main one
        else:
            self._right.addWidget(button)
        if escape or self._escape is None and role == "secondary" and not apart:
            self._escape = button
        if default:
            self._make_default(button)
        return button

    def add_standard(self, button: Button, role: str = "secondary", *, default: bool = False,
                     text: str | None = None) -> QPushButton:
        widget = self.add_button(text or _label(button), role, default=default, apart=button in _APART,
                                 escape=button in _ESCAPE[:-1])
        self._standard[widget] = button
        return widget

    def _make_default(self, button: QPushButton) -> None:
        self._default = button
        for other in self.findChildren(QPushButton):
            other.setDefault(other is button)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt name
        super().showEvent(event)
        if self._default is not None:
            self._default.setFocus()  # Qt otherwise focuses (and so defaults) the first button

    def _finish(self, button: QPushButton) -> None:
        self.clicked = button
        self.result_button = self._standard.get(button, Button.NoButton)
        self.accept()

    def reject(self) -> None:
        escape = self._escape
        if escape is None:
            buttons = list(self._standard)
            escape = buttons[0] if len(buttons) == 1 else None
        if escape is not None:
            self.clicked = escape
            self.result_button = self._standard.get(escape, Button.NoButton)
        super().reject()

    # --- showing ---------------------------------------------------------

    def _move_drag(self, event, start: bool) -> None:
        position = event.globalPosition().toPoint()
        if start:
            self._drag = position - self.frameGeometry().topLeft()
        elif self._drag is not None:
            self.move(position - self._drag)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt name
        if event.button() == Qt.MouseButton.LeftButton:
            self._move_drag(event, True)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt name
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._move_drag(event, False)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt name
        self._drag = None
        super().mouseReleaseEvent(event)

    def _place(self) -> None:
        self.adjustSize()
        anchor = self.parentWidget().window() if self.parentWidget() else None
        if anchor is not None and anchor.isVisible():
            centre = anchor.frameGeometry().center()
            self.move(centre.x() - self.width() // 2, centre.y() - self.height() // 2 - 40)
            return
        screen = QApplication.primaryScreen()
        if screen is not None:
            self.move(screen.availableGeometry().center() - self.rect().center())

    def exec(self) -> int:
        if not self._standard and self.clicked is None and not self.findChildren(QPushButton, "MessageButton"):
            self.add_standard(Button.Ok, "primary", default=True)
        if not any(button.isDefault() for button in self.findChildren(QPushButton, "MessageButton")):
            buttons = self.findChildren(QPushButton, "MessageButton")
            main = [b for b in buttons if b.property("role") in ("primary", "destructive")]
            self._make_default((main or buttons)[-1])
        self._place()
        anchor = self.parentWidget().window() if self.parentWidget() else None
        if anchor is not None and anchor.isVisible():
            self._scrim = _Scrim(anchor)
            self._scrim.show()
        if motion.enabled():
            self.setWindowOpacity(0.0)
            fade = QPropertyAnimation(self, b"windowOpacity", self)
            fade.setDuration(140)
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)
            fade.setEasingCurve(QEasingCurve.Type.OutCubic)
            fade.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        try:
            return super().exec()
        finally:
            if self._scrim is not None:
                self._scrim.deleteLater()
                self._scrim = None


# --- the QMessageBox-style calls -------------------------------------------

def _ask(kind: str, parent, title: str, text: str, buttons, default: Button, *, danger: bool = False,
         detail: str = "", labels: dict | None = None) -> Button:
    box = MessageBox(kind, title, text, parent, detail=detail)
    labels = labels or {}
    chosen = [b for b in _ORDER if buttons & b]
    affirmative = default if default in chosen and default not in _ESCAPE[:-1] else next(
        (b for b in _AFFIRMATIVE if b in chosen), None)
    for button in chosen:
        if button is affirmative:
            continue
        box.add_standard(button, default=button == default, text=labels.get(button))
    if affirmative is not None:
        role = "destructive" if danger and affirmative != Button.Ok else "primary"
        box.add_standard(affirmative, role, default=default in (affirmative, Button.NoButton), text=labels.get(affirmative))
    box.exec()
    return box.result_button


# ``labels`` names a button by what it does ({Button.Yes: "Delete session"}) instead of Yes or OK.

def information(parent, title: str, text: str, buttons=Button.Ok, defaultButton: Button = Button.NoButton,  # noqa: N803
                labels: dict | None = None) -> Button:
    return _ask("info", parent, title, text, buttons, defaultButton, labels=labels)


def warning(parent, title: str, text: str, buttons=Button.Ok, defaultButton: Button = Button.NoButton,  # noqa: N803
            labels: dict | None = None) -> Button:
    """A warning; with more than OK (a confirmation that removes something) the main button is red."""
    return _ask("warning", parent, title, text, buttons, defaultButton, danger=True, labels=labels)


def critical(parent, title: str, text: str, buttons=Button.Ok, defaultButton: Button = Button.NoButton,  # noqa: N803
             detail: str = "") -> Button:
    return _ask("critical", parent, title, text, buttons, defaultButton, danger=True, detail=detail)


def question(parent, title: str, text: str, buttons=Button.Yes | Button.No,
             defaultButton: Button = Button.NoButton, labels: dict | None = None) -> Button:  # noqa: N803
    return _ask("question", parent, title, text, buttons, defaultButton, labels=labels)


def about(parent, title: str, text: str) -> None:
    box = MessageBox("info", title, text, parent)
    box.add_standard(Button.Ok, "primary", default=True)
    box.exec()
