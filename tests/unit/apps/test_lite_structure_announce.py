"""QUILL Lite says "Heading 2" because nothing else in the stack can.

The wiring, not the rules -- the rules are tested in
``tests/unit/core/test_structure_announce.py``. What matters here is that the
caret hook feeds the latch, that an edit does not masquerade as an arrival, that
the formatting commands do not get echoed a second time, and that QUILL Lite
never mentions a table.
"""

from __future__ import annotations

import pathlib

from quill.apps.lite_window_headings import DocumentHeadingsMixin
from quill.apps.lite_window_markup import DocumentMarkupMixin
from quill.core.document_text import DocumentText
from quill.ui.richedit_editing import PLAIN, RICH

DOC = "# Title\n\nbody line\n\n## Section\n\n| a | b |\n| --- | --- |\n| c | d |\n"


class _Control:
    """A text control, and the mirror the window keeps beside it.

    ``SetValue`` invalidates the mirror because the real control raises
    ``EVT_TEXT`` and the real window's hook does exactly that. A stub that set
    the text and left the mirror alone would be testing a window that cannot
    exist -- and would hide the one failure mode a mirror has, which is
    answering a question about the new document with the old one's text.
    """

    def __init__(self, text: str, caret: int = 0) -> None:
        self._text = text
        self._caret = caret
        self.doc_text = DocumentText(self.GetValue)

    def GetValue(self) -> str:  # noqa: N802 - wx spelling
        return self._text

    def SetValue(self, text: str) -> None:  # noqa: N802 - wx spelling
        self._text = text
        self.doc_text.invalidate()

    def GetInsertionPoint(self) -> int:  # noqa: N802 - wx spelling
        return self._caret

    def SetInsertionPoint(self, caret: int) -> None:  # noqa: N802 - wx spelling
        self._caret = caret


class _Editor:
    def __init__(self, mode: str = PLAIN, level: int = 0) -> None:
        self.mode = mode
        self._level = level

    def heading_level_at_caret(self) -> int:
        return self._level


class _Settings:
    announce_headings = True
    announce_lists = True
    # "after" keeps the tests above reading as they did -- the level alone,
    # queued behind the reader. The shipped default is "before", and it has a
    # class of its own at the bottom of this file where the composed sentence is
    # what is being tested.
    heading_announce_position = "after"


class _App:
    def __init__(self) -> None:
        self.settings = _Settings()
        self.saved = 0

    def save_settings(self) -> None:
        self.saved += 1


class _Window(DocumentHeadingsMixin, DocumentMarkupMixin):
    def __init__(
        self, text: str = DOC, caret: int = 0, *, mode: str = PLAIN, name: str | None = "notes.md"
    ) -> None:
        self.control = _Control(text, caret)
        self.doc_text = self.control.doc_text
        self.editor = _Editor(mode)
        self.app = _App()
        self.path = pathlib.Path(name) if name else None
        self.announcements: list[str] = []
        self.interrupted: list[bool] = []
        self.status_touches = 0

    def _touch_status(self) -> None:
        self.status_touches += 1

    def _set_modified(self, _flag: bool) -> None:
        pass

    def _announce(self, message: str, *, interrupt: bool = True) -> None:
        # Recorded, because the heading cue must never interrupt: the reader
        # is mid-line when it fires.
        self.announcements.append(message)
        self.interrupted.append(interrupt)

    def at(self, needle: str) -> None:
        offset = self.control.GetValue().find(needle)
        assert offset >= 0, needle
        self.control.SetInsertionPoint(offset)
        self.announce_structure_at_caret()


def test_arriving_at_a_heading_says_the_level() -> None:
    win = _Window()
    win.at("body line")
    win.at("Section")
    assert win.announcements == ["Heading 2"]


def test_the_text_of_the_heading_is_never_repeated() -> None:
    # In "after" mode the screen reader is already reading the line, so saying
    # it again here is the double-speaking GATE-13 exists to catch. "Before"
    # mode carries the text *instead of* the reader's reading, not on top of it,
    # which is why it interrupts -- see TestWhereTheLevelGoes.
    win = _Window()
    win.at("body line")
    win.at("Section")
    assert "Section" not in win.announcements[0]


def test_moving_inside_a_heading_stays_quiet() -> None:
    win = _Window()
    win.at("body line")
    win.at("Section")
    win.control.SetInsertionPoint(win.control.GetInsertionPoint() + 3)
    win.announce_structure_at_caret()
    assert win.announcements == ["Heading 2"]


