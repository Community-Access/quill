"""What Ctrl+B writes, what the heading keys write, and which picker is offered.

The rules are tested in ``tests/unit/core`` -- ``test_list_structure.py`` for
the reading and ``test_structure_announce.py`` for the deciding. What matters
here is the *wiring*: that a ``.md`` gets asterisks and a ``.html`` gets
``<strong>``, that a ``.py`` gets neither and is told why, that the tag picker
the document cannot use is greyed out rather than silently doing the wrong
thing, and that every one of those says something a listener can act on.
"""

from __future__ import annotations

import pathlib

import pytest

from quill.apps.lite_window_format import DocumentFormatCommandsMixin
from quill.apps.lite_window_headings import DocumentHeadingsMixin
from quill.apps.lite_window_markup import MARKUP_COMMANDS, DocumentMarkupMixin
from quill.ui.richedit_editing import PLAIN, RICH


class _Control:
    """Just enough ``wx.TextCtrl`` to exercise an insertion and a selection."""

    def __init__(self, text: str = "", caret: int = 0) -> None:
        self._text = text
        self._caret = caret
        self._sel = (caret, caret)
        self.focused = 0

    def GetValue(self) -> str:  # noqa: N802 - wx spelling
        return self._text

    def GetInsertionPoint(self) -> int:  # noqa: N802 - wx spelling
        return self._caret

    def SetInsertionPoint(self, caret: int) -> None:  # noqa: N802 - wx spelling
        self._caret = max(0, min(int(caret), len(self._text)))
        self._sel = (self._caret, self._caret)

    def GetSelection(self) -> tuple[int, int]:  # noqa: N802 - wx spelling
        return self._sel

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802 - wx spelling
        self._sel = (start, end)
        self._caret = end

    def GetStringSelection(self) -> str:  # noqa: N802 - wx spelling
        start, end = self._sel
        return self._text[start:end]

    def Replace(self, start: int, end: int, text: str) -> None:  # noqa: N802 - wx spelling
        self._text = self._text[:start] + text + self._text[end:]
        self._caret = start + len(text)
        self._sel = (self._caret, self._caret)

    def WriteText(self, text: str) -> None:  # noqa: N802 - wx spelling
        self.Replace(*self._sel, text)

    def SetFocus(self) -> None:  # noqa: N802 - wx spelling
        self.focused += 1


class _Editor:
    def __init__(self, mode: str = PLAIN) -> None:
        self.mode = mode

    def heading_level_at_caret(self) -> int:
        return 0

    def rtf_available(self) -> bool:
        return True


class _Settings:
    announce_headings = True
    announce_lists = True


class _App:
    def __init__(self) -> None:
        self.settings = _Settings()
        self.saved = 0

    def save_settings(self) -> None:
        self.saved += 1


class _Window(DocumentMarkupMixin, DocumentFormatCommandsMixin, DocumentHeadingsMixin):
    def __init__(self, text: str = "", *, name: str | None = "notes.md", mode: str = PLAIN):
        self.control = _Control(text)
        self.editor = _Editor(mode)
        self.app = _App()
        self.path = pathlib.Path(name) if name else None
        self.said: list[str] = []
        self.modified = False

    def _announce(self, message: str, *, interrupt: bool = True) -> None:
        self.said.append(message)

    def _set_modified(self, flag: bool) -> None:
        self.modified = bool(flag)

    def _touch_status(self) -> None:
        pass

    def select(self, needle: str) -> None:
        start = self.control.GetValue().index(needle)
        self.control.SetSelection(start, start + len(needle))

    def at(self, needle: str) -> None:
        self.control.SetInsertionPoint(self.control.GetValue().index(needle))

    @property
    def text(self) -> str:
        return self.control.GetValue()


# -- which language a document is ---------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("notes.md", "markdown"),
        ("notes.markdown", "markdown"),
        ("page.html", "html"),
        ("page.htm", "html"),
        ("page.xhtml", "html"),
        ("notes.txt", "plain"),
        ("build.py", "plain"),
        ("nginx.conf", "plain"),
        ("app.log", "plain"),
        (None, "plain"),
    ],
)
def test_the_file_name_decides_the_language(name: str | None, expected: str) -> None:
    assert _Window(name=name).document_language() == expected


