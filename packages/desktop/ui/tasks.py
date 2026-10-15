"""Run slow work (transcription, analysis, export) off the UI thread."""

from __future__ import annotations

from collections.abc import Callable
import traceback
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(object)
    progress = Signal(float, str)


class _Task(QRunnable):
    def __init__(self, fn: Callable[..., Any], with_progress: bool) -> None:
        super().__init__()
        self.fn = fn
        self.with_progress = with_progress
        self.signals = _Signals()

    def run(self) -> None:
        try:
            if self.with_progress:
                result = self.fn(lambda fraction, stage: self.signals.progress.emit(float(fraction), str(stage)))
            else:
                result = self.fn()
        except Exception as exc:  # noqa: BLE001 - every failure is reported to the UI
            exc.__traceback_text__ = traceback.format_exc()  # type: ignore[attr-defined]
            self.signals.failed.emit(exc)
        else:
            self.signals.done.emit(result)


class TaskRunner(QObject):
    """Keeps running tasks referenced until they finish."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.pool = QThreadPool.globalInstance()
        self._running: set[_Task] = set()

    def run(
        self,
        fn: Callable[..., Any],
        *,
        on_done: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        on_progress: Callable[[float, str], None] | None = None,
    ) -> None:
        """Call ``fn`` in a worker thread; callbacks run on the UI thread.

        With ``on_progress`` the function receives a ``progress(fraction, stage)``
        argument it may call from the worker.
        """
        task = _Task(fn, with_progress=on_progress is not None)
        self._running.add(task)

        def finish(handler: Callable[[Any], None] | None, value: Any) -> None:
            self._running.discard(task)
            if handler is not None:
                handler(value)

        task.signals.done.connect(lambda value: finish(on_done, value))
        task.signals.failed.connect(lambda exc: finish(on_error, exc))
        if on_progress is not None:
            task.signals.progress.connect(on_progress)
        self.pool.start(task)

    @property
    def busy(self) -> bool:
        return bool(self._running)

    def wait(self, msecs: int = -1) -> bool:
        return self.pool.waitForDone(msecs)
