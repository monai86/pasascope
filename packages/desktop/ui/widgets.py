"""Small reusable widgets: chips, cards, the waveform and the trend chart."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from packages.desktop.ui import theme


def chip(text: str, kind: str = "neutral") -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(theme.chip_style(kind))
    label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def set_chip(label: QLabel, text: str, kind: str) -> None:
    label.setText(text)
    label.setStyleSheet(theme.chip_style(kind))


def button(text: str, role: str = "", tooltip: str = "") -> QPushButton:
    btn = QPushButton(text)
    if role:
        btn.setProperty("role", role)
    if tooltip:
        btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    return frame, layout


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


class EmptyState(QWidget):
    def __init__(self, title: str, body: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addStretch(1)
        self.title = label(title, "EmptyTitle", wrap=True)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)
        self.body = label(body, "Muted", wrap=True)
        self.body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.body)
        self.actions = QVBoxLayout()
        self.actions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(self.actions)
        layout.addStretch(2)

    def set_text(self, title: str, body: str = "") -> None:
        self.title.setText(title)
        self.body.setText(body)


class WaveformView(QWidget):
    """Peaks of a recording with utterance regions and a playhead.

    Clicking sends ``seek(seconds)``.
    """

    seek = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(84)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._peaks = np.zeros(0, dtype="float32")
        self._duration = 0.0
        self._regions: list[tuple[float, float, str]] = []
        self._selected: tuple[float, float] | None = None
        self._playhead: float | None = None
        self._message = "ยังไม่มีไฟล์เสียง"

    def set_message(self, text: str) -> None:
        self._peaks = np.zeros(0, dtype="float32")
        self._duration = 0.0
        self._message = text
        self.update()

    def set_audio(self, peaks: np.ndarray, duration: float) -> None:
        self._peaks = peaks
        self._duration = duration
        self._message = "" if duration > 0 else "ไฟล์เสียงว่าง"
        self.update()

    def set_regions(self, regions: Sequence[tuple[float, float, str]]) -> None:
        self._regions = list(regions)
        self.update()

    def set_selected(self, region: tuple[float, float] | None) -> None:
        self._selected = region
        self.update()

    def set_playhead(self, seconds: float | None) -> None:
        self._playhead = seconds
        self.update()

    @property
    def duration(self) -> float:
        return self._duration

    def _x(self, seconds: float) -> float:
        return 0.0 if self._duration <= 0 else seconds / self._duration * self.width()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._duration > 0 and event.button() == Qt.MouseButton.LeftButton:
            self.seek.emit(max(0.0, min(self._duration, event.position().x() / max(1, self.width()) * self._duration)))

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor(theme.SURFACE))
        painter.setPen(QPen(QColor(theme.LINE)))
        painter.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        if self._duration <= 0 or not self._peaks.size:
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._message)
            return

        h = rect.height()
        for start, end, speaker in self._regions:
            color = QColor(theme.SPEAKER_COLORS.get(speaker, theme.MUTED))
            color.setAlpha(28)
            painter.fillRect(QRectF(self._x(start), 0, max(1.0, self._x(end) - self._x(start)), h), color)
        if self._selected:
            start, end = self._selected
            color = QColor(theme.PRIMARY)
            color.setAlpha(60)
            painter.fillRect(QRectF(self._x(start), 0, max(2.0, self._x(end) - self._x(start)), h), color)

        mid = h / 2
        step = self.width() / len(self._peaks)
        painter.setPen(QPen(QColor(theme.INK_SOFT), max(1.0, step * 0.7)))
        for i, peak in enumerate(self._peaks):
            x = i * step + step / 2
            half = max(0.5, float(peak) * (mid - 6))
            painter.drawLine(QPointF(x, mid - half), QPointF(x, mid + half))

        if self._playhead is not None:
            painter.setPen(QPen(QColor(theme.DANGER), 2))
            x = self._x(self._playhead)
            painter.drawLine(QPointF(x, 0), QPointF(x, h))


class TrendChart(QWidget):
    """One feature across sessions: a line with labelled points."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._points: list[tuple[str, float]] = []
        self._title = ""
        self._format = "{:.2f}"

    def set_series(self, title: str, points: Sequence[tuple[str, float]], value_format: str = "{:.2f}") -> None:
        self._title = title
        self._points = list(points)
        self._format = value_format
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        painter.fillRect(rect, QColor(theme.SURFACE))
        if len(self._points) < 2:
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(
                rect, Qt.AlignmentFlag.AlignCenter,
                "ต้องมีอย่างน้อย 2 session ที่วิเคราะห์แล้ว จึงจะเห็นแนวโน้ม",
            )
            return
        left, right, top, bottom = 52.0, 52.0, 30.0, 34.0
        plot = rect.adjusted(left, top, -right, -bottom)
        values = [v for _, v in self._points]
        low, high = min(values), max(values)
        if high == low:
            low, high = low - 1, high + 1
        pad = (high - low) * 0.15
        low, high = low - pad, high + pad

        def point(i: int, v: float) -> QPointF:
            x = plot.left() + (plot.width() * i / (len(self._points) - 1))
            y = plot.bottom() - (v - low) / (high - low) * plot.height()
            return QPointF(x, y)

        title_font = QFont(self.font())
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor(theme.INK))
        painter.drawText(QRectF(0, 4, rect.width(), 20), Qt.AlignmentFlag.AlignHCenter, self._title)
        painter.setFont(self.font())

        painter.setPen(QPen(QColor(theme.LINE), 1))
        for frac in (0.0, 0.5, 1.0):
            y = plot.bottom() - frac * plot.height()
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(QRectF(0, y - 9, left - 6, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             self._format.format(low + frac * (high - low)))
            painter.setPen(QPen(QColor(theme.LINE), 1))

        path = QPainterPath()
        for i, (_, v) in enumerate(self._points):
            p = point(i, v)
            path.moveTo(p) if i == 0 else path.lineTo(p)
        painter.setPen(QPen(QColor(theme.PRIMARY), 2.5))
        painter.drawPath(path)

        for i, (when, v) in enumerate(self._points):
            p = point(i, v)
            painter.setBrush(QColor(theme.PRIMARY))
            painter.setPen(QPen(QColor(theme.SURFACE), 2))
            painter.drawEllipse(p, 5, 5)
            painter.setPen(QColor(theme.INK))
            painter.drawText(QRectF(p.x() - 40, p.y() - 24, 80, 16), Qt.AlignmentFlag.AlignCenter, self._format.format(v))
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(QRectF(p.x() - 50, plot.bottom() + 8, 100, 18), Qt.AlignmentFlag.AlignCenter, when)