def test_plain_text_stays_plain() -> None:
    """A `.txt` is not Markdown, and neither is an unnamed buffer.

    The rule is the file's name, and only the file's name. Guessing was tried
    and dropped: being wrong is invisible in one direction -- two asterisks
    written into a plain note -- and relentless in the other, a "Heading 1"
    spoken over every line of a log that begins with a hash. One keystroke says
    otherwise when somebody means otherwise.
    """
    for name in ("notes.txt", "diary.txt", "app.log", None):
        win = _Window("- a line\n# a line\n", name=name)
        assert win.markup_surface() is None
        win.select("a line")
        win.cmd_bold()
        assert "**" not in win.text


def test_a_rich_document_has_no_markup_surface_whatever_it_is_called() -> None:
    # Rich text has real bold. Inserting ** into it would put two asterisks on
    # the page beside a word that is already bold.
    assert _Window(name="notes.md", mode=RICH).markup_surface() is None


def test_the_language_can_be_overridden_and_says_so() -> None:
    win = _Window(name="scratch.txt")
    win.set_document_language("html")
    assert win.document_language() == "html"
    assert win.said == ["Document language: HTML"]


def test_the_override_does_not_forget_what_the_file_name_said() -> None:
    # The chooser marks the file name's own answer, so going back to it is a
    # choice somebody can find rather than a state they have to restart to reach.
    win = _Window(name="page.html")
    win.set_document_language("plain")
    assert win.default_document_language() == "html"


# -- bold, italic and underline ------------------------------------------------


@pytest.mark.parametrize(
    ("command", "markdown", "html"),
    [
        (lambda w: w.cmd_bold(), "**word**", "<strong>word</strong>"),
        (lambda w: w.cmd_italic(), "*word*", "<em>word</em>"),
        (lambda w: w.cmd_underline(), "<u>word</u>", "<u>word</u>"),
    ],
)
def test_the_run_keys_write_the_documents_own_markup(command, markdown, html) -> None:
    for name, expected in (("notes.md", markdown), ("page.html", html)):
        win = _Window("a word here", name=name)
        win.select("word")
        command(win)
        assert expected in win.text


def test_bold_uses_strong_rather_than_b() -> None:
    # Not synonyms to the thing that reads them out: <strong> carries importance
    # into the accessibility tree and <b> carries only a typeface.
    win = _Window("a word here", name="page.html")
    win.select("word")
    win.cmd_bold()
    assert "<strong>" in win.text and "<b>" not in win.text


def test_the_announcement_names_the_markup_not_the_effect() -> None:
    # "Bold on" would be a small lie: nothing went bold, two asterisks appeared,
    # and somebody who cannot see them needs to know which of the two happened.
    win = _Window("a word here", name="notes.md")
    win.select("word")
    win.cmd_bold()
    assert win.said == ["Bold in Markdown"]


def test_with_nothing_selected_the_caret_lands_between_the_tags() -> None:
    win = _Window("", name="page.html")
    win.cmd_bold()
    assert win.text == "<strong></strong>"
    assert win.control.GetInsertionPoint() == len("<strong>")


def test_a_plain_document_refuses_and_offers_both_ways_out() -> None:
    win = _Window("hello", name="build.py")
    win.select("hello")
    win.cmd_bold()
    assert win.text == "hello"
    said = win.said[0]
    assert "Control Shift M" in said and "Control Alt F6" in said


def test_a_markdown_document_in_rich_mode_is_sent_to_rich_formatting() -> None:
    # The refusal has to name the *real* obstacle. Telling the author of a .py
    # to switch to rich text is advice; telling them that in a .md they are
    # already in rich text is the fact they needed.
    win = _Window("hello", name="notes.md", mode=RICH)
    win.editor.rtf_available = lambda: False  # type: ignore[method-assign]
    win.cmd_bold()
    assert "unavailable on this system" in win.said[0]


# -- headings -------------------------------------------------------------------


def test_a_heading_key_writes_hashes_in_markdown() -> None:
    win = _Window("Some title\n", name="notes.md")
    win.at("Some")
    win.cmd_heading_2()
    assert win.text.startswith("## Some title")
    assert win.said == ["Heading 2"]


def test_a_heading_key_writes_a_tag_in_html() -> None:
    win = _Window("Some title\n", name="page.html")
    win.at("Some")
    win.cmd_heading_2()
    assert win.text.startswith("<h2>Some title</h2>")
    assert win.said == ["Heading 2"]


