"""Quill Radio's rows for the Command Key (docs/design/command-key.md 16.4).

Say or Type a Command and What Can I Say Here (Ctrl+Alt+Shift+F1, QUILL's key
for it, rule 2), in the Help menu under Command Palette. Everything they do is
the shared module's (:mod:`quill.ui.command_key_hosts`).

Say or Type a Command is **Alt+F11** in Quill Radio, not F11: Video > Full
Screen is on F11, as browsers have it (rule 1, decision 2), and one menu bar
cannot give one key to two rows. Alt+F11 sits beside it and is no dictation
key anywhere in the family; Ctrl+Grave, the plan's first fallback (9.4), is a
key wx cannot bind. Giving Full Screen to the video window's own keys, so the
player can have F11 too, is a follow-up in the plan.
"""

from __future__ import annotations

from typing import Any

__all__ = ["append_command_key_rows"]

COMMAND_KEY = "app.command_key"
WHAT_CAN_I_SAY = "help.what_can_i_do_here"


def append_command_key_rows(host: Any, help_menu: Any, wx: Any) -> None:
    """Register the two commands and put their rows in *help_menu*, on S and I:
    the letters of both names Help has not spent (GATE-14)."""
    from quill.ui.command_key_hosts import radio_command_key, radio_what_can_i_say_here

    host.commands.try_register(
        COMMAND_KEY, "Say or Type a Command...", lambda: radio_command_key(host)
    )
    host.commands.try_register(
        WHAT_CAN_I_SAY, "What Can I Say Here?", lambda: radio_what_can_i_say_here(host)
    )
    for label, command_id in (
        ("&Say or Type a Command...", COMMAND_KEY),
        ("What Can &I Say Here?", WHAT_CAN_I_SAY),
    ):
        item_id = wx.NewIdRef()
        help_menu.Append(item_id, host._menu_label(label, command_id))
        host.frame.Bind(
            wx.EVT_MENU, lambda _event, cid=command_id: host.commands.run(cid), id=item_id
        )
