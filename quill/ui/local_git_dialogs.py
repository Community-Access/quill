"""Dialogs for local git accessibility (`docs/planning/github.md` section 4):
the uncommitted-changes viewer, the merge-conflict walker, and the
interactive-rebase list.

All three follow the same shape as the existing PR diff viewer
(`github_pr_diff_dialog.py`): a modal list-over-detail dialog, content
rendered through `quill.core.compare_service` (via the same
`render_pull_file_diff` helper the PR diff viewer already uses -- it's
format-agnostic, taking two text blobs and two labels, so no new compare
logic is needed here), every control named, `show_modal_dialog` +
`apply_modal_ids` (never raw `ShowModal`).

The underlying git orchestration is `quill.core.local_git`, wx-free; these
dialogs only render its models and call back into it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.github_items_view import render_pull_file_diff

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.core.local_git import ConflictHunk, FileChange, RebaseTodoEntry

# ---------------------------------------------------------------------------
# Uncommitted changes viewer
# ---------------------------------------------------------------------------


class UncommittedChangesDialog:
    """List of changed files with an accessible diff for the selected one,
    and Stage/Unstage/Stage All actions."""

    def __init__(
        self,
        parent: object,
        changes: list[FileChange],
        *,
        diff_provider: Callable[[str], tuple[str, str]],
        on_stage: Callable[[str], None],
        on_unstage: Callable[[str], None],
        on_stage_all: Callable[[], None],
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._changes = changes
        self._diff_provider = diff_provider
        self._on_stage = on_stage
        self._on_unstage = on_unstage
        self._on_stage_all = on_stage_all
        self._announce = announce_cb or (lambda _m: None)

        self.dialog = wx.Dialog(
            parent, title="Uncommitted Changes", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((640, 460))
        self.dialog.SetSize((760, 560))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        self._list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._list.SetName("Changed files; select a file to see its differences")
        self._list.InsertColumn(0, "Staged")
        self._list.InsertColumn(1, "Unstaged")
        self._list.InsertColumn(2, "File")
        root.Add(self._list, 2, wx.EXPAND | wx.ALL, 10)

        root.Add(wx.StaticText(panel, label="Differences"), 0, wx.LEFT | wx.TOP, 6)
        self._details = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
        self._details.SetName("Differences for the selected file")
        root.Add(self._details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._stage_btn = wx.Button(panel, label="&Stage")
        self._stage_btn.SetName("Stage the selected file")
        self._unstage_btn = wx.Button(panel, label="&Unstage")
        self._unstage_btn.SetName("Unstage the selected file")
        self._stage_all_btn = wx.Button(panel, label="Stage &All")
        self._stage_all_btn.SetName("Stage every changed file")
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close dialog")
        for b in (self._stage_btn, self._unstage_btn, self._stage_all_btn):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self._stage_btn.Bind(wx.EVT_BUTTON, lambda _e: self._stage_selected())
        self._unstage_btn.Bind(wx.EVT_BUTTON, lambda _e: self._unstage_selected())
        self._stage_all_btn.Bind(wx.EVT_BUTTON, lambda _e: self._stage_all())

        self._populate()

    def _populate(self) -> None:
        self._list.DeleteAllItems()
        for change in self._changes:
            idx = self._list.InsertItem(self._list.GetItemCount(), change.staged_label or "")
            self._list.SetItem(idx, 1, change.unstaged_label or "")
            self._list.SetItem(idx, 2, change.path)

    def _selected_change(self) -> FileChange | None:
        idx = self._list.GetFirstSelected()
        if idx < 0 or idx >= len(self._changes):
            return None
        return self._changes[idx]

    def _on_select(self, _event: object) -> None:
        change = self._selected_change()
        if change is None:
            return
        head_text, working_text = self._diff_provider(change.path)
        rendered = render_pull_file_diff(
            change.path, head_text, working_text, base_label="HEAD", head_label="working copy"
        )
        self._details.SetValue(rendered)

    def _stage_selected(self) -> None:
        change = self._selected_change()
        if change is None:
            self._announce("Select a file first.")
            return
        self._on_stage(change.path)

    def _unstage_selected(self) -> None:
        change = self._selected_change()
        if change is None:
            self._announce("Select a file first.")
            return
        self._on_unstage(change.path)

    def _stage_all(self) -> None:
        self._on_stage_all()

    def refresh(self, changes: list[FileChange]) -> None:
        self._changes = changes
        self._populate()

    def show(self) -> None:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        try:
            show_modal_dialog(self.dialog, "Uncommitted Changes")
        finally:
            self.dialog.Destroy()


# ---------------------------------------------------------------------------
# Merge-conflict walker
# ---------------------------------------------------------------------------


class MergeConflictDialog:
    """Walk a conflicted file's hunks one at a time: "Conflict 1 of 3: your
    version says X, their version says Y" with keep-yours/keep-theirs/
    keep-both/edit-manually per hunk."""

    def __init__(
        self,
        parent: object,
        path: str,
        hunks: list[ConflictHunk],
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._path = path
        self._hunks = hunks
        self._resolutions: list[str] = ["ours"] * len(hunks)
        self._index = 0
        self._announce = announce_cb or (lambda _m: None)
        self._cancelled = False

        self.dialog = wx.Dialog(
            parent, title=f"Resolve Conflicts: {path}", style=wx.DEFAULT_DIALOG_STYLE
        )
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Conflict position")
        root.Add(self._status, 0, wx.ALL, 10)

        self._ours_box = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(500, 100))
        self._ours_box.SetName("Your version")
        root.Add(wx.StaticText(panel, label="Your version:"), 0, wx.LEFT, 10)
        root.Add(self._ours_box, 0, wx.EXPAND | wx.ALL, 10)

        self._theirs_box = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(500, 100)
        )
        self._theirs_box.SetName("Their version")
        root.Add(wx.StaticText(panel, label="Their version:"), 0, wx.LEFT, 10)
        root.Add(self._theirs_box, 0, wx.EXPAND | wx.ALL, 10)

        self._choice = wx.RadioBox(
            panel,
            label="Keep",
            choices=["Your version", "Their version", "Both", "Edit manually"],
        )
        self._choice.SetName("Which version to keep for this conflict")
        root.Add(self._choice, 0, wx.EXPAND | wx.ALL, 10)

        self._manual_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(500, 80))
        self._manual_ctrl.SetName("Manual replacement text")
        root.Add(self._manual_ctrl, 0, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._prev_btn = wx.Button(panel, label="&Previous")
        self._prev_btn.SetName("Previous conflict")
        self._next_btn = wx.Button(panel, label="&Next")
        self._next_btn.SetName("Next conflict")
        self._apply_btn = wx.Button(panel, wx.ID_OK, "&Apply All")
        self._apply_btn.SetName("Apply resolutions and finish")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetName("Cancel without resolving")
        for b in (self._prev_btn, self._next_btn, self._apply_btn):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.Fit()

        self._prev_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(-1))
        self._next_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(1))
        self._choice.Bind(wx.EVT_RADIOBOX, lambda _e: self._save_current_choice())

        self._render_current()

    def _render_current(self) -> None:
        hunk = self._hunks[self._index]
        self._status.SetLabel(f"Conflict {self._index + 1} of {len(self._hunks)}")
        self._ours_box.SetValue("\n".join(hunk.ours))
        self._theirs_box.SetValue("\n".join(hunk.theirs))
        current = self._resolutions[self._index]
        selection = {"ours": 0, "theirs": 1, "both": 2}.get(current, 3)
        self._choice.SetSelection(selection)
        if selection == 3:
            self._manual_ctrl.SetValue(current if current not in ("ours", "theirs", "both") else "")
        self._announce(self._status.GetLabel())

    def _save_current_choice(self) -> None:
        selection = self._choice.GetSelection()
        if selection == 0:
            self._resolutions[self._index] = "ours"
        elif selection == 1:
            self._resolutions[self._index] = "theirs"
        elif selection == 2:
            self._resolutions[self._index] = "both"
        else:
            self._resolutions[self._index] = self._manual_ctrl.GetValue()

    def _move(self, delta: int) -> None:
        self._save_current_choice()
        new_index = self._index + delta
        if new_index < 0:
            self._announce("Already at the first conflict.")
            return
        if new_index >= len(self._hunks):
            self._announce("Already at the last conflict.")
            return
        self._index = new_index
        self._render_current()

    def show(self) -> list[str] | None:
        """Returns the per-hunk resolutions in order, or None if cancelled."""
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            self._save_current_choice()
            answer = show_modal_dialog(self.dialog, "Resolve Conflicts")
            if answer != wx.ID_OK:
                return None
            self._save_current_choice()
            return list(self._resolutions)
        finally:
            self.dialog.Destroy()


# ---------------------------------------------------------------------------
# Interactive rebase, spoken
# ---------------------------------------------------------------------------

_REBASE_ACTIONS = ("pick", "squash", "reword", "drop")


class InteractiveRebaseDialog:
    """A real list dialog for the pick/squash/reword/drop todo list, instead
    of an editor buffer meant to be reordered by eye."""

    def __init__(
        self,
        parent: object,
        todo: list[RebaseTodoEntry],
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._todo = todo
        self._announce = announce_cb or (lambda _m: None)

        self.dialog = wx.Dialog(
            parent, title="Interactive Rebase", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((560, 400))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            panel,
            label="Commits, oldest first. Choose an action per commit, then reorder if needed.",
        )
        root.Add(intro, 0, wx.ALL, 10)

        self._list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._list.SetName("Commits to rebase; select a row to change its action or move it")
        self._list.InsertColumn(0, "Action")
        self._list.InsertColumn(1, "Commit")
        self._list.InsertColumn(2, "Subject")
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        action_row = wx.BoxSizer(wx.HORIZONTAL)
        action_row.Add(
            wx.StaticText(panel, label="&Action for selected commit:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._action_choice = wx.Choice(panel, choices=list(_REBASE_ACTIONS))
        self._action_choice.SetName("Action for the selected commit")
        action_row.Add(self._action_choice, 0)
        root.Add(action_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._up_btn = wx.Button(panel, label="Move &Up")
        self._up_btn.SetName("Move selected commit earlier")
        self._down_btn = wx.Button(panel, label="Move &Down")
        self._down_btn.SetName("Move selected commit later")
        self._start_btn = wx.Button(panel, wx.ID_OK, "&Start Rebase")
        self._start_btn.SetName("Start the rebase with these actions")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetName("Cancel without rebasing")
        for b in (self._up_btn, self._down_btn, self._start_btn):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self._action_choice.Bind(wx.EVT_CHOICE, lambda _e: self._apply_action_change())
        self._up_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(-1))
        self._down_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(1))

        self._populate()

    def _populate(self) -> None:
        self._list.DeleteAllItems()
        for entry in self._todo:
            idx = self._list.InsertItem(self._list.GetItemCount(), entry.action)
            self._list.SetItem(idx, 1, entry.sha[:7])
            self._list.SetItem(idx, 2, entry.subject)

    def _on_select(self, _event: object) -> None:
        idx = self._list.GetFirstSelected()
        if 0 <= idx < len(self._todo):
            self._action_choice.SetStringSelection(self._todo[idx].action)

    def _apply_action_change(self) -> None:
        idx = self._list.GetFirstSelected()
        if idx < 0 or idx >= len(self._todo):
            return
        self._todo[idx].action = self._action_choice.GetStringSelection()
        self._list.SetItem(idx, 0, self._todo[idx].action)
        self._announce(f"{self._todo[idx].subject}: {self._todo[idx].action}")

    def _move(self, delta: int) -> None:
        idx = self._list.GetFirstSelected()
        if idx < 0:
            self._announce("Select a commit first.")
            return
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self._todo):
            self._announce("Can't move further in that direction.")
            return
        self._todo[idx], self._todo[new_idx] = self._todo[new_idx], self._todo[idx]
        self._populate()
        self._list.Select(new_idx)
        self._list.Focus(new_idx)
        self._announce(f"Moved to position {new_idx + 1} of {len(self._todo)}")

    def show(self) -> list[RebaseTodoEntry] | None:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            answer = show_modal_dialog(self.dialog, "Interactive Rebase")
            if answer != wx.ID_OK:
                return None
            return list(self._todo)
        finally:
            self.dialog.Destroy()


__all__ = ["InteractiveRebaseDialog", "MergeConflictDialog", "UncommittedChangesDialog"]
