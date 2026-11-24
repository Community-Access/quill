"""What each app counts as "the moment that matters" (FUX-15).

Each function returns the probes for one app: callables answering ``""`` when
that work is idle, or the end of "... waits until <phrase>" while it is busy
(see :mod:`quill.core.maintenance_moment`). They read state the app already
keeps and add none. :func:`probes_for` picks the app's set by its key.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.maintenance_moment import Probe

__all__ = ["DICTATION_ENDS", "READ_ALOUD_STOPS", "probes_for"]

DICTATION_ENDS = "dictation ends"
READ_ALOUD_STOPS = "reading aloud stops"


def _windows_dictation() -> str:
    from quill.ui.windows_dictation_commands import dictation_active

    return DICTATION_ENDS if dictation_active() else ""


def _quill(host: Any) -> list[Probe]:
    def locked_dictation() -> str:
        controller = getattr(host, "_live_dictation", None)
        return DICTATION_ENDS if controller is not None and controller.is_busy else ""

    def read_aloud() -> str:
        reader = getattr(host, "_read_aloud", None)
        return READ_ALOUD_STOPS if getattr(reader, "state", "") == "playing" else ""

    return [locked_dictation, _windows_dictation, read_aloud]


def _lite(_host: Any) -> list[Probe]:
    return [_windows_dictation]


_BY_APP: dict[str, Callable[[Any], list[Probe]]] = {
    "quill": _quill,
    "quilllite": _lite,
}


def probes_for(app_key: str, host: Any) -> list[Probe]:
    """*host*'s probes; an app with none listed has only the shared rules."""
    build = _BY_APP.get(app_key)
    return build(host) if build is not None else []
