"""The Search in Files / Replace Across Files window, for both editors.

QUILL's window since 2026-09, moved here on 2026-10-15 when QUILL Lite gained
the same two commands: QUILL Lite may never be ahead of QUILL, and the way it
is never behind either is that the editors share the window rather than each
keeping a copy. The editor passes what only it knows -- its parent window, the
folder to start in, and how it shows a modal dialog and a message -- and gets
back a :class:`FileSearchRequest`, the whole of what crosses the seam.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.search import SearchOptions
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["FileSearchRequest", "prompt_file_search"]


@dataclass(slots=True)
class FileSearchRequest:
    """Everything the window collected."""

    root: Path
    pattern: str
    query: str
    replacement: str | None
    options: SearchOptions
    output_mode: str
    preview_before_replace: bool


_OUTPUT_MODES = ("filenames", "filenames_lines_counts", "counts", "context")


def prompt_file_search(
    *,
    parent: Any,
    default_root: Path,
    replace: bool,
    show_modal: Callable[[Any, str], int],
    show_message: Callable[[str, str, int], Any],
    wx_module: Any = None,
) -> FileSearchRequest | None:
    """Ask what to search for, where; None when the listener cancels.

    *wx_module* is the editor's own handle on wx, so a test that gives the
    editor a stand-in reaches this window with it too.
    """
    if wx_module is None:
        import wx as wx_module
    wx = wx_module

    dialog_label = "Replace Across Files" if replace else "Search in Files"
    dialog = wx.Dialog(parent, title=dialog_label, size=(700, 0))
    root = wx.BoxSizer(wx.VERTICAL)
    form = wx.FlexGridSizer(0, 3, 8, 8)
    form.AddGrowableCol(1, 1)

    def add_row(label: str, make_ctrl: Callable[[], Any], help_text: str) -> Any:
        form.Add(wx.StaticText(dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        ctrl = make_ctrl()
        ctrl.SetHelpText(help_text)
        form.Add(ctrl, 1, wx.EXPAND)
        form.AddSpacer(1)
        return ctrl

    folder_picker = add_row(
        "Starting folder",
        lambda: wx.DirPickerCtrl(dialog, path=str(default_root)),
        "The folder to search. Every folder inside it is searched too.",
    )
    file_pattern_ctrl = add_row(
        "File pattern",
        lambda: wx.TextCtrl(dialog, value="*"),
        "Which files to look in, such as *.txt or *.md. A star on its own means every file.",
    )
    query_ctrl = add_row(
        "Search text",
        lambda: wx.TextCtrl(dialog, value="", style=wx.TE_PROCESS_ENTER),
        "What to look for. Press Enter to start.",
    )
    replacement_ctrl = None
    if replace:
        replacement_ctrl = add_row(
            "Replacement",
            lambda: wx.TextCtrl(dialog, value="", style=wx.TE_PROCESS_ENTER),
            "What every match becomes. Leave it empty to delete the matches.",
        )
    mode_choice = add_row(
        "Match mode",
        lambda: wx.Choice(dialog, choices=["Plain text", "Wildcard", "Regular expression"]),
        "Plain text finds the text as typed. Wildcard understands * and ?. "
        "Regular expression is a pattern.",
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
        "How the results are written out: just the files, the files with line numbers "
        "and counts, the counts alone, or each matching line.",
    )
    output_choice.SetSelection(3)

    case_sensitive = wx.CheckBox(dialog, label="Case sensitive")
    case_sensitive.SetHelpText("Only find text with the same capital and small letters.")
    whole_word = wx.CheckBox(dialog, label="Whole word")
    whole_word.SetHelpText("Only find the text as a whole word, not inside a longer one.")
    root.Add(form, 0, wx.ALL | wx.EXPAND, 8)
    root.Add(case_sensitive, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    root.Add(whole_word, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    preview_before_replace = None
    if replace:
        preview_before_replace = wx.CheckBox(dialog, label="Preview before replacing")
        preview_before_replace.SetHelpText(
            "Show every change first and ask before any file is written. Leave this "
            "checked the first time you use it."
        )
        preview_before_replace.SetValue(True)
        root.Add(preview_before_replace, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
    if buttons is not None:
        # A StdDialogButtonSizer must be added with wx.EXPAND, not
        # wx.ALIGN_RIGHT: right-aligned it left OK and Cancel unrealized on
        # Windows, so Cancel could not be clicked and the dialog trapped the
        # user (#84). EXPAND plus an explicit default button fixes it.
        ok_button = dialog.FindWindowById(wx.ID_OK)
        if ok_button is not None:
            ok_button.SetDefault()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    dialog.SetSizerAndFit(root)

    def submit(_event: object) -> None:
        dialog.EndModal(wx.ID_OK)

    query_ctrl.Bind(wx.EVT_TEXT_ENTER, submit)
    if replacement_ctrl is not None:
        replacement_ctrl.Bind(wx.EVT_TEXT_ENTER, submit)
    if hasattr(wx, "CallAfter"):
        wx.CallAfter(query_ctrl.SetFocus)
    else:
        query_ctrl.SetFocus()

    try:
        if show_modal(dialog, dialog_label) != wx.ID_OK:
            return None
        query = query_ctrl.GetValue().strip()
        if not query:
            show_message("Search text cannot be blank.", dialog_label, wx.ICON_ERROR | wx.OK)
            return None
        mode = mode_choice.GetStringSelection()
        options = SearchOptions(
            case_sensitive=bool(case_sensitive.GetValue()),
            whole_word=bool(whole_word.GetValue()),
            use_regex=mode == "Regular expression",
            wildcard=mode == "Wildcard",
        )
        return FileSearchRequest(
            root=Path(folder_picker.GetPath()),
            pattern=file_pattern_ctrl.GetValue().strip() or "*",
            query=query,
            replacement=replacement_ctrl.GetValue() if replacement_ctrl is not None else None,
            options=options,
            output_mode=_OUTPUT_MODES[max(0, min(output_choice.GetSelection(), 3))],
            preview_before_replace=bool(preview_before_replace.GetValue())
            if preview_before_replace is not None
            else False,
        )
    finally:
        dialog.Destroy()