def test_applying_a_level_rewrites_rather_than_stacking() -> None:
    # The bug this exists to prevent: "## ### Notes", which renders as a
    # Heading 2 whose text begins with three hashes and which nothing announces.
    win = _Window("### Notes\n", name="notes.md")
    win.at("Notes")
    win.cmd_heading_2()
    assert win.text.startswith("## Notes")


def test_html_attributes_survive_a_level_change() -> None:
    # An id= on a heading is very often the anchor somebody else's link points
    # at, and dropping it while changing a level breaks that link silently.
    win = _Window('<h3 id="install">Setup</h3>\n', name="page.html")
    win.at("Setup")
    win.cmd_heading_1()
    assert win.text.startswith('<h1 id="install">Setup</h1>')


def test_body_text_takes_the_marker_back_off() -> None:
    win = _Window("## Notes\n", name="notes.md")
    win.at("Notes")
    win.cmd_heading_0()
    assert win.text.startswith("Notes")
    assert win.said == ["Body text"]


def test_body_text_on_a_line_that_is_not_a_heading_says_so() -> None:
    win = _Window("Just a line\n", name="notes.md")
    win.at("Just")
    win.cmd_heading_0()
    assert win.text == "Just a line\n"
    assert win.said == ["Already body text"]


def test_demote_walks_an_html_heading_not_a_markdown_one() -> None:
    win = _Window("<h2>Setup</h2>\n", name="page.html")
    win.at("Setup")
    win.cmd_demote_heading()
    assert win.text.startswith("<h3>Setup</h3>")


def test_a_heading_key_in_a_plain_document_refuses_rather_than_writing_a_hash() -> None:
    win = _Window("Some title\n", name="build.py")
    win.at("Some")
    win.cmd_heading_2()
    assert win.text == "Some title\n"
    assert win.said


# -- the pickers ----------------------------------------------------------------


def test_the_html_picker_refuses_in_a_markdown_document_and_names_the_key() -> None:
    win = _Window("", name="notes.md")
    win.cmd_insert_html_tag()
    assert win.text == ""
    said = win.said[0]
    assert "HTML document" in said and "Markdown" in said and "Control Alt F6" in said


def test_the_markdown_picker_refuses_in_an_html_document() -> None:
    win = _Window("", name="page.html")
    win.cmd_insert_markdown_tag()
    assert win.text == ""
    assert "Markdown document" in win.said[0]


def test_both_pickers_refuse_in_rich_text_and_say_how_to_leave_it() -> None:
    for name in ("notes.md", "page.html"):
        win = _Window("", name=name, mode=RICH)
        win.cmd_insert_html_tag()
        win.cmd_insert_markdown_tag()
        assert all("Control Shift M" in message for message in win.said)


def test_the_menu_map_pairs_each_picker_with_exactly_one_language() -> None:
    from quill.apps.lite_window_markup import MARKUP_COMMANDS

    assert MARKUP_COMMANDS == {
        "cmd_insert_markdown_tag": ("markdown",),
        "cmd_insert_html_tag": ("html",),
    }


# -- list announcements ----------------------------------------------------------


def test_the_list_toggle_names_the_consequence_and_persists() -> None:
    win = _Window("- one\n", name="notes.md")
    win.cmd_toggle_list_announcements()
    assert win.app.settings.announce_lists is False
    assert win.said == ["Lists will not be announced"]
    assert win.app.saved == 1
    win.cmd_toggle_list_announcements()
    assert win.said[-1] == "Lists announced as you enter them"


def test_walking_into_a_list_says_what_it_is() -> None:
    win = _Window("Notes\n\n- bread\n- milk\n", name="notes.md")
    win.at("Notes")
    win.announce_structure_at_caret()
    win.at("bread")
    win.announce_structure_at_caret()
    assert win.said == ["Bulleted list, 2 items"]


def test_an_html_list_is_announced_the_same_way() -> None:
    win = _Window("<p>Notes</p>\n<ul>\n<li>bread</li>\n<li>milk</li>\n</ul>\n", name="page.html")
    win.at("Notes")
    win.announce_structure_at_caret()
    win.at("bread")
    win.announce_structure_at_caret()
    assert win.said == ["Bulleted list, 2 items"]


