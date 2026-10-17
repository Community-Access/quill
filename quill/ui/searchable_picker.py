"""QUILL's type-to-filter picker: Insert Snippet, Insert HTML Tag, Move Section To.

Moved out of ``main_frame.py`` on 2026-10-16 (GATE-11), when it learned two
things a large library needed. Both were measured first
(``docs/design/2026-10-16-editor-completion-measurements.md``):

* **The list shows at most :data:`SHOWN_LIMIT` rows.** Loading a ten-thousand
  snippet library takes 25 ms and filtering it 6.5 ms a keystroke; putting the
  matches *into the list box* took 2.2 to 3 seconds, once on opening and again
  after every key that left thousands of matches. Two hundred rows fill in
  about 50 ms. Nothing is hidden for good: the line above the list says how
  many matched and that typing more narrows them, and every match is still
  reachable by typing a little more of its name.
* **Typing is gathered before the list is refilled** when the library is
  larger than one screen of rows: the refill waits :data:`FILTER_DELAY_MS` after
  the last key, so typing "meeting notes" fills the list once rather than
  thirteen times. Enter and Down Arrow never act on a stale list -- a pending
  refill runs first. Small lists (Insert HTML Tag) refill on every key, as
  before.

The keys are unchanged: type in the search box (spaces included), Down or Up
Arrow to the results, Enter to choose, Escape to cancel.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

__all__ = ["FILTER_DELAY_MS", "SHOWN_LIMIT", "choose_searchable_option", "match_status"]

#: Rows put in the list at once. A listener does not arrow through more than a
#: screenful before typing a better word, and each row costs about 0.25 ms.
SHOWN_LIMIT = 200

#: How long after the last key a large list is refilled.
FILTER_DELAY_MS = 150


def match_status(matches: list[str], shown: int, examples: tuple[str, ...] = ()) -> str:
    """The line above the list: how many matched, the top one, and any cap."""
    if not matches:
        if examples:
            return f"No matching options. Try: {', '.join(examples)}"
        return "No matching options"
    if shown < len(matches):
        return (
            f"{len(matches)} matches; showing the first {shown}. Type more to narrow "
            f"them. Top match: {matches[0]}"
        )
    return f"{len(matches)} match(es). Top match: {matches[0]}"


def choose_searchable_option(
    wx: Any,
    parent: Any,
    show_modal: Callable[[Any, str], int],
    remembered: dict[str, str],
    *,
    title: str,
    prompt: str,
    dialog_label: str,
    initial_choices: list[str],
    search_callback: Callable[[str], list[str]],
    empty_search_examples: tuple[str, ...] = (),
) -> str | None:
    """Show the picker; the chosen row's text, or ``None`` on Cancel.

    *remembered* maps a picker's label to the last search typed in it, so a
    picker opens on the search somebody left it with.
    """
    with wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER) as dialog:
        dialog.SetSize((560, 420))
        root = wx.BoxSizer(wx.VERTICAL)

        # A visible label built just before the box: on Windows that is where a
        # screen reader takes the box's name from (check_control_labels).
        root.Add(wx.StaticText(dialog, label="&Search:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        search = wx.SearchCtrl(dialog, style=wx.TE_PROCESS_ENTER)
        search.ShowSearchButton(True)
        search.SetDescriptiveText(prompt)
        set_accessible_name(search, prompt)
        search.SetHelpText(
            "Type any part of a name, spaces included, to narrow the list. Down Arrow "
            "moves to the list; Enter chooses the top match; Escape cancels."
        )
        root.Add(search, 0, wx.EXPAND | wx.ALL, 8)

        status = wx.StaticText(dialog, label="")
        root.Add(status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        results = wx.ListBox(dialog)
        set_accessible_name(results, dialog_label)
        results.SetHelpText(
            "The matches, best first. Enter chooses the row you are on. A long "
            "list shows its first rows; type more in the search box to narrow it."
        )
        root.Add(results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        dialog.SetSizer(root)

        last_query = remembered.get(dialog_label, "")
        if last_query:
            search.SetValue(last_query)

        filtered = list(initial_choices)
        gathered = len(initial_choices) > SHOWN_LIMIT
        pending: list[Any] = []

        def _refresh() -> None:
            nonlocal filtered
            while pending:
                timer = pending.pop()
                if timer.IsRunning():
                    timer.Stop()
            filtered = list(search_callback(search.GetValue()))
            shown = filtered[:SHOWN_LIMIT]
            results.Set(shown)
            if shown:
                results.SetSelection(0)
            status.SetLabel(match_status(filtered, len(shown), empty_search_examples))
            # The cap is said where the reader looks when it reaches the list: in
            # the list's own name, so row 200 is never mistaken for the last match.
            capped = len(shown) < len(filtered)
            set_accessible_name(
                results,
                f"{dialog_label}, first {len(shown)} of {len(filtered)} matches"
                if capped
                else dialog_label,
            )

        def _on_text(_event: object) -> None:
            if not gathered:
                _refresh()
                return
            while pending:
                pending.pop().Stop()
            pending.append(wx.CallLater(FILTER_DELAY_MS, _refresh))

        def _flush() -> None:
            if pending:
                _refresh()

        def _announce_selected() -> None:
            selected = results.GetSelection()
            if 0 <= selected < min(len(filtered), SHOWN_LIMIT):
                status.SetLabel(f"Selected: {filtered[selected]}")

        def _accept(_event: object) -> None:
            _flush()
            if results.GetCount() == 0:
                return
            dialog.EndModal(wx.ID_OK)

        def _on_char_hook(event: Any) -> None:
            key_code = event.GetKeyCode()
            if key_code == wx.WXK_ESCAPE:
                dialog.EndModal(wx.ID_CANCEL)
                return
            if key_code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                _accept(event)
                return
            # From the search box only: inside the list the arrows move by one
            # row, as a list's arrows do.
            if key_code in (wx.WXK_DOWN, wx.WXK_UP) and not results.HasFocus():
                _flush()
                if results.GetCount() > 0:
                    last = results.GetCount() - 1
                    results.SetSelection(0 if key_code == wx.WXK_DOWN else last)
                    results.SetFocus()
                    _announce_selected()
                    return
            event.Skip()

        search.Bind(wx.EVT_TEXT, _on_text)
        search.Bind(wx.EVT_TEXT_ENTER, _accept)
        results.Bind(wx.EVT_LISTBOX, lambda _event: _announce_selected())
        results.Bind(wx.EVT_LISTBOX_DCLICK, _accept)
        dialog.Bind(wx.EVT_CHAR_HOOK, _on_char_hook)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        _refresh()
        search.SetFocus()

        result = show_modal(dialog, dialog_label)
        remembered[dialog_label] = search.GetValue().strip()
        while pending:
            pending.pop().Stop()
        if result != wx.ID_OK:
            return None
        selected = results.GetSelection()
        if selected == wx.NOT_FOUND or selected < 0 or selected >= len(filtered):
            return None
        return filtered[selected]
