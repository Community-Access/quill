"""Import and Export in Manage Abbreviations: the work, and the sentence it ends with.

Moved out of :mod:`quill.ui.abbreviation_manager_dialog` for the family's
"actual result, said once" (FUX-04, ``docs/design/fux-04-adoption.md``). Export
used to end with an "Export Complete" box saying how many were exported but
not where they went, and Import's box called every entry it left out a
"duplicate ID", including the ones it could not use at all. Now:

* the sentence names the file and its folder
  (:func:`quill.core.action_feedback.written_result` and ``place_of``);
* it says how many were already in the list and how many could not be used,
  separately, because those are different things to do something about;
* it is said, not shown in a box, and kept in Activity (Shift+F9) with Open
  Folder, through :func:`quill.ui.outcome_report.report_outcome`, when the
  window was opened by an app that can speak. Opened without one, the same
  sentence is shown as before.

A failure to read or write the file is still a box: it needs reading and
acknowledging, and nothing changed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.abbreviations import (
    SCHEMA_VERSION,
    AbbreviationLibrary,
    save_abbreviation_library,
)
from quill.core.abbreviations_store import entry_from_dict, entry_to_dict

__all__ = [
    "ImportCounts",
    "export_abbreviations",
    "export_sentence",
    "import_abbreviations",
    "import_sentence",
    "merge_imported",
]

_WILDCARD = "JSON files (*.json)|*.json|All files (*.*)|*.*"


@dataclass(frozen=True, slots=True)
class ImportCounts:
    """What an import did with each entry in the file."""

    added: int = 0
    already: int = 0
    unusable: int = 0


def _abbreviations(count: int) -> str:
    return "1 abbreviation" if count == 1 else f"{count} abbreviations"


def import_sentence(path: str | Path, counts: ImportCounts) -> str:
    """``Imported 5 abbreviations from team.json in Downloads. 2 were already in your list.``"""
    from quill.core.action_feedback import place_of

    where = place_of(path)
    if counts.added:
        parts = [f"Imported {_abbreviations(counts.added)} from {where}."]
    else:
        parts = [f"No abbreviations were added from {where}."]
    if counts.already:
        verb = "was" if counts.already == 1 else "were"
        parts.append(f"{counts.already} {verb} already in your list.")
    if counts.unusable:
        noun = "entry" if counts.unusable == 1 else "entries"
        parts.append(f"{counts.unusable} {noun} could not be used: no abbreviation or no text.")
    return " ".join(parts)


def export_sentence(path: str | Path, count: int) -> str:
    """``Exported 12 abbreviations to abbreviations.json in Documents.``"""
    from quill.core.action_feedback import written_result

    return written_result(f"Exported {_abbreviations(count)}", path)


def merge_imported(library: AbbreviationLibrary, incoming: list[Any]) -> ImportCounts:
    """Add the usable, new entries of *incoming* to *library*; count each kind."""
    existing_ids = {a.id for a in library.abbreviations}
    added = already = unusable = 0
    for item in incoming:
        if not isinstance(item, dict):
            unusable += 1
            continue
        if item.get("id") in existing_ids:
            already += 1
            continue
        try:
            entry = entry_from_dict(item)  # every per-entry setting, as stored
        except Exception:  # noqa: BLE001 - one bad entry must not stop the rest
            unusable += 1
            continue
        if not (entry.abbreviation and entry.expansion):
            unusable += 1
            continue
        library.abbreviations.append(entry)
        existing_ids.add(entry.id)
        added += 1
    if added:
        library.abbreviations.sort(key=lambda a: a.abbreviation.lower())
    return ImportCounts(added=added, already=already, unusable=unusable)


def _tell(parent: Any, host: Any, action: str, sentence: str, path: Path, title: str) -> None:
    """Say and keep *sentence* through *host*; without one, show it as before."""
    if host is not None and callable(getattr(host, "_announce", None)):
        from quill.ui.outcome_report import report_outcome

        report_outcome(host, action, sentence, object_name=path.name, path=path)
        return
    import wx

    from quill.ui.dialog_contract import show_message_box

    show_message_box(sentence, title, wx.OK | wx.ICON_INFORMATION, parent)


def _error(parent: Any, message: str, title: str) -> None:
    import wx

    from quill.ui.dialog_contract import show_message_box

    show_message_box(message, title, wx.OK | wx.ICON_ERROR, parent)


def _choose(parent: Any, title: str, style: int, default_file: str = "") -> Path | None:
    import wx

    dlg = wx.FileDialog(parent, title, defaultFile=default_file, wildcard=_WILDCARD, style=style)
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return None
        return Path(dlg.GetPath())
    finally:
        dlg.Destroy()


def import_abbreviations(parent: Any, library: AbbreviationLibrary, host: Any = None) -> bool:
    """Import Abbreviations...: True when the library changed."""
    import wx

    path = _choose(parent, "Import Abbreviations", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
    if path is None:
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        incoming = raw.get("abbreviations", [])
    except Exception as exc:  # noqa: BLE001 - any unreadable file is reported
        _error(parent, f"Could not read file: {exc}", "Import Failed")
        return False
    counts = merge_imported(library, list(incoming))
    if counts.added:
        save_abbreviation_library(library)
    _tell(
        parent, host, "Import abbreviations", import_sentence(path, counts), path, "Import Complete"
    )
    return bool(counts.added)


def export_abbreviations(parent: Any, library: AbbreviationLibrary, host: Any = None) -> None:
    """Export Abbreviations...: write the file, then say where it is."""
    import wx

    path = _choose(
        parent,
        "Export Abbreviations",
        wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        default_file="abbreviations.json",
    )
    if path is None:
        return
    # The same shape the library is saved in, so Export is a whole backup: the
    # category (AutoCorrect entries), speech, sound, triggers and per-app scope
    # used to be dropped, and an import made them plain abbreviations (FUX-05).
    data = {
        "version": SCHEMA_VERSION,
        "abbreviations": [entry_to_dict(a) for a in library.abbreviations],
    }
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001 - any failed write is reported
        _error(parent, f"Could not write file: {exc}", "Export Failed")
        return
    sentence = export_sentence(path, len(library.abbreviations))
    _tell(parent, host, "Export abbreviations", sentence, path, "Export Complete")
