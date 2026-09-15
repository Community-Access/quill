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
from quill.apps.lite_window_history import DocumentHistoryMixin
from quill.core.locations import LocationRing
from quill.core.settings import Settings
from quill.ui.richedit_editing import PLAIN


class _Voice:
    def __init__(self) -> None:
        self.said: list[str] = []

    def speak(self, message: str) -> None:
        self.said.append(message)


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

    def GetInsertionPoint(self) -> int:
        return self.selection[0]

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


class _Window(DocumentCommandsMixin, DocumentHistoryMixin):
    """Only the parts of the document window the search path touches."""

    def __init__(self, text: str) -> None:
        self.control = _Control(text)
        self.announcements: list[str] = []
        self._find_options: dict[str, object] = {}
        # A search hit is a jump, and every jump feeds the location ring so
        # Alt+Left can take it back.
        self.locations = LocationRing()
        self.modified = False
        # Plain text: Replace All only asks for confirmation in rich mode,
        # where a replacement takes the formatting of where it lands.
        self.editor = SimpleNamespace(mode=PLAIN)
        # Real Settings, because the search path reads two of them now:
        # ``wrap_find`` decides whether Find Next carries on from the other end,
        # and ``find_not_found_feedback`` decides whether a miss is a tone, words,
        # both or neither. Both default the way the shipped app defaults.
        self.app = SimpleNamespace(settings=Settings(), voice=_Voice())
        self.cues: list[str] = []

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _cue(self, event: str) -> None:
        self.cues.append(str(event))

    def _has_sound_for(self, _event: str) -> bool:
        """The pack has a clip for every event these tests care about."""
        return True

    def _set_status_message(self, message: str) -> None:
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


def test_count_occurrences_with_nothing_searched_yet_opens_find() -> None:
    """It asks for the thing it needs rather than refusing.

    It used to say "Search for something first, then count it", which is a
    correct sentence and a dead end: the answer was to press a different key,
    and the user had to know which. Opening Find *is* the next step. The row is
    never greyed out instead, because a disabled menu item keeps advertising its
    key and stops dispatching it -- so the key would go from saying something
    unhelpful to doing nothing at all.
    """
    win = _Window("cat")
    opened: list[bool] = []
    win.cmd_find = lambda: opened.append(True)  # type: ignore[method-assign]
    win.cmd_count_occurrences()
    assert opened == [True]
    assert win.announcements == []


def test_find_all_with_nothing_searched_yet_opens_find() -> None:
    win = _Window("cat")
    opened: list[bool] = []
    win.cmd_find = lambda: opened.append(True)  # type: ignore[method-assign]
    win.cmd_find_all()
    assert opened == [True]
    assert win.announcements == []


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


def test_replace_all_is_one_edit_in_plain_text() -> None:
    """One Ctrl+Z puts the whole Replace All back, as it does in QUILL.

    It used to be one control.Replace per match, so undoing two hundred
    replacements took two hundred presses -- which for a listener is
    indistinguishable from an undo that does not work. The count of edits is the
    test, because the undo stack itself belongs to the native control.
    """
    win = _Window("one 1 two 2 three 3 four 4")
    edits: list[tuple[int, int, str]] = []
    real_replace = win.control.Replace

    def _record(start: int, end: int, text: str) -> None:
        edits.append((start, end, text))
        real_replace(start, end, text)

    win.control.Replace = _record  # type: ignore[method-assign]
    win._do_replace_all(_options(r"\d", mode="regex", replacement="#"))  # noqa: SLF001

    assert len(edits) == 1, f"one edit, not one per match; got {len(edits)}"
    assert edits[0][0] == 0, "the single edit covers the document"
    assert win.control.GetValue() == "one # two # three # four #"
    assert any("Replaced 4" in message for message in win.announcements)


def test_replace_all_still_reports_nothing_when_nothing_matched() -> None:
    win = _Window("alpha bravo")
    win._do_replace_all(_options("zulu", replacement="x"))  # noqa: SLF001
    assert win.control.GetValue() == "alpha bravo"
    assert any("Replaced 0" in message for message in win.announcements)


def test_replace_all_honours_the_mode() -> None:
    win = _Window("a1b22c")
    win._do_replace_all(_options(r"\d+", mode="regex", replacement="#"))  # noqa: SLF001
    assert win.control.GetValue() == "a#b#c"
    assert any("Replaced 2" in message for message in win.announcements)
