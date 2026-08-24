"""QUILL Cast's F1 wiring: the shared engine plus Cast's authored catalogue.

The engine -- finding the focused control, composing purpose + control help +
role line, the help window, the provider fix, the dialog-contract hook --
lives in :mod:`quill.ui.app_context_help`, shared by the whole family since
2026-08-23. Cast inherited the wiring that day and answered F1 everywhere,
but with the generic sentence for the surface: :func:`activate` hands the
shared engine Cast's authored, gated purpose catalogue
(:mod:`quill.core.podcasts.surface_help`), added 2026-08-24. The rest of the
names re-export so Cast's callers and tests keep one import, exactly as
:mod:`quill.ui.radio.context_help` does for Quill Radio.
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
    """Turn F1 help on for QUILL Cast, with Cast's purpose catalogue.

    Called after ``_init_app_shell`` (which activates the shared engine with
    the generic resolver) so Cast's catalogue wins -- last registration wins,
    by design.
    """
    from quill.core.podcasts import surface_help
    from quill.ui import app_context_help

    app_context_help.activate(surface_help.purpose_for_title)


__all__ = ["activate", "ensure_help_provider", "install", "show_help", "topics_for"]
