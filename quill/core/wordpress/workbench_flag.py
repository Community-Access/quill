"""Tools > WordPress doors always open the WordPress Workbench in both editors."""

from __future__ import annotations

__all__ = ["workbench_window_enabled"]


def workbench_window_enabled() -> bool:
    """The classic windows cannot be selected or forced back on."""
    return True