def test_a_dash_in_a_shell_script_is_not_a_list() -> None:
    win = _Window("#!/bin/sh\n- not a bullet\n", name="run.sh")
    win.at("#!")
    win.announce_structure_at_caret()
    win.at("not a bullet")
    win.announce_structure_at_caret()
    assert win.said == []


def test_switching_lists_off_silences_them_and_leaves_headings_alone() -> None:
    # The two toggles are separate on purpose, and this is the test that keeps
    # them that way: silencing one must not silence the other.
    win = _Window("# Title\n\n- bread\n- milk\n\n## Next\n", name="notes.md")
    win.app.settings.announce_lists = False
    win.at("Title")
    win.announce_structure_at_caret()
    win.at("bread")
    win.announce_structure_at_caret()
    assert win.said == []
    win.at("Next")
    win.announce_structure_at_caret()
    # The level and then the words, in one sentence: that is the shipped
    # default, and it is what survives a Ctrl+Home.
    assert win.said == ["Heading 2, Next"]


def test_switching_headings_off_leaves_lists_alone() -> None:
    win = _Window("# Title\n\n- bread\n- milk\n", name="notes.md")
    win.app.settings.announce_headings = False
    win.at("Title")
    win.announce_structure_at_caret()
    win.at("bread")
    win.announce_structure_at_caret()
    assert win.said == ["Bulleted list, 2 items"]


def test_the_list_cue_never_interrupts_the_reader() -> None:
    win = _Window("Notes\n\n- bread\n", name="notes.md")
    recorded: list[bool] = []
    win._announce = lambda m, *, interrupt=True: (
        (  # type: ignore[method-assign]
            win.said.append(m),
            recorded.append(interrupt),
        )
        and None
    )
    win.at("Notes")
    win.announce_structure_at_caret()
    win.at("bread")
    win.announce_structure_at_caret()
    assert recorded == [False]


# -- the Ctrl+Shift+M ring --------------------------------------------------------


def _ring_stops(win: _Window, presses: int = 5) -> list[str]:
    """Where the ring lands, press by press, named as the user would name it."""
    stops = []
    for _ in range(presses):
        win.cmd_switch_document_kind()
        stops.append("rich" if win.editor.mode == RICH else win.document_language())
    return stops


def test_the_ring_reaches_every_kind_of_document_and_comes_back() -> None:
    # The key has always meant "make this the other kind". Once a plain document
    # has a language there are four kinds, and reaching three of them would be
    # the worse half of the old behaviour rather than a smaller version of it.
    win = _Window("hello", name="scratch.txt")
    win.set_document_language("plain", announce=False)
    win.switch_mode = lambda mode: setattr(win.editor, "mode", mode)  # type: ignore[method-assign]
    assert _ring_stops(win) == ["markdown", "html", "rich", "plain", "markdown"]


def test_moving_between_the_three_plain_stops_never_touches_the_document() -> None:
    # Plain, Markdown and HTML differ in what the *keys* write. Nothing on disk
    # or in the buffer changes, which is what lets the ring be walked at speed.
    win = _Window("hello there", name="scratch.txt")
    win.set_document_language("plain", announce=False)
    win.switch_mode = lambda mode: None  # type: ignore[method-assign]
    win.cmd_switch_document_kind()
    win.cmd_switch_document_kind()
    assert win.text == "hello there"
    assert win.modified is False


def test_every_stop_announces_itself() -> None:
    win = _Window("hello", name="scratch.txt")
    win.set_document_language("plain", announce=False)
    win.switch_mode = lambda mode: None  # type: ignore[method-assign]
    win.cmd_switch_document_kind()
    win.cmd_switch_document_kind()
    assert win.said == ["Document language: Markdown", "Document language: HTML"]


def test_declining_the_conversion_out_of_rich_text_leaves_the_ring_where_it_was() -> None:
    # switch_mode asks before discarding formatting. A key that quietly moved
    # you somewhere else after you said no is worse than one that did nothing.
    win = _Window("hello", name="notes.md", mode=RICH)
    win.switch_mode = lambda mode: None  # type: ignore[method-assign]  # declines
    win.cmd_switch_document_kind()
    assert win.editor.mode == RICH
    assert win.said == []


# -- the two commands that live behind a dialog ------------------------------------
#
# Reached through the shared recorder rather than a stub of their own, because
# what needs testing is the half *after* the dialog: a command that acts on a
# cancelled dialog is the bug the recorder's cancel-by-default exists to catch.


