"""Import, Export and the shared word list, for My Words and Phrases (dict.md D-12).

The window (:mod:`quill.ui.dictation_words_dialog`) owns the list; this module
owns the three things that move a list between files:

* **Export...** writes the list to a ``.md`` or ``.csv`` file the person
  names, and says how many entries went.
* **Import...** reads one, shows what it would add in a preview (the counts
  as the list's label, the entries themselves in the list), and only on
  **Add Them** backs the list up and merges. Nothing is ever replaced: an
  entry already there, or one that differs from yours, keeps yours.
* **Use the shared word list** (QUILL Lite only, never in a portable copy):
  switch to the list QUILL, QUILL Transcribe and Quill Inkwell use, merging
  QUILL Lite's own words into it after the same preview; unchecked, QUILL Lite
  goes back to its own list, which was never changed.

Every flow takes its file chooser and its preview as arguments, so the tests
drive the real decisions with fakes and no window opens.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

from quill.core.windows_dictation.words_exchange import (
    MergePlan,
    SharedWords,
    WordsImportError,
    apply_merge,
    back_up,
    count_phrase,
    export_words,
    plan_merge,
    preview_sentence,
    read_import,
    summary_sentence,
)
from quill.core.windows_dictation.words_file import WordsFile, load_words, save_words
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size

__all__ = [
    "ImportPreviewDialog",
    "choose_export_path",
    "choose_import_path",
    "confirm_plan",
    "run_export",
    "run_import",
    "switch_shared",
]

_PAD = 8
_WILDCARD = "Word list in Markdown (*.md)|*.md|Spreadsheet, say and write columns (*.csv)|*.csv"
_OPEN_WILDCARD = "Word lists (*.md;*.csv)|*.md;*.csv|" + _WILDCARD

Say = Callable[[str], None]
Chooser = Callable[[Any], Path | None]
Confirm = Callable[[Any, MergePlan, str, str], bool]


class ImportPreviewDialog(wx.Dialog):
    """What an import would add, before anything changes."""

    def __init__(self, parent: Any, plan: MergePlan, title: str, action: str) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        root = wx.BoxSizer(wx.VERTICAL)
        # The counts are the list's label, so the reader says them as the list
        # takes focus: no announcement is needed (GATE-13).
        label = wx.StaticText(self, label=preview_sentence(plan) + " &New entries:")
        self.list = wx.ListBox(self, choices=[entry.label() for entry in plan.new])
        self.list.SetHelpText(
            "Each entry the file would add to your list, as it would read in My "
            "Words and Phrases. Entries already in your list are not shown, and "
            "where the file differs from yours, yours is kept."
        )
        self.list.SetMinSize(dip_size(self.list, 520, 220))
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.list, 1, wx.EXPAND | wx.ALL, _PAD)
        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self, wx.ID_OK, action)
        ok.SetHelpText(
            "Add these entries. Your list as it was is kept first, as "
            "dictation-before-import.md beside it."
        )
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Change nothing.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)
        self.SetSizerAndFit(root)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label=action,
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        ok.SetDefault()
        if plan.new:
            self.list.SetSelection(0)
        self.list.SetFocus()


# -- the real choosers and preview (replaced by fakes in the tests) ---------------


def choose_import_path(parent: Any) -> Path | None:
    with wx.FileDialog(
        parent,
        "Import Words",
        wildcard=_OPEN_WILDCARD,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as dialog:
        if dialog.ShowModal() != wx.ID_OK:
            return None
        return Path(dialog.GetPath())


def choose_export_path(parent: Any) -> Path | None:
    with wx.FileDialog(
        parent,
        "Export Words",
        defaultFile="my-dictation-words.md",
        wildcard=_WILDCARD,
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as dialog:
        if dialog.ShowModal() != wx.ID_OK:
            return None
        path = Path(dialog.GetPath())
        wanted = ".csv" if dialog.GetFilterIndex() == 1 else ".md"
        if path.suffix.lower() not in {".md", ".csv"}:
            path = path.with_name(path.name + wanted)
        return path


def confirm_plan(parent: Any, plan: MergePlan, title: str, action: str) -> bool:
    dialog = ImportPreviewDialog(parent, plan, title, action)
    try:
        return bool(dialog.ShowModal() == wx.ID_OK)
    finally:
        dialog.Destroy()


# -- the flows --------------------------------------------------------------------


def run_export(
    parent: Any, words: WordsFile, say: Say, *, choose: Chooser = choose_export_path
) -> Path | None:
    """Export *words*; the file written, or ``None`` when nothing was."""
    if not words.entries():
        say("Nothing to export yet. Add a word, a phrase or a correction first.")
        return None
    path = choose(parent)
    if path is None:
        return None
    try:
        count = export_words(words, path)
    except OSError as error:
        say(f"The list could not be exported. {error.strerror or error}")
        return None
    say(f"Exported {count_phrase(words.entries()) if count else 'nothing'} to {path.name}.")
    return path


def run_import(
    parent: Any,
    list_path: Path,
    words: WordsFile,
    say: Say,
    *,
    choose: Chooser = choose_import_path,
    confirm: Confirm = confirm_plan,
) -> bool:
    """Import into *words* (saved to *list_path*); whether the list changed."""
    path = choose(parent)
    if path is None:
        return False
    try:
        incoming = read_import(path)
    except WordsImportError as error:
        say(str(error.args[0]))
        return False
    plan = plan_merge(words, incoming)
    if not plan.new:
        kept = (
            f" {len(plan.different)} differ from yours; yours were kept." if plan.different else ""
        )
        say(f"Nothing new in {path.name}: everything in it is already in your list.{kept}")
        return False
    if not confirm(parent, plan, "Import Words", "Add Them"):
        return False
    try:
        back_up(list_path)
        apply_merge(words, plan)
        save_words(list_path, words)
    except OSError as error:
        say(f"Nothing was imported: your list could not be saved. {error.strerror or error}")
        words.__dict__.update(load_words(list_path).__dict__)
        return False
    say(summary_sentence(plan))
    return True


def switch_shared(
    parent: Any, shared: SharedWords, on: bool, say: Say, *, confirm: Confirm = confirm_plan
) -> bool:
    """Check or uncheck "Use the shared word list"; whether the choice changed."""
    if not on:
        shared.set_on(False)
        own = load_words(shared.own_path).entries()
        say(f"Now using QUILL Lite's own word list: {count_phrase(own) if own else 'empty'}.")
        return True
    mine = load_words(shared.own_path)
    family = load_words(shared.shared_path)
    plan = plan_merge(family, mine)
    added = ""
    if plan.new:
        if not confirm(parent, plan, "Use the Shared Word List", "Use the Shared List"):
            # The box is set back without the reader hearing it change.
            say("Nothing changed. QUILL Lite keeps its own word list.")
            return False
        try:
            back_up(shared.shared_path)
            apply_merge(family, plan)
            save_words(shared.shared_path, family)
        except OSError as error:
            say(f"The shared list could not be saved. {error.strerror or error}")
            return False
        added = f" {count_phrase(plan.new)} of yours added to it."
    shared.set_on(True)
    total = family.entries()
    say(f"Now using the shared word list: {count_phrase(total) if total else 'empty'}.{added}")
    return True
