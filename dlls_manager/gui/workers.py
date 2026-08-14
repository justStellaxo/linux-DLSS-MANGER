"""Async job runner using QThread to avoid blocking the GUI."""
from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QThread, Signal


class JobWorker(QThread):
    progress = Signal(str)
    finished_job = Signal(object)
    error = Signal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished_job.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))