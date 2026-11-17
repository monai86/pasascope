"""Small reusable widgets: chips, cards, the waveform and the trend chart."""

from __future__ import annotations

from packages.desktop.core.i18n import tr

from collections.abc import Iterator, Sequence
from contextlib import contextmanager

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHeaderView, QLabel, QPushButton, QSizePolicy, QTableWidget, QVBoxLayout, QWidget

from packages.desktop.ui import motion, theme


def repolish(widget: QWidget) -> None:
    """Apply the style sheet again after a property its selectors use has changed."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def set_style_property(widget: QWidget, name: str, value: str) -> None:
    if widget.property(name) != value:
        widget.setProperty(name, value)
        repolish(widget)


@contextmanager
def filling(table: QTableWidget) -> Iterator[QTableWidget]:
    """Fill ``table`` without re-measuring it after every cell.

    A column that sizes itself to its contents measures every row again each
    time a cell is set, so filling n rows costs n² (a 500-line transcript took
    6 s). Inside this block those columns keep their width and the table does
    not repaint; they measure once when it ends.
    """
    header = table.horizontalHeader()
    auto = [i for i in range(header.count()) if header.sectionResizeMode(i) == QHeaderView.ResizeMode.ResizeToContents]
    sorting = table.isSortingEnabled()
    table.setSortingEnabled(False)
    table.setUpdatesEnabled(False)
    for index in auto:
        header.setSectionResizeMode(index, QHeaderView.ResizeMode.Interactive)
    try:
        yield table
    finally:
        for index in auto:
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)
        table.setSortingEnabled(sorting)
        table.setUpdatesEnabled(True)


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


class LiveLevelMeter(QWidget):
    """Smooth rolling microphone level bars used while recording."""

    BARS = 36

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(34)
        self.setMaximumHeight(42)
        self._history: list[float] = [0.0] * self.BARS
        self._smoothed = 0.0
        self._active = False

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            self._smoothed = 0.0
        self.update()

    def push(self, level: float) -> None:
        raw = max(0.0, min(1.0, float(level)))
        if motion.enabled():
            alpha = 0.7 if raw >= self._smoothed else 0.35
            self._smoothed = alpha * raw + (1.0 - alpha) * self._smoothed
        else:
            self._smoothed = raw
        self._history.pop(0)
        self._history.append(self._smoothed)
        self.update()

    def reset(self) -> None:
        self._active = False
        self._smoothed = 0.0
        self._history = [0.0] * self.BARS
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        painter.setPen(QPen(QColor(theme.LINE), 1.0))
        painter.setBrush(QColor(theme.SIDEBAR))
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 6.0, 6.0)

        inner = rect.adjusted(8.0, 5.0, -8.0, -5.0)
        if inner.width() <= 0 or inner.height() <= 0:
            return
        mid = inner.center().y()
        max_half = inner.height() / 2.0
        step = inner.width() / len(self._history)
        bar_w = min(4.0, max(2.0, step * 0.58))
        offset = (step - bar_w) / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        for index, value in enumerate(self._history):
            x = inner.left() + index * step + offset
            if self._active and value > 0.02:
                color = QColor(theme.DANGER if value > 0.9 else theme.PRIMARY)
                half = max(2.0, value * max_half)
            else:
                color = QColor(theme.LINE_STRONG)
                half = 1.5
            painter.setBrush(color)
            radius = min(1.5, bar_w / 2.0, half)
            painter.drawRoundedRect(QRectF(x, mid - half, bar_w, half * 2.0), radius, radius)


class WaveformView(QWidget):
    """Peaks of a recording with utterance regions, hover scrubbing, and a playhead.

    Clicking or dragging sends ``seek(seconds)``.
    """

    seek = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(84)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._peaks = np.zeros(0, dtype="float32")
        self._duration = 0.0
        self._regions: list[tuple[float, float, str]] = []
        self._selected: tuple[float, float] | None = None
        self._playhead: float | None = None
        self._hover_x: float | None = None
        self._scrubbing = False
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

    def _seconds_at(self, x: float) -> float:
        if self._duration <= 0:
            return 0.0
        return max(0.0, min(self._duration, x / max(1, self.width()) * self._duration))

    @staticmethod
    def _format_time(seconds: float) -> str:
        total_tenths = int(round(max(0.0, seconds) * 10))
        mins, rem = divmod(total_tenths, 600)
        secs, tenths = divmod(rem, 10)
        return f"{mins:02d}:{secs:02d}.{tenths}"

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._hover_x = float(event.position().x())
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._hover_x = None
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._duration > 0 and event.button() == Qt.MouseButton.LeftButton:
            self._scrubbing = True
            self._hover_x = float(event.position().x())
            seconds = self._seconds_at(self._hover_x)
            self._playhead = seconds
            self.seek.emit(seconds)
            self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._hover_x = float(event.position().x())
        if self._duration > 0 and (event.buttons() & Qt.MouseButton.LeftButton):
            seconds = self._seconds_at(self._hover_x)
            self._playhead = seconds
            self.seek.emit(seconds)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self._scrubbing = False
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        outer = QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.SURFACE))
        painter.drawRoundedRect(outer, 8.0, 8.0)

        if self._duration <= 0 or not self._peaks.size:
            painter.setPen(QPen(QColor(theme.LINE), 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(outer, 8.0, 8.0)
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._message)
            return

        w = max(1.0, float(rect.width()))
        h = max(1.0, float(rect.height()))
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(rect).adjusted(1.0, 1.0, -1.0, -1.0), 7.0, 7.0)
        painter.save()
        painter.setClipPath(clip)

        for start, end, speaker in self._regions:
            color = QColor(theme.SPEAKER_COLORS.get(speaker, theme.MUTED))
            color.setAlpha(24)
            painter.fillRect(QRectF(self._x(start), 0.0, max(1.0, self._x(end) - self._x(start)), h), color)
        if self._selected:
            start, end = self._selected
            color = QColor(theme.PRIMARY)
            color.setAlpha(42)
            painter.fillRect(QRectF(self._x(start), 0.0, max(2.0, self._x(end) - self._x(start)), h), color)

        mid = h / 2.0
        painter.setPen(QPen(QColor(theme.LINE), 1.0))
        painter.drawLine(QPointF(0.0, mid), QPointF(w, mid))

        # Mirrored rounded waveform bars
        n_peaks = len(self._peaks)
        n_bars = max(1, int(w // 4.5))
        if n_peaks > n_bars:
            bars = [
                float(self._peaks[int(i * n_peaks / n_bars):max(int(i * n_peaks / n_bars) + 1, int((i + 1) * n_peaks / n_bars))].max())
                for i in range(n_bars)
            ]
            step = w / n_bars
            bar_w = min(3.0, max(2.0, step * 0.65))
        else:
            bars = [float(p) for p in self._peaks]
            step = w / max(1, len(bars))
            bar_w = min(4.0, max(2.0, step * 0.68))
        offset = (step - bar_w) / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        for i, peak in enumerate(bars):
            x = i * step + offset
            t_bar = ((x + bar_w / 2.0) / w) * self._duration
            if self._selected and self._selected[0] <= t_bar <= self._selected[1]:
                bar_color = QColor(theme.PRIMARY)
            elif self._playhead is not None and t_bar <= self._playhead:
                bar_color = QColor(theme.INK_SOFT)
                bar_color.setAlpha(210)
            else:
                bar_color = QColor(theme.MUTED)
                bar_color.setAlpha(150)
            painter.setBrush(bar_color)
            half = max(1.5, min(1.0, max(0.0, peak)) * (mid - 10.0))
            radius = min(1.5, bar_w / 2.0, half)
            painter.drawRoundedRect(QRectF(x, mid - half, bar_w, half * 2.0), radius, radius)

        if self._hover_x is not None and 0.0 <= self._hover_x <= w:
            hx = max(1.0, min(w - 1.0, self._hover_x))
            hover_color = QColor(theme.INK_SOFT)
            hover_color.setAlpha(130)
            painter.setPen(QPen(hover_color, 1.0, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(hx, 2.0), QPointF(hx, h - 2.0))

            pill_text = self._format_time(self._seconds_at(hx))
            pill_font = QFont(self.font())
            pill_font.setPointSize(11)
            pill_font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(pill_font)
            fm = QFontMetrics(pill_font)
            pill_w = float(fm.horizontalAdvance(pill_text) + 12)
            pill_h = float(fm.height() + 4)
            pill_x = max(4.0, min(w - pill_w - 4.0, hx - pill_w / 2.0))
            pill_rect = QRectF(pill_x, 4.0, pill_w, pill_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.TOOLTIP))
            painter.drawRoundedRect(pill_rect, 4.0, 4.0)
            painter.setPen(QColor(theme.TOOLTIP_TEXT))
            painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, pill_text)

        if self._playhead is not None:
            px = max(1.0, min(w - 1.0, self._x(self._playhead)))
            primary = QColor(theme.PRIMARY)
            painter.setPen(QPen(primary, 2.0))
            painter.drawLine(QPointF(px, 6.0), QPointF(px, h - 1.0))
            cap = QPainterPath()
            cap.moveTo(px - 5.0, 1.0)
            cap.lineTo(px + 5.0, 1.0)
            cap.lineTo(px + 5.0, 5.0)
            cap.lineTo(px, 9.5)
            cap.lineTo(px - 5.0, 5.0)
            cap.closeSubpath()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(primary)
            painter.drawPath(cap)

        painter.restore()
        painter.setPen(QPen(QColor(theme.LINE), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(outer, 8.0, 8.0)


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
