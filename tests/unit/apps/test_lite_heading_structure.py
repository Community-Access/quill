"""QuillLite can rearrange headings, not only make them and walk between them.

Reorganising a document was, until 2026-09-09, cut-and-paste only -- and that is
the operation cut-and-paste is worst at. Moving a section by hand means
selecting from one heading to exactly the start of the next: a boundary that is
invisible, that has to be found by ear, and that takes your place in the
document with it when you get it wrong.

Both mechanisms are covered here because "make this heading one level shallower"
is one idea to the person doing it and two implementations underneath -- the
rich-text ladder (bold plus a point size) and Markdown's hashes -- and a command
that worked in one mode and silently did nothing in the other would be worse
than not having it.
"""

from __future__ import annotations

from quill.apps.lite_window_format import DocumentFormatCommandsMixin
from quill.apps.lite_window_headings import DocumentHeadingsMixin
from quill.apps.lite_window_markup import DocumentMarkupMixin
from quill.ui.richedit_editing import PLAIN, RICH


class _Control:
    def __init__(self, text: str, cursor: int = 0) -> None:
        self._text = text
        self._cursor = cursor
        self.shown = -1

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._cursor

    def SetInsertionPoint(self, position: int) -> None:
        self._cursor = position

    def GetLastPosition(self) -> int:
        return len(self._text)

    def ShowPosition(self, position: int) -> None:
        self.shown = position

    def Replace(self, start: int, end: int, text: str) -> None:
        self._text = self._text[:start] + text + self._text[end:]


class _Editor:
    """The rich surface, reduced to the heading ladder."""

    def __init__(self, mode: str, level: int = 0) -> None:
        self.mode = mode
        self._level = level
        self.applied: list[int] = []

    def heading_level_at_caret(self) -> int:
        return self._level

    def set_heading(self, level: int) -> None:
        self.applied.append(level)
        self._level = level


class _Settings:
    announce_headings = True
    announce_lists = True
    heading_announce_position = "before"


class _App:
    settings = _Settings()

    def save_settings(self) -> None:
        pass


class _Window(DocumentFormatCommandsMixin, DocumentHeadingsMixin, DocumentMarkupMixin):
    def __init__(self, text: str, cursor: int = 0, *, mode: str = PLAIN, level: int = 0) -> None:
        self.control = _Control(text, cursor)
        self.editor = _Editor(mode, level)
        self.announcements: list[str] = []
        self.modified = False
        # A Markdown document, which is what a heading-structure test is about.
        # The mixin reads the name; there is no file, so it is said outright.
        self._language_override = "markdown"
        self.app = _App()

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _set_modified(self, value: bool) -> None:
        self.modified = value

    def _touch_status(self) -> None:
        pass

    def _require_rich(self) -> bool:
        return self.editor.mode == RICH


# --------------------------------------------------------------------------- #
# Plain text: Markdown hashes
# --------------------------------------------------------------------------- #


def test_promoting_in_plain_text_edits_the_hashes_and_says_the_new_level() -> None:
    win = _Window("## Installing\nbody\n", cursor=5)

    win.cmd_promote_heading()

    assert win.control.GetValue() == "# Installing\nbody\n"
    assert win.announcements == ["Heading 1"]
    assert win.modified is True


def test_demoting_in_plain_text_goes_the_other_way() -> None:
    win = _Window("## Installing\n", cursor=5)

    win.cmd_demote_heading()

    assert win.control.GetValue() == "### Installing\n"
    assert win.announcements == ["Heading 3"]


def test_the_caret_keeps_its_place_in_the_line_as_the_line_changes_length() -> None:
    """The line just grew or shrank by a hash in front of the caret."""
    win = _Window("## Installing\n", cursor=len("## Inst"))

    win.cmd_promote_heading()

    # Still just after "Inst", which is now one character earlier.
    assert win.control.GetValue()[: win.control.GetInsertionPoint()] == "# Inst"


