"""Import and Export for the List Speech Templates editor: the file and question dialogs.

The rules (what a file may hold, what counts as a conflict) are in
:mod:`quill.core.list_speech.exchange`; this module only asks for a file and,
for every template whose name is already saved, whether to replace it. Nothing
is overwritten without that question, and a file that already exists is never
replaced on export without the system's own confirmation.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.list_speech import exchange
from quill.core.list_speech.library import Library
from quill.ui.dialog_contract import show_modal_dialog

__all__ = ["export_to_file", "import_from_file"]

_WILDCARD = "List speech templates (*.json)|*.json|All files (*.*)|*.*"


def _pick_file(
    wx: Any, parent: Any, title: str, saving: bool, announce: Callable[[str], None]
) -> str:
    style = (
        (wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) if saving else (wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
    )
    with wx.FileDialog(
        parent,
        title,
        defaultFile="list-speech-templates.json" if saving else "",
        wildcard=_WILDCARD,
        style=style,
    ) as dialog:
        if show_modal_dialog(dialog, title, announce=None) != wx.ID_OK:
            return ""
        return str(dialog.GetPath())


def export_to_file(wx: Any, parent: Any, library: Library, announce: Callable[[str], None]) -> str:
    """Write the saved templates to a file the person picks; returns the sentence to say."""
    if not library.templates:
        return "There are no saved templates to export. Save one first."
    path = _pick_file(wx, parent, "Export List Speech Templates", True, announce)
    if not path:
        return ""
    try:
        tmp = Path(path + ".tmp")
        tmp.write_text(exchange.export_templates(library), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as error:
        return f"The templates could not be saved to that file: {error.strerror or error}."
    count = len(library.templates)
    noun = "template" if count == 1 else "templates"
    return f"Exported {count} {noun} to {Path(path).name}."


def _ask_replace(
    wx: Any, parent: Any, name: str, kind: str, announce: Callable[[str], None]
) -> int:
    """wx.YES to replace, wx.NO to keep the saved one, wx.CANCEL to stop the import."""
    with wx.MessageDialog(
        parent,
        f"A template named {name} is already saved for {kind}. "
        "Replace it with the one in the file?",
        "Replace Template",
        wx.YES_NO | wx.CANCEL | wx.NO_DEFAULT | wx.ICON_QUESTION,
    ) as ask:
        ask.SetYesNoCancelLabels("&Replace", "&Keep Mine", "Cancel Import")
        return int(show_modal_dialog(ask, "Replace Template", announce=None))


def import_from_file(
    wx: Any, parent: Any, library: Library, announce: Callable[[str], None]
) -> tuple[Library, str]:
    """Read a file the person picks and add its templates; returns the library and a sentence."""
    from quill.core.list_speech.catalog import get_list_type

    path = _pick_file(wx, parent, "Import List Speech Templates", False, announce)
    if not path:
        return library, ""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return library, "That file could not be read. Nothing was changed."
    incoming = exchange.read_import(text)
    notes = " ".join(incoming.notes)
    if incoming.error:
        return library, f"{incoming.error} {notes} Nothing was changed.".replace("  ", " ")
    replace: set[tuple[str, str]] = set()
    for template in exchange.conflicts(library, incoming.templates):
        kind = get_list_type(template.list_type)
        answer = _ask_replace(
            wx, parent, template.name, kind.title if kind else template.list_type, announce
        )
        if answer == wx.ID_CANCEL:
            return library, "Import cancelled. Nothing was changed."
        if answer == wx.ID_YES:
            replace.add(exchange.template_key(template))
    new_library, summary = exchange.apply_import(library, incoming.templates, frozenset(replace))
    return new_library, f"{summary} {notes}".strip()
