"""The AI menu's setup rows, extracted from main_frame_menu under GATE-11.

Two on-ramps, side by side at the top of the AI menu. **Set Up AI** is the
general wizard: cloud accounts, agents, or skipping the whole thing. **Set Up
Local AI (Ollama)** is the guided local path issue #1558 asked for -- check
the machine, fetch the installer, download a model, connect -- which the
general wizard could only describe ("install it from ollama.com, then try
again"). They are appended together because a person choosing between them is
making one decision, and finding the second option three menus away is how
the reporter of #1558 ended up in Ollama Cloud when they wanted their own
machine.

Direct-bound (no command-registry ids) so the size-budgeted menu module does
not grow per row; both dialogs rebuild the menu themselves on completion.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.i18n import _


def append_ai_setup_items(controller: Any, menu: wx.Menu) -> None:
    """Append the two setup rows to *menu* and bind them on the host frame."""
    from quill.core.ai.onboarding import ai_needs_setup
    from quill.ui.ai_setup_wizard import run_ai_setup_wizard
    from quill.ui.local_ai_wizard import run_local_ai_setup

    # Labeled "start here" and shown first until AI is set up, then it stays
    # as a quiet re-run point.
    setup_id = wx.NewIdRef()
    setup_label = _("&Set Up AI... (start here)") if ai_needs_setup() else _("&Set Up AI...")
    menu.Append(setup_id, setup_label)
    controller.frame.Bind(wx.EVT_MENU, lambda _e: run_ai_setup_wizard(controller), id=setup_id)

    local_id = wx.NewIdRef()
    menu.Append(local_id, _("Set Up Local AI (&Ollama)..."))
    controller.frame.Bind(wx.EVT_MENU, lambda _e: run_local_ai_setup(controller), id=local_id)
