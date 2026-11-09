"""QUILL Lite's Navigate > Code: blocks, indent changes, Check This File and the
problem keys (quill/apps/lite_window_code_nav.py), called the way the menu does."""

from __future__ import annotations

from quill.core.lite.parity import COMMAND_EQUIVALENTS

HTML = "<body>\n<header>Top</header>\n<p>one</p>\n<p>two</p>\n<main>\n<h2>Title</h2>\n</main>\n"
CODE = "def f():\n    a = 1\n\n    if a:\n        b = 2\nc = 3\n"


def test_next_and_previous_block_in_html_stop_at_landmarks_and_headings(lite_window) -> None:
    win = lite_window(HTML, cursor=0)
    win.set_document_language("html", announce=False)
    win.cmd_next_block()
    assert win.control.GetInsertionPoint() == HTML.index("<header>")
    win.cmd_next_block()
    assert win.control.GetInsertionPoint() == HTML.index("<main>")
    win.cmd_next_block()
    assert win.control.GetInsertionPoint() == HTML.index("<h2>")
    win.cmd_next_block()
    assert win.announcements[-1] == "No next block"
    win.cmd_previous_block()
    assert win.control.GetInsertionPoint() == HTML.index("<main>")


def test_blocks_in_markdown_are_paragraphs(lite_window) -> None:
    text = "# Title\n\nFirst para\nstill first\n\nSecond para\n"
    win = lite_window(text, cursor=0)
    win.set_document_language("markdown", announce=False)
    win.cmd_next_block()
    assert win.control.GetInsertionPoint() == text.index("First")
    win.cmd_previous_block()
    assert win.control.GetInsertionPoint() == 0
    win.cmd_previous_block()
    assert win.announcements[-1] == "No previous block"


def test_indent_change_moves_and_says_how_deep(lite_window) -> None:
    win = lite_window(CODE, cursor=0)
    win.cmd_next_indent()
    assert win.control.GetInsertionPoint() == CODE.index("a = 1")
    assert win.announcements[-1] == "4 spaces"
    win.cmd_next_indent()
    assert win.control.GetInsertionPoint() == CODE.index("b = 2")
    win.cmd_previous_indent()
    assert win.control.GetInsertionPoint() == CODE.index("if a:")
    win.control.SetInsertionPoint(CODE.index("c = 3"))
    win.cmd_next_indent()
    assert win.announcements[-1] == "No change of indent below"


def test_check_this_file_lists_every_problem_and_goes_to_the_one_chosen(
    lite_window, lite_dialogs
) -> None:
    text = "# Title\n### Skipped\n\n![](pic.png)\n"
    win = lite_window(text, cursor=0)
    win.set_document_language("markdown", announce=False)
    lite_dialogs.answer("choose_from_rows", 1)
    win.cmd_check_this_file()
    kwargs = lite_dialogs.kwargs_for("choose_from_rows")
    assert kwargs["title"] == "Problems"
    assert kwargs["label"].startswith("2 problems: 1 error, 1 warning.")
    rows = [row for _key, row in kwargs["rows"]]
    assert rows[0].startswith("Line 2, column 1, warning:")
    assert win.control.GetInsertionPoint() == text.index("![](")


def test_check_this_file_cancelled_leaves_the_caret(lite_window, lite_dialogs) -> None:
    win = lite_window("<b>open", cursor=3)
    win.set_document_language("html", announce=False)
    win.cmd_check_this_file()
    assert lite_dialogs.names() == ["choose_from_rows"]
    assert win.control.GetInsertionPoint() == 3


def test_a_clean_file_says_so_without_a_list(lite_window, lite_dialogs) -> None:
    win = lite_window("<p>fine</p>\n", cursor=0)
    win.set_document_language("html", announce=False)
    win.cmd_check_this_file()
    assert lite_dialogs.names() == []
    assert win.announcements[-1] == "No problems found."


def test_next_and_previous_problem_walk_and_wrap(lite_window) -> None:
    text = "<div>\n<img src=a>\n<b>x\n</div>\n"
    win = lite_window(text, cursor=0)
    win.set_document_language("html", announce=False)
    win.cmd_next_problem()
    assert win.announcements[-1].startswith("Problem 1 of 2, line 2, column 1, warning:")
    assert win.control.GetInsertionPoint() == text.index("<img")
    win.cmd_next_problem()
    assert win.announcements[-1].startswith("Problem 2 of 2, line 3")
    win.cmd_next_problem()
    assert win.announcements[-1].startswith("Problem 1 of 2")
    win.cmd_previous_problem()
    assert win.announcements[-1].startswith("Problem 2 of 2")


def test_the_problem_keys_check_again_after_an_edit(lite_window) -> None:
    win = lite_window("<p>fine</p>\n", cursor=0)
    win.set_document_language("html", announce=False)
    win.cmd_next_problem()
    assert win.announcements[-1] == "No problems found."
    win.control.SetValue("<b>open\n")
    win.cmd_next_problem()
    assert win.announcements[-1].startswith("Problem 1 of 1")


def test_plain_text_is_not_checked_and_says_where_it_would_be(lite_window, lite_dialogs) -> None:
    win = lite_window('{"a": }', cursor=0)
    win.set_document_language("plain", announce=False)
    for command in (
        lambda w: w.cmd_check_this_file(),
        lambda w: w.cmd_next_problem(),
        lambda w: w.cmd_previous_problem(),
    ):
        command(win)
        assert win.announcements[-1].startswith("Nothing to check: QUILL Lite checks Markdown")
    assert lite_dialogs.names() == []


