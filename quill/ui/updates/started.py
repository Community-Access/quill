"""Telling the update helper "I started", once the first window is up (plan 6.6).

Every app with release channels calls :func:`confirm_after_start` from its
start-up, deferred until the event loop runs. It writes the marker the update
helper waits for, settles a pending update in Update History, ages out what
was kept for undoing an update, and -- when the helper had to undo one --
says once, plainly, what happened.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

__all__ = ["confirm_after_start", "confirm_for_shell"]

#: Long enough for the screen reader to finish the window title first.
_SPEAK_DELAY_MS = 2500


def confirm_after_start(
    *,
    app_key: str,
    app_name: str,
    version: str,
    updates_dir: Path,
    announce: Callable[[str], object],
) -> None:
    """Run the start-up book-keeping now; never raises."""
    if not version:
        return
    from quill.core.updater.apply import confirm_started

    report = confirm_started(updates_dir, app_key=app_key, app_name=app_name, version=version)
    if report.notice:
        try:
            wx.CallLater(_SPEAK_DELAY_MS, announce, report.notice)
        except Exception:  # noqa: BLE001 - no event loop (tests): say it now
            announce(report.notice)


def confirm_for_shell(shell: Any, app_id: str) -> None:
    """:func:`confirm_after_start` for an app built on ``quill.ui.app_shell``."""
    from quill.core.paths import app_data_dir

    try:
        from quill.ui.updates.shell import installed_app_version

        version = installed_app_version(app_id)
    except (KeyError, ImportError):
        from quill.core.app_version import installed_version

        version = installed_version("")
    confirm_after_start(
        app_key=app_id,
        app_name=shell._update_app_name(),
        version=version,
        updates_dir=app_data_dir() / "updates",
        announce=shell._announce,
    )
