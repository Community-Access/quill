"""QUILL says "Heading 2", "Table, 3 rows, 2 columns" and "Bulleted list, 5 items".

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
    announce_lists = True
    # "after" keeps these tests reading as they did: the level alone, queued
    # behind the reader. The "before" default is exercised by its own class at
    # the bottom, where the composed sentence is the thing under test.
    heading_announce_position = "after"


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
        self.interrupted: list[bool] = []

    def _announce(self, message: str, *, force: bool = False) -> None:
        self.announcements.append(message)
        self.interrupted.append(bool(force))

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


LISTS = """\
Before the list.

- fruit
    - apple
    - pear
- veg

After the list.
"""

HTML_LISTS = """\
<p>Before.</p>
<ol>
  <li>first</li>
  <li>second</li>
</ol>
<p>After.</p>
"""


class TestLists:
    """The cue a screen reader gives you in a browser and cannot give you here."""

    def test_entering_a_markdown_list_names_it_and_counts_it(self) -> None:
        frame = _Frame(LISTS)
        frame.at("Before the list")
        frame.at("fruit")
        assert frame.announcements == ["Bulleted list, 2 items"]

    def test_going_a_level_down_says_the_level_and_the_new_count(self) -> None:
        frame = _Frame(LISTS)
        frame.at("Before the list")
        frame.at("fruit")
        frame.announcements.clear()
        frame.at("apple")
        assert frame.announcements == ["Level 2, 2 items"]

    def test_leaving_says_out_of_list(self) -> None:
        frame = _Frame(LISTS)
        frame.at("fruit")
        frame.announcements.clear()
        frame.at("After the list")
        assert frame.announcements == ["Out of list"]

    def test_moving_between_items_of_one_list_is_silent(self) -> None:
        # What the caret does nearly all the time in a list. The reader is
        # already speaking the item; a cue per item would make lists unusable.
        frame = _Frame(LISTS)
        frame.at("fruit")
        frame.announcements.clear()
        frame.at("veg")
        assert frame.announcements == []

    def test_html_lists_are_read_with_the_html_scanner(self) -> None:
        frame = _Frame(HTML_LISTS, markup="html")
        frame.at("Before")
        frame.at("first")
        assert frame.announcements == ["Numbered list, 2 items"]

    def test_a_plain_document_never_hears_about_lists(self) -> None:
        # A letter is full of hyphens. A cue that fired on them would be
        # superstition rather than help, so "plain" is searched for nothing.
        frame = _Frame("Dear Kate,\n- and this is the bit -\nyours\n", markup="plain")
        frame.at("Dear")
        frame.at("and this")
        assert frame.announcements == []

    def test_a_rich_document_never_hears_about_markup_lists(self) -> None:
        # Rich bullets are the control's own, set through the Text Object Model.
        # A "-" typed into one is a hyphen.
        frame = _Frame(LISTS, mode="rich", wrapper=_Wrapper(0))
        frame.at("Before the list")
        frame.at("fruit")
        assert frame.announcements == []

    def test_the_toggle_names_the_consequence_and_saves(self, monkeypatch) -> None:
        saved: list[object] = []
        monkeypatch.setattr(
            "quill.ui.main_frame_structure.save_settings", lambda s: saved.append(s)
        )
        frame = _Frame(LISTS)
        frame.toggle_list_announcements()
        assert frame.settings.announce_lists is False
        assert frame.announcements == ["Lists will not be announced"]
        assert len(saved) == 1
        frame.announcements.clear()
        frame.toggle_list_announcements()
        assert frame.announcements == ["Lists announced as you enter them"]

    def test_switching_lists_off_leaves_headings_alone(self, monkeypatch) -> None:
        # The whole case for two switches rather than one. Silencing either must
        # never silence the other.
        monkeypatch.setattr("quill.ui.main_frame_structure.save_settings", lambda _s: None)
        frame = _Frame("# Title\n\n- bread\n- milk\n\n## Next\n")
        frame.settings.announce_lists = False
        frame.at("Title")
        frame.at("bread")
        assert frame.announcements == []
        frame.at("Next")
        assert frame.announcements == ["Heading 2"]

    def test_switching_headings_off_leaves_lists_alone(self, monkeypatch) -> None:
        monkeypatch.setattr("quill.ui.main_frame_structure.save_settings", lambda _s: None)
        frame = _Frame("# Title\n\n- bread\n- milk\n")
        frame.settings.announce_headings = False
        frame.at("Title")
        frame.at("bread")
        assert frame.announcements == ["Bulleted list, 2 items"]


class TestWhereTheLevelGoes:
    """ "Heading 2, Installing" or "Installing... Heading 2" -- and why it matters.

    Not a matter of taste. A cue *queued behind* the reader is at the reader's
    mercy: on a large caret jump NVDA and JAWS cancel what is pending and start
    again on the new line, so the level waiting its turn is never heard at all.
    That was reported exactly that way -- arrowing onto a heading announced it,
    Ctrl+Home onto the same heading did not.
    """

    def test_before_says_the_level_and_then_the_words_in_one_sentence(self) -> None:
        frame = _Frame()
        frame.settings.heading_announce_position = "before"
        frame.at("body line")
        frame.at("Section")
        assert frame.announcements == ["Heading 2, Section"]

    def test_before_interrupts_because_the_words_are_already_in_the_sentence(self) -> None:
        # Interrupting is safe here precisely because the text the reader was
        # about to say is inside the phrase that replaces it.
        frame = _Frame()
        frame.settings.heading_announce_position = "before"
        frame.at("body line")
        frame.at("Section")
        assert frame.interrupted == [True]

    def test_after_says_the_level_alone_and_waits_its_turn(self) -> None:
        frame = _Frame()
        frame.settings.heading_announce_position = "after"
        frame.at("body line")
        frame.at("Section")
        assert frame.announcements == ["Heading 2"]
        assert frame.interrupted == [False]

    def test_a_jump_to_the_top_of_the_document_still_announces(self) -> None:
        # The reported bug, from both ends: the announcer always had the right
        # answer, and in "after" mode the reader threw it away.
        frame = _Frame()
        frame.settings.heading_announce_position = "before"
        frame.at("more body" if "more body" in frame.text else "body line")
        frame.announcements.clear()
        frame.editor.SetInsertionPoint(0)
        frame.announce_structure_at_caret()
        assert frame.announcements == ["Heading 1, Title"]

    def test_a_settings_object_that_predates_the_field_leads_with_the_level(self) -> None:
        # The default that works on every kind of move, not the lossy one.
        class _Old:
            announce_headings = True
            announce_lists = True

        frame = _Frame()
        frame.settings = _Old()
        frame.at("body line")
        frame.at("Section")
        assert frame.announcements == ["Heading 2, Section"]

    def test_the_list_cue_is_unaffected_by_where_the_level_goes(self) -> None:
        # Lists never carry their item's text: the reader reads the item, and
        # the cue is about the container.
        frame = _Frame(LISTS)
        frame.settings.heading_announce_position = "before"
        frame.at("Before the list")
        frame.at("fruit")
        assert frame.announcements == ["Bulleted list, 2 items"]
        assert frame.interrupted == [False]