def test_choosing_a_language_adopts_it_and_says_so(lite_window, lite_dialogs):
    win = lite_window("hello")
    lite_dialogs.answer("choose_document_language", "html")
    win.cmd_set_language()
    assert win.document_language() == "html"
    assert win.announcements[-1] == "Document language: HTML"


def test_cancelling_the_language_chooser_changes_nothing(lite_window, lite_dialogs):
    win = lite_window("hello")
    before = win.document_language()
    win.cmd_set_language()
    assert win.document_language() == before
    assert win.announcements == []


def test_the_emoji_picker_inserts_the_character_and_names_it(lite_window, lite_dialogs):
    # The name, because this is the one insertion whose result the reader cannot
    # describe: a bare emoji is read as anything from its own name to silence
    # depending on the synthesiser and the voice.
    class _Entry:
        char = "\N{PARTY POPPER}"
        name = "party popper"

    win = lite_window("done ")
    win.control.SetInsertionPoint(len("done "))
    lite_dialogs.answer("EmojiPickerDialog", _Entry())
    win.cmd_insert_emoji()
    assert win.control.GetValue() == "done \N{PARTY POPPER}"
    assert win.announcements[-1] == "Inserted party popper"


def test_cancelling_the_emoji_picker_inserts_nothing(lite_window, lite_dialogs):
    win = lite_window("done ")
    win.cmd_insert_emoji()
    assert win.control.GetValue() == "done "


def test_the_emoji_picker_is_offered_in_rich_text_too(lite_window, lite_dialogs):
    # An emoji is a character, not markup. Windows' own Win+Period picker is no
    # more reachable in a rich document than anywhere else.
    class _Entry:
        char = "\N{PARTY POPPER}"
        name = "party popper"

    win = lite_window("", mode=RICH)
    lite_dialogs.answer("EmojiPickerDialog", _Entry())
    win.cmd_insert_emoji()
    assert "\N{PARTY POPPER}" in win.control.GetValue()


# -- the menu rows the language dims -------------------------------------------
#
# The logic, not a real menu bar: what has to be right is *which* rows are
# enabled for which document, and a wx.MenuBar adds nothing to that question
# while costing a display. The rows are refreshed on every menu open, so the
# state can never be stale -- what this pins down is the answer it refreshes to.


class _Item:
    """Enough of ``wx.MenuItem`` for the enable sweep to act on."""

    def __init__(self) -> None:
        self.enabled = True

    def Enable(self, value: bool) -> None:  # noqa: N802 - wx spelling
        self.enabled = bool(value)


class _MenuWindow(_Window):
    """A window carrying the menu-item registry the sweep reads."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._menu_items = {handler: _Item() for handler in MARKUP_COMMANDS}

    def state(self) -> dict[str, bool]:
        from quill.apps.lite_window_menus import DocumentMenuMixin

        DocumentMenuMixin._sync_enabled_items(self)
        return {handler: item.enabled for handler, item in self._menu_items.items()}


@pytest.mark.parametrize(
    ("name", "markdown_row", "html_row"),
    [
        ("notes.md", True, False),
        ("page.html", False, True),
        ("build.py", False, False),
        ("notes.txt", False, False),
        (None, False, False),
    ],
)
def test_exactly_one_picker_is_live_and_it_is_the_documents_own(
    name: str | None, markdown_row: bool, html_row: bool
) -> None:
    state = _MenuWindow(name=name).state()
    assert state["cmd_insert_markdown_tag"] is markdown_row
    assert state["cmd_insert_html_tag"] is html_row


def test_rich_text_dims_both_pickers() -> None:
    # Rich headings are a point size and rich bold is real bold, so a markup tag
    # inserted into one would put literal angle brackets beside formatted text.
    state = _MenuWindow(name="notes.md", mode=RICH).state()
    assert not any(state.values())


def test_changing_the_language_changes_which_row_is_live() -> None:
    window = _MenuWindow(name="build.py")
    assert not any(window.state().values())
    window.set_document_language("html", announce=False)
    assert window.state()["cmd_insert_html_tag"] is True
    window.set_document_language("markdown", announce=False)
    assert window.state()["cmd_insert_markdown_tag"] is True
    assert window.state()["cmd_insert_html_tag"] is False
