"""Closing the window: Exit vs Minimize to Tray, with a persisted default.

Exit is the default button. Anything else makes Alt+F4 answer a question the
listener did not ask -- see the comment on the button row.

Triggered from ``_on_radio_app_close`` (the titlebar X, Alt+F4, and the
Station > Exit menu item all funnel through the same ``EVT_CLOSE`` handler)
whenever ``RadioHistory.close_action`` is still ``"ask"``. The problem this
solves: closing the window used to always fully exit -- silently stopping an
in-progress recording -- even though "keep running in the tray" was one
click away in the Station menu the whole time. "Don't ask me again" writes
the chosen action back to ``close_action`` so this dialog stops appearing;
Preferences (Ctrl+,) can always set it back to "Ask every time".
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


class RadioCloseConfirmDialog:
    """Returns ``(action, dont_ask_again)`` where ``action`` is ``"exit"``
    or ``"minimize"``, or ``None`` if the user cancelled (the window stays
    open, nothing happens)."""

    def __init__(
        self,
        parent: object,
        *,
        recording_active: bool,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: tuple[str, bool] | None = None
        self._minimize_id = int(wx.NewIdRef())
        self._exit_id = int(wx.NewIdRef())

        self.dialog = wx.Dialog(parent, title="Closing Quill Radio")
        root = wx.BoxSizer(wx.VERTICAL)

        message = (
            "Recording is in progress -- exiting now stops it.\n\n" if recording_active else ""
        ) + "Exit Quill Radio, or minimize it to the system tray and keep it running?"
        intro = wx.StaticText(self.dialog, label=message)
        intro.Wrap(360)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        self._dont_ask_check = wx.CheckBox(self.dialog, label="&Don't ask me again")
        self._dont_ask_check.SetName(
            "Don't ask me again -- remembers this choice; change it later in Preferences"
        )
        root.Add(self._dont_ask_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        # Exit first, and the default. Alt+F4 and the titlebar X are the "close
        # this window" gesture, so the answer Enter gives has to be the one the
        # gesture asked for. Minimize led and was the default until 2026-08-21,
        # which meant Alt+F4 followed by Enter -- the whole interaction, for
        # somebody driving by keyboard -- tucked the window into the tray
        # instead of closing it, and the only thing that really exited was the
        # Exit menu item. Minimize is the interesting alternative here, not the
        # expected answer.
        exit_btn = wx.Button(self.dialog, self._exit_id, "E&xit")
        minimize_btn = wx.Button(self.dialog, self._minimize_id, "&Minimize to Tray")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        buttons.Add(exit_btn, 0, wx.RIGHT, 6)
        buttons.Add(minimize_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

        minimize_btn.Bind(wx.EVT_BUTTON, lambda _e: self._choose("minimize"))
        exit_btn.Bind(wx.EVT_BUTTON, lambda _e: self._choose("exit"))

    def _choose(self, action: str) -> None:
        self._result = (action, self._dont_ask_check.GetValue())
        self.dialog.EndModal(self._minimize_id if action == "minimize" else self._exit_id)

    def show(self) -> tuple[str, bool] | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._exit_id,
            affirmative_label="Exit",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(self.dialog, "Closing Quill Radio", announce=self._announce)
            return self._result if answer in (self._minimize_id, self._exit_id) else None
        finally:
            self.dialog.Destroy()
