"""My Words and Phrases: the window that edits ``dictation.md`` (dict.md 5).

Until 2026-09-28 the only way to teach dictation a name was to open a
Markdown file and know its two headings. This window lists every entry as a
sentence -- "Word: NVDA", "Phrase: say my email address, writes ...",
"Correction: heard quill light, write QUILL Lite" -- and offers Add Word, Add
Phrase, Add Correction, Edit and Remove. Each change is saved at once and said
out loud; the next phrase dictated uses it, because the profile is re-read
whenever the file's time changes.

Open the File is still there, last, for whoever prefers the file. Shared by
QUILL and QUILL Lite through :class:`~quill.ui.windows_dictation_tools.DictationToolsMixin`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

from quill.core.windows_dictation.words_file import Entry, WordsFile, load_words, save_words
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids, bind_close_button

__all__ = ["DictationWordsDialog"]

_PAD = 8

_KIND_TITLES = {"word": "Word", "phrase": "Phrase", "correction": "Correction"}
_FIELD_LABELS = {
    "phrase": ("&Say:", "&Writes:"),
    "correction": ("&Heard as:", "&Write instead:"),
}
_FIELD_HELP = {
    "phrase": (
        "The words you will say. Two or more is safest, so an ordinary sentence "
        "does not trigger it by accident.",
        "What dictation writes when you say them. Press Enter for a new line; "
        "a signature can be two lines.",
    ),
    "correction": (
        "What the speech engine keeps writing, exactly as it comes out, such as quill light.",
        "What to write instead, such as QUILL Lite. Applied to every phrase, "
        "whatever the capitals.",
    ),
}


class _EntryDialog(wx.Dialog):
    """One word, or one pair: the form behind Add and Edit."""

    def __init__(self, parent: Any, kind: str, entry: Entry | None = None) -> None:
        verb = "Edit" if entry is not None else "Add"
        super().__init__(parent, title=f"{verb} {_KIND_TITLES[kind]}")
        self._kind = kind
        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=_PAD, hgap=_PAD)
        grid.AddGrowableCol(1, 1)
        if kind == "word":
            grid.Add(wx.StaticText(self, label="&Word:"), 0, wx.ALIGN_CENTER_VERTICAL)
            self._spoken = wx.TextCtrl(self, value=entry.spoken if entry else "")
            self._spoken.SetHelpText(
                "A name, term or acronym, spelled the way you want it. When the "
                "engine writes something that sounds or looks close, it becomes this."
            )
            grid.Add(self._spoken, 1, wx.EXPAND)
            self._written: wx.TextCtrl | None = None
        else:
            spoken_label, written_label = _FIELD_LABELS[kind]
            spoken_help, written_help = _FIELD_HELP[kind]
            grid.Add(wx.StaticText(self, label=spoken_label), 0, wx.ALIGN_CENTER_VERTICAL)
            self._spoken = wx.TextCtrl(self, value=entry.spoken if entry else "")
            self._spoken.SetHelpText(spoken_help)
            grid.Add(self._spoken, 1, wx.EXPAND)
            grid.Add(wx.StaticText(self, label=written_label), 0, wx.ALIGN_TOP)
            self._written = wx.TextCtrl(
                self, value=entry.written if entry else "", style=wx.TE_MULTILINE
            )
            self._written.SetHelpText(written_help)
            self._written.SetMinSize((320, 72))
            grid.Add(self._written, 1, wx.EXPAND)
        root.Add(grid, 1, wx.EXPAND | wx.ALL, _PAD)
        root.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), 0, wx.EXPAND | wx.ALL, _PAD)
        self.SetSizerAndFit(root)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self._spoken.SetFocus()

    def entry(self) -> Entry:
        written = self._written.GetValue() if self._written is not None else ""
        return Entry(self._kind, self._spoken.GetValue().strip(), written)


class DictationWordsDialog(wx.Dialog):
    """Words, phrases and corrections, each a sentence in one list."""

    def __init__(
        self,
        parent: Any,
        path: Path,
        *,
        say: Callable[[str], None],
        open_file: Callable[[Path], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            title="My Words and Phrases",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._path = path
        self._say = say
        self._open_file = open_file
        self._words: WordsFile = load_words(path)
        self._entries: list[Entry] = []

        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="Your words, phrases and &corrections:")
        self.list = wx.ListBox(self)
        self.list.SetHelpText(
            "Everything dictation has been taught: words to spell your way, "
            "phrases that write something longer, and corrections for what the "
            "engine keeps hearing wrong. Enter edits the one you are on."
        )
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.list, 1, wx.EXPAND | wx.ALL, _PAD)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        add_word = wx.Button(self, label="Add &Word...")
        add_word.SetHelpText(
            "A name, term or acronym spelled the way you want it; the engine's "
            "near misses are corrected to it."
        )
        add_phrase = wx.Button(self, label="Add &Phrase...")
        add_phrase.SetHelpText(
            "Words you say that write something else: my email address, my signature."
        )
        add_correction = wx.Button(self, label="Add Co&rrection...")
        add_correction.SetHelpText(
            "What the engine keeps writing wrong, and what to write instead."
        )
        edit = wx.Button(self, label="&Edit...")
        edit.SetHelpText("Change the entry you are on.")
        remove = wx.Button(self, label="Re&move")
        remove.SetHelpText(
            "Take the entry you are on out. It is saved at once; add it again to undo."
        )
        for button, handler in (
            (add_word, lambda _e: self._add("word")),
            (add_phrase, lambda _e: self._add("phrase")),
            (add_correction, lambda _e: self._add("correction")),
            (edit, self._on_edit),
            (remove, self._on_remove),
        ):
            button.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(button, 0, wx.RIGHT, _PAD)
        root.Add(buttons, 0, wx.LEFT | wx.RIGHT, _PAD)

        bottom = wx.BoxSizer(wx.HORIZONTAL)
        if open_file is not None:
            open_button = wx.Button(self, label="Open the &File...")
            open_button.SetHelpText(
                "Open dictation.md itself in the editor, for anyone who prefers a "
                "file. Everything here is in it, under three headings."
            )
            open_button.Bind(wx.EVT_BUTTON, self._on_open_file)
            bottom.Add(open_button, 0, wx.RIGHT, _PAD)
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close this window. Every change was already saved.")
        bottom.Add(close, 0)
        root.Add(bottom, 0, wx.ALL, _PAD)

        self.SetSizer(root)
        self.SetSize((640, 460))
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        bind_close_button(self, close, modeless=False)
        apply_listbox_activation(self.list, self._on_edit)  # Enter, Space and double-click
        self._rebuild(select=0)
        self.list.SetFocus()

    # -- the list ------------------------------------------------------------ #

    def _rebuild(self, select: int) -> None:
        self._entries = self._words.entries()
        self.list.Set([entry.label() for entry in self._entries])
        if self._entries:
            self.list.SetSelection(max(0, min(select, len(self._entries) - 1)))

    def _selected(self) -> tuple[int, Entry | None]:
        index = self.list.GetSelection()
        if index == wx.NOT_FOUND or index >= len(self._entries):
            return -1, None
        return int(index), self._entries[int(index)]

    def _save(self, said: str, select: int) -> None:
        try:
            save_words(self._path, self._words)
        except OSError as error:
            self._say(f"Your words could not be saved. {error}")
            self._words = load_words(self._path)
            self._rebuild(select=select)
            return
        self._rebuild(select=select)
        self._say(said)

    # -- the buttons --------------------------------------------------------- #

    def _ask(self, kind: str, entry: Entry | None = None) -> Entry | None:
        dialog = _EntryDialog(self, kind, entry)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            return dialog.entry()
        finally:
            dialog.Destroy()

    def _add(self, kind: str) -> None:
        entry = self._ask(kind)
        if entry is None:
            return
        if not self._words.add(entry):
            self._say(_refusal(entry))
            return
        self._save(f"Added. {entry.label()}", select=len(self._words.entries()) - 1)

    def _on_edit(self, _event: Any) -> None:
        index, entry = self._selected()
        if entry is None:
            self._say("Nothing to edit yet. Add a word, a phrase or a correction first.")
            return
        changed = self._ask(entry.kind, entry)
        if changed is None:
            return
        if not self._words.replace(entry, changed):
            self._say(_refusal(changed))
            return
        self._save(f"Changed. {changed.label()}", select=index)

    def _on_remove(self, _event: Any) -> None:
        index, entry = self._selected()
        if entry is None:
            self._say("Nothing to remove.")
            return
        self._words.remove(entry)
        self._save(f"Removed. {entry.label()}", select=index)

    def _on_open_file(self, _event: Any) -> None:
        if self._open_file is None:
            return
        self.EndModal(wx.ID_CANCEL)
        self._open_file(self._path)


def _refusal(entry: Entry) -> str:
    if not entry.spoken:
        return "Nothing was added: the first box was empty."
    if entry.kind != "word" and not entry.written.strip("\r\n"):
        return "Nothing was added: say what it should write."
    return f"Not added: {entry.spoken} is already in the list."