def test_off_a_heading_it_says_why_rather_than_nothing() -> None:
    """Silence is indistinguishable by ear from a key that is not bound."""
    win = _Window("just a paragraph\n", cursor=4)

    win.cmd_promote_heading()

    assert win.announcements == ["Put the cursor on a heading line to change its level"]
    assert win.modified is False


def test_the_two_ends_of_the_ladder_are_named_separately() -> None:
    top = _Window("# Title\n", cursor=3)
    top.cmd_promote_heading()
    assert top.announcements == ["Already Heading 1"]

    bottom = _Window("###### Deep\n", cursor=8)
    bottom.cmd_demote_heading()
    assert bottom.announcements == ["Already Heading 6"]


# --------------------------------------------------------------------------- #
# Rich text: the point-size ladder
# --------------------------------------------------------------------------- #


def test_promoting_in_rich_text_moves_along_the_point_size_ladder() -> None:
    win = _Window("Installing", mode=RICH, level=3)

    win.cmd_promote_heading()

    assert win.editor.applied == [2]
    assert win.announcements == ["Heading 2"]


def test_promoting_a_heading_one_does_not_turn_it_into_body_text() -> None:
    """Losing the heading is not what Alt+Shift+Left means.

    It would also quietly drop the paragraph out of the headings list, which is
    how a listener finds anything in a long document.
    """
    win = _Window("Title", mode=RICH, level=1)

    win.cmd_promote_heading()

    assert win.editor.applied == []
    assert win.announcements == ["Already Heading 1"]


def test_rich_text_stops_at_the_bottom_of_its_own_ladder() -> None:
    """Six levels in rich text as well as in Markdown, since 2026-09-09.

    Five and six existed in the ladder and shared the 11-point body size, so the
    editor could set them and then could not read them back: heading navigation
    walked past a Heading 5 as if it were an ordinary paragraph. They have sizes
    of their own now (11.5 and 10.5), which is what made it honest to offer them
    in Format > Headings.
    """
    win = _Window("Deep", mode=RICH, level=6)

    win.cmd_demote_heading()

    assert win.editor.applied == []
    assert win.announcements == ["Already at the smallest heading"]


def test_outside_a_heading_in_rich_text_says_so() -> None:
    win = _Window("body", mode=RICH, level=0)

    win.cmd_promote_heading()

    assert win.announcements == ["Put the cursor in a heading to change its level"]


# --------------------------------------------------------------------------- #
# Section move
# --------------------------------------------------------------------------- #


def test_moving_a_section_up_takes_its_body_with_it() -> None:
    text = "# One\nfirst body\n\n# Two\nsecond body\n"
    win = _Window(text, cursor=text.index("# Two") + 2)

    win.cmd_move_section_up()

    assert win.control.GetValue().index("# Two") < win.control.GetValue().index("# One")
    assert "second body" in win.control.GetValue()
    assert win.modified is True
    assert win.announcements, "a move that makes no sound is a move nobody can confirm"


def test_moving_a_section_down_is_the_mirror_of_moving_the_next_one_up() -> None:
    text = "# One\nfirst\n\n# Two\nsecond\n"
    win = _Window(text, cursor=2)

    win.cmd_move_section_down()

    moved = win.control.GetValue()
    assert moved.index("# Two") < moved.index("# One")


def test_the_top_section_refuses_and_says_so() -> None:
    text = "# One\nbody\n\n# Two\nbody\n"
    win = _Window(text, cursor=2)

    win.cmd_move_section_up()

    assert win.control.GetValue() == text
    assert win.announcements, "the refusal has to be spoken; nothing else marks it"


def test_rich_text_is_told_the_operation_belongs_to_plain_documents() -> None:
    """A rich heading is a font size; there is nothing in the text to move.

    Saying so beats a key that quietly does nothing in half the documents
    somebody opens.
    """
    win = _Window("Installing", mode=RICH, level=1)

    win.cmd_move_section_up()

    assert win.announcements == [
        "Moving sections works in plain text documents, where headings are Markdown"
    ]
    assert win.modified is False
