"""QuillLite's Find, now over the shared find model.

What is being pinned is the *seam*: QuillLite used to compile its own regex,
escaping the needle, which meant it could never offer a search mode. Routing it
through :mod:`quill.core.find_model` is what buys the three modes, the count and
the match list at once -- and the risk of a seam like that is a silent change
in what counts as a match, so the ordinary literal search is tested here
alongside the new modes rather than assumed.

The peek count deserves its own note. One match and no matches sound identical
to somebody pressing Find next in the dark, and the count is the only place that
difference is available before committing. It is therefore a *label*, read by
the screen reader when it changes, not an announcement spoken over the typing
that produced it.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.apps.lite_window_commands import DocumentCommandsMixin
from quill.ui.richedit_editing import PLAIN


class _Control:
    def __init__(self, text: str) -> None:
        self._text = text
        self.selection = (0, 0)
        self.shown = -1
        self.focused = False

    def GetValue(self) -> str:
        return self._text

    def GetSelection(self) -> tuple[int, int]:
        return self.selection

    def SetSelection(self, start: int, end: int) -> None:
        self.selection = (start, end)

    def ShowPosition(self, position: int) -> None:
        self.shown = position

    def SetFocus(self) -> None:
        self.focused = True

    def GetLastPosition(self) -> int:
        return len(self._text)

    def Replace(self, start: int, end: int, text: str) -> None:
        self._text = self._text[:start] + text + self._text[end:]


class _Window(DocumentCommandsMixin):
    """Only the parts of the document window the search path touches."""

    def __init__(self, text: str) -> None:
        self.control = _Control(text)
        self.announcements: list[str] = []
        self._find_options: dict[str, object] = {}
        self.modified = False
        # Plain text: Replace All only asks for confirmation in rich mode,
        # where a replacement takes the formatting of where it lands.
        self.editor = SimpleNamespace(mode=PLAIN)

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _set_modified(self, value: bool) -> None:
        self.modified = value

    def _touch_status(self) -> None:
        pass


def _options(needle: str, **kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "needle": needle,
        "match_case": False,
        "whole_word": False,
        "mode": "normal",
    }
    base.update(kwargs)
    return base


def test_a_normal_search_is_still_literal_after_the_rewiring() -> None:
    """``c.t`` means those three characters unless a mode says otherwise."""
    win = _Window("cat c.t")
    assert win._do_find(_options("c.t"), False) is True  # noqa: SLF001
    assert win.control.selection == (4, 7)


def test_regex_mode_treats_the_needle_as_a_pattern() -> None:
    win = _Window("cat cot")
    assert win._do_find(_options("c[ao]t", mode="regex"), False) is True  # noqa: SLF001
    assert win.control.selection == (0, 3)


def test_extended_mode_finds_a_character_there_is_no_key_for() -> None:
    """The other half of Describe Character: find every other one like it."""
    win = _Window("a\tb")
    assert win._do_find(_options(r"\t", mode="extended"), False) is True  # noqa: SLF001
    assert win.control.selection == (1, 2)


def test_a_broken_pattern_says_what_is_wrong_rather_than_finding_nothing() -> None:
    """A failed search and an empty result are different problems."""
    win = _Window("anything")
    assert win._do_find(_options("(unclosed", mode="regex"), False) is False  # noqa: SLF001
    assert any("closing parenthesis" in message for message in win.announcements)
    assert not any("Not found" in message for message in win.announcements)


def test_an_empty_needle_asks_for_one_instead_of_erroring() -> None:
    win = _Window("text")
    assert win._do_find(_options(""), False) is False  # noqa: SLF001
    assert win.announcements == ["Type something to find"]


def test_the_wrap_is_still_announced() -> None:
    """The one thing the reader cannot know for itself."""
    win = _Window("cat and more")
    win.control.selection = (8, 8)
    assert win._do_find(_options("cat"), False) is True  # noqa: SLF001
    assert "Wrapped to the start" in win.announcements


def test_peek_counts_without_moving_the_cursor() -> None:
    win = _Window("cat cat cat")
    assert win.peek_match_count(_options("cat")) == "3 matches"
    assert win.control.selection == (0, 0)


def test_peek_says_no_matches_rather_than_returning_nothing() -> None:
    """Silence would be indistinguishable from "not counted yet"."""
    win = _Window("cat")
    assert win.peek_match_count(_options("dog")) == "No matches"


def test_peek_uses_the_singular_for_one() -> None:
    win = _Window("cat")
    assert win.peek_match_count(_options("cat")) == "1 match"


def test_peek_is_silent_for_an_empty_needle() -> None:
    win = _Window("cat")
    assert win.peek_match_count(_options("")) == ""


def test_peek_is_silent_rather_than_shouting_about_a_half_typed_pattern() -> None:
    """A pattern is invalid for most of the time it is being typed."""
    win = _Window("cat")
    assert win.peek_match_count(_options("(", mode="regex")) == ""


def test_count_occurrences_reports_the_number_and_the_needle() -> None:
    win = _Window("cat cat")
    win._find_options = _options("cat")  # noqa: SLF001
    win.cmd_count_occurrences()
    assert win.announcements == ["2 matches for cat"]


def test_count_occurrences_with_nothing_searched_yet_says_what_to_do() -> None:
    win = _Window("cat")
    win.cmd_count_occurrences()
    assert win.announcements == ["Search for something first, then count it"]


def test_whole_word_wraps_a_whole_regex_alternation() -> None:
    """``cat|dog`` must not mean "the word cat, or dog anywhere"."""
    win = _Window("catalog dog")
    assert (
        win._do_find(  # noqa: SLF001
            _options("cat|dog", mode="regex", whole_word=True), False
        )
        is True
    )
    assert win.control.selection == (8, 11)


def test_replace_all_honours_the_mode() -> None:
    win = _Window("a1b22c")
    win._do_replace_all(_options(r"\d+", mode="regex", replacement="#"))  # noqa: SLF001
    assert win.control.GetValue() == "a#b#c"
    assert any("Replaced 2" in message for message in win.announcements)
