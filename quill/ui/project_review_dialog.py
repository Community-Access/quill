"""Review Changes for a project turn: a list of files over one change at a time (code.md 5.4).

The shape ``UncommittedChangesDialog`` and the PR diff viewer already use, and
the one readers handle well: a list, then detail.

- **The file list.** One row per file, a whole sentence ("cli.py, changed, 3
  changes, taken"). The row says whether it is taken, rather than a check box
  saying it (a check-list box's state is not read on arrowing, A11Y-SR-1).
  Space takes or leaves the whole file; Enter moves to its changes.
- **One change at a time,** read through :mod:`quill.core.ai.code_diff`: where
  it is ("Change 2 of 3, lines 40 to 44, in function parse_args"), a token diff
  for a one-line change, indentation as a count, line numbers leading every
  line. Accept and Reject act on the change shown; Next and Previous move
  between changes and on to the next file.
- **Why This Change?** says the reason the agent gave with the change.
- **Apply Accepted Changes** (Enter on the button, the default) writes every
  accepted change at once; **Reject All** (Escape) writes nothing.

Nothing here writes a file: the dialog only marks the
:class:`~quill.core.ai.change_set.ChangeSet`, and the task applies it after the
checkpoint is safe (GATE-PROJECT-REVIEW).

**Spoken (GATE-13):** the reader says the rows, the details and the buttons.
The dialog speaks only what changes on a control that does not have focus --
"Change 2 accepted" after Accept, because the row text it changes is not where
focus is.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.ai import project_task_words as words
from quill.core.ai.change_set import ChangeKind, ChangeSet, FileChange
from quill.core.ai.code_diff import describe_file, describe_hunk
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["ProjectReviewDialog", "review_project_changes"]

_PAD = 8


class ProjectReviewDialog(wx.Dialog):
    """Every file the turn would change, and each change in it."""

    def __init__(
        self, parent: Any, changes: ChangeSet, announce: Callable[[str], None] | None = None
    ) -> None:
        super().__init__(
            parent,
            title="Review Changes",  # words.REVIEW_TITLE
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._changes = changes
        self._announce = announce or (lambda _text: None)
        self._file = 0
        self._hunk = 0
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        sizer.Add(wx.StaticText(self, label="&Files"), 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        # A plain list, not a check-list box (A11Y-SR-1): the row's own sentence
        # says "taken" or "not taken", so the state is read with the row.
        self.files = wx.ListBox(self, choices=[f.row_text() for f in changes.files])
        set_accessible_name(self.files, "Files")
        self.files.SetHelpText(
            "Every file this turn would change, each row saying whether it is taken. "
            "Space takes or leaves the whole file. Enter moves to the file's changes."
        )
        self.files.Bind(wx.EVT_LISTBOX, lambda _e: self._select_file(self.files.GetSelection()))
        self.files.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self.details.SetFocus())
        self.files.Bind(wx.EVT_KEY_DOWN, self._on_files_key)
        sizer.Add(self.files, 1, wx.EXPAND | wx.ALL, _PAD)

        sizer.Add(
            wx.StaticText(self, label="Change &details"), 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD
        )
        self.details = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_DONTWRAP
        )
        set_accessible_name(self.details, "Change details")
        self.details.SetHelpText(
            "The change shown now: where it is, what it does, and each line with its "
            "line number first. Indentation is said as a count when it changes. "
            "Read it with the arrow keys."
        )
        sizer.Add(self.details, 2, wx.EXPAND | wx.ALL, _PAD)

        row = wx.BoxSizer(wx.HORIZONTAL)
        specs = (
            ("&Accept", "Takes the change shown.", lambda: self._mark(True)),
            (
                "&Reject",
                "Leaves the change shown out; it is never written.",
                lambda: self._mark(False),
            ),
            ("&Next Change", "Shows the next change, then the next file's.", lambda: self._step(1)),
            ("&Previous Change", "Shows the change before this one.", lambda: self._step(-1)),
            (
                "Accept All in F&ile",
                "Takes every change in this file.",
                lambda: self._mark_file(True),
            ),
            (
                "Reject All in Fi&le",
                "Leaves every change in this file out.",
                lambda: self._mark_file(False),
            ),
            (
                "&Why This Change?",
                "Says the reason the agent gave for the change shown.",
                self._why,
            ),
        )
        for label, help_text, action in specs:
            button = wx.Button(self, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, run=action: run())
            row.Add(button, 0, wx.RIGHT, _PAD)
        sizer.Add(row, 0, wx.LEFT | wx.RIGHT, _PAD)

        end = wx.BoxSizer(wx.HORIZONTAL)
        end.AddStretchSpacer(1)
        self.apply_button = wx.Button(self, wx.ID_OK, "Apply Accepted Changes")
        self.apply_button.SetHelpText(
            "Writes every accepted change at once, after QUILL has kept a copy for "
            "Undo Last Turn. Rejected changes are never written."
        )
        self.reject_button = wx.Button(self, wx.ID_CANCEL, "Reject All")
        self.reject_button.SetHelpText("Writes nothing from this turn. Escape does the same.")
        end.Add(self.apply_button, 0, wx.RIGHT, _PAD)
        end.Add(self.reject_button, 0)
        sizer.Add(end, 0, wx.EXPAND | wx.ALL, _PAD)
        self.apply_button.SetDefault()
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Apply Accepted Changes",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Reject All",
        )
        if changes.files:
            self.files.SetSelection(0)
            self._select_file(0)
        self.SetInitialSize(dip_size(self, 760, 600))
        self.Centre()
        self.files.SetFocus()

    # -- what is shown ----------------------------------------------------------- #

    @property
    def current(self) -> FileChange | None:
        files = self._changes.files
        return files[self._file] if 0 <= self._file < len(files) else None

    def _select_file(self, index: int) -> None:
        if index < 0 or index >= len(self._changes.files):
            return
        self._file = index
        self._hunk = 0
        self._show()

    def _show(self) -> None:
        change = self.current
        if change is None:
            self.details.SetValue(words.NO_CHANGES)
            return
        if change.kind is ChangeKind.EDIT and change.hunks:
            said = describe_hunk(change, self._hunk)
        else:
            said = describe_file(change)
        self.details.SetValue(f"{change.path}. {said.heading}\n{said.body}")
        self.details.SetInsertionPoint(0)

    def _refresh_rows(self) -> None:
        for index, change in enumerate(self._changes.files):
            self.files.SetString(index, change.row_text())

    # -- what the person does ---------------------------------------------------- #

    def _mark(self, accepted: bool) -> None:
        change = self.current
        if change is None:
            return
        if change.kind is ChangeKind.EDIT and change.hunks:
            change.hunks[self._hunk].accepted = accepted
            said = words.change_marked(self._hunk + 1, accepted)
        else:
            change.set_all(accepted)
            said = words.file_marked(change.path, accepted)
        self._refresh_rows()
        self._show()
        self._announce(said)  # the row it changed is not where focus is

    def _mark_file(self, accepted: bool) -> None:
        change = self.current
        if change is None:
            return
        change.set_all(accepted)
        self._refresh_rows()
        self._show()
        self._announce(words.file_marked(change.path, accepted))

    def toggle_file(self) -> None:
        """Space on a row: take the whole file, or leave it if it was all taken."""
        change = self.current
        if change is not None:
            self._mark_file(change.accepted_count != change.change_count)

    def _step(self, delta: int) -> None:
        change = self.current
        if change is None:
            return
        count = len(change.hunks) if change.kind is ChangeKind.EDIT and change.hunks else 1
        target = self._hunk + delta
        if 0 <= target < count:
            self._hunk = target
        else:
            following = self._file + delta
            if not 0 <= following < len(self._changes.files):
                self._announce(words.NO_MORE_CHANGES if delta > 0 else words.NO_EARLIER_CHANGES)
                return
            self._file = following
            self.files.SetSelection(following)
            nxt = self._changes.files[following]
            span = len(nxt.hunks) if nxt.kind is ChangeKind.EDIT and nxt.hunks else 1
            self._hunk = 0 if delta > 0 else span - 1
        self._show()
        self.details.SetFocus()

    def _why(self) -> None:
        change = self.current
        if change is not None:
            self._announce(words.why_sentence(change.path, change.reason))

    def _on_files_key(self, event: Any) -> None:
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.details.SetFocus()
            return
        if event.GetKeyCode() == wx.WXK_SPACE:
            self.toggle_file()
            return
        event.Skip()


def review_project_changes(
    parent: Any, changes: ChangeSet, announce: Callable[[str], None] | None = None
) -> bool:
    """Show the review; True when the person chose Apply Accepted Changes.

    Escape, Reject All or closing the window marks every change rejected, so a
    caller that ignores the answer still writes nothing.
    """
    dialog = ProjectReviewDialog(parent, changes, announce)
    try:
        result = show_modal_dialog(dialog, words.REVIEW_TITLE)
    finally:
        dialog.Destroy()
    if result != wx.ID_OK:
        changes.reject_all()
        return False
    return True
