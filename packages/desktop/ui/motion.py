"""Short fades when a page appears, and toasts: brief messages that fade away.

Motion follows the computer's "Reduce motion" setting (macOS Accessibility,
Windows "Show animations") unless the therapist picks one in Settings. With
motion reduced, pages change at once and toasts appear and go without fading.
"""

from __future__ import annotations

from functools import lru_cache
import subprocess
import sys

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, QSettings, Qt, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

SETTINGS_KEY = "appearance/motion"
MODES = ("system", "reduce", "full")
PAGE_FADE_MS = 150
TOAST_FADE_MS = 180


def saved_mode() -> str:
    """``system`` (follow the computer), ``reduce`` or ``full``."""
    mode = QSettings().value(SETTINGS_KEY, "system")
    return mode if mode in MODES else "system"


def save_mode(mode: str) -> None:
    if mode not in MODES:
        raise ValueError(f"unknown motion setting {mode!r}")
    QSettings().setValue(SETTINGS_KEY, mode)


@lru_cache(maxsize=1)
def system_reduces_motion() -> bool:
    """Whether the computer asks apps to reduce motion (read once per run)."""
    try:
        if sys.platform == "darwin":
            out = subprocess.run(
                ["defaults", "read", "com.apple.universalaccess", "reduceMotion"],
                capture_output=True, text=True, timeout=2,
            )
            return out.stdout.strip() == "1"
        if sys.platform == "win32":
            import ctypes

            enabled = ctypes.c_bool(True)
            spi_get_client_area_animation = 0x1042
            ctypes.windll.user32.SystemParametersInfoW(spi_get_client_area_animation, 0, ctypes.byref(enabled), 0)
            return not enabled.value
    except Exception:  # noqa: BLE001 - unknown means motion stays on
        return False
    return False


def enabled() -> bool:
    mode = saved_mode()
    if mode == "system":
        return not system_reduces_motion()
    return mode == "full"


def fade_in(widget: QWidget | None, duration: int = PAGE_FADE_MS) -> None:
    """Fade ``widget`` in from transparent; nothing happens when motion is reduced.

    The opacity effect is removed when the fade ends, so the page draws
    normally afterwards (an effect left in place slows tables and previews).
    """
    if widget is None or not enabled() or not widget.isVisible():
        return
    current = widget.graphicsEffect()
    if current is not None and not isinstance(current, QGraphicsOpacityEffect):
        return  # keep someone else's effect
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def finish() -> None:
        if widget.graphicsEffect() is effect:
            widget.setGraphicsEffect(None)

    animation.finished.connect(finish)
    animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


class Toast(QLabel):
    """A short message near the bottom of a window that goes away by itself.

    One per window: a new message replaces the one showing. Clicking it
    closes it. Screen readers hear it as an announcement.
    """

    MARGIN = 18
    MAX_WIDTH = 560

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.setObjectName("Toast")
        self.setTextFormat(Qt.TextFormat.PlainText)  # names typed by the therapist stay text
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hide()
        self._host = host
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(1.0)
        self.setGraphicsEffect(self._effect)
        self._fade = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade.setDuration(TOAST_FADE_MS)
        self._fade.finished.connect(self._faded)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.dismiss)
        host.installEventFilter(self)

    def show_message(self, text: str, msecs: int = 5000) -> None:
        self.setText(text)
        self._place()
        self.raise_()
        self._fade.stop()
        if enabled() and not self.isVisible():
            self._effect.setOpacity(0.0)
            self.show()
            self._run_fade(1.0)
        else:
            self._effect.setOpacity(1.0)
            self.show()
        self._timer.start(max(1500, msecs))
        _announce(self, text)

    def dismiss(self) -> None:
        self._timer.stop()
        if not self.isVisible():
            return
        if enabled():
            self._run_fade(0.0)
        else:
            self.hide()

    def _run_fade(self, end: float) -> None:
        self._fade.stop()
        self._fade.setStartValue(self._effect.opacity())
        self._fade.setEndValue(end)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic if end else QEasingCurve.Type.InCubic)
        self._fade.start()

    def _faded(self) -> None:
        if self._fade.endValue() == 0.0:
            self.hide()

    def _place(self) -> None:
        # Word wrap makes adjustSize pick a narrow box; size it to the text, then wrap past 560 px.
        self.ensurePolished()
        margins = self.contentsMargins()
        padding = 2 * 16 + 2 + margins.left() + margins.right()
        width = min(self.MAX_WIDTH, self.fontMetrics().horizontalAdvance(self.text()) + padding + 4,
                    self._host.width() - 2 * self.MARGIN)
        self.resize(width, self.heightForWidth(width))
        host = self._host.rect()
        bottom = host.bottom() - self.MARGIN
        status = getattr(self._host, "statusBar", None)
        if callable(status) and self._host.statusBar().isVisible():
            bottom -= self._host.statusBar().height()
        self.move(host.center().x() - self.width() // 2, bottom - self.height())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt override
        try:
            if watched is self._host and event.type() == QEvent.Type.Resize and self.isVisible():
                self._place()
        except RuntimeError:  # the window is being torn down at quit
            pass
        return False

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.dismiss()
        event.accept()


def _announce(widget: QWidget, text: str) -> None:
    try:
        from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent

        QAccessible.updateAccessibility(QAccessibleAnnouncementEvent(widget, text))
    except Exception:  # noqa: BLE001 - older Qt, or no accessibility bridge
        pass