def test_body_text_says_nothing_at_all() -> None:
    win = _Window()
    win.at("Title")
    win.at("body line")
    assert win.announcements == []


def test_an_edit_that_shifts_the_lines_is_not_an_arrival() -> None:
    """Deleting a line above a heading must not announce the heading.

    The paragraph key is a line index, so a deletion above the caret changes it
    without the caret going anywhere. Announcing there would interrupt typing
    with "Heading 2" -- the exact over-announcement that makes an app feel
    chatty and gets absorbed rather than filed.
    """
    win = _Window()
    win.at("body line")
    win.at("Section")
    win.announcements.clear()
    win.control.SetValue(DOC.replace("body line\n", ""))
    win.control.SetInsertionPoint(win.control.GetValue().find("Section"))
    win.announce_structure_at_caret()
    assert win.announcements == []


def test_rich_mode_reads_the_level_off_the_control() -> None:
    # Rich headings are a point-size ladder, not hashes; the level comes from
    # the Text Object Model so it cannot disagree with the status bar.
    win = _Window("plain paragraph\nanother paragraph\n", mode=RICH)
    win.editor._level = 0
    win.at("plain")
    win.editor._level = 3
    win.at("another")
    assert win.announcements == ["Heading 3"]


def test_a_failing_text_object_model_falls_back_to_silence_not_a_crash() -> None:
    class _Broken(_Editor):
        def heading_level_at_caret(self) -> int:
            raise RuntimeError("no TOM here")

    win = _Window("one\ntwo\n", mode=RICH)
    win.editor = _Broken(RICH)
    win.at("one")
    win.at("two")
    assert win.announcements == []


def test_quilllite_never_announces_a_table() -> None:
    # Accessible table navigation is a full-QUILL feature. Announcing the edge
    # of a grid the small editor cannot navigate advertises what is not there.
    win = _Window()
    win.at("Section")
    win.at("| a | b |")
    win.at("| c | d |")
    assert all("Table" not in said for said in win.announcements)


def test_a_reset_makes_the_next_position_silent() -> None:
    win = _Window()
    win.at("body line")
    win.reset_structure_announcer()
    win.at("Section")
    assert win.announcements == []


def test_sync_stops_a_command_from_being_echoed() -> None:
    win = _Window()
    win.at("body line")
    win.control.SetInsertionPoint(win.control.GetValue().find("Section"))
    win.sync_structure_announcer()  # what cmd_heading_2 does after announcing
    win.announce_structure_at_caret()
    assert win.announcements == []


# --------------------------------------------------------------------------- #
# Heading navigation in a plain-text document
# --------------------------------------------------------------------------- #

MARKDOWN = "# One\nbody\n## Two\nmore\n### Three\n"


class _NavWindow(_Window):
    """Adds the two things heading navigation needs from the frame."""

    def __init__(self, text: str = MARKDOWN, caret: int = 0) -> None:
        super().__init__(text, caret, mode=PLAIN)
        self.jumps: list[int] = []

    def _go_to(self, position: int) -> None:
        self.jumps.append(position)
        self.control.SetInsertionPoint(position)


def test_next_heading_finds_a_markdown_heading_in_plain_text() -> None:
    # It used to refuse outright -- "Headings are only available in rich text"
    # -- in a document whose headings Alt+Shift+Right would happily re-level.
    win = _NavWindow(caret=0)
    win.cmd_next_heading()
    assert win.control.GetInsertionPoint() == MARKDOWN.find("## Two")
    assert win.announcements[-1] == "Heading 2: Two"


def test_previous_heading_goes_back() -> None:
    win = _NavWindow(caret=MARKDOWN.find("### Three"))
    win.cmd_previous_heading()
    assert win.control.GetInsertionPoint() == MARKDOWN.find("## Two")


def test_running_out_says_which_way_you_were_going() -> None:
    win = _NavWindow(caret=len(MARKDOWN))
    win.cmd_next_heading()
    assert win.announcements[-1] == "No next heading"
    win.cmd_previous_heading()
    assert win.announcements[-1] == "Heading 3: Three"


def test_a_hash_inside_a_fenced_code_block_is_not_a_heading() -> None:
    # A shell comment in a code sample is the classic false positive, and the
    # reason this parses through markdown_sections rather than a regex.
    text = "intro\n\n```sh\n# not a heading\n```\n\n## Real\n"
    win = _NavWindow(text, caret=0)
    win.cmd_next_heading()
    assert win.control.GetInsertionPoint() == text.find("## Real")


