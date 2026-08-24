"""Quill Radio's three first-run screens.

The shape is QUILL Cast's, deliberately: one window with a **read-only text
area** carrying the screen's words, and Back / Next / Skip beneath it. A text
area rather than a wall of labels for the one reason that matters here -- it can
be reviewed with the arrow keys, character by character, and copied. Somebody
who missed a sentence can go back over it at their own pace instead of asking
the app to say it again.

**Skip is a first-class button, not a small link.** Somebody who already knows
what an internet radio is should be able to leave in one keystroke, and making
that awkward is a way of insisting they read something they do not need.

**Browse Stations is offered from inside the flow**, on the two screens where
somebody is ready to use it, because the flow is pointing at it. Taking it
leaves the flow finished rather than pending: a listener who went and found a
station has been onboarded, whatever screen they were on.

The words live in :mod:`quill.core.radio.onboarding`, with the keystroke
resolver that keeps them true for somebody who has rebound anything.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from quill.core.radio.onboarding import (
    FIRST_RUN_SCREENS,
    SCREEN_TITLES,
    RadioOnboardingState,
    needs_first_run,
    screen_body,
)
from quill.ui.dialog_contract import apply_modal_ids

_log = logging.getLogger(__name__)


class RadioFirstRunDialog:
    """Welcome, find something to listen to, keep the ones you like."""

    def __init__(
        self,
        parent: Any,
        *,
        state: RadioOnboardingState,
        announce: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
        resolve_key: Callable[[str], str] | None = None,
        on_browse: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._state = state
        self._announce = announce or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog
        self._resolve_key = resolve_key
        self._on_browse = on_browse
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
        self._body.SetName("About Quill Radio; arrow through to read at your own pace")
        root.Add(self._body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        self._tips_check = wx.CheckBox(self._dialog, label="Show me a &tip now and then")
        self._tips_check.SetName(
            "One sentence, once each, the first time you reach somewhere a tip would help"
        )
        self._tips_check.SetValue(state.tips_enabled)
        root.Add(self._tips_check, 0, wx.ALL, 12)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._back_btn = wx.Button(self._dialog, label="&Back")
        self._back_btn.SetHelpText("Returns to the previous screen of the tour.")
        self._next_btn = wx.Button(self._dialog, label="&Next")
        self._next_btn.SetHelpText(
            "Moves to the next screen; the last screen's Next finishes the tour."
        )
        self._browse_btn = wx.Button(self._dialog, label="Browse &Stations Now...")
        self._browse_btn.SetHelpText(
            "Skips the rest of the tour and opens Browse Stations, the tree "
            "of everything there is to listen to."
        )
        self._skip_btn = wx.Button(self._dialog, wx.ID_CANCEL, "&Skip")
        self._skip_btn.SetHelpText(
            "Leaves the tour. Nothing is lost: every door it shows has a key and a menu item."
        )
        for button in (self._back_btn, self._next_btn, self._browse_btn, self._skip_btn):
            buttons.Add(button, 0, wx.RIGHT, 6)
        root.Add(buttons, 0, wx.ALL, 12)

        self._dialog.SetSizer(root)
        self._dialog.SetMinSize((560, 400))
        apply_modal_ids(self._dialog, cancel_id=wx.ID_CANCEL)

        self._back_btn.Bind(wx.EVT_BUTTON, lambda _e: self.go(-1))
        self._next_btn.Bind(wx.EVT_BUTTON, lambda _e: self.go(1))
        self._browse_btn.Bind(wx.EVT_BUTTON, lambda _e: self.browse())
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
        self._body.SetValue(screen_body(key, self._resolve_key))
        self._back_btn.Enable(self._index > 0)
        last = self._index == len(FIRST_RUN_SCREENS) - 1
        self._next_btn.SetLabel("&Finish" if last else "&Next")
        # Offered on the screen that explains browsing, and on the last one,
        # because those are the two moments somebody is ready to.
        self._browse_btn.Show(self._index >= 1 and self._on_browse is not None)
        self._dialog.Layout()
        self._announce(f"{title}. Screen {self._index + 1} of {len(FIRST_RUN_SCREENS)}.")
        # Focus the words, not the first button: the words are what there is to
        # do here, and a first-run window whose focus lands on "Back" reads as
        # though something already went wrong.
        self._body.SetFocus()

    def go(self, delta: int) -> None:
        if self._index + delta >= len(FIRST_RUN_SCREENS):
            self.finish()
            return
        self._show(self._index + delta)

    def browse(self) -> None:
        """Leave the flow and open Browse Stations -- the thing it points at."""
        if self._on_browse is None:
            return
        self.finish()
        self._on_browse()

    def finish(self) -> None:
        self._state.completed_first_run = True
        self._state.tips_enabled = bool(self._tips_check.GetValue())
        # Guarded: wx asserts ("EndModal() called for non modal dialog") if the
        # window is not on a modal loop. Finishing is meaningful either way --
        # the state above is the part that matters -- so a dialog shown any
        # other way records the choice and simply has no loop to end.
        if self._dialog.IsModal():
            self._dialog.EndModal(self._wx.ID_OK)

    def show(self) -> RadioOnboardingState:
        """Run the flow and return the state, whether finished or skipped.

        **Skipping still counts as done.** Somebody who skipped chose to, and
        showing it again next launch would be overriding that choice with a
        guess about what they meant.
        """
        try:
            if self._show_modal_dialog is not None:
                self._show_modal_dialog(self._dialog, "Welcome to Quill Radio")
            else:
                self._dialog.ShowModal()  # dialog_button_contract: exempt
            self._state.completed_first_run = True
            self._state.tips_enabled = bool(self._tips_check.GetValue())
            return self._state
        finally:
            self._dialog.Destroy()


def maybe_run_first_run(host: Any) -> bool:
    """Run the flow at launch if this listener needs it. True when it ran.

    Called deferred (``wx.CallAfter``) once the window is up. Never raises: a
    welcome that can take the app down on its very first launch would be the
    worst possible first impression, and there is nothing here worth failing a
    launch over.

    Deliberately *not* the same shape as the media-health notice beside it. That
    one is a spoken courtesy, because it is news the listener did not ask for
    and does not have to act on. This is modal, because it is the whole content
    of the first launch and there is nothing else on screen to do -- and because
    Skip leaves in one keystroke.

    QUILL Cast's equivalent dialog has existed for months with **no caller at
    all**: written, tested, and never once shown. That is the failure this
    function exists to not repeat.

    **It refuses over a window that is not on screen.** The launch path shows
    the main window and *then* enters the loop this deferred call runs in, so
    in a real launch the frame is always up. Anywhere else -- a frame built
    and never shown, which is what a test harness does -- a modal would be a
    dialog with nothing behind it and nobody able to answer it, and
    ``ShowModal`` would sit there forever. A welcome nobody can see is not a
    welcome; skipping it is the honest answer, and it costs a real launch
    nothing because a real launch is always shown.
    """
    try:
        frame = getattr(host, "frame", None)
        is_shown = getattr(frame, "IsShown", None)
        if frame is None or (callable(is_shown) and not is_shown()):
            return False
        history = getattr(host, "_radio_history", None)
        state = getattr(history, "onboarding", None)
        if state is None:
            return False
        favorites = getattr(getattr(host, "_radio_favorites", None), "favorites", [])
        if not needs_first_run(state, has_favorites=bool(favorites)):
            return False

        browse = getattr(host, "open_internet_radio", None)
        dialog = RadioFirstRunDialog(
            getattr(host, "frame", None),
            state=state,
            announce=getattr(host, "_announce", None),
            show_modal_dialog=getattr(host, "_show_modal_dialog", None),
            resolve_key=lambda command_id: host._binding_for(command_id) or "",
            on_browse=(lambda: browse()) if callable(browse) else None,
        )
        dialog.show()
        saver = getattr(host, "_save_radio_history", None)
        if callable(saver):
            saver()
        return True
    except Exception:  # noqa: BLE001 - a welcome must never break a launch
        _log.exception("first-run flow failed")
        return False
