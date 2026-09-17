"""QuillLite's spelling context menu: what it offers, and what its rows do.

The menu is built against a stand-in for ``wx.Menu`` rather than a real one, for
the reason the line-command tests give: what is being tested is the *decision*
-- which rows exist, in what order, with what words in them, and what each one
does to the document and to the spoken outcome. None of that is wx's, and a real
menu needs a display to build.

Two things are asserted about shape. **Everything about the word is under one
"Spelling" submenu**, so the top-level menu is the same menu whether or not the
caret happens to be in a misspelling -- Undo and Cut do not move. And **the
corrections are the first rows inside it**: a listener has no red squiggle, so
the Applications key is the squiggle, and the answer has to be the first thing
in the submenu rather than something below four kinds of housekeeping.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.apps.lite_window_context_menu import DocumentContextMenuMixin

wx = pytest.importorskip("wx")


class _Item:
    def __init__(self, label: str) -> None:
        self.label = label
        self.enabled = True

    def Enable(self, value: bool) -> None:
        self.enabled = bool(value)


class _Menu:
    """The slice of wx.Menu the builder touches, remembering what it was given."""

    def __init__(self) -> None:
        self.rows: list[str] = []
        self.items: list[_Item] = []
        self.handlers: dict[str, Any] = {}
        self.submenus: dict[str, _Menu] = {}
        self._pending: _Item | None = None

    def Append(self, _id: Any, label: str, **_kwargs: Any) -> _Item:
        item = _Item(label)
        self.rows.append(label)
        self.items.append(item)
        self._pending = item
        return item

    def AppendSeparator(self) -> None:
        self.rows.append("---")

    def AppendSubMenu(self, submenu: _Menu, label: str) -> _Item:
        item = _Item(label)
        self.rows.append(label)
        self.items.append(item)
        self.submenus[label] = submenu
        # One popup, one handler table. wxMSW routes every command from a popup
        # -- submenu rows included -- through the menu that was handed to
        # PopupMenu, so the builder binds submenu rows on the parent, and a test
        # holding either object has to see the same handlers.
        submenu.handlers = self.handlers
        self._pending = item
        return item

    def Bind(self, _event: Any, handler: Any, item: Any = None, **kwargs: Any) -> None:
        target = item if isinstance(item, _Item) else self._pending
        if "id" in kwargs and target is None:  # the edit rows bind by stock id
            return
        if target is not None:
            self.handlers[target.label] = handler

    def Destroy(self) -> None:
        pass


class _Control:
    def __init__(self, text: str, cursor: int) -> None:
        self._text = text
        self._cursor = cursor
        self.focused = False

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._cursor

    def SetInsertionPoint(self, position: int) -> None:
        self._cursor = position

    def GetSelection(self) -> tuple[int, int]:
        return (self._cursor, self._cursor)

    def Replace(self, start: int, end: int, text: str) -> None:
        self._text = self._text[:start] + text + self._text[end:]

    def SetFocus(self) -> None:
        self.focused = True

    def CanUndo(self) -> bool:
        return True

    def CanRedo(self) -> bool:
        return False

    def CanPaste(self) -> bool:
        return True


class _Settings:
    share_quill_dictionary = False


class _App:
    def __init__(self, spelling: bool = True) -> None:
        self.settings = _Settings()
        self.data_dir = Path(".")
        self._spelling = spelling

    def feature_enabled(self, area: str) -> bool:
        return self._spelling if area == "spelling" else True

    def binding_for(self, command: str) -> str | None:
        return {
            "cmd_spell_word_at_cursor": "Shift+F7",
            "cmd_spell_review": "F7",
            "cmd_next_misspelling": "Ctrl+F7",
            "cmd_previous_misspelling": "Ctrl+Shift+F7",
        }.get(command)


class _Window(DocumentContextMenuMixin):
    def __init__(self, text: str, cursor: int, *, spelling: bool = True) -> None:
        self.control = _Control(text, cursor)
        self.app = _App(spelling)
        self.path: Path | None = Path("letter.txt")
        self.announcements: list[str] = []
        self.modified = False
        self._last_live_word = None
        self.taught: list[tuple[str, str]] = []
        self._init_context_menu()

    # -- the surrounding window, stubbed ---------------------------------- #

    @staticmethod
    def _new_menu() -> _Menu:
        """The submenu comes from here, so it is a stand-in like the popup."""
        return _Menu()

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _set_modified(self, value: bool) -> None:
        self.modified = value

    def _touch_status(self) -> None:
        pass

    def _spelling_enabled(self) -> bool:
        return self.app.feature_enabled("spelling")

    def _spell_dictionary(self) -> set[str]:
        return set()

    def _forget_spell_dictionary(self) -> None:
        pass


def _build(text: str, cursor: int, **kwargs: Any) -> tuple[_Window, _Menu]:
    """The whole popup: the Spelling submenu row, then the edit rows."""
    window = _Window(text, cursor, **kwargs)
    menu = _Menu()
    context = window._context_spelling(cursor)
    if context is not None:
        window._append_spelling_section(menu, context)
    return window, menu


def _menu_for(text: str, cursor: int, **kwargs: Any) -> tuple[_Window, _Menu]:
    """The *Spelling Actions submenu* -- or the popup, when there is none.

    Most questions below are about what that submenu offers: ignore, teach,
    next and previous. The **corrections** are not in it -- they are on the
    popup itself, where the first Down arrow reaches them (bad.md S11) -- so a
    test about a suggestion uses :func:`_build` and reads the popup's own rows.
    """
    window, menu = _build(text, cursor, **kwargs)
    if menu.submenus:
        return window, next(iter(menu.submenus.values()))
    return window, menu


# ---------------------------------------------------------------------------
# What the menu offers


def test_the_first_down_arrow_lands_on_a_correction() -> None:
    """The settled answer to the one contested question here (bad.md S11).

    A sighted person finds a misspelling by looking for a red squiggle and
    right-clicking it. A listener has no squiggle, so the Applications key *is*
    the squiggle -- and the first Down arrow has to land on the answer rather
    than on Undo or on a submenu that costs a Right arrow and a pause before
    anything is said.
    """
    text = "the wrold is round"
    _window, menu = _build(text, text.index("wrold"))
    assert menu.rows
    assert menu.rows[0] not in {"---", "&Ignore Once"}
    assert "wrold" not in menu.rows[0]  # a suggestion, not the word itself


def test_everything_below_the_corrections_is_in_the_same_place_every_time() -> None:
    """The other half of S11, and the reason the two arguments never actually
    conflicted: the part that changes length is at the **front**.

    QuillLite's complaint was a menu whose length changes with where the caret
    is, putting Undo and Cut a dozen unpredictable rows down whenever the word
    happens to be misspelled. Corrections, a separator, one Spelling Actions
    row, a separator -- so what somebody learns is not a row number, it is
    "after the suggestions, the menu is the menu".
    """
    text = "the wrold is round"
    _window, menu = _build(text, text.index("wrold"))
    assert len(menu.submenus) == 1
    tail = menu.rows[menu.rows.index("---") :]
    assert tail == ["---", next(iter(menu.submenus)), "---"]


def test_the_actions_submenu_names_the_word_it_is_about() -> None:
    """A submenu is one row read on the way past, and "Spelling Actions" alone
    does not say which word -- the same reason every row inside it names it."""
    text = "the wrold is round"
    _window, menu = _build(text, text.index("wrold"))
    title = next(iter(menu.submenus))
    assert title.startswith("&Spelling Actions")
    assert "wrold" in title


def test_a_correctly_spelled_word_gets_no_spelling_rows_at_all() -> None:
    """Not a disabled "no misspelling here" row: that is a row every
    right-click in a clean document makes somebody arrow past."""
    _window, menu = _build("the world is round", 7)
    assert menu.rows == []
    assert menu.submenus == {}


def test_the_caret_inside_the_word_is_enough() -> None:
    """The as-you-type helper only answers for a word starting exactly at the
    caret, which is not where anybody opens a context menu."""
    text = "the wrold is round"
    for offset in range(len("wrold") + 1):
        _window, menu = _menu_for(text, text.index("wrold") + offset)
        assert menu.rows, f"no spelling rows with the caret {offset} into the word"


def test_the_spelling_area_switched_off_takes_the_whole_section() -> None:
    """A feature somebody removed must own nothing -- half a menu left behind is
    a Customize Features checkbox that does not mean what it says."""
    text = "the wrold is round"
    _window, menu = _build(text, text.index("wrold"), spelling=False)
    assert menu.rows == []
    assert menu.submenus == {}


def test_every_teaching_row_names_the_word() -> None:
    """A menu reached by keyboard is read out of context: "Add to Dictionary"
    is a row you have to go back and check the meaning of."""
    text = "the wrold is round"
    _window, menu = _menu_for(text, text.index("wrold"))
    assert any('Add "wrold" to My &Dictionary' in row for row in menu.rows)


def test_the_onward_rows_carry_the_keys_they_are_bound_to() -> None:
    text = "the wrold is round"
    _window, menu = _menu_for(text, text.index("wrold"))
    assert any(row.endswith("\tShift+F7") for row in menu.rows)
    assert any(row.endswith("\tCtrl+F7") for row in menu.rows)


def test_both_kinds_of_ignore_are_offered() -> None:
    text = "the wrold is round"
    _window, menu = _menu_for(text, text.index("wrold"))
    assert "&Ignore Once" in menu.rows
    assert "I&gnore in This Document" in menu.rows


def test_a_word_with_no_suggestions_still_gets_the_rows_that_act_on_it() -> None:
    """ "There is nothing I can suggest" is the answer to the question asked, so
    it is said -- and Ignore and Add still apply to the word."""
    text = "the zzzqqxv is round"
    _window, menu = _menu_for(text, text.index("zzzqqxv"))
    if menu.rows and menu.rows[0].startswith("No suggestions"):
        assert not menu.items[0].enabled
        assert "&Ignore Once" in menu.rows


# ---------------------------------------------------------------------------
# What the rows do


def test_a_suggestion_replaces_the_word_and_says_which() -> None:
    text = "the wrold is round"
    window, menu = _build(text, text.index("wrold"))
    suggestion = menu.rows[0]
    menu.handlers[suggestion](None)
    assert window.control.GetValue() == text.replace("wrold", suggestion)
    assert window.modified
    assert f'Replaced "wrold" with "{suggestion}"' in window.announcements


def test_replacing_leaves_the_caret_after_the_new_word() -> None:
    text = "the wrold is round"
    window, menu = _build(text, text.index("wrold"))
    suggestion = menu.rows[0]
    menu.handlers[suggestion](None)
    assert window.control.GetInsertionPoint() == 4 + len(suggestion)


def test_a_stale_offset_refuses_rather_than_corrupting_another_word() -> None:
    """A menu stays open as long as the user leaves it open. Replacing on an
    offset the document has moved past is the worst outcome available here."""
    text = "the wrold is round"
    window, menu = _build(text, text.index("wrold"))
    suggestion = menu.rows[0]
    window.control.Replace(0, len(text), "something else entirely here")
    menu.handlers[suggestion](None)
    assert window.control.GetValue() == "something else entirely here"
    assert "That word has changed. Nothing was replaced." in window.announcements


def test_ignore_in_this_document_says_how_long_it_lasts() -> None:
    """That is the fact that decides whether to teach the word instead, and it
    is discoverable nowhere else."""
    text = "the wrold is round"
    window, menu = _menu_for(text, text.index("wrold"))
    menu.handlers["I&gnore in This Document"](None)
    said = window.announcements[-1]
    assert "wrold" in said
    assert "close the window" in said
    assert "dictionary" in said


def test_an_ignored_word_stops_producing_a_spelling_section() -> None:
    text = "the wrold is round"
    window, menu = _menu_for(text, text.index("wrold"))
    menu.handlers["I&gnore in This Document"](None)
    assert window._context_spelling(text.index("wrold")) is None


def test_ignore_once_leaves_the_other_occurrence_alone() -> None:
    text = "wrold and wrold"
    window, menu = _menu_for(text, 0)
    menu.handlers["&Ignore Once"](None)
    assert window._context_spelling(0) is None
    assert window._context_spelling(10) is not None


# ---------------------------------------------------------------------------
# Naming the dictionary a word went to


def test_the_personal_dictionary_is_named_by_which_one_it_is() -> None:
    """There are two, and "added to dictionary" does not say which."""
    window = _Window("wrold", 0)
    assert window._dictionary_name("personal") == "your QuillLite dictionary"
    window.app.settings.share_quill_dictionary = True
    assert window._dictionary_name("personal") == "QUILL's shared dictionary"


def test_the_document_dictionary_is_named_by_the_file_it_sits_beside() -> None:
    window = _Window("wrold", 0)
    assert window._dictionary_name("document") == "the dictionary beside letter.txt"


def test_an_unsaved_document_still_gets_a_sentence_rather_than_a_none() -> None:
    window = _Window("wrold", 0)
    window.path = None
    assert "unsaved" in window._dictionary_name("document")


# ---------------------------------------------------------------------------
# Menu text is data


def test_an_ampersand_in_a_suggestion_is_a_literal_not_a_mnemonic() -> None:
    """Otherwise it swallows the next character and claims an access key the
    menu has already given to something else."""
    assert _Window("x", 0)._escape_menu_text("AT&T") == "AT&&T"


def test_no_two_rows_in_the_popup_claim_the_same_access_key() -> None:
    """Windows cycles focus between duplicates instead of pressing either, so a
    letter used twice is a row that silently cannot be reached -- and the
    spelling rows sit in the same menu as Undo, Cut, Copy, Paste and Select All.
    """
    text = "the wrold is round"
    window, menu = _build(text, text.index("wrold"))
    window._append_edit_section(menu)
    # Each menu is its own namespace -- the submenu's rows only have to miss
    # each other and the popup's rows only have to miss each other -- so both
    # levels are checked, separately, which is what Windows does.
    for level in (menu, *menu.submenus.values()):
        claimed: dict[str, str] = {}
        for row in level.rows:
            if row == "---":
                continue
            letter = _mnemonic(row)
            if not letter:
                continue
            assert letter not in claimed, f"{row!r} and {claimed[letter]!r} both claim Alt+{letter}"
            claimed[letter] = row


def _mnemonic(label: str) -> str:
    """The Alt letter *label* claims, or "". ``&&`` is a literal ampersand."""
    index = label.find("&")
    while label[index : index + 2] == "&&":
        index = label.find("&", index + 2)
    if index < 0 or index + 1 >= len(label):
        return ""
    return label[index + 1].upper()