def test_the_headings_list_offers_the_plain_documents_headings() -> None:
    win = _NavWindow(caret=0)
    assert [level for _start, level, _title in win._plain_headings()] == [1, 2, 3]


def test_navigation_latches_the_announcer_so_arrival_is_not_said_twice() -> None:
    win = _NavWindow(caret=0)
    win.cmd_next_heading()
    win.announcements.clear()
    win.announce_structure_at_caret()
    assert win.announcements == []


def test_the_heading_cue_never_interrupts_the_reader() -> None:
    """The one thing that would make this feature worse than silence.

    The cue fires as the screen reader is reading the line the caret landed on.
    QUILL Lite's announcements interrupt by default -- which is right for the
    outcome of a command and exactly wrong here, because interrupting would
    take away the text the user moved there to hear.
    """
    win = _Window()
    win.at("body line")
    win.at("Section")
    assert win.announcements == ["Heading 2"]
    assert win.interrupted == [False]


def _status_frame(text: str, caret: int, surface: str | None):
    """A status mixin over a document of a given markup language.

    The language is not the mode: a Markdown document and a plain text one are
    both ``PLAIN`` to the control, and only one of them has headings.
    """
    from quill.apps.lite_window_status import DocumentStatusMixin

    class _Frame(DocumentStatusMixin):
        def __init__(self) -> None:
            self.control = _Control(text, caret)
            self.editor = _Editor(PLAIN)

        def markup_surface(self):
            return surface

    return _Frame()


def test_the_status_bar_heading_cell_reads_a_markdown_documents_headings() -> None:
    """The cell used to read "Not in rich text" in a Markdown document.

    Wrong twice over: those documents have real headings, and pressing Enter on
    the cell has always opened a list of them.
    """
    frame = _status_frame(MARKDOWN, MARKDOWN.find("## Two"), "markdown")
    assert frame._heading_text(MARKDOWN) == "Heading 2"
    frame.control.SetInsertionPoint(MARKDOWN.find("body"))
    assert frame._heading_text(MARKDOWN) == "Body text"


def test_a_plain_document_has_no_headings_however_the_line_starts() -> None:
    """Reported: the editor was "misleading about markdown ... in plain text we
    are not writing markdown, just plain text".

    ``heading_level_at`` defaults to reading Markdown and the cell did not say
    otherwise, so a plain document whose line begins with two hashes announced
    "Heading 2" -- when the hashes are the text. A plain document has no
    headings at all, and the cell says so.
    """
    frame = _status_frame(MARKDOWN, MARKDOWN.find("## Two"), None)
    assert frame._heading_text(MARKDOWN) == "Body text"


# --------------------------------------------------------------------------- #
# The toggle, and the documents where a "#" is not a heading
# --------------------------------------------------------------------------- #


def test_the_toggle_silences_the_cue_and_says_the_consequence() -> None:
    win = _Window()
    win.at("body line")
    win.cmd_toggle_heading_announcements()
    assert win.announcements[-1] == "Headings will not be announced"
    win.announcements.clear()
    win.at("Section")
    assert win.announcements == []


def test_toggling_back_on_says_so_and_resumes() -> None:
    win = _Window()
    win.cmd_toggle_heading_announcements()
    win.at("body line")
    win.announcements.clear()
    win.cmd_toggle_heading_announcements()
    assert win.announcements == ["Headings announced on arrival"]
    win.announcements.clear()
    win.at("Section")
    assert win.announcements == ["Heading 2"]


def test_the_toggle_is_persisted() -> None:
    win = _Window()
    win.cmd_toggle_heading_announcements()
    assert win.app.settings.announce_headings is False
    assert win.app.saved == 1


def test_switching_off_still_feeds_the_latch() -> None:
    """Off must not mean blind.

    If the latch stopped being fed, switching the cue back on inside a heading
    would say nothing until you left it and returned -- which reads as the
    toggle not having worked.
    """
    win = _Window()
    win.at("body line")
    win.cmd_toggle_heading_announcements()
    win.at("Section")  # arrives on the heading while off
    win.announcements.clear()
    win.cmd_toggle_heading_announcements()
    win.announcements.clear()
    win.announce_structure_at_caret()  # still in the same heading
    assert win.announcements == []


def test_a_hash_in_a_shell_script_is_a_comment_not_a_heading() -> None:
    """QUILL Lite is a Notepad replacement, so this is the common case.

    A ``.sh``, ``.py``, ``.ini`` or ``.conf`` uses ``#`` for comments. Reading
    those as headings would announce "Heading 1" on most lines of a build
    script and fill the headings list with comments.
    """
    script = "#!/bin/sh\nset -e\n# build the thing\nmake all\n"
    win = _Window(script, name="build.sh")
    win.at("set -e")
    win.at("# build the thing")
    assert win.announcements == []
    assert win._plain_headings() == []


