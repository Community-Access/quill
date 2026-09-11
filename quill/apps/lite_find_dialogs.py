"""QuillLite's three searching windows: Find, Replace, and All Matches.

Split out of :mod:`quill.apps.lite_dialogs` when the search modes, the live
match count and the match list pushed that module past GATE-11's default cap.
They belong together anyway: all three read the same options dictionary, offer
the same Search mode chooser, and are the only windows in the app whose whole
job is to answer "where is it, and how many".

Two decisions are worth keeping in view.

**Find and Replace are modeless.** Searching is something you do *while*
reading; a modal Find would make every second match a matter of reopening the
window. The document window owns the search itself and is called back with the
options, so Find Next from the menu and Find Next from here run identical code.

**The match count is a label, not an announcement.** One match and no matches
sound identical to somebody pressing Find next in the dark, so the count is the
only place that difference is available before committing to a search -- but
speaking it on every keystroke would talk over the typing that produced it. A
label change on an unfocused control is exactly what a screen reader reports of
its own accord, which is GATE-12's cure and GATE-13's rule met at once.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.apps.lite_dialogs import _PAD, _labelled_text, choose_from_rows
from quill.ui.dialog_contract import (
    apply_modal_ids,
    bind_close_button,
    set_accessible_name,
)

__all__ = [
    "SEARCH_MODES",
    "FindDialog",
    "ReplaceDialog",
    "choose_match",
]

#: The three ways the Find box can read what you typed, in the order they are
#: offered. Kept as data so Find and Replace cannot drift apart about either the
#: labels or the order, and so the mode a row means is the string the shared
#: :mod:`quill.core.find_model` already understands.
#:
#: **No ``&`` in these titles.** They are rows of a ``wx.Choice``, and a choice's
#: rows are data rather than control labels: wx honours a mnemonic ampersand on
#: a button, a checkbox or a menu item and prints it literally in a list. These
#: read "&Normal" on screen, and out loud, until 2026-09-09. The Alt letter
#: belongs to the "Search &mode:" label beside the control, which is the place
#: wx will actually act on one.
#:
#: The names are meant to be readable by somebody who has never heard of an
#: escape sequence. The middle row was called "Escapes", which names the
#: mechanism rather than the job and told a user nothing; it now shows the two
#: codes anybody actually reaches for. QUILL calls the same mode "Extended
#: (special characters)" -- different words, same promise, and both say what
#: they do rather than what they are.
SEARCH_MODES: tuple[tuple[str, str, str], ...] = (
    (
        "normal",
        "Normal text",
        "What you type is what is looked for, punctuation and all.",
    ),
    (
        "extended",
        "Special characters (\\t, \\n)",
        "Backslash escapes mean the characters you cannot type: \\t is a tab, "
        "\\n a line break, \\u2014 an em dash.",
    ),
    (
        "regex",
        "Regular expression",
        "The text is a search pattern: . matches any character, * repeats, "
        "[abc] matches one of those. A pattern that is not valid is refused "
        "with the reason.",
    ),
)


def _add_mode_choice(dialog: wx.Dialog, sizer: wx.Sizer) -> wx.Choice:
    """A labelled Search-mode chooser, built the same way in both dialogs.

    A ``wx.Choice`` rather than three radio buttons: three modes is one more
    thing to Tab past every time you open Find, and a collapsed control that
    announces its current value costs one stop instead of three.
    """
    label = wx.StaticText(dialog, label="Search &mode:")
    choice = wx.Choice(dialog, choices=[title for _id, title, _help in SEARCH_MODES])
    choice.SetSelection(0)
    set_accessible_name(choice, "Search mode")
    choice.SetHelpText(
        "How the text you typed is read: as itself, as backslash escapes, or "
        "as a regular expression."
    )
    sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
    sizer.Add(choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)
    return choice


def _mode_of(choice: wx.Choice) -> str:
    index = choice.GetSelection()
    if index < 0 or index >= len(SEARCH_MODES):
        return "normal"
    return SEARCH_MODES[index][0]


class FindDialog(wx.Dialog):
    """Modeless find. Enter finds next, Shift+Enter finds previous.

    Modeless because finding is something you do *while* reading: a modal find
    would make every other match a matter of reopening the dialog. The window
    owns the search itself and is called back with the options, so Find Next
    from the menu and Find Next from here run the identical code.
    """

    def __init__(
        self,
        parent: wx.Window,
        initial: str,
        on_find: Callable[[dict[str, Any], bool], object],
        on_count: Callable[[dict[str, Any]], str] | None = None,
    ) -> None:
        super().__init__(parent, title="Find", style=wx.DEFAULT_DIALOG_STYLE)
        self._on_find = on_find
        self._on_count = on_count
        root = wx.BoxSizer(wx.VERTICAL)
        self.text = _labelled_text(
            self,
            root,
            "Find &what:",
            initial,
            help_text="The text to look for. Enter finds the next one, Shift Enter the previous.",
        )
        self.match_case = wx.CheckBox(self, label="Match &case")
        self.match_case.SetHelpText("When checked, Cat and cat are different words.")
        self.whole_word = wx.CheckBox(self, label="Whole wor&d only")
        self.whole_word.SetHelpText(
            "When checked, cat does not match catalogue -- only the word on its own."
        )
        root.Add(self.match_case, 0, wx.LEFT | wx.RIGHT, _PAD)
        root.Add(self.whole_word, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)
        self.mode = _add_mode_choice(self, root)

        # The count of what you have typed so far, before you commit to it. One
        # match and no matches sound identical when you are pressing Find next
        # in the dark; this is the only place that difference is available.
        self.count_label = wx.StaticText(self, label="")
        set_accessible_name(self.count_label, "Matches")
        root.Add(self.count_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.next_btn = wx.Button(self, wx.ID_OK, "Find &next")
        self.next_btn.SetHelpText("Find the next match after the cursor, wrapping at the end.")
        self.prev_btn = wx.Button(self, label="Find &previous")
        self.prev_btn.SetHelpText("Find the previous match, wrapping at the start.")
        close_btn = wx.Button(self, wx.ID_CANCEL, "Close")
        close_btn.SetHelpText("Close this window. The search you typed is remembered for F3.")
        for button in (self.next_btn, self.prev_btn):
            buttons.Add(button, 0, wx.RIGHT, _PAD)
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)

        self.SetSizerAndFit(root)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Find next",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
        )
        self.next_btn.Bind(wx.EVT_BUTTON, lambda _event: self._find(False))
        self.prev_btn.Bind(wx.EVT_BUTTON, lambda _event: self._find(True))
        bind_close_button(self, close_btn, modeless=True)
        self.Bind(wx.EVT_CLOSE, lambda _event: self.Destroy())
        self.text.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self.text.Bind(wx.EVT_TEXT, self._on_text_changed)
        for control in (self.match_case, self.whole_word):
            control.Bind(wx.EVT_CHECKBOX, self._on_text_changed)
        self.mode.Bind(wx.EVT_CHOICE, self._on_text_changed)
        self.text.SetFocus()
        self.text.SelectAll()
        self._refresh_count()

    def _on_key(self, event: wx.KeyEvent) -> None:
        key = event.GetKeyCode()
        if key == wx.WXK_RETURN and event.ShiftDown():
            self._find(True)
            return
        if key == wx.WXK_ESCAPE:
            self.Close()
            return
        # Peek: step through the matches without leaving the search box, so the
        # next one can be heard and the query still adjusted. Enter commits and
        # moves focus to the document; these do not.
        if key == wx.WXK_DOWN and event.ControlDown():
            self._find(False)
            self.text.SetFocus()
            return
        if key == wx.WXK_UP and event.ControlDown():
            self._find(True)
            self.text.SetFocus()
            return
        event.Skip()

    def _on_text_changed(self, event: wx.CommandEvent) -> None:
        self._refresh_count()
        event.Skip()

    def _refresh_count(self) -> None:
        """Put the match count on its label, where the reader will say it.

        Announced by the label rather than spoken directly: a count spoken on
        every keystroke would talk over the typing it is describing, and a
        label change on an unfocused control is exactly what a screen reader
        reports of its own accord.
        """
        if self._on_count is None:
            return
        try:
            self.count_label.SetLabel(self._on_count(self.options()))
        except RuntimeError:  # the window is going away
            pass

    def options(self) -> dict[str, Any]:
        return {
            "needle": self.text.GetValue(),
            "match_case": self.match_case.GetValue(),
            "whole_word": self.whole_word.GetValue(),
            "mode": _mode_of(self.mode),
        }

    def _find(self, reverse: bool) -> None:
        self._on_find(self.options(), reverse)


class ReplaceDialog(wx.Dialog):
    """Modeless replace: find, replace one, or replace every one."""

    def __init__(
        self,
        parent: wx.Window,
        initial: str,
        on_find: Callable[[dict[str, Any], bool], object],
        on_replace: Callable[[dict[str, Any]], object],
        on_replace_all: Callable[[dict[str, Any]], object],
    ) -> None:
        super().__init__(parent, title="Replace", style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)
        self.text = _labelled_text(
            self, root, "Find &what:", initial, help_text="The text to look for."
        )
        self.replacement = _labelled_text(
            self,
            root,
            "Replace w&ith:",
            help_text="What each match becomes. Leave it empty to delete the matches.",
        )
        self.match_case = wx.CheckBox(self, label="Match &case")
        self.match_case.SetHelpText("When checked, Cat and cat are different words.")
        self.whole_word = wx.CheckBox(self, label="Whole wor&d only")
        self.whole_word.SetHelpText(
            "When checked, cat does not match catalogue -- only the word on its own."
        )
        root.Add(self.match_case, 0, wx.LEFT | wx.RIGHT, _PAD)
        root.Add(self.whole_word, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)
        self.mode = _add_mode_choice(self, root)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        find_btn = wx.Button(self, wx.ID_OK, "Find &next")
        find_btn.SetHelpText("Move to the next match without changing anything.")
        replace_btn = wx.Button(self, label="&Replace")
        replace_btn.SetHelpText("Replace the match you are on, then move to the next one.")
        all_btn = wx.Button(self, label="Replace &all")
        all_btn.SetHelpText("Replace every match in the document and say how many were changed.")
        close_btn = wx.Button(self, wx.ID_CANCEL, "Close")
        close_btn.SetHelpText("Close this window. Nothing you have already replaced is undone.")
        for button in (find_btn, replace_btn, all_btn):
            buttons.Add(button, 0, wx.RIGHT, _PAD)
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)

        self.SetSizerAndFit(root)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Find next",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
        )
        find_btn.Bind(wx.EVT_BUTTON, lambda _event: on_find(self.options(), False))
        replace_btn.Bind(wx.EVT_BUTTON, lambda _event: on_replace(self.options()))
        all_btn.Bind(wx.EVT_BUTTON, lambda _event: on_replace_all(self.options()))
        bind_close_button(self, close_btn, modeless=True)
        self.Bind(wx.EVT_CLOSE, lambda _event: self.Destroy())
        self.text.SetFocus()
        self.text.SelectAll()

    def options(self) -> dict[str, Any]:
        return {
            "needle": self.text.GetValue(),
            "replacement": self.replacement.GetValue(),
            "match_case": self.match_case.GetValue(),
            "whole_word": self.whole_word.GetValue(),
            "mode": _mode_of(self.mode),
        }


def choose_match(
    parent: wx.Window, rows: list[tuple[str, int]], *, truncated: bool = False
) -> int | None:
    """Pick one match from every match in the document. Returns its offset.

    A list rather than repeated Find Next, because those answer different
    questions. Find Next tells you where the next one is; this tells you how
    many there are and what each is *surrounded by*, which is how somebody
    decides whether a Replace All is safe before running it.

    Each row leads with its line and column, so the list is navigable by the
    first characters a reader speaks rather than by a sentence that may begin
    with the same six words as its neighbour.
    """
    label = "&Matches in this document:"
    if truncated:
        # Say so rather than presenting a capped list as a complete one.
        label = "&Matches in this document (the first of very many):"
    chosen = choose_from_rows(
        parent,
        title="All matches",
        label=label,
        help_text=(
            "Choose a match and press Enter to select it in the document. "
            "The list is every match, in order, with the words around each one."
        ),
        rows=[(offset, text) for text, offset in rows],
        size=(720, 420),
    )
    return None if chosen is None else int(chosen)  # type: ignore[arg-type]
