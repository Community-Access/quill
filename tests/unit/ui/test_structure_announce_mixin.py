"""QUILL says "Heading 2" and "Table, 3 rows, 2 columns" because nothing else can.

The wiring, not the rules -- those are ``tests/unit/core/test_structure_announce``.
What is tested here is that the mixin asks the right mode for the heading level,
that an edit is not mistaken for an arrival, and that the table cue that used to
live inline in ``main_frame`` (untested, and quieter than it needed to be) still
fires on the same crossings.
"""

from __future__ import annotations

import pytest

from quill.ui.main_frame_structure import StructureAnnounceMixin

DOC = "# Title\n\nbody line\n\n## Section\n\n| a | b |\n| --- | --- |\n| c | d |\n\nafter\n"


class _Wrapper:
    """Stands in for the QuillRichEdit wrapper on ``editor.quill_richedit``."""

    def __init__(self, level: int = 0) -> None:
        self.level = level

    def heading_level_at_caret(self) -> int:
        return self.level


class _Editor:
    def __init__(self, caret: int = 0, wrapper: _Wrapper | None = None) -> None:
        self._caret = caret
        if wrapper is not None:
            self.quill_richedit = wrapper

    def GetInsertionPoint(self) -> int:  # noqa: N802 - wx spelling
        return self._caret

    def SetInsertionPoint(self, caret: int) -> None:  # noqa: N802 - wx spelling
        self._caret = caret


class _Settings:
    announce_headings = True


class _Frame(StructureAnnounceMixin):
    def __init__(
        self,
        text: str = DOC,
        *,
        mode: str = "markup",
        markup: str = "markdown",
        wrapper: _Wrapper | None = None,
    ) -> None:
        self.text = text
        self.mode = mode
        self.markup = markup
        self.editor = _Editor(0, wrapper)
        self.settings = _Settings()
        self.announcements: list[str] = []

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _document_text_for_display(self) -> str:
        return self.text

    def _current_editor_mode(self) -> str:
        return self.mode

    def _effective_markup_kind(self) -> str:
        return self.markup

    def at(self, needle: str) -> None:
        offset = self.text.find(needle)
        assert offset >= 0, needle
        self.editor.SetInsertionPoint(offset)
        self.announce_structure_at_caret()


class TestHeadings:
    def test_markdown_headings_announce_their_level(self) -> None:
        frame = _Frame()
        frame.at("body line")
        frame.at("Section")
        assert frame.announcements == ["Heading 2"]

    def test_html_headings_are_read_with_the_html_patterns(self) -> None:
        frame = _Frame("<p>body</p>\n<h3>Sub</h3>\n", markup="html")
        frame.at("body")
        frame.at("Sub")
        assert frame.announcements == ["Heading 3"]

    def test_plain_text_has_no_headings_to_announce(self) -> None:
        frame = _Frame("# not markup here\nsecond line\n", markup="plain")
        frame.at("second line")
        frame.at("not markup")
        assert frame.announcements == []

    def test_rich_mode_reads_the_ladder_off_the_control(self) -> None:
        wrapper = _Wrapper(0)
        frame = _Frame("first paragraph\nsecond paragraph\n", mode="rich", wrapper=wrapper)
        frame.at("first")
        wrapper.level = 1
        frame.at("second")
        assert frame.announcements == ["Heading 1"]

    def test_rich_mode_without_a_wrapper_is_silent_not_broken(self) -> None:
        frame = _Frame("one\ntwo\n", mode="rich")
        frame.at("one")
        frame.at("two")
        assert frame.announcements == []

    def test_a_failing_text_object_model_does_not_break_typing(self) -> None:
        class _Broken(_Wrapper):
            def heading_level_at_caret(self) -> int:
                raise RuntimeError("TOM unavailable")

        frame = _Frame("one\ntwo\n", mode="rich", wrapper=_Broken())
        frame.at("one")
        frame.at("two")
        assert frame.announcements == []

    def test_the_heading_text_is_never_repeated(self) -> None:
        frame = _Frame()
        frame.at("body line")
        frame.at("Section")
        assert "Section" not in frame.announcements[0]

    def test_moving_within_one_heading_is_silent(self) -> None:
        frame = _Frame()
        frame.at("body line")
        frame.at("Section")
        frame.editor.SetInsertionPoint(frame.editor.GetInsertionPoint() + 2)
        frame.announce_structure_at_caret()
        assert frame.announcements == ["Heading 2"]

    def test_an_edit_that_renumbers_the_lines_is_not_an_arrival(self) -> None:
        frame = _Frame()
        frame.at("body line")
        frame.at("Section")
        frame.announcements.clear()
        frame.text = DOC.replace("body line\n", "")
        frame.editor.SetInsertionPoint(frame.text.find("Section"))
        frame.announce_structure_at_caret()
        assert frame.announcements == []


