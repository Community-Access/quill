"""Move several podcasts into a folder at once.

Filing has always been one show at a time (``_on_move_show_to_folder``), so
tidying a library of forty into six folders was forty trips through a picker.
The bulk machinery already existed for *episodes*
(``manager_actions._selected_rows``) and the show tree had no equivalent.

**Why a list rather than a multi-select tree.** The obvious implementation is to
make the subscription tree ``TR_MULTIPLE`` and read its selection. That was
rejected: a multi-select tree is meaningfully harder to drive with a screen
reader -- selection becomes Ctrl+arrow and Ctrl+Space, and every existing
single-select behaviour in that tree changes underneath people -- for a job
that happens perhaps twice in the life of a library. A plain
``wx.ListBox`` with ``LB_EXTENDED`` is a control screen readers have always
handled well: arrows move, Shift+arrows extend, Ctrl+Space toggles, and each row
is announced as selected or not without being asked.

Checkboxes inside a list were rejected for the reason this codebase always
rejects them: a checkbox in a list is a state a screen reader has to be asked
for, where a selection is a place you land on.

The folder itself is chosen with the existing ``FolderPickerDialog``, unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids

TITLE = "Move Podcasts to Folder"

__all__ = ["MoveShowsDialog", "move_one_show", "open_move_shows"]


class MoveShowsDialog:
    """Pick the podcasts. Returns the chosen shows, or [] on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        library: Any,
        announce_cb: Callable[[str], None] | None = None,
        preselect: str = "",
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._shows = sorted(
            getattr(library, "shows", []) or [], key=lambda show: str(show.title).casefold()
        )
        self._result: list[Any] = []

        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((520, 460))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(
                self.dialog,
                label="Choose the podcasts to move, then choose where they go.",
            ),
            0,
            wx.ALL,
            10,
        )
        root.Add(wx.StaticText(self.dialog, label="&Podcasts:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._list = wx.ListBox(
            self.dialog,
            choices=[self._row_label(show) for show in self._shows],
            style=wx.LB_EXTENDED,
        )
        self._list.SetName(
            "Your podcasts. Arrow to move, Shift and arrow to extend the "
            "selection, Ctrl and Space to add or remove one."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        select_row = wx.BoxSizer(wx.HORIZONTAL)
        all_btn = wx.Button(self.dialog, label="Select &All")
        none_btn = wx.Button(self.dialog, label="Select &None")
        select_row.Add(all_btn, 0, wx.RIGHT, 6)
        select_row.Add(none_btn, 0)
        root.Add(select_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._count = wx.StaticText(self.dialog, label="Nothing selected.")
        self._count.SetName("How many podcasts are selected")
        root.Add(self._count, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        self._ok_btn = wx.Button(self.dialog, wx.ID_OK, "Choose &Folder...")
        buttons.Add(self._ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(self.dialog, wx.ID_CANCEL, "Cancel"), 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        all_btn.Bind(wx.EVT_BUTTON, lambda _e: self._select_all(True))
        none_btn.Bind(wx.EVT_BUTTON, lambda _e: self._select_all(False))
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._refresh_count())
        self._ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)

        if preselect:
            for index, show in enumerate(self._shows):
                if str(getattr(show, "id", "")) == preselect:
                    self._list.SetSelection(index)
                    break
        self._refresh_count()

    def _row_label(self, show: Any) -> str:
        """One row, saying where the show is now as well as what it is."""
        title = str(getattr(show, "title", "") or "Untitled")
        folder_id = getattr(show, "folder_id", None)
        return f"{title}, in a folder" if folder_id else f"{title}, top level"

    def _select_all(self, wanted: bool) -> None:
        for index in range(self._list.GetCount()):
            if wanted:
                self._list.SetSelection(index)
            else:
                self._list.Deselect(index)
        self._refresh_count()

    def _selected(self) -> list[Any]:
        return [self._shows[index] for index in self._list.GetSelections()]

    def _refresh_count(self) -> None:
        count = len(self._list.GetSelections())
        if count:
            self._count.SetLabel(f"{count} podcast{'' if count == 1 else 's'} selected.")
        else:
            self._count.SetLabel("Nothing selected.")
        self._ok_btn.Enable(bool(count))

    def _on_ok(self, event: Any) -> None:
        chosen = self._selected()
        if not chosen:
            # Cannot happen while the button is disabled, but a dialog that
            # closes on an empty selection would move nothing and say nothing.
            self._announce("Choose at least one podcast first.")
            return
        self._result = chosen
        event.Skip()

    def show(self) -> list[Any]:
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Choose Folder",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(self.dialog, TITLE, announce=self._announce)
            return self._result if answer == self._wx.ID_OK else []
        finally:
            self.dialog.Destroy()


def open_move_shows(dialog: Any, preselect: str = "") -> None:
    """Pick podcasts, pick a folder, move them, say what happened."""
    from quill.ui.podcasts.folder_picker_dialog import FolderPickerDialog

    chosen = MoveShowsDialog(
        dialog.dialog,
        library=dialog._library,
        announce_cb=dialog._announce,
        preselect=preselect,
    ).show()
    if not chosen:
        return

    count = len(chosen)
    picker = FolderPickerDialog(
        dialog.dialog,
        library=dialog._library,
        title=f"Move {count} Podcast{'' if count == 1 else 's'} to Folder",
        announce_cb=dialog._announce,
    )
    result = picker.show()
    if not result.confirmed:
        return
    folder_id = result.folder_id
    for show in chosen:
        show.folder_id = folder_id or None
    dialog._on_library_changed()
    dialog.refresh_tree()
    destination = dialog._library.find_folder(folder_id) if folder_id else None
    where = destination.name if destination is not None else "the top level"
    dialog._announce(f"Moved {count} podcast{'' if count == 1 else 's'} to {where}.")


def move_one_show(dialog: Any, show: Any) -> None:
    """File a single podcast, keeping the tree cursor where it was.

    Beside its bulk sibling rather than in the manager dialog: the two do the
    same thing to a different number of shows, and reading them together is how
    the announcement and the anchor handling stay in step.
    """
    from quill.ui.podcasts.folder_picker_dialog import FolderPickerDialog

    picker = FolderPickerDialog(
        dialog.dialog,
        library=dialog._library,
        title=f"Move {show.title} to Folder",
        announce_cb=dialog._announce,
    )
    result = picker.show()
    if not result.confirmed:
        return
    chosen = result.folder_id
    # Taken before the move: once the show has left, the row it was next to is
    # where the cursor has to land, and afterwards there is nothing to ask.
    anchor = dialog._neighbor_anchor_for_show(show.id)
    show.folder_id = chosen or None
    dialog._on_library_changed()
    dialog.refresh_tree()
    dialog._restore_tree_anchor(anchor)
    destination = dialog._library.find_folder(chosen) if chosen else None
    where = destination.name if destination is not None else "the top level"
    dialog._announce(f"Moved {show.title} to {where}")
