"""QUILL Lite can rearrange headings, not only make them and walk between them.

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

import pytest

from quill.apps.lite_window_format import DocumentFormatCommandsMixin
from quill.apps.lite_window_headings import DocumentHeadingsMixin
from quill.apps.lite_window_markup import DocumentMarkupMixin
from quill.apps.lite_window_sections import DocumentSectionCommandsMixin
from quill.ui.richedit_editing import PLAIN, RICH


class _Control:
    def __init__(self, text: str, cursor: int = 0) -> None:
        self._text = text
        self._cursor = cursor
        self.shown = -1
        self.selection = (-1, -1)

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

    def SetSelection(self, start: int, end: int) -> None:
        self.selection = (start, end)

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


class _Window(
    DocumentFormatCommandsMixin,
    DocumentSectionCommandsMixin,
    DocumentHeadingsMixin,
    DocumentMarkupMixin,
):
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


def test_selecting_a_section_takes_the_subsections_and_says_how_much() -> None:
    """The move keys reorder; this one hands the section to the clipboard, which
    is how it reaches a place with no heading to move past. The count is the
    point: the reader says a selection changed, not how much is in it."""
    text = "# Top\n\ntop\n\n## Bread\n\nbread\n\n### Sourdough\n\nsour\n\n## Soup\n\nsoup\n"
    win = _Window(text, cursor=text.index("## Bread"))

    win.cmd_select_section()

    start, end = win.control.selection
    assert text[start:end] == "## Bread\n\nbread\n\n### Sourdough\n\nsour"
    assert win.announcements == ["Selected Bread and 1 section under it, 7 lines"]
    assert win.modified is False, "selecting is not an edit"


def test_selecting_in_a_document_with_no_markup_says_so() -> None:
    win = _Window("just prose\n", cursor=0)
    win._language_override = "plain"

    win.cmd_select_section()

    assert win.announcements, "a refusal nobody can hear is a key that seems unbound"
    assert win.control.selection == (-1, -1)


def test_the_nested_outline_moves_up_and_says_why_it_cannot_move_down() -> None:
    """The reported bug, from QUILL Lite's side: a document whose headings step
    # / ## / ### has no siblings anywhere, so every Alt+Shift+Up and every
    Alt+Shift+Down answered "No sibling to swap with" and moved nothing.

    Up now moves -- Heading 2 rises above Heading 1's own heading and body,
    taking Heading 3 with it. Down still cannot, and that is the document
    rather than the key: everything below Heading 2 *is* Heading 2.
    """
    text = (
        "# Heading 1\n\nfirst body\n\n## Heading 2\n\nsecond body\n\n### Heading 3\n\nthird body\n"
    )
    win = _Window(text, cursor=text.index("## Heading 2"))

    win.cmd_move_section_up()

    assert win.control.GetValue() == (
        "## Heading 2\n\nsecond body\n\n### Heading 3\n\nthird body\n\n# Heading 1\n\nfirst body\n"
    )
    assert win.announcements == ["Section moved above Heading 1"]
    assert win.modified is True


def test_a_section_that_contains_everything_below_it_says_so() -> None:
    text = (
        "# Heading 1\n\nfirst body\n\n## Heading 2\n\nsecond body\n\n### Heading 3\n\nthird body\n"
    )
    win = _Window(text, cursor=text.index("## Heading 2"))

    win.cmd_move_section_down()

    assert win.control.GetValue() == text
    assert win.announcements == [
        "Bottom of Heading 1. Everything below is inside this section. "
        "Alt Shift Left promotes Heading 3 to make it a sibling."
    ]
    assert win.modified is False


def test_a_move_that_happens_says_that_it_happened() -> None:
    """QUILL Lite used to say the bare heading name, which sounds like the caret
    landed on something rather than like the document changed. The sentence is
    composed in core now, so both editors say the one thing -- including where
    the section has landed, which the reader never says."""
    text = "# One\nfirst\n\n# Two\nsecond\n"
    win = _Window(text, cursor=2)

    win.cmd_move_section_down()

    assert win.announcements == ["Section moved below Two. Now 2 of 2 at this level"]


def test_rich_text_is_told_the_operation_belongs_to_plain_documents() -> None:
    """A rich heading is a font size; there is nothing in the text to move.

    Saying so beats a key that quietly does nothing in half the documents
    somebody opens.
    """
    win = _Window("Installing", mode=RICH, level=1)

    win.cmd_move_section_up()

    assert win.announcements == [
        "Moving a section needs a Markdown or HTML document: a rich-text "
        "heading is a font size rather than markup."
    ]
    assert win.modified is False


# --------------------------------------------------------------------------- #
# Move Section To: a destination instead of a direction
# --------------------------------------------------------------------------- #

_OUTLINE = "# Top\n\ntop\n\n## Bread\n\nbread\n\n### Sourdough\n\nsour\n\n## Soup\n\nsoup\n"


def _answer_pickers(monkeypatch, *answers: str | None) -> list[list[str]]:
    """Make QUILL Lite's searchable chooser answer *answers*, in order.

    Patched where it is **defined** rather than where it is used, because
    ``cmd_move_section_to`` imports it inside the method -- so the name is
    looked up at call time and the definition site is the one that counts. The
    rows it was offered come back, because what a row says is half of this
    command: "3 of 7, level 2 - Bread" is what makes two headings called Notes
    two distinguishable choices.
    """
    offered: list[list[str]] = []
    pending = list(answers)

    def choose(_parent, *, choices, **_kwargs):
        rows = list(choices)
        offered.append(rows)
        wanted = pending.pop(0)
        if wanted is None:
            return None
        return next(row for row in rows if wanted in row)

    monkeypatch.setattr("quill.apps.lite_dialogs.choose_searchable", choose)
    return offered


def test_moving_a_section_to_a_chosen_heading(monkeypatch) -> None:
    win = _Window(_OUTLINE, cursor=_OUTLINE.index("## Soup"))
    _answer_pickers(monkeypatch, "Bread", "Before it")

    win.cmd_move_section_to()

    moved = win.control.GetValue()
    assert moved.index("## Soup") < moved.index("## Bread")
    assert win.announcements == ["Moved Soup before Bread. Now 1 of 2 at this level"]
    assert win.modified is True


def test_the_destination_list_is_the_outline_in_document_order(monkeypatch) -> None:
    win = _Window(_OUTLINE, cursor=_OUTLINE.index("## Soup"))
    offered = _answer_pickers(monkeypatch, "Bread", "After it")

    win.cmd_move_section_to()

    assert offered[0] == [
        "1 of 4, level 1 - Top",
        "2 of 4, level 2 - Bread",
        "3 of 4, level 3 - Sourdough",
        "4 of 4, level 2 - Soup (the section you are moving)",
    ]


def test_after_puts_it_past_the_whole_chosen_subtree(monkeypatch) -> None:
    win = _Window(_OUTLINE, cursor=_OUTLINE.index("## Soup"))
    _answer_pickers(monkeypatch, "level 2 - Bread", "After it")

    win.cmd_move_section_to()

    moved = win.control.GetValue()
    assert moved.index("### Sourdough") < moved.index("## Soup")


def test_inside_changes_the_level_and_says_so(monkeypatch) -> None:
    """The one placement that edits more than the order, so it is the one that
    has to be announced: a renumbering nobody is told about is a silent edit."""
    win = _Window(_OUTLINE, cursor=_OUTLINE.index("## Soup"))
    _answer_pickers(monkeypatch, "level 2 - Bread", "Inside it")

    win.cmd_move_section_to()

    assert "### Soup" in win.control.GetValue()
    assert "now Heading 3" in win.announcements[0]


@pytest.mark.parametrize(
    "answers",
    [(None,), ("level 2 - Bread", None)],
    ids=["backed out of the heading", "backed out of the placement"],
)
def test_cancelling_either_question_changes_nothing_and_says_nothing(monkeypatch, answers) -> None:
    win = _Window(_OUTLINE, cursor=_OUTLINE.index("## Soup"))
    _answer_pickers(monkeypatch, *answers)

    win.cmd_move_section_to()

    assert win.control.GetValue() == _OUTLINE
    assert win.announcements == [], "Escape changed nothing, so there is nothing to say"
    assert win.modified is False


def test_a_destination_inside_the_moving_section_is_refused_out_loud(monkeypatch) -> None:
    win = _Window(_OUTLINE, cursor=_OUTLINE.index("## Bread"))
    _answer_pickers(monkeypatch, "Sourdough", "Inside it")

    win.cmd_move_section_to()

    assert win.control.GetValue() == _OUTLINE
    assert "Sourdough is inside Bread" in win.announcements[0]
    assert "Promote Sourdough" in win.announcements[0]


def test_move_section_to_in_a_rich_document_says_where_it_works(monkeypatch) -> None:
    win = _Window(_OUTLINE, cursor=0, mode=RICH)
    _answer_pickers(monkeypatch)

    win.cmd_move_section_to()

    assert win.control.GetValue() == _OUTLINE
    assert "needs a Markdown or HTML document" in win.announcements[0]


def test_move_section_to_in_a_document_with_no_markup_says_so(monkeypatch) -> None:
    win = _Window("just prose\n", cursor=0)
    win._language_override = "plain"
    _answer_pickers(monkeypatch)

    win.cmd_move_section_to()

    assert win.announcements, "a refusal nobody can hear is a key that seems unbound"


def test_move_section_to_needs_somewhere_to_move_to(monkeypatch) -> None:
    win = _Window("# Only\n\nbody\n", cursor=0)
    _answer_pickers(monkeypatch)

    win.cmd_move_section_to()

    assert win.control.GetValue() == "# Only\n\nbody\n"
    assert "only one section" in win.announcements[0]
