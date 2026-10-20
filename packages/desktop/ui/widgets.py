"""Small reusable widgets: chips, cards, the waveform and the trend chart."""

from __future__ import annotations

from packages.desktop.core.i18n import tr

from collections.abc import Sequence

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from packages.desktop.ui import theme


def repolish(widget: QWidget) -> None:
    """Apply the style sheet again after a property its selectors use has changed."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def set_style_property(widget: QWidget, name: str, value: str) -> None:
    if widget.property(name) != value:
        widget.setProperty(name, value)
        repolish(widget)


def chip(text: str, kind: str = "neutral") -> QLabel:
    """A Notion-style tag: tinted background, coloured text (``#Chip[kind=...]`` in the theme)."""
    label = QLabel(text)
    label.setObjectName("Chip")
    label.setProperty("kind", kind)
    label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def set_chip(label: QLabel, text: str, kind: str) -> None:
    label.setText(text)
    set_style_property(label, "kind", kind)


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


def notice(text: str = "", kind: str = "attention") -> QLabel:
    """A full-width banner for a warning the therapist should read before going on."""
    widget = label(text, wrap=True)
    widget.setObjectName("Notice")
    widget.setProperty("kind", kind)
    return widget


class MetricCard(QFrame):
    """One headline value: a caption, the number, and a line of context."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Metric")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setSpacing(1)
        self.title = label(title, "MetricTitle", wrap=True)
        self.value = label("—", "MetricValue")
        self.detail = label("", "Muted", wrap=True)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)

    def set_value(self, value: str, detail: str = "", tooltip: str = "") -> None:
        self.value.setText(value)
        self.detail.setText(detail)
        self.setToolTip(tooltip)


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

    @staticmethod
    def steps() -> tuple[str, ...]:
        return (
            tr("เพิ่มเสียงหรือ transcript", "Add a recording or transcript"),
            tr("ตรวจ transcript กับเสียง แล้วรับรอง", "Check the transcript against the recording and attest it"),
            tr("วิเคราะห์ และตรวจ cue", "Analyse and review the cues"),
            tr("ร่างรายงาน แก้ แล้วลงนาม", "Draft, edit and sign the report"),
        )

    def set_steps(self, step: int) -> None:
        """Where the session stands: finished steps quiet, the next one in ink, later ones faint."""
        if not hasattr(self, "_steps"):
            self._steps = QWidget()
            self._steps.setObjectName("Panel")
            self._steps.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self._steps.setFixedWidth(440)
            QVBoxLayout(self._steps).setContentsMargins(18, 14, 18, 14)
            self.layout().insertWidget(1, self._steps, 0, Qt.AlignmentFlag.AlignHCenter)
            self.layout().insertSpacing(2, 14)
        rows = self._steps.layout()
        while rows.count():
            item = rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for index, name in enumerate(self.steps()):
            row = label(f"{index + 1}   {name}", "Step", wrap=True)
            row.setProperty("state", "done" if index < step else "current" if index == step else "todo")
            rows.addWidget(row)


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
        self._message = tr("ยังไม่มีไฟล์เสียง", "No recording")

    def set_message(self, text: str) -> None:
        self._peaks = np.zeros(0, dtype="float32")
        self._duration = 0.0
        self._message = text
        self.update()

    def set_audio(self, peaks: np.ndarray, duration: float) -> None:
        self._peaks = peaks
        self._duration = duration
        self._message = "" if duration > 0 else tr("ไฟล์เสียงว่าง", "Empty recording")
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


def _nice_ceiling(value: float) -> float:
    """The next round number at or above ``value`` (1, 2, 2.5 or 5 times a power of ten), for tidy axis labels."""
    import math

    power = 10 ** math.floor(math.log10(value))
    return next(step * power for step in (1, 2, 2.5, 5, 10) if step * power >= value)


class TrendChart(QWidget):
    """One feature across sessions, drawn so that small changes do not look large.

    The value axis starts at zero, and a session whose sample is shorter than
    the recommended size is drawn as a hollow point with its utterance count,
    so a therapist reads a jump between two short samples with caution.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(180)
        self._points: list[tuple[str, float]] = []
        self._samples: list[float | None] = []
        self._min_sample = 0
        self._title = ""
        self._format = "{:.2f}"

    def set_series(self, title: str, points: Sequence[tuple[str, float]], value_format: str = "{:.2f}",
                   samples: Sequence[float | None] | None = None, min_sample: int = 0) -> None:
        self._title = title
        self._points = list(points)
        self._samples = list(samples) if samples is not None else [None] * len(self._points)
        self._min_sample = min_sample
        self._format = value_format
        self.update()

    def _short(self, index: int) -> bool:
        n = self._samples[index] if index < len(self._samples) else None
        return bool(self._min_sample) and n is not None and n < self._min_sample

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        painter.fillRect(rect, QColor(theme.SURFACE))
        if len(self._points) < 2:
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(
                rect, Qt.AlignmentFlag.AlignCenter,
                tr("ต้องมีอย่างน้อย 2 session ที่วิเคราะห์แล้ว จึงจะเห็นแนวโน้ม", "A trend needs at least 2 analysed sessions."),
            )
            return
        left, right, top, bottom = 44.0, 40.0, 30.0, 52.0
        plot = rect.adjusted(left, top, -right, -bottom)
        values = [v for _, v in self._points]
        low = 0.0 if min(values) >= 0 else min(values) * 1.15
        high = _nice_ceiling(max(values) * 1.1) if max(values) > 0 else 1.0

        def point(i: int, v: float) -> QPointF:
            x = plot.left() + (plot.width() * i / (len(self._points) - 1))
            y = plot.bottom() - (v - low) / (high - low) * plot.height()
            return QPointF(x, y)

        title_font = QFont(self.font())
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor(theme.INK))
        painter.drawText(QRectF(0, 4, rect.width(), 20), Qt.AlignmentFlag.AlignHCenter, self._title)
        painter.setFont(self.font())

        for frac in (0.0, 0.5, 1.0):
            y = plot.bottom() - frac * plot.height()
            painter.setPen(QPen(QColor(theme.LINE), 1))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(QRectF(0, y - 9, left - 6, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             self._format.format(low + frac * (high - low)))

        path = QPainterPath()
        for i, (_, v) in enumerate(self._points):
            p = point(i, v)
            path.moveTo(p) if i == 0 else path.lineTo(p)
        painter.setPen(QPen(QColor(theme.PRIMARY), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        for i, (when, v) in enumerate(self._points):
            p = point(i, v)
            short = self._short(i)
            painter.setBrush(QColor(theme.SURFACE) if short else QColor(theme.PRIMARY))
            painter.setPen(QPen(QColor(theme.PRIMARY), 2))
            painter.drawEllipse(p, 4.5, 4.5)
            painter.setPen(QColor(theme.INK))
            painter.drawText(QRectF(p.x() - 40, p.y() - 24, 80, 16), Qt.AlignmentFlag.AlignCenter, self._format.format(v))
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(QRectF(p.x() - 50, plot.bottom() + 6, 100, 18), Qt.AlignmentFlag.AlignCenter, when)
            n = self._samples[i] if i < len(self._samples) else None
            if n is not None:
                painter.setPen(QColor(theme.ATTENTION if short else theme.FAINT))
                painter.drawText(QRectF(p.x() - 50, plot.bottom() + 22, 100, 16), Qt.AlignmentFlag.AlignCenter, tr(f"{int(n)} ประโยค", f"{int(n)} utts"))
