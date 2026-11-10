"""The GitHub Workbench is the one GitHub management window in both editors."""

from __future__ import annotations

__all__ = ["workbench_window_enabled"]


def workbench_window_enabled() -> bool:
    """The retired dialog fallback is unavailable; all doors use the Workbench."""
    return True
