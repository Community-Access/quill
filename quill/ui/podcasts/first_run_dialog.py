"""The three first-run screens, and the tips switch that lives beside them.

Three screens, not seven. Welcome, add your first podcast, you're set. QUILL Cast
has no account, no tracker and no cloud, so it does not need the privacy screens a
phone app needs -- and a first-run flow that asks somebody to page through consent
they never gave anything is how people learn to dismiss dialogs without reading
them.

The shape is one window with a **read-only text area** carrying the screen's
words, and Back / Next / Skip beneath it. A text area rather than a wall of
labels for one reason that matters here: it can be reviewed with the arrow keys,
character by character, and copied. Somebody who missed a sentence can go back
over it at their own pace instead of asking the app to say it again.

**Skip is a first-class button, not a small link.** Somebody who already knows
what a podcast player is should be able to leave in one keystroke, and making
that awkward is a way of insisting they read something they do not need.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.podcasts.onboarding import (
    FIRST_RUN_SCREENS,
    SCREEN_BODIES,
    SCREEN_TITLES,
    OnboardingState,
)
from quill.ui.dialog_contract import apply_modal_ids


class FirstRunDialog:
    """Welcome, add your first podcast, you're set."""

    def __init__(
        self,
        parent: Any,
        *,
        state: OnboardingState,
        announce: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
        on_add_podcast: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._state = state
        self._announce = announce or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog
        self._on_add_podcast = on_add_podcast
        self._index = 0

        self._dialog = wx.Dialog(
            parent,
            title=SCREEN_TITLES[FIRST_RUN_SCREENS[0]],
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        root = wx.BoxSizer(wx.VERTICAL)

        self._heading = wx.StaticText(self._dialog, label="")
        root.Add(self._heading, 0, wx.ALL, 12)

        self._body = wx.TextCtrl(
            self._dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP
        )
        self._body.SetName("About QUILL Cast; arrow through to read at your own pace")
        root.Add(self._body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self._tips_check = wx.CheckBox(self._dialog, label="Show me a &tip now and then")
        self._tips_check.SetName(
            "One sentence, once each, the first time you reach somewhere a tip would help"
        )
        self._tips_check.SetValue(state.tips_enabled)
        root.Add(self._tips_check, 0, wx.ALL, 12)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._back_btn = wx.Button(self._dialog, label="&Back")
        self._next_btn = wx.Button(self._dialog, label="&Next")
        self._add_btn = wx.Button(self._dialog, label="&Add a Podcast Now...")
        self._skip_btn = wx.Button(self._dialog, wx.ID_CANCEL, "&Skip")
        for button in (self._back_btn, self._next_btn, self._add_btn, self._skip_btn):
            buttons.Add(button, 0, wx.RIGHT, 6)
        root.Add(buttons, 0, wx.ALL, 12)

        self._dialog.SetSizer(root)
        self._dialog.SetMinSize((560, 400))
        apply_modal_ids(self._dialog, cancel_id=wx.ID_CANCEL)

        self._back_btn.Bind(wx.EVT_BUTTON, lambda _e: self.go(-1))
        self._next_btn.Bind(wx.EVT_BUTTON, lambda _e: self.go(1))
        self._add_btn.Bind(wx.EVT_BUTTON, lambda _e: self.add_podcast())
        self._show(0)

    @property
    def dialog(self) -> Any:
        return self._dialog

    def _show(self, index: int) -> None:
        self._index = max(0, min(len(FIRST_RUN_SCREENS) - 1, index))
        key = FIRST_RUN_SCREENS[self._index]
        title = SCREEN_TITLES[key]
        self._dialog.SetTitle(title)
        self._heading.SetLabel(title)
        self._body.SetValue(SCREEN_BODIES[key])
        self._back_btn.Enable(self._index > 0)
        last = self._index == len(FIRST_RUN_SCREENS) - 1
        self._next_btn.SetLabel("&Finish" if last else "&Next")
        # Offered on the screen that talks about adding one, and on the last,
        # because those are the two moments somebody is ready to.
        self._add_btn.Show(self._index >= 1 and self._on_add_podcast is not None)
        self._dialog.Layout()
        self._announce(f"{title}. Screen {self._index + 1} of {len(FIRST_RUN_SCREENS)}.")
        self._body.SetFocus()

    def go(self, delta: int) -> None:
        if self._index + delta >= len(FIRST_RUN_SCREENS):
            self.finish()
            return
        self._show(self._index + delta)

    def add_podcast(self) -> None:
        """Leave the flow and open Add Podcast -- the thing it was pointing at."""
        if self._on_add_podcast is None:
            return
        self.finish()
        self._on_add_podcast()

    def finish(self) -> None:
        self._state.completed_first_run = True
        self._state.tips_enabled = bool(self._tips_check.GetValue())
        self._dialog.EndModal(self._wx.ID_OK)

    def show(self) -> OnboardingState:
        """Run the flow and return the state, whether finished or skipped.

        **Skipping still counts as done.** Somebody who skipped chose to, and
        showing it again next launch would be overriding that choice with a
        guess about what they meant.
        """
        try:
            if self._show_modal_dialog is not None:
                self._show_modal_dialog(self._dialog, "Welcome to QUILL Cast")
            else:
                self._dialog.ShowModal()  # dialog_button_contract: exempt
            self._state.completed_first_run = True
            self._state.tips_enabled = bool(self._tips_check.GetValue())
            return self._state
        finally:
            self._dialog.Destroy()
