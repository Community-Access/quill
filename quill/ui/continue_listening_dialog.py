"""**Continue Listening** -- everything you started, wherever you started it.

One window over what used to be four separate memories: a podcast episode's
saved position, a LibriVox chapter or an Internet Archive recording in Quill
Radio's resume store, and a local file. Each worked. None of them could answer
*"what was I in the middle of?"*

The list is newest first and every row names its provider, because "The
Moonstone, chapter 4" means something different depending on whether Enter
starts a podcast, a stream or a file -- and a list that hides which is one you
have to try things in to understand.

Two rules the window keeps:

* **Nothing is offered that cannot be resumed.** The gatherer already drops
  anything whose address was not kept; the window additionally disables Resume
  when the app it is running in has no way to play that kind. Cast has no radio
  player and Quill Radio has no podcast library, and a Resume that silently
  declines is worse than one that says it cannot.
* **Forget is here too.** The reason people avoid a resume list is that it fills
  with things they abandoned on purpose. Removing one is a first-class button,
  not something you have to finish an episode to achieve.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.media.continue_listening import Unfinished, summarise
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

TITLE = "Continue Listening"

#: Shown when nothing is unfinished. A finished library is a good state, and
#: saying so plainly beats an empty list that reads as a failure.
NOTHING_HEADING = "Nothing unfinished. Everything you started, you finished."


class ContinueListeningDialog:
    """Pick up whatever you were in the middle of."""

    def __init__(
        self,
        parent: Any,
        *,
        rows: list[Unfinished],
        resume: Callable[[Unfinished], bool] | None = None,
        forget: Callable[[Unfinished], bool] | None = None,
        can_resume: Callable[[Unfinished], bool] | None = None,
        announce: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._rows = list(rows)
        self._resume = resume
        self._forget = forget
        self._can_resume = can_resume or (lambda _row: resume is not None)
        self._announce = announce or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog

        self._dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self._dialog, label=summarise(self._rows) if self._rows else NOTHING_HEADING
            ),
            0,
            wx.ALL,
            10,
        )
        root.Add(wx.StaticText(self._dialog, label="&Unfinished:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._list = wx.ListBox(
            self._dialog, choices=[row.row_label() for row in self._rows], style=wx.LB_SINGLE
        )
        self._list.SetName("Things you started and did not finish, most recent first")
        if self._rows:
            self._list.SetSelection(0)
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._resume_btn = wx.Button(self._dialog, wx.ID_OK, "&Resume")
        self._forget_btn = wx.Button(self._dialog, label="&Forget This One")
        buttons.Add(self._resume_btn, 0, wx.RIGHT, 6)
        buttons.Add(self._forget_btn, 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(self._dialog, wx.ID_CANCEL, "Cl&ose"), 0)
        root.Add(buttons, 0, wx.ALL, 10)

        self._dialog.SetSizer(root)
        self._dialog.SetMinSize((620, 400))
        self._dialog.Fit()
        apply_modal_ids(self._dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

        self._resume_btn.Bind(wx.EVT_BUTTON, lambda _e: self.resume_selected())
        self._forget_btn.Bind(wx.EVT_BUTTON, lambda _e: self.forget_selected())
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._sync_buttons())
        # Enter and Space activate as well as double-click (GATE-13): a
        # wx.ListBox emits no item-activated event of its own, so binding only
        # the double-click would put Resume out of reach of the keyboard -- in
        # a window whose entire audience is using one.
        apply_listbox_activation(self._list, lambda _e: self.resume_selected())
        self._sync_buttons()
        self._list.SetFocus()

    @property
    def dialog(self) -> Any:
        return self._dialog

    def selected(self) -> Unfinished | None:
        index = self._list.GetSelection()
        if index < 0 or index >= len(self._rows):
            return None
        return self._rows[index]

    def _sync_buttons(self) -> None:
        """Enable only what this app can actually do with the highlighted row."""
        row = self.selected()
        self._resume_btn.Enable(row is not None and bool(self._can_resume(row)))
        self._forget_btn.Enable(row is not None and self._forget is not None)

    def resume_selected(self) -> bool:
        """Play the highlighted row from where it was left."""
        row = self.selected()
        if row is None or self._resume is None:
            return False
        if not self._can_resume(row):
            # Named rather than merely refused: knowing *which app* has it is
            # the useful half of the answer.
            self._announce(f"{row.title} cannot be played here. Open it in the app that has it.")
            return False
        if not self._resume(row):
            self._announce(f"{row.title} could not be started.")
            return False
        self._dialog.EndModal(self._wx.ID_OK)
        return True

    def forget_selected(self) -> bool:
        """Drop the saved place, and take the row out of the list."""
        row = self.selected()
        if row is None or self._forget is None:
            return False
        if not self._forget(row):
            self._announce(f"{row.title} could not be forgotten.")
            return False
        index = self._list.GetSelection()
        self._rows.pop(index)
        self._list.Delete(index)
        if self._rows:
            self._list.SetSelection(min(index, len(self._rows) - 1))
        self._sync_buttons()
        self._announce(f"Forgot where you were in {row.title}.")
        return True

    def show(self) -> int:
        """Show the window, and always destroy it afterwards (A11Y-4)."""
        try:
            if self._show_modal_dialog is not None:
                return int(self._show_modal_dialog(self._dialog, TITLE))
            return int(self._dialog.ShowModal())  # dialog_button_contract: exempt
        finally:
            self._dialog.Destroy()