def test_lite_never_starts_an_outside_tool(lite_window, monkeypatch) -> None:
    from quill.core.problems import outside

    def refuse(*_args, **_kwargs):
        raise AssertionError("QUILL Lite started an outside checker")

    monkeypatch.setattr(outside, "run_outside_checkers", refuse)
    win = lite_window("<b>x", cursor=0)
    win.set_document_language("html", announce=False)
    win.cmd_next_problem()
    assert win.announcements[-1].startswith("Problem 1 of 1")


def test_the_commands_are_quills_commands() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    keys = {row[3]: row[2] for row in COMMANDS}
    for handler in (
        "cmd_next_indent",
        "cmd_previous_indent",
        "cmd_check_this_file",
        "cmd_next_problem",
        "cmd_previous_problem",
    ):
        assert keys[handler] == DEFAULT_KEYMAP[COMMAND_EQUIVALENTS[handler]], handler
    assert COMMAND_EQUIVALENTS["cmd_next_block"] == "navigate.next_block"


# -- View > Problems Pane ------------------------------------------------------


class _FakePane:
    """The pane's surface, without wx: the real widget is tested on its own."""

    def __init__(self) -> None:
        from types import SimpleNamespace

        self.shown = False
        self.focused = False
        self.report = None
        self.focus_calls = 0
        self.panel = SimpleNamespace(Show=lambda value: setattr(self, "shown", bool(value)))

    def is_shown(self) -> bool:
        return self.shown

    def has_focus(self) -> bool:
        return self.focused

    def show_report(self, report) -> None:
        self.report = report

    def count_sentence(self) -> str:
        from quill.core.problems.pane import count_sentence

        return count_sentence(len(self.report.problems) if self.report else 0)

    def focus(self) -> None:
        self.focus_calls += 1


def _with_pane(win) -> _FakePane:
    pane = _FakePane()
    win._problems_pane_widget = pane
    return pane


def test_problems_pane_shows_checks_and_hides(lite_window) -> None:
    win = lite_window("<b>open\n", cursor=0)
    win.set_document_language("html", announce=False)
    pane = _with_pane(win)
    win.cmd_toggle_problems_pane()
    assert win.app.settings.problems_pane_visible is True
    assert win.app.reapplied == 1
    win.apply_problems_pane_visibility()
    assert pane.shown
    assert win.announcements[-1].startswith("Problems pane shown. 1 problem: 1 error")
    assert len(pane.report.problems) == 1
    win.cmd_toggle_problems_pane()
    assert win.app.settings.problems_pane_visible is False
    win.apply_problems_pane_visibility()
    assert not pane.shown
    assert win.announcements[-1] == "Problems pane hidden"


def test_check_this_file_fills_the_shown_pane_instead_of_the_list(
    lite_window, lite_dialogs
) -> None:
    text = "# Title\n### Skipped\n"
    win = lite_window(text, cursor=0)
    win.set_document_language("markdown", announce=False)
    pane = _with_pane(win)
    pane.shown = True
    win.cmd_check_this_file()
    assert lite_dialogs.names() == []
    assert pane.report is not None and len(pane.report.problems) == 1
    assert win.announcements[-1].startswith("1 problem: 1 warning")


def test_enter_on_a_pane_row_goes_there_and_rechecks_after_an_edit(lite_window) -> None:
    text = "<p>a</p>\n<b>open\n"
    win = lite_window(text, cursor=0)
    win.set_document_language("html", announce=False)
    pane = _with_pane(win)
    pane.shown = True
    win.cmd_check_this_file()
    win._problems_pane_go_to(0)
    assert win.control.GetInsertionPoint() == text.index("<b>")
    edited = "<p>new line</p>\n" + text
    win.control.SetValue(edited)
    win.control.SetInsertionPoint(0)
    win._problems_pane_go_to(0)
    assert win.control.GetInsertionPoint() == edited.index("<b>")
    win.control.SetValue("<p>fixed</p>\n")
    win._problems_pane_go_to(0)
    assert win.announcements[-1].startswith("That problem is gone. No problems found.")


def test_escape_from_the_pane_and_copy_message(lite_window) -> None:
    win = lite_window("<b>x", cursor=2)
    win._problems_back_to_editor()
    assert win.control.GetInsertionPoint() == 2
    assert win.control.GetValue() == "<b>x"
    win._problems_copy("Unclosed b")
    assert win.control.clipboard == "Unclosed b"


def test_f6_goes_to_the_pane_first_then_the_status_bar(lite_window) -> None:
    win = lite_window("text", cursor=0)
    win.cmd_focus_status_bar()
    assert win.status_bar_focused == 1
    pane = _with_pane(win)
    pane.shown = True
    win.cmd_focus_status_bar()
    assert pane.focus_calls == 1
    assert win.status_bar_focused == 1
    pane.focused = True
    win.cmd_focus_status_bar()
    assert win.status_bar_focused == 2


def test_f6_from_the_pane_with_no_status_bar_goes_back_to_the_text(lite_window) -> None:
    win = lite_window("text", cursor=1)
    win.app.settings.show_status_bar = False
    pane = _with_pane(win)
    pane.shown = pane.focused = True
    win.cmd_focus_status_bar()
    assert win.status_bar_focused == 0
    assert win.announcements == []


def test_problems_pane_in_plain_text_shows_without_checking(lite_window) -> None:
    win = lite_window("plain words", cursor=0)
    win.set_document_language("plain", announce=False)
    pane = _with_pane(win)
    win.cmd_toggle_problems_pane()
    assert win.announcements[-1] == "Problems pane shown"
    assert pane.report is None


def test_problems_pane_is_quills_command() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    keys = {row[3]: row[2] for row in COMMANDS}
    assert COMMAND_EQUIVALENTS["cmd_toggle_problems_pane"] == "view.problems_pane"
    assert keys["cmd_toggle_problems_pane"] == DEFAULT_KEYMAP["view.problems_pane"] == ""
