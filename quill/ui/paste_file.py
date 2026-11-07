"""Paste File, one implementation for both editors.

QUILL reaches :meth:`PasteFileMixin.cmd_paste_file` through
:mod:`quill.ui.main_frame_editor_parity`, QUILL Lite through
:mod:`quill.apps.lite_window_say`; both put it in Edit > Clipboard, beside Say
Clipboard, which already says when the clipboard holds files. The decisions
and the sentences are :mod:`quill.core.paste_file`'s. Each host supplies three
hooks: how it speaks, how it shows a modal window, and how it writes text in
at the caret as one undo step.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.paste_file import CHOICES, describe_paste, plan_paste

__all__ = ["PasteFileMixin", "choose_paste_kind"]

_PAD = 8
TITLE = "Paste File"


def choose_paste_kind(
    parent: Any, names: list[str], show_modal: Callable[[Any, str], int]
) -> str | None:
    """Ask whether to paste the files' text or their paths. ``None`` is Cancel."""
    import wx

    from quill.ui.accessible_names import set_accessible_name
    from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids
    from quill.ui.dpi import dip_size

    count = len(names)
    shown = ", ".join(names[:5]) + (f", and {count - 5} more" if count > 5 else "")
    noun = "file" if count == 1 else "files"
    dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    try:
        root = wx.BoxSizer(wx.VERTICAL)
        what = wx.StaticText(dialog, label=f"The clipboard holds {count} {noun}: {shown}.")
        root.Add(what, 0, wx.ALL, _PAD)
        label = wx.StaticText(dialog, label="&Paste:")
        listbox = wx.ListBox(dialog, choices=[row for _key, row in CHOICES])
        set_accessible_name(listbox, "Paste")
        listbox.SetHelpText(
            "Each file's text puts in what the file says, read the way this editor "
            "opens it, with a blank line between files; files that are too large or "
            "are not text are left out and named. Each file's full path puts in one "
            "path per line. Enter pastes."
        )
        listbox.SetSelection(0)
        root.Add(label, 0, wx.LEFT | wx.RIGHT, _PAD)
        root.Add(listbox, 1, wx.EXPAND | wx.ALL, _PAD)
        ok = wx.Button(dialog, wx.ID_OK, "OK")
        ok.SetHelpText("Paste what is chosen in the list.")
        ok.SetDefault()
        cancel = wx.Button(dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Paste nothing.")
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        buttons.Add(ok, 0, wx.RIGHT, _PAD)
        buttons.Add(cancel, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)
        dialog.SetSizerAndFit(root)
        dialog.SetSize(dip_size(dialog, 480, 260))
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        apply_listbox_activation(listbox, lambda _event: dialog.EndModal(wx.ID_OK))
        listbox.SetFocus()
        if show_modal(dialog, TITLE) != wx.ID_OK:
            return None
        index = listbox.GetSelection()
        return CHOICES[index][0] if 0 <= index < len(CHOICES) else None
    finally:
        dialog.Destroy()


class PasteFileMixin:
    """``cmd_paste_file``. Hosts override the ``_paste_file_*`` hooks."""

    def _paste_file_say(self, message: str) -> None:
        self._announce(message)  # type: ignore[attr-defined]

    def _paste_file_parent(self) -> Any:
        return self

    def _paste_file_show_modal(self, dialog: Any, title: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return show_modal_dialog(dialog, title)

    def _paste_file_read_only(self) -> bool:
        return False

    def _paste_file_insert(self, text: str) -> None:
        raise NotImplementedError  # each host writes at its own caret

    def cmd_paste_file(self) -> None:
        """Paste the text, or the full paths, of files copied in File Explorer."""
        from quill.ui import say_commands

        if self._paste_file_read_only():
            self._paste_file_say("Document is read-only")
            return
        contents = say_commands.read_clipboard()
        if not contents.files:
            self._paste_file_say(
                "There are no copied files on the clipboard. Copy a file in File "
                "Explorer first, or press Control V to paste text"
            )
            return
        paths = [Path(name) for name in contents.files]
        choice = choose_paste_kind(
            self._paste_file_parent(), [p.name for p in paths], self._paste_file_show_modal
        )
        if choice is None:
            return  # cancelled: the window closing is the answer
        plan = plan_paste(paths, choice)
        if plan.text:
            self._paste_file_insert(plan.text)
        self._paste_file_say(describe_paste(plan, choice))
