"""Dialogs for Tools > Local Git > Worktrees.

Two surfaces, both raw ``wx.Dialog`` (the sanctioned ``hardened_custom``
base), both with every control parented directly on the dialog so no
layout-only panel turns up as a "group" node a screen-reader user has to
navigate into:

* :class:`WorktreesDialog` -- the list of worktrees. Each row is a whole
  sentence produced by :meth:`quill.core.git_worktree.WorktreeEntry.describe`,
  because "Linked worktree at S:\\code\\quill-feature-x, on branch feature/x,
  locked" is something a screen reader reads once and the user understands,
  whereas four narrow columns are four separate arrow-key journeys.
* :class:`NewWorktreeDialog` -- the create form: where the folder goes, which
  branch it holds, and whether that branch is being created here.

Both dialogs are pure UI. They never run git: the mixin
(``main_frame_worktrees.py``) supplies callbacks that do the work through
:mod:`quill.core.git_worktree` and hand back the sentence to announce.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from quill.core.path_input import clean_typed_path
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids, show_modal_dialog

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from quill.core.git_worktree import WorktreeEntry

__all__ = ["NewWorktreeDialog", "NewWorktreeRequest", "WorktreesDialog"]


@dataclass(frozen=True, slots=True)
class NewWorktreeRequest:
    """What the user asked for in :class:`NewWorktreeDialog`."""

    path: str
    branch: str
    create_branch: bool = False
    from_ref: str = ""


# ---------------------------------------------------------------------------
# The worktree list
# ---------------------------------------------------------------------------


class WorktreesDialog:
    """List every worktree, with the actions that operate on the selected one.

    Callbacks all return the sentence to announce, so the dialog never has to
    know what git did -- only what to say and that the list should be reread.
    ``on_open`` additionally returns whether a document was opened; when it
    was, the dialog closes, because the user's attention has moved to the
    editor and leaving a modal in front of it would strand them.
    """

    def __init__(
        self,
        parent: object,
        entries: Sequence[WorktreeEntry],
        *,
        refresh_provider: Callable[[], Sequence[WorktreeEntry]],
        on_new: Callable[[], str],
        on_open: Callable[[WorktreeEntry], tuple[str, bool]],
        on_remove: Callable[[WorktreeEntry], str],
        on_lock_toggle: Callable[[WorktreeEntry], str],
        on_prune: Callable[[], str],
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._entries: list[WorktreeEntry] = list(entries)
        self._refresh_provider = refresh_provider
        self._on_new = on_new
        self._on_open = on_open
        self._on_remove = on_remove
        self._on_lock_toggle = on_lock_toggle
        self._on_prune = on_prune
        self._announce = announce_cb or (lambda _m: None)

        self.dialog = wx.Dialog(
            parent, title="Worktrees", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((640, 400))
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "Each worktree is a folder of its own with one branch checked out in it.\n"
                "Switching branches by opening a different folder means the document you "
                "already have open never changes underneath you."
            ),
        )
        root.Add(intro, 0, wx.ALL, 10)

        self._list = wx.ListBox(self.dialog, choices=[], style=wx.LB_SINGLE)
        self._list.SetName("Worktrees in this repository")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Last worktree action")
        root.Add(self._status, 0, wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._new_btn = wx.Button(self.dialog, label="&New Worktree...")
        self._new_btn.SetName("Create a new worktree folder")
        self._open_btn = wx.Button(self.dialog, label="&Open in QUILL")
        self._open_btn.SetName("Open the selected worktree in QUILL")
        self._remove_btn = wx.Button(self.dialog, label="&Remove...")
        self._remove_btn.SetName("Remove the selected worktree")
        self._lock_btn = wx.Button(self.dialog, label="&Lock")
        self._lock_btn.SetName("Lock or unlock the selected worktree")
        self._prune_btn = wx.Button(self.dialog, label="&Prune")
        self._prune_btn.SetName("Forget worktrees whose folders are gone")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close dialog")
        for button in (
            self._new_btn,
            self._open_btn,
            self._remove_btn,
            self._lock_btn,
            self._prune_btn,
        ):
            btn_row.Add(button, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self.dialog.Fit()

        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._sync_buttons())
        apply_listbox_activation(self._list, lambda _e: self._open_selected())
        self._new_btn.Bind(wx.EVT_BUTTON, lambda _e: self._create_new())
        self._open_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_selected())
        self._remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self._remove_selected())
        self._lock_btn.Bind(wx.EVT_BUTTON, lambda _e: self._toggle_lock_selected())
        self._prune_btn.Bind(wx.EVT_BUTTON, lambda _e: self._prune())

        self._populate(select_index=0)

    # -- list plumbing ------------------------------------------------------

    def _populate(self, *, select_index: int = 0) -> None:
        self._list.Set([entry.describe() for entry in self._entries])
        if self._entries:
            index = max(0, min(select_index, len(self._entries) - 1))
            self._list.SetSelection(index)
        self._sync_buttons()

    def _selected(self) -> WorktreeEntry | None:
        index = self._list.GetSelection()
        if index < 0 or index >= len(self._entries):
            return None
        return self._entries[index]

    def _sync_buttons(self) -> None:
        entry = self._selected()
        has_selection = entry is not None
        self._open_btn.Enable(has_selection)
        # The main worktree is the repository itself; it is not removable.
        self._remove_btn.Enable(has_selection and not (entry and entry.is_main))
        self._lock_btn.Enable(has_selection and not (entry and entry.is_main))
        self._lock_btn.SetLabel("&Unlock" if entry is not None and entry.is_locked else "&Lock")

    def _report(self, message: str, *, keep_index: int | None = None) -> None:
        """Say what happened, reread the list, and put focus back on it."""
        self._status.SetLabel(message)
        self._announce(message)
        self._entries = list(self._refresh_provider())
        index = self._list.GetSelection() if keep_index is None else keep_index
        self._populate(select_index=max(0, index))
        self._list.SetFocus()

    # -- actions ------------------------------------------------------------

    def _create_new(self) -> None:
        message = self._on_new()
        if message:
            self._report(message, keep_index=len(self._entries))

    def _open_selected(self) -> None:
        entry = self._selected()
        if entry is None:
            self._announce("Select a worktree first.")
            return
        message, opened = self._on_open(entry)
        if opened:
            self._announce(message)
            self.dialog.EndModal(self._wx.ID_CANCEL)
            return
        self._report(message)

    def _remove_selected(self) -> None:
        entry = self._selected()
        if entry is None:
            self._announce("Select a worktree first.")
            return
        index = self._list.GetSelection()
        message = self._on_remove(entry)
        if message:
            self._report(message, keep_index=max(0, index - 1))

    def _toggle_lock_selected(self) -> None:
        entry = self._selected()
        if entry is None:
            self._announce("Select a worktree first.")
            return
        message = self._on_lock_toggle(entry)
        if message:
            self._report(message)

    def _prune(self) -> None:
        message = self._on_prune()
        if message:
            self._report(message, keep_index=0)

    # -- show ---------------------------------------------------------------

    def show(self) -> None:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        count = len(self._entries)
        if count == 1:
            self._announce("Worktrees: 1, the main one.")
        else:
            self._announce(f"Worktrees: {count}.")
        try:
            show_modal_dialog(self.dialog, "Worktrees")
        finally:
            self.dialog.Destroy()


# ---------------------------------------------------------------------------
# The create form
# ---------------------------------------------------------------------------


class NewWorktreeDialog:
    """Collect the folder, the branch, and whether the branch is new.

    Validation happens before the dialog closes, and every refusal is spoken,
    so a mistyped path or a missing branch name is heard here rather than
    surfacing later as a git error with no obvious cause.
    """

    def __init__(
        self,
        parent: object,
        branches: Sequence[str],
        *,
        default_parent_folder: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: NewWorktreeRequest | None = None

        self.dialog = wx.Dialog(parent, title="New Worktree", style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "Choose a folder outside the repository. Git will fill it with the "
                "branch you pick, and your open document will not change."
            ),
        )
        root.Add(intro, 0, wx.ALL, 10)

        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        grid.Add(
            wx.StaticText(self.dialog, label="&Folder for the new worktree:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        path_row = wx.BoxSizer(wx.HORIZONTAL)
        self._path_ctrl = wx.TextCtrl(self.dialog, value=default_parent_folder)
        self._path_ctrl.SetName("Folder for the new worktree")
        path_row.Add(self._path_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        browse_btn = wx.Button(self.dialog, label="&Browse...")
        browse_btn.SetName("Browse for the worktree folder")
        path_row.Add(browse_btn, 0)
        grid.Add(path_row, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="Branch &to check out:"), 0, wx.ALIGN_CENTER_VERTICAL
        )
        self._branch_choice = wx.Choice(self.dialog, choices=list(branches))
        self._branch_choice.SetName("Branch to check out in the new worktree")
        if branches:
            self._branch_choice.SetSelection(0)
        grid.Add(self._branch_choice, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label=""), 0)
        self._create_check = wx.CheckBox(self.dialog, label="Create a &new branch instead")
        self._create_check.SetName("Create a new branch in this worktree")
        grid.Add(self._create_check, 0)

        grid.Add(wx.StaticText(self.dialog, label="New branch n&ame:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._new_branch_ctrl = wx.TextCtrl(self.dialog)
        self._new_branch_ctrl.SetName("Name for the new branch")
        self._new_branch_ctrl.Enable(False)
        grid.Add(self._new_branch_ctrl, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="Start the new branch f&rom:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._from_ref_ctrl = wx.TextCtrl(self.dialog)
        self._from_ref_ctrl.SetName(
            "Branch, tag, or commit the new branch starts from; leave blank for the current one"
        )
        self._from_ref_ctrl.Enable(False)
        grid.Add(self._from_ref_ctrl, 1, wx.EXPAND)

        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "&Create Worktree")
        ok_btn.SetName("Create the worktree")
        ok_btn.SetDefault()
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetName("Cancel without creating a worktree")
        btn_row.AddStretchSpacer()
        btn_row.Add(ok_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self.dialog.Fit()

        browse_btn.Bind(wx.EVT_BUTTON, lambda _e: self._browse())
        self._create_check.Bind(wx.EVT_CHECKBOX, lambda _e: self._sync_mode())
        ok_btn.Bind(wx.EVT_BUTTON, lambda _e: self._confirm())

    # -- helpers ------------------------------------------------------------

    def _sync_mode(self) -> None:
        creating = bool(self._create_check.GetValue())
        self._new_branch_ctrl.Enable(creating)
        self._from_ref_ctrl.Enable(creating)
        self._branch_choice.Enable(not creating)
        if creating:
            self._announce("Creating a new branch. Type its name.")
            self._new_branch_ctrl.SetFocus()
        else:
            self._announce("Checking out an existing branch.")

    def _browse(self) -> None:
        wx = self._wx
        current = clean_typed_path(self._path_ctrl.GetValue())
        with wx.DirDialog(
            self.dialog,
            "Choose a folder for the new worktree",
            defaultPath=current,
            style=wx.DD_DEFAULT_STYLE,
        ) as chooser:
            if show_modal_dialog(chooser, "Choose Folder") != wx.ID_OK:
                return
            self._path_ctrl.SetValue(chooser.GetPath())
        self._path_ctrl.SetFocus()

    def _confirm(self) -> None:
        path = clean_typed_path(self._path_ctrl.GetValue())
        if not path:
            self._announce("Type or browse to the folder the new worktree should use.")
            self._path_ctrl.SetFocus()
            return
        creating = bool(self._create_check.GetValue())
        if creating:
            branch = self._new_branch_ctrl.GetValue().strip()
            if not branch:
                self._announce("Type a name for the new branch.")
                self._new_branch_ctrl.SetFocus()
                return
        else:
            branch = self._branch_choice.GetStringSelection().strip()
            if not branch:
                self._announce("Choose the branch to check out, or create a new one.")
                self._branch_choice.SetFocus()
                return
        self._result = NewWorktreeRequest(
            path=path,
            branch=branch,
            create_branch=creating,
            from_ref=self._from_ref_ctrl.GetValue().strip() if creating else "",
        )
        self.dialog.EndModal(self._wx.ID_OK)

    # -- show ---------------------------------------------------------------

    def show(self) -> NewWorktreeRequest | None:
        wx = self._wx
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            escape_id=wx.ID_CANCEL,
        )
        try:
            if show_modal_dialog(self.dialog, "New Worktree") != wx.ID_OK:
                return None
            return self._result
        finally:
            self.dialog.Destroy()
