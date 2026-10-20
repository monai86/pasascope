"""The window shown while PasaScope starts: the logo, what the app is, and what it is loading.

It is drawn with QPainter so it can appear before the rest of the UI is
imported. The logo grows in, rings like sound waves spread from it while
loading continues, the text fades in, and a thin bar runs along the bottom
edge. With motion reduced (``motion.enabled()``) everything is shown at once
and nothing moves. Its colours come from the theme in use.
"""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from packages.desktop.core.i18n import tr
from packages.desktop.ui import motion, theme

LOGO = Path(__file__).resolve().parent / "assets" / "logo.png"
WIDTH, HEIGHT = 560, 330
MARGIN = 18  # room around the card for its shadow
INTRO_MS = 1300  # the logo, title and text have all arrived by then
RING_PERIOD_MS = 1800
BAR_PERIOD_MS = 1300


def _ease_out_back(t: float) -> float:
    c1, c3 = 1.4, 2.4
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def _ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def _phase(elapsed: float, start: float, end: float) -> float:
    """0 before ``start``, 1 after ``end`` (fractions of INTRO_MS), linear between."""
    t = elapsed / INTRO_MS
    if t <= start:
        return 0.0
    if t >= end:
        return 1.0
    return (t - start) / (end - start)


class Splash(QWidget):
    def __init__(self, version: str = "", demo: bool = False) -> None:
        super().__init__(None, Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(WIDTH + 2 * MARGIN, HEIGHT + 2 * MARGIN)
        self.version = version
        self.demo = demo
        self.status = tr("กำลังเริ่มโปรแกรม…", "Starting…")
        self.animated = motion.enabled()
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self.update)
        self._closing = False
        self.closed = False  # set when it has gone; the window deletes itself then
        logo = QPixmap(str(LOGO))
        self._logo = logo if not logo.isNull() else None
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            centre = screen.availableGeometry().center()
            self.move(centre.x() - self.width() // 2, centre.y() - self.height() // 2)

    # ------------------------------------------------------------------
    def show(self) -> None:  # noqa: D102 - QWidget.show, with the clock started
        self._clock.start()
        if self.animated:
            self._timer.start()
        super().show()
        self.raise_()

    def set_status(self, text: str) -> None:
        if text != self.status:
            self.status = text
            self.update()

    def elapsed_ms(self) -> int:
        return self._clock.elapsed() if self._clock.isValid() else 0

    def minimum_shown(self) -> bool:
        """The intro has played (or there is none to play)."""
        return not self.animated or self.elapsed_ms() >= INTRO_MS

    def finish(self) -> None:
        """Fade out and close (at once when motion is reduced)."""
        if self._closing:
            return
        self._closing = True
        if not self.animated:
            self._close_now()
            return
        steps = {"left": 10}

        def step() -> None:
            steps["left"] -= 1
            self.setWindowOpacity(max(0.0, steps["left"] / 10))
            if steps["left"] <= 0:
                fade.stop()
                self._close_now()

        fade = QTimer(self)
        fade.setInterval(16)
        fade.timeout.connect(step)
        fade.start()

    def _close_now(self) -> None:
        self.closed = True
        self._timer.stop()
        self.close()
        self.deleteLater()

    # ------------------------------------------------------------------
    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        elapsed = float(self.elapsed_ms()) if self.animated else float(INTRO_MS)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        card = QRectF(MARGIN, MARGIN, WIDTH, HEIGHT)
        self._paint_card(painter, card)
        centre = QPointF(card.center().x(), card.top() + 92)
        self._paint_rings(painter, centre, elapsed)
        self._paint_logo(painter, centre, elapsed)
        self._paint_text(painter, card, elapsed)
        self._paint_bar(painter, card, elapsed)
        painter.end()

    def _paint_card(self, painter: QPainter, card: QRectF) -> None:
        for spread, alpha in ((14, 10), (9, 16), (5, 24)):  # a soft shadow
            shadow = QColor(0, 0, 0, alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(shadow)
            painter.drawRoundedRect(card.adjusted(-spread / 2, -spread / 4, spread / 2, spread), 14 + spread / 2, 14 + spread / 2)
        painter.setBrush(QColor(theme.SURFACE))
        painter.setPen(QPen(QColor(theme.LINE_STRONG), 1))
        painter.drawRoundedRect(card, 14, 14)

    def _paint_rings(self, painter: QPainter, centre: QPointF, elapsed: float) -> None:
        if not self.animated:
            return
        start = INTRO_MS * 0.3
        if elapsed < start:
            return
        painter.setBrush(Qt.BrushStyle.NoBrush)
        base = 40.0  # just outside the logo; the widest ring stops above the title
        for index in range(3):
            phase = ((elapsed - start) / RING_PERIOD_MS + index / 3) % 1.0
            radius = base + 30 * _ease_out_cubic(phase)
            colour = QColor(theme.PRIMARY)
            colour.setAlphaF(0.32 * (1 - phase) * min(1.0, (elapsed - start) / 400))
            painter.setPen(QPen(colour, 2))
            painter.drawEllipse(centre, radius, radius)

    def _paint_logo(self, painter: QPainter, centre: QPointF, elapsed: float) -> None:
        grow = _phase(elapsed, 0.0, 0.45)
        scale = 0.82 + 0.18 * _ease_out_back(grow) if grow < 1 else 1.0
        size = 72 * scale
        painter.setOpacity(_phase(elapsed, 0.0, 0.3))
        target = QRectF(centre.x() - size / 2, centre.y() - size / 2, size, size)
        if self._logo is not None:
            painter.drawPixmap(target, self._logo, QRectF(self._logo.rect()))
        else:
            painter.setBrush(QColor(theme.PRIMARY))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(target)
        painter.setOpacity(1.0)

    def _paint_text(self, painter: QPainter, card: QRectF, elapsed: float) -> None:
        def draw(text: str, top: float, size: int, colour: str, weight: QFont.Weight, appear: float) -> float:
            font = QFont()
            font.setPixelSize(size)
            font.setWeight(weight)
            painter.setFont(font)
            painter.setOpacity(_ease_out_cubic(appear))
            painter.setPen(QColor(colour))
            lift = 8 * (1 - _ease_out_cubic(appear))
            height = QFontMetrics(font).height()
            painter.drawText(QRectF(card.left() + 32, top + lift, card.width() - 64, height),
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, text)
            painter.setOpacity(1.0)
            return top + height

        title_in = _phase(elapsed, 0.25, 0.6)
        body_in = _phase(elapsed, 0.45, 0.85)
        top = card.top() + 172
        top = draw("PasaScope", top, 26, theme.INK, QFont.Weight.Bold, title_in) + 2
        top = draw(tr("ภาษา-สโคป · ตัวช่วยวิเคราะห์ตัวอย่างภาษาของเด็ก", "Language sample analysis for children's therapists"),
                   top, 14, theme.INK_SOFT, QFont.Weight.Normal, title_in) + 14
        for line in (
            tr("ถอดเสียงและวิเคราะห์บนเครื่องนี้ ข้อมูลของเด็กไม่ออกจากเครื่อง", "Transcribes and analyses on this computer; children's data stays here"),
            tr("ช่วยการตัดสินใจทางคลินิก ไม่ใช่การวินิจฉัย", "Supports clinical judgement; it does not diagnose"),
        ):
            top = draw(line, top, 12, theme.MUTED, QFont.Weight.Normal, body_in) + 2
        font = QFont()
        font.setPixelSize(11)
        painter.setFont(font)
        painter.setPen(QColor(theme.MUTED))
        footer = QRectF(card.left() + 20, card.bottom() - 34, card.width() - 40, 18)
        painter.drawText(footer, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         QFontMetrics(font).elidedText(self.status, Qt.TextElideMode.ElideRight, int(footer.width() * 0.7)))
        right = (tr("ข้อมูลสาธิต · ", "Demonstration data · ") if self.demo else "") + (
            tr(f"รุ่น {self.version}", f"Version {self.version}") if self.version else "")
        painter.drawText(footer, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, right)

    def _paint_bar(self, painter: QPainter, card: QRectF, elapsed: float) -> None:
        if not self.animated:
            return
        track = QRectF(card.left() + 1, card.bottom() - 3, card.width() - 2, 2)
        clip = QPainterPath()
        clip.addRoundedRect(card, 14, 14)
        painter.save()
        painter.setClipPath(clip)
        phase = (elapsed % BAR_PERIOD_MS) / BAR_PERIOD_MS
        width = track.width() * 0.28
        left = track.left() - width + (track.width() + width) * (0.5 - 0.5 * math.cos(math.pi * phase))
        painter.fillRect(QRectF(left, track.top(), width, track.height()), QColor(theme.PRIMARY))
        painter.restore()
