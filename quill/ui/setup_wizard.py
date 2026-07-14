"""QUILL first-run setup wizard.

Shown automatically the first time QUILL launches
(``settings.setup_wizard_completed == False``).  Re-runnable from
Help > Personalise QUILL.

The wizard walks the user through ten pages and writes the result into
``Settings`` and ``FeatureManager`` before closing.  No feature is toggled
mid-wizard; all changes are applied atomically when the user clicks Finish.

Usage::

    from quill.ui.setup_wizard import run_setup_wizard
    changed = run_setup_wizard(parent, settings, feature_manager)
    if changed:
        # reload menu, announce profile change, etc.
        ...
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import wx

from quill.core.features import FeatureManager
from quill.core.i18n import _, lazy_gettext
from quill.core.settings import Settings

_log = logging.getLogger(__name__)

_WIZARD_TITLE = lazy_gettext("Personalise QUILL")
_PAGE_COUNT = 9


def run_setup_wizard(
    parent: wx.Window,
    settings: Settings,
    feature_manager: FeatureManager,
    *,
    announce_cb: Callable[[str], None] | None = None,
    show_modal_fn: Callable[[Any, str], int] | None = None,
    open_ai_hub: Callable[[], None] | None = None,
) -> tuple[bool, bool]:
    """Open the setup wizard as a modal dialog.

    Returns ``(completed, aborted)`` where:
    - ``completed`` is True when the user pressed Finish.
    - ``aborted`` is True when the user pressed Cancel (first-run use case).

    The caller is responsible for saving ``settings`` and ``feature_manager``
    after a ``True`` completed return.

    Pass ``show_modal_fn`` (typically ``MainFrame._show_modal_dialog``) so the
    dialog gets screen-reader enter/exit announcements and region tracking.
    Pass ``announce_cb`` to give the wizard access to the SR announcement channel.
    """
    from quill.ui.setup_wizard_pages import SetupWizardDialog

    dlg = SetupWizardDialog(
        parent, settings, feature_manager, announce_cb=announce_cb, open_ai_hub=open_ai_hub
    )
    try:
        if show_modal_fn is not None:
            result = show_modal_fn(dlg, _("Setup Wizard"))
        else:
            result = dlg.ShowModal()
        completed = result == wx.ID_OK
        aborted = dlg.aborted_first_run
        if completed:
            settings.setup_wizard_completed = True
        return completed, aborted
    finally:
        dlg.Destroy()
