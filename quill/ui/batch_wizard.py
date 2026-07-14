"""Batch Import / Export wizard launcher (issue #262).

Mirrors :mod:`quill.ui.setup_wizard` — a thin module-level entry point that
constructs the dialog, runs it modally through the host application's
``_show_modal_dialog`` hook, and returns the user's choices (or ``None`` if
they cancelled).

The wizard collects a :class:`quill.core.batch_convert.BatchPlan`. The caller
is responsible for submitting the plan to ``MainFrame._run_background_task``
and surfacing the Status Page so the user sees progress.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import wx

from quill.core.batch_convert import BatchPlan, OutputLayout, OverwritePolicy
from quill.core.i18n import _
from quill.core.settings import Settings

_log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BatchRequest:
    """Result of a successful wizard run, ready for the worker pool."""

    plan: BatchPlan


def run_batch_wizard(
    parent: wx.Window,
    settings: Settings,
    *,
    announce_cb: Callable[[str], None] | None = None,
    show_modal_fn: Callable[[Any, str], int] | None = None,
) -> BatchRequest | None:
    """Open the Batch Conversion wizard as a modal dialog.

    Returns a :class:`BatchRequest` when the user clicks Start, or ``None``
    when they cancel. The wizard does not mutate ``settings``; the caller
    persists any defaults it wants to remember.

    ``show_modal_fn`` (typically ``MainFrame._show_modal_dialog``) ensures the
    dialog gets screen-reader enter/exit announcements. ``announce_cb`` lets
    the wizard speak progress through the configured announcement backend.
    """

    from quill.ui.batch_wizard_pages import BatchWizardDialog

    dlg = BatchWizardDialog(parent, settings, announce_cb=announce_cb)
    try:
        if show_modal_fn is not None:
            result = show_modal_fn(dlg, _("Batch Conversion"))
        else:
            result = dlg.ShowModal()
        if result != wx.ID_OK:
            return None
        request = dlg.build_request()
        return request
    finally:
        dlg.Destroy()


__all__ = ["BatchRequest", "run_batch_wizard", "OverwritePolicy", "OutputLayout", "Path"]