def test_a_markdown_file_still_has_headings() -> None:
    win = _Window(MARKDOWN, name="notes.md")
    win.at("body")
    win.at("## Two")
    assert win.announcements == ["Heading 2"]


def test_a_plain_txt_file_has_no_headings() -> None:
    """Plain text stays plain, and that is the rule for `.txt` too.

    It used to count as Markdown, on the argument that a plain text file is
    where somebody writes prose with `#` headings. True of some `.txt` files and
    false of most -- and the cost of being wrong lands on every line of the ones
    it is wrong about. Ctrl+Shift+M says otherwise in one keystroke.
    """
    win = _Window("# Heading\n\nbody\n", name="notes.txt")
    win.at("body")
    win.at("Heading")
    assert win.announcements == []
    assert win._plain_headings() == []


def test_an_untitled_buffer_has_no_headings_either() -> None:
    win = _Window("# Heading\n\nbody\n", name=None)
    win.at("body")
    win.at("Heading")
    assert win.announcements == []


def test_a_txt_file_told_it_is_markdown_gets_its_headings_back() -> None:
    """Nothing is lost by the rule -- only guessed-at behaviour is."""
    win = _Window("# Heading\n\nbody\n", name="notes.txt")
    win.set_document_language("markdown", announce=False)
    win.at("body")
    win.at("Heading")
    # The level alone, because this file's stub asks for "after" ordering; the
    # shipped default composes the sentence (see TestWhereTheLevelGoes).
    assert win.announcements == ["Heading 1"]


def test_rich_text_is_unaffected_by_the_file_name() -> None:
    # The rich ladder is not "#" at all, so a .py opened as rich text (it
    # cannot be, but the guard must not depend on that) still reads its levels.
    win = _Window("one\ntwo\n", mode=RICH, name="build.py")
    win.editor._level = 0
    win.at("one")
    win.editor._level = 2
    win.at("two")
    assert win.announcements == ["Heading 2"]


class TestWhereTheLevelGoes:
    """The level before the heading's words, or after them -- and why it matters.

    Not a matter of taste. A cue *queued behind* the reader is at the reader's
    mercy: on a large caret jump NVDA and JAWS cancel whatever is pending and
    start again on the new line, so the level waiting its turn is never heard.
    Reported exactly that way -- arrowing onto a heading announced it, Ctrl+Home
    onto the same heading did not.
    """

    @staticmethod
    def _win(position: str) -> _Window:
        win = _Window()
        win.app.settings.heading_announce_position = position
        return win

    def test_before_is_one_sentence_of_quilllites_own(self) -> None:
        win = self._win("before")
        win.at("body line")
        win.at("Section")
        assert win.announcements == ["Heading 2, Section"]

    def test_before_interrupts_because_it_carries_the_words_with_it(self) -> None:
        # Safe precisely because the text the reader was about to say is inside
        # the phrase replacing it.
        win = self._win("before")
        win.at("body line")
        win.at("Section")
        assert win.interrupted == [True]

    def test_after_is_the_level_alone_and_waits_its_turn(self) -> None:
        win = self._win("after")
        win.at("body line")
        win.at("Section")
        assert win.announcements == ["Heading 2"]
        assert win.interrupted == [False]

    def test_jumping_to_the_top_of_the_document_still_announces(self) -> None:
        win = self._win("before")
        win.at("Section")
        win.announcements.clear()
        win.control.SetInsertionPoint(0)
        win.announce_structure_at_caret()
        assert win.announcements == ["Heading 1, Title"]

    def test_a_settings_object_that_predates_the_field_leads_with_the_level(self) -> None:
        # The behaviour that works on every kind of move, not the lossy one.
        class _Old:
            announce_headings = True
            announce_lists = True

        win = _Window()
        win.app.settings = _Old()
        win.at("body line")
        win.at("Section")
        assert win.announcements == ["Heading 2, Section"]

    def test_an_html_heading_loses_its_tags_on_the_way_into_the_sentence(self) -> None:
        win = _Window("<p>body</p>\n<h3>Installing</h3>\n", name="page.html")
        win.app.settings.heading_announce_position = "before"
        win.at("body")
        win.at("Installing")
        assert win.announcements == ["Heading 3, Installing"]
