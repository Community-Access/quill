"""Quill Radio's F1 wiring: the shared engine plus Radio's authored catalogue.

The engine -- finding the focused control, composing purpose + control help +
role line, the help window, the provider fix, the dialog-contract hook --
lives in :mod:`quill.ui.app_context_help`, shared by the whole family since
2026-08-23. This module is Radio's registration: :func:`activate` hands the
shared engine Radio's authored, gated purpose catalogue
(:mod:`quill.core.radio.surface_help`), and the rest of the names re-export
so Radio's callers and tests keep one import.
"""

from __future__ import annotations

from quill.ui.app_context_help import (
    ensure_help_provider as ensure_help_provider,
)
from quill.ui.app_context_help import (
    install as install,
)
from quill.ui.app_context_help import (
    show_help as show_help,
)
from quill.ui.app_context_help import (
    topics_for as topics_for,
)


def activate() -> None:
    """Turn F1 help on for Quill Radio, with Radio's purpose catalogue.

    The shared engine registers its handler with the dialog contract,
    installs the wx help provider, and from then on every window the contract
    shows answers F1 with Radio's authored surface purposes leading the
    answer.
    """
    from quill.core.radio import surface_help
    from quill.ui import app_context_help

    app_context_help.activate(surface_help.purpose_for_title)


__all__ = ["activate", "ensure_help_provider", "install", "show_help", "topics_for"]
