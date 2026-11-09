"""QUILL's half of the Command Key: F11 and What Can I Say Here.

docs/design/command-key.md 16.4. Everything the Command Key does is shared --
the policy in :mod:`quill.core.command_catalogue.policy`, the windows in
:mod:`quill.ui.command_key_ui`, each app's four answers in
:mod:`quill.ui.command_key_hosts` -- and QUILL Lite reaches the same code on
the same keys. This mixin registers QUILL's command, puts its row in the Tools
menu, and answers Help, What Can I Say Here, which keeps the id and key of
What Can I Do Here (decision 12).
"""

from __future__ import annotations

from typing import Any

__all__ = ["COMMAND_KEY", "CommandKeyMixin"]

COMMAND_KEY = "app.command_key"


class CommandKeyMixin:
    """Say or Type a Command, in QUILL."""

    def _register_command_key_commands(self) -> None:
        host: Any = self
        host.commands.register(
            COMMAND_KEY,
            "Say or Type a Command...",
            self.open_command_key,
            host._binding_for(COMMAND_KEY),
        )

    def _append_command_key_item(self, menu: Any) -> None:
        """Called from the Tools menu, under Command Palette. No access key:
        both are ways into every command, and the palette took C (GATE-14)."""
        import wx

        from quill.core.i18n import _

        host: Any = self
        self._id_command_key = wx.NewIdRef()
        menu.Append(
            self._id_command_key, host._menu_label(_("Say or Type a Command..."), COMMAND_KEY)
        )
        host.frame.Bind(
            wx.EVT_MENU, lambda _event: self.open_command_key(), id=self._id_command_key
        )

    def open_command_key(self) -> None:
        """F11: type what you want this window to do. Never touches dictation."""
        from quill.ui.command_key_hosts import quill_command_key

        quill_command_key(self)

    def show_what_can_i_say_here(self) -> None:
        """Ctrl+Alt+Shift+F1: this window's commands right now, grouped, to read or run."""
        from quill.ui.command_key_hosts import quill_what_can_i_say_here

        quill_what_can_i_say_here(self)
