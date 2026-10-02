"""Saying, once, that the last session could not finish saving (F-06).

The teardown side is :mod:`quill.core.shutdown_report`. This is the launch side
for Quill Radio and QUILL Cast: read the pending sentence the previous session
left, say it once, and register the Retry that Recent Problems offers for the
"Closing" rows.

**Retry is honest about what it can do.** The data a closing session failed to
write went with that session; nothing can bring it back. What Retry *can* do is
the same write again now, from what this session holds -- which proves the data
folder is writable again, and for Radio's recording marker it is the whole fix.
Each app passes its own ``retry`` that does exactly that and says what happened.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core import problem_log, shutdown_report

__all__ = ["register_shutdown_retry", "surface_previous_shutdown"]


def surface_previous_shutdown(app: Any, app_id: str) -> str:
    """Say the previous session's closing failure, if it left one. Returns it.

    Called once at launch, deferred, so it is said after the window is up.
    Never raises: a notice that cannot be read is not worth a failed launch.
    """
    try:
        from quill.core.paths import app_data_dir

        said = shutdown_report.take_pending(app_data_dir(), app_id)
    except Exception:  # noqa: BLE001 - launch must never fail over a notice
        return ""
    if said:
        try:
            app._announce(said)
        except Exception:  # noqa: BLE001
            pass
    return said


def register_shutdown_retry(retry: Callable[[], str]) -> None:
    """Teach Recent Problems what Retry means on a "Closing" row for this app."""
    from quill.ui.problems_dialog import register_retry

    def handler(_problem: problem_log.Problem) -> str:
        try:
            return retry()
        except Exception:  # noqa: BLE001 - a retry that fails says so
            return "That still could not be saved. Check that the data folder can be written to."

    register_retry(problem_log.KIND_SHUTDOWN, handler)
