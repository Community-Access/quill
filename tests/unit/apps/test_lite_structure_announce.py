"""QuillLite says "Heading 2" because nothing else in the stack can.

The wiring, not the rules -- the rules are tested in
``tests/unit/core/test_structure_announce.py``. What matters here is that the
caret hook feeds the latch, that an edit does not masquerade as an arrival, that
the formatting commands do not get echoed a second time, and that QuillLite
never mentions a table.
"""

from __future__ import annotations

import pathlib

from quill.apps.lite_window_headings import DocumentHeadingsMixin
from quill.ui.richedit_editing import PLAIN, RICH

DOC = "# Title\n\nbody line\n\n## Section\n\n| a | b |\n| --- | --- |\n| c | d |\n"


class _Control:
    def __init__(self, text: str, caret: int = 0) -> None:
        self._text = text
        self._caret = caret

    def GetValue(self) -> str:  # noqa: N802 - wx spelling
        return self._text

    def SetValue(self, text: str) -> None:  # noqa: N802 - wx spelling
        self._text = text

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


class _App:
    def __init__(self) -> None:
        self.settings = _Settings()
        self.saved = 0

    def save_settings(self) -> None:
        self.saved += 1


class _Window(DocumentHeadingsMixin):
    def __init__(
        self, text: str = DOC, caret: int = 0, *, mode: str = PLAIN, name: str | None = "notes.md"
    ) -> None:
        self.control = _Control(text, caret)
        self.editor = _Editor(mode)
        self.app = _App()
        self.path = pathlib.Path(name) if name else None
        self.announcements: list[str] = []
        self.interrupted: list[bool] = []

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
    # The screen reader is already reading the line. Saying it again here is
    # the double-speaking GATE-13 exists to catch.
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
    QuillLite's announcements interrupt by default -- which is right for the
    outcome of a command and exactly wrong here, because interrupting would
    take away the text the user moved there to hear.
    """
    win = _Window()
    win.at("body line")
    win.at("Section")
    assert win.announcements == ["Heading 2"]
    assert win.interrupted == [False]


def test_the_status_bar_heading_cell_reads_a_plain_documents_headings() -> None:
    """The cell used to read "Not in rich text" in a plain document.

    Wrong twice over: those documents have real Markdown headings, and pressing
    Enter on the cell has always opened a list of them.
    """
    from quill.apps.lite_window_status import DocumentStatusMixin

    class _Frame(DocumentStatusMixin):
        def __init__(self, text: str, caret: int) -> None:
            self.control = _Control(text, caret)
            self.editor = _Editor(PLAIN)

    frame = _Frame(MARKDOWN, MARKDOWN.find("## Two"))
    assert frame._heading_text() == "Heading 2"
    frame.control.SetInsertionPoint(MARKDOWN.find("body"))
    assert frame._heading_text() == "Body text"


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
    """QuillLite is a Notepad replacement, so this is the common case.

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


def test_a_plain_txt_file_has_headings() -> None:
    # Nothing conventionally starts a line of prose with "#", and a .txt is
    # where somebody writes Markdown-ish headings without saying so.
    win = _Window(MARKDOWN, name="notes.txt")
    win.at("body")
    win.at("## Two")
    assert win.announcements == ["Heading 2"]


def test_an_untitled_buffer_has_headings() -> None:
    win = _Window(MARKDOWN, name=None)
    win.at("body")
    win.at("## Two")
    assert win.announcements == ["Heading 2"]


def test_rich_text_is_unaffected_by_the_file_name() -> None:
    # The rich ladder is not "#" at all, so a .py opened as rich text (it
    # cannot be, but the guard must not depend on that) still reads its levels.
    win = _Window("one\ntwo\n", mode=RICH, name="build.py")
    win.editor._level = 0
    win.at("one")
    win.editor._level = 2
    win.at("two")
    assert win.announcements == ["Heading 2"]
