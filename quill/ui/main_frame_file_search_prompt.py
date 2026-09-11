"""The Search in Files / Replace Across Files dialog, on its own.

Split out of :mod:`quill.ui.main_frame_search` for GATE-11 (2026-09-10) and
because it is the one thing in there that is not a search: a hundred and fifty
lines of form building with two conditional rows, next to a file of one-screen
command handlers. The module it left is now commands, and this is the window
they open.

It stays a mixin method rather than becoming a free function because it reads
three things only the frame can answer -- the current document's folder for the
starting path, the frame for parentage, and the hardened
``_show_modal_dialog`` / ``_show_message_box`` every QUILL dialog goes through.
The request it returns (:class:`FileSearchRequest`)
is the whole of what the callers need, so nothing else crosses the seam.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.search import SearchOptions
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["FileSearchPromptMixin", "FileSearchRequest"]


@dataclass(slots=True)
class FileSearchRequest:
    """Everything the dialog collected, and the whole of what crosses the seam.

    Moved here with the dialog rather than left behind: it is this window's
    output, and a caller that never opens the window never needs it.
    ``main_frame_search`` re-exports it under its old private name so nothing
    that imports it has to change.
    """

    root: Path
    pattern: str
    query: str
    replacement: str | None
    options: SearchOptions
    output_mode: str
    preview_before_replace: bool


class FileSearchPromptMixin:
    """The one method, composed onto ``MainFrame`` beside the search commands."""

    def _prompt_file_search(self, *, replace: bool) -> FileSearchRequest | None:
        wx = self._wx
        default_root = self.document.path.parent if self.document.path is not None else Path.cwd()
        dialog_label = "Replace Across Files" if replace else "Search in Files"
        dialog = wx.Dialog(
            self.frame,
            title=dialog_label,
            size=(700, 0),
        )
        root = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(0, 3, 8, 8)
        form.AddGrowableCol(1, 1)

        def add_row(label: str, make_ctrl, button: object | None = None) -> object:
            form.Add(wx.StaticText(dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = make_ctrl()
            form.Add(ctrl, 1, wx.EXPAND)
            if button is None:
                form.AddSpacer(1)
            else:
                form.Add(button, 0)
            return ctrl

        folder_picker = add_row(
            "Starting folder", lambda: wx.DirPickerCtrl(dialog, path=str(default_root))
        )
        file_pattern_ctrl = add_row("File pattern", lambda: wx.TextCtrl(dialog, value="*"))
        query_ctrl = add_row(
            "Search text", lambda: wx.TextCtrl(dialog, value="", style=wx.TE_PROCESS_ENTER)
        )

        replacement_ctrl = None
        if replace:
            replacement_ctrl = add_row(
                "Replacement",
                lambda: wx.TextCtrl(dialog, value="", style=wx.TE_PROCESS_ENTER),
            )

        mode_choice = add_row(
            "Match mode",
            lambda: wx.Choice(dialog, choices=["Plain text", "Wildcard", "Regular expression"]),
        )
        mode_choice.SetSelection(0)

        output_choice = add_row(
            "Output format",
            lambda: wx.Choice(
                dialog,
                choices=[
                    "Filenames only",
                    "Filenames with line numbers and counts",
                    "Counts only",
                    "Filename with line context",
                ],
            ),
        )
        output_choice.SetSelection(3)

        case_sensitive = wx.CheckBox(dialog, label="Case sensitive")
        whole_word = wx.CheckBox(dialog, label="Whole word")
        root.Add(form, 0, wx.ALL | wx.EXPAND, 8)
        root.Add(case_sensitive, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        root.Add(whole_word, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        preview_before_replace = None
        if replace:
            preview_before_replace = wx.CheckBox(dialog, label="Preview before replacing")
            preview_before_replace.SetValue(True)
            root.Add(preview_before_replace, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            # Mirror the proven single-document search dialog (_prompt_search):
            # a StdDialogButtonSizer must be added with wx.EXPAND, not
            # wx.ALIGN_RIGHT. Adding it right-aligned left the OK/Cancel buttons
            # unrealized on Windows, so the Cancel button could not be clicked
            # and the dialog trapped the user (#84). EXPAND plus an explicit
            # default button restores reliable, keyboard-accessible dismissal.
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.SetSizerAndFit(root)

        def submit(_event: object) -> None:
            dialog.EndModal(wx.ID_OK)

        query_ctrl.Bind(wx.EVT_TEXT_ENTER, submit)
        if replacement_ctrl is not None:
            replacement_ctrl.Bind(wx.EVT_TEXT_ENTER, submit)

        def focus_query() -> None:
            query_ctrl.SetFocus()

        if hasattr(wx, "CallAfter"):
            wx.CallAfter(focus_query)
        else:
            focus_query()

        try:
            if self._show_modal_dialog(dialog, dialog_label) != wx.ID_OK:
                return None
            query = query_ctrl.GetValue().strip()
            if not query:
                self._show_message_box(
                    "Search text cannot be blank.",
                    dialog_label,
                    wx.ICON_ERROR | wx.OK,
                )
                return None
            mode = mode_choice.GetStringSelection()
            options = SearchOptions(
                case_sensitive=bool(case_sensitive.GetValue()),
                whole_word=bool(whole_word.GetValue()),
                use_regex=mode == "Regular expression",
                wildcard=mode == "Wildcard",
            )
            replacement_value = (
                replacement_ctrl.GetValue() if replacement_ctrl is not None else None
            )
            preview = (
                bool(preview_before_replace.GetValue())
                if preview_before_replace is not None
                else False
            )
            output_modes = (
                "filenames",
                "filenames_lines_counts",
                "counts",
                "context",
            )
            return FileSearchRequest(
                root=Path(folder_picker.GetPath()),
                pattern=file_pattern_ctrl.GetValue().strip() or "*",
                query=query,
                replacement=replacement_value,
                options=options,
                output_mode=output_modes[
                    max(0, min(output_choice.GetSelection(), len(output_modes) - 1))
                ],
                preview_before_replace=preview,
            )
        finally:
            dialog.Destroy()
