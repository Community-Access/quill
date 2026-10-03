"""Look Up: the dictionary without AI, shared by QUILL and QUILL Lite.

The offline half is the thesaurus data every copy ships (synonyms, opposites,
related words); the online half is three free, keyless services --
the Free Dictionary for definitions, Datamuse for synonyms, opposites, rhymes
and related words, and a Wikipedia summary -- reached only after the listener
has said so (:mod:`quill.core.lexical`, DICT-1 to DICT-3). It was QUILL's
``show_lookup_dialog``; it lives here now so QUILL Lite opens the same window,
and because QUILL's copy went online whenever the dictionary feature was on,
which is not consent. The switch is in the window, where the question arises:
**Use online sources** sends the word -- only the word, never the sentence or
the document -- and the choice is remembered.

The window is the house shape: a read-only result focus lands on (the reader
reads it; nothing is announced on top, GATE-13), a list of the words that can
go into the document, and buttons that say what they do. Online results
arrive in the background and replace the offline ones when they come, with one
sentence said when they do, because the field they land in is the one with
focus and a label change on a focused read-only field is not something the
reader repeats.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.lexical import (
    ACTION_INSERT,
    LexicalResult,
    LookupItem,
    build_lookup_items,
    render_lookup,
)
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids, dialog_alive
from quill.ui.update_download import thread_submit

__all__ = ["TITLE", "ONLINE_LABEL", "show_lookup"]

TITLE = "Look Up"
ONLINE_LABEL = (
    "Use &online sources (sends only the word to the Free Dictionary, Datamuse and Wikipedia)"
)


def show_lookup(
    parent: Any,
    word: str,
    *,
    service: Any,
    online: bool,
    set_online: Callable[[bool], None],
    replace: Callable[[str], None] | None,
    teach: Callable[[str], str] | None,
    announce: Callable[[str], None],
    show_modal: Callable[[Any, str], int],
) -> None:
    """Open the Look Up window for *word*.

    *service* answers ``lookup(word, online=...)`` (a ``LexicalService``);
    *online* is the remembered consent and *set_online* stores a change;
    *replace* writes a chosen word over the one looked up (``None`` when the
    word was typed rather than in the document); *teach* adds the word to the
    spelling dictionary and returns the sentence to say.
    """
    dialog = wx.Dialog(
        parent, title=f"{TITLE}: {word}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
    )
    root = wx.BoxSizer(wx.VERTICAL)

    caption = wx.StaticText(dialog, label="&Result:")  # before the field: its name on wxMSW
    field = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP)
    field.SetMinSize((560, 260))
    field.SetHelpText(
        "What the dictionary and thesaurus know about the word: definitions and "
        "an encyclopedia summary when online sources are on, then synonyms, "
        "opposites, related words and rhymes. Read only; arrow through it."
    )
    root.Add(caption, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
    root.Add(field, 1, wx.EXPAND | wx.ALL, 8)

    online_box = wx.CheckBox(dialog, label=ONLINE_LABEL)
    online_box.SetValue(bool(online))
    online_box.SetHelpText(
        "Off, nothing leaves this computer and the answer is the thesaurus that "
        "ships with the app. On, the word alone -- never the sentence or the "
        "document -- goes to three free services for definitions, more words "
        "and a short encyclopedia summary. Remembered for next time."
    )
    root.Add(online_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    list_caption = wx.StaticText(dialog, label="&Words you can use:")
    words = wx.ListBox(dialog, style=wx.LB_SINGLE)
    words.SetMinSize((560, 140))
    words.SetHelpText(
        "Synonyms, opposites, related words and rhymes, each saying which it is. "
        "Enter, or Replace Word, puts the selected one in place of the word you "
        "looked up; Control Z takes it back."
    )
    root.Add(list_caption, 0, wx.LEFT | wx.RIGHT, 8)
    root.Add(words, 0, wx.EXPAND | wx.ALL, 8)

    row = wx.BoxSizer(wx.HORIZONTAL)
    replace_btn = wx.Button(dialog, label="&Replace Word")
    replace_btn.SetHelpText(
        "Puts the selected word in place of the one you looked up. Control Z takes it back."
    )
    copy_btn = wx.Button(dialog, label="&Copy")
    copy_btn.SetHelpText("Copies the selected word, or the whole result when no word is selected.")
    teach_btn = wx.Button(dialog, label="&Add to Dictionary")
    teach_btn.SetHelpText("Adds the word you looked up to your spelling dictionary.")
    close_btn = wx.Button(dialog, wx.ID_CLOSE, label="Close")
    close_btn.SetHelpText("Closes Look Up. Nothing changes in your document.")
    for button in (replace_btn, copy_btn, teach_btn):
        row.Add(button, 0, wx.RIGHT, 6)
    row.AddStretchSpacer()
    row.Add(close_btn, 0)
    root.Add(row, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizer(root)
    dialog.Fit()
    dialog.CenterOnParent()
    apply_modal_ids(dialog, affirmative_id=close_btn.GetId(), escape_id=close_btn.GetId())

    items: list[LookupItem] = []
    state = {"generation": 0}

    def _fill(result: LexicalResult, *, arrived_online: bool) -> None:
        if not dialog_alive(dialog):
            return
        field.SetValue(render_lookup(result))
        field.SetInsertionPoint(0)
        items[:] = [item for item in build_lookup_items(result) if item.action == ACTION_INSERT]
        words.Set([f"{item.kind}: {item.label}" for item in items])
        if items:
            words.SetSelection(0)
        _sync()
        if arrived_online:
            announce("Online results arrived." if not result.is_empty else "Nothing found online.")

    def _sync() -> None:
        has_choice = words.GetSelection() != wx.NOT_FOUND and bool(items)
        replace_btn.Enable(has_choice and replace is not None)
        teach_btn.Enable(teach is not None)

    def _selected() -> LookupItem | None:
        index = words.GetSelection()
        if index == wx.NOT_FOUND or index >= len(items):
            return None
        return items[index]

    def _query(use_online: bool) -> None:
        """Offline now; online on a worker, delivered only if still wanted."""
        _fill(service.lookup(word, online=False), arrived_online=False)
        if not use_online:
            return
        state["generation"] += 1
        generation = state["generation"]

        def work(**_kwargs: Any) -> LexicalResult:
            return service.lookup(word, online=True)

        def arrived(_name: str, result: LexicalResult) -> None:
            if generation == state["generation"]:
                wx.CallAfter(_fill, result, arrived_online=True)

        def failed(_name: str, _error: BaseException) -> None:
            return None  # the offline answer stays on screen

        announce("Looking up online.")
        # The family's one-thread submit (QUILL Lite has no task manager); the
        # generation counter above is the cancellation.
        thread_submit("quill-look-up", work, on_success=arrived, on_failure=failed)

    def _on_online(_event: Any) -> None:
        flag = bool(online_box.GetValue())
        set_online(flag)
        state["generation"] += 1  # a pending online answer is no longer wanted when switched off
        _query(flag)

    def _on_replace(_event: Any = None) -> None:
        chosen = _selected()
        if chosen is None or replace is None:
            announce(
                "Choose a word in the list first."
                if replace is not None
                else "The word was typed, not in the document, so there is nothing to replace."
            )
            return
        replace(chosen.value)
        announce(f'Replaced "{word}" with "{chosen.value}". Press Control Z to undo.')
        dialog.EndModal(wx.ID_CLOSE)

    def _on_copy(_event: Any) -> None:
        chosen = _selected()
        text = chosen.value if chosen is not None else field.GetValue()
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
            announce("Copied.")

    def _on_teach(_event: Any) -> None:
        if teach is None:
            return
        announce(teach(word) or f'Added "{word}" to your dictionary.')

    online_box.Bind(wx.EVT_CHECKBOX, _on_online)
    replace_btn.Bind(wx.EVT_BUTTON, _on_replace)
    copy_btn.Bind(wx.EVT_BUTTON, _on_copy)
    teach_btn.Bind(wx.EVT_BUTTON, _on_teach)
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
    words.Bind(wx.EVT_LISTBOX, lambda _e: _sync())
    apply_listbox_activation(words, _on_replace)
    _query(bool(online))
    wx.CallAfter(field.SetFocus)
    # *show_modal* is the host's _show_modal_dialog: the accessible show path
    # every modal in the family goes through (the hardening contract's rule).
    _show_modal_dialog = show_modal
    try:
        _show_modal_dialog(dialog, TITLE)
    finally:
        state["generation"] += 1
        dialog.Destroy()