class TestTableBoundary:
    def test_entering_a_table_now_says_how_big_it_is(self) -> None:
        # The cue this replaced said only "Entering table". The shape is the
        # part a listener cannot get any other way without walking every cell.
        frame = _Frame()
        frame.at("Section")
        frame.at("| a | b |")
        assert frame.announcements[-1] == "Table, 2 rows, 2 columns"

    def test_leaving_a_table_says_so(self) -> None:
        frame = _Frame()
        frame.at("| a | b |")
        frame.at("after")
        assert frame.announcements[-1] == "Out of table"

    def test_moving_inside_a_table_stays_quiet(self) -> None:
        frame = _Frame()
        frame.at("| a | b |")
        before = len(frame.announcements)
        frame.at("| c | d |")
        assert len(frame.announcements) == before


class TestLifecycle:
    def test_reset_makes_the_next_position_silent(self) -> None:
        frame = _Frame()
        frame.at("body line")
        frame.reset_structure_announcer()
        frame.at("Section")
        assert frame.announcements == []

    def test_sync_stops_a_command_being_echoed(self) -> None:
        frame = _Frame()
        frame.at("body line")
        frame.editor.SetInsertionPoint(frame.text.find("Section"))
        frame.sync_structure_announcer()  # what format_heading does after reporting
        frame.announce_structure_at_caret()
        assert frame.announcements == []

    @pytest.mark.parametrize("broken", ["mode", "markup", "text"])
    def test_a_host_that_cannot_answer_is_survivable(self, broken: str) -> None:
        frame = _Frame()

        def raiser(*_args: object) -> str:
            raise RuntimeError("host is mid-teardown")

        setattr(
            frame,
            {"mode": "_current_editor_mode", "markup": "_effective_markup_kind"}.get(
                broken, "_document_text_for_display"
            ),
            raiser,
        )
        frame.announce_structure_at_caret()  # must not raise


class TestTheToggle:
    def test_off_silences_the_cue_and_names_the_consequence(self, monkeypatch) -> None:
        monkeypatch.setattr("quill.ui.main_frame_structure.save_settings", lambda _s: None)
        frame = _Frame()
        frame.at("body line")
        frame.toggle_heading_announcements()
        assert frame.announcements[-1] == "Headings will not be announced"
        frame.announcements.clear()
        frame.at("Section")
        assert frame.announcements == []

    def test_back_on_says_so_and_resumes(self, monkeypatch) -> None:
        monkeypatch.setattr("quill.ui.main_frame_structure.save_settings", lambda _s: None)
        frame = _Frame()
        frame.toggle_heading_announcements()
        frame.at("body line")
        frame.announcements.clear()
        frame.toggle_heading_announcements()
        assert frame.announcements == ["Headings announced on arrival"]
        frame.announcements.clear()
        frame.at("Section")
        assert frame.announcements == ["Heading 2"]

    def test_off_silences_the_table_cue_too(self, monkeypatch) -> None:
        monkeypatch.setattr("quill.ui.main_frame_structure.save_settings", lambda _s: None)
        frame = _Frame()
        frame.settings.announce_headings = False
        frame.at("Section")
        frame.at("| a | b |")
        assert frame.announcements == []

    def test_off_still_feeds_the_latch(self, monkeypatch) -> None:
        """Off must not mean blind.

        If the latch stopped being fed, switching back on inside a heading
        would stay quiet until you left and returned -- which reads as the
        toggle not having worked.
        """
        monkeypatch.setattr("quill.ui.main_frame_structure.save_settings", lambda _s: None)
        frame = _Frame()
        frame.at("body line")
        frame.toggle_heading_announcements()
        frame.at("Section")
        frame.toggle_heading_announcements()
        frame.announcements.clear()
        frame.announce_structure_at_caret()
        assert frame.announcements == []
