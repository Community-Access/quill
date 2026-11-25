"""Retry a durable queue lock without stealing it from a live app."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

_POLLERS: dict[Path, Any] = {}
_RETRY_MS = 5000
logger = logging.getLogger(__name__)


def _closing(host: Any) -> bool:
    if getattr(host, "_exit_requested", False):
        return True
    app = getattr(host, "app", None)
    if getattr(app, "shutting_down", False):
        return True
    frame = getattr(host, "frame", None)
    deleting = getattr(frame, "IsBeingDeleted", None)
    return bool(callable(deleting) and deleting())


def cancel(path: Path) -> None:
    timer = _POLLERS.pop(Path(path), None)
    stop = getattr(timer, "Stop", None)
    if callable(stop):
        stop()


def after_lock(host: Any, path: Path, resume: Callable[[Any], int]) -> None:
    path = Path(path)
    if path in _POLLERS:
        return
    get_app = getattr(wx, "GetApp", None)
    call_later = getattr(wx, "CallLater", None)
    if not callable(call_later) or (callable(get_app) and get_app() is None):
        return

    def retry() -> None:
        _POLLERS.pop(path, None)
        if _closing(host):
            return
        try:
            resume(host)
        except Exception:  # noqa: BLE001 - retrying a persisted queue is best-effort
            logger.warning("Could not check the transcription queue lock", exc_info=True)
            after_lock(host, path, resume)

    try:
        _POLLERS[path] = call_later(_RETRY_MS, retry)
    except Exception:  # noqa: BLE001 - a missing timer must not start or stop the queue
        _POLLERS.pop(path, None)


__all__ = ["after_lock", "cancel"]
