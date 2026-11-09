"""QUILL's Navigate > Code (quill.ui.main_frame_code_nav), and the language-aware
Next / Previous Block it answers, called the way the menu calls them."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.language_profile import get_profile_for_path
from quill.ui.main_frame import MainFrame
from quill.ui.main_frame_code_nav import _CODE_ROWS, CodeNavMixin


class _Editor:
    def __init__(self, text: str, caret: int = 0) -> None:
        self.text, self.caret = text, caret

    def GetValue(self) -> str:  # noqa: N802 - wx spelling
        return self.text

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self.caret

    def SetInsertionPoint(self, value: int) -> None:  # noqa: N802
        self.caret = value

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
        self.caret = start

    def SetFocus(self) -> None:  # noqa: N802
        pass


class _Ring:
    def __init__(self) -> None:
        self.recorded: list[int] = []

    def record(self, offset: int) -> None:
        self.recorded.append(offset)


class _Host(CodeNavMixin):
    def __init__(self, text: str, path: str | None = None, caret: int = 0) -> None:
        self.editor = _Editor(text, caret)
        file = Path(path) if path else None
        self.document = SimpleNamespace(path=file, modified=True)
        self._current_tab = SimpleNamespace(_language_profile=get_profile_for_path(file))
        self._location_ring = _Ring()
        self.said: list[str] = []
        self.moves: list[tuple[str, int]] = []
        self.chosen: int | None = None
        self.lists: list[tuple[str, list[str]]] = []
        self.background: list[Any] = []

    def _set_status(self, message: str) -> None:
        self.said.append(message)

    def _announce_navigation_move(self, prefix: str, target: int, **_kwargs: Any) -> None:
        self.moves.append((prefix, target))

    def _record_location_before_jump(self) -> None:
        pass

    def _problems_choose(self, summary: str, rows: list[str]) -> int | None:
        self.lists.append((summary, rows))
        return self.chosen

    def _problems_in_background(self, work, done) -> None:  # type: ignore[no-untyped-def]
        self.background.append(work)
        done(work())


def test_next_block_in_python_names_the_def() -> None:
    text = "import os\n\ndef first():\n    pass\n\nclass Second:\n    pass\n"
    host = _Host(text, "tool.py")
    MainFrame._navigate_block(host, reverse=False)  # type: ignore[arg-type]
    assert host.editor.caret == text.index("def first")
    assert host.moves[-1] == ("def first():", text.index("def first"))
    MainFrame._navigate_block(host, reverse=False)  # type: ignore[arg-type]
    assert host.moves[-1][0] == "class Second:"
    MainFrame._navigate_block(host, reverse=False)  # type: ignore[arg-type]
    assert host.said[-1] == "No next block"


def test_next_block_in_an_unknown_language_is_still_paragraphs() -> None:
    text = "one\n\ntwo\n"
    host = _Host(text, "notes.txt")
    assert host._block_pattern() == ""
    MainFrame._navigate_block(host, reverse=False)  # type: ignore[arg-type]
    assert host.moves[-1] == ("Moved to next block", text.index("two"))


def test_indent_change_moves_and_says_how_deep() -> None:
    text = "items:\n  - a\n  - b\n    deep: 1\nend: 2\n"
    host = _Host(text, "list.yaml")
    host.navigate_next_indent()
    assert host.moves[-1] == ("2 spaces", text.index("- a"))
    host.navigate_next_indent()
    assert host.moves[-1] == ("4 spaces", text.index("deep"))
    host.navigate_previous_indent()
    assert host.editor.caret == text.index("- b")
    host.editor.caret = text.index("end")
    host.navigate_next_indent()
    assert host.said[-1] == "No change of indent below"
    assert host._location_ring.recorded


def test_check_this_file_lists_problems_and_goes_to_the_choice() -> None:
    text = '{\n  "a": 1,\n  "b": \n}\n'
    host = _Host(text, "data.json")
    host.chosen = 0
    host.tools_check_this_file()
    summary, rows = host.lists[-1]
    assert summary == "1 problem: 1 error."
    assert rows == ["Line 4, column 1, error: Expecting value (JSON)"]
    assert host.editor.caret == text.index("}")


def test_check_this_file_with_nothing_wrong_only_says_so() -> None:
    host = _Host("[tool]\nname = 'x'\n", "pyproject.toml")
    host.tools_check_this_file()
    assert host.lists == []
    assert host.said[-1] == "No problems found."


def test_problem_keys_walk_and_say_the_problem() -> None:
    text = "[a]\nx=1\nx=2\n"
    host = _Host(text, "settings.ini")
    host.navigate_next_problem()
    assert host.said[-1] == "Problem 1 of 1, line 3, column 1, error: x appears twice in [a]"
    assert host.editor.caret == text.index("x=2")
    host.navigate_previous_problem()
    assert host.said[-1].startswith("Problem 1 of 1")


def test_an_outside_tool_runs_in_the_background(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.problems import outside

    calls: list[str] = []

    def fake(text: str, **kwargs: Any) -> outside.OutsideResult:
        calls.append(kwargs["language"])
        return outside.OutsideResult((), ("node",), ())

    monkeypatch.setattr("quill.core.problems.registry.run_outside_checkers", fake)
    host = _Host("let a = 1;\n", "app.js")
    host.navigate_next_problem()
    assert calls == ["javascript"]
    assert host.background, "a check with an outside tool must not run on the UI thread"
    assert host.said == ["Checking this file", "No problems found."]


def test_rows_and_keys_match_quill_lite() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS
    from quill.core.lite.parity import COMMAND_EQUIVALENTS

    lite = {
        COMMAND_EQUIVALENTS[row[3]]: (row[1], row[2])
        for row in COMMANDS
        if row[0] == "&Navigate|&Code" and row[3]
    }
    for command_id, label, _palette, _handler in _CODE_ROWS:
        if command_id:
            assert lite[command_id] == (label, DEFAULT_KEYMAP[command_id]), command_id


# -- View > Problems > Show Pane ------------------------------------------------------


class _FakePane:
    def __init__(self) -> None:
        self.shown = self.focused = False
        self.report: Any = None
        self.focus_calls = 0
        self.panel = SimpleNamespace(Show=lambda value: setattr(self, "shown", bool(value)))

    def is_shown(self) -> bool:
        return self.shown

    def set_shown(self, shown: bool) -> None:
        self.shown = bool(shown)

    def set_all_files(self, all_files: bool) -> None:
        self.all_files = bool(all_files)

    def has_focus(self) -> bool:
        return self.focused

    def show_report(self, report: Any) -> None:
        self.report = report

    def count_sentence(self) -> str:
        from quill.core.problems.pane import count_sentence

        return count_sentence(len(self.report.problems) if self.report else 0)

    def focus(self) -> None:
        self.focus_calls += 1


class _PaneHost(_Host):
    def __init__(self, text: str, path: str | None = None) -> None:
        super().__init__(text, path)
        self._problems_pane_widget = _FakePane()
        self.settings = SimpleNamespace(problems_pane_visible=False)
        self.checked: list[bool] = []
        self.regions: list[str] = []
        self.clipboard: list[str] = []
        sizer = SimpleNamespace(Layout=lambda: None)
        menu_bar = SimpleNamespace(Check=lambda _id, value: self.checked.append(value))
        self.frame = SimpleNamespace(GetSizer=lambda: sizer, GetMenuBar=lambda: menu_bar)
        self._id_problems_pane = 7

    def _set_active_region(self, label: str) -> None:
        self.regions.append(label)

    def _copy_text_to_clipboard(self, text: str) -> bool:
        self.clipboard.append(text)
        return True


@pytest.fixture
def no_settings_write(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    saved: list[Any] = []
    monkeypatch.setattr("quill.core.settings.save_settings", saved.append)
    return saved


def test_problems_pane_shows_with_a_check_and_hides(no_settings_write: list[Any]) -> None:
    host = _PaneHost('{"a": }\n', "data.json")
    host.view_toggle_problems_pane()
    pane = host._problems_pane_widget
    assert pane.shown and host.settings.problems_pane_visible
    assert host.checked == [True] and no_settings_write
    assert host.said[-1] == "Problems pane shown. 1 problem: 1 error."
    assert len(pane.report.problems) == 1
    assert host._problems_pane_is_shown()
    pane.focused = True
    host.view_toggle_problems_pane()
    assert not pane.shown and host.checked[-1] is False
    assert host.regions == ["Editor"], "hiding the focused pane puts focus back in the text"
    assert host.said[-1] == "Problems pane hidden"


def test_check_this_file_fills_the_shown_pane_not_the_list(no_settings_write: list[Any]) -> None:
    host = _PaneHost('{\n  "b": \n}\n', "data.json")
    host._problems_pane_widget.shown = True
    host.tools_check_this_file()
    assert host.lists == []
    assert host.said[-1] == "1 problem: 1 error."
    host._problems_pane_go_to(0)
    assert host.editor.caret == host.editor.text.index("}")


def test_pane_row_after_an_edit_rechecks_and_finds_the_problem() -> None:
    host = _PaneHost('{\n  "b": \n}\n', "data.json")
    host._problems_pane_widget.shown = True
    host.tools_check_this_file()
    host.editor.text = '\n\n{\n  "b": \n}\n'
    host._problems_pane_go_to(0)
    assert host.editor.caret == host.editor.text.index("}")
    host.editor.text = '{"b": 1}\n'
    host._problems_pane_go_to(0)
    assert host.said[-1].startswith("That problem is gone.")
    host._problems_pane_go_to(5)  # out of range: nothing happens
    assert host.said[-1].startswith("That problem is gone.")


def test_escape_copy_and_the_f6_hooks() -> None:
    host = _PaneHost("x", "a.json")
    host._problems_back_to_editor()
    assert host.regions == ["Editor"]
    host._problems_copy("Expecting value")
    assert host.clipboard == ["Expecting value"]
    pane = host._problems_pane_widget
    assert host._is_problems_panel(pane.panel)
    host._focus_problems_pane()
    assert pane.focus_calls == 1


def test_problems_pane_row_matches_quill_lite() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS
    from quill.core.lite.parity import COMMAND_EQUIVALENTS

    row = next(r for r in COMMANDS if r[3] == "cmd_toggle_problems_pane")
    assert row[0] == "&View|&Problems" and row[1] == "&Show Pane"
    assert COMMAND_EQUIVALENTS[row[3]] == "view.problems_pane"
    assert DEFAULT_KEYMAP["view.problems_pane"] == row[2] == ""


# -- quiet checks: after a save, after a pause ---------------------------------


def _shown_host(text: str) -> _PaneHost:
    host = _PaneHost(text, "data.json")
    host._problems_pane_widget.shown = True
    host.settings.problems_check_after_pause = False
    return host


def test_saving_checks_again_and_says_only_a_changed_count() -> None:
    host = _shown_host('{"a": }\n')
    host.document.modified = True
    host._problems_tick(now=0.0)
    assert host.said == [], "nothing happens while the file is still modified"
    host.document.modified = False
    host._problems_tick(now=1.0)
    assert host.said == ["1 problem"]
    host.document.modified = True
    host.editor.text = '{"a": 2}\n'
    host._problems_tick(now=2.0)
    host.document.modified = False
    host._problems_tick(now=3.0)
    assert host.said[-1] == "No problems"


def test_a_save_that_leaves_the_count_alone_says_nothing() -> None:
    host = _shown_host('{"a": }\n')
    host.tools_check_this_file()
    said = len(host.said)
    host.editor.text = '{"b": }\n'
    host.document.modified = True
    host._problems_tick(now=0.0)
    host.document.modified = False
    host._problems_tick(now=0.5)
    assert len(host.said) == said
    assert host._problems_checked_text == host.editor.text


def test_check_after_a_pause_waits_for_the_pause_and_is_off_by_default() -> None:
    from quill.ui.problems_commands import PAUSE_SECONDS

    host = _shown_host('{"a": 1}\n')
    host.document.modified = True
    host._problems_tick(now=0.0)
    host.editor.text = '{"a": }\n'
    host._problems_tick(now=1.0)
    host._problems_tick(now=1.0 + PAUSE_SECONDS + 1)
    assert host.said == [], "off by default"
    host._problems_set_pause_enabled(True)
    assert host.settings.problems_check_after_pause is True
    host._problems_tick(now=10.0)
    assert host.said == ["1 problem"], "turned on, the unchecked text is checked"
    host.editor.text = '{"a": 3}\n'
    host._problems_tick(now=20.0)
    host._problems_tick(now=20.0 + PAUSE_SECONDS / 2)
    assert host.said == ["1 problem"], "not until the text has been still long enough"
    host._problems_tick(now=20.0 + PAUSE_SECONDS)
    assert host.said == ["1 problem", "No problems"]
    host._problems_tick(now=40.0)
    assert len(host.said) == 2, "the same text is never checked twice"


def test_no_quiet_checks_while_the_pane_is_hidden() -> None:
    host = _shown_host('{"a": }\n')
    host._problems_pane_widget.shown = False
    host.document.modified = True
    host._problems_tick(now=0.0)
    host.document.modified = False
    host._problems_tick(now=1.0)
    assert host.said == [] and host._problems_report is None


# -- All open files ------------------------------------------------------------


class _Tab:
    def __init__(self, text: str, name: str) -> None:
        self.editor = _Editor(text)
        self.document = SimpleNamespace(path=Path(name), name=name, modified=True)
        self._language_profile = get_profile_for_path(Path(name))


def test_all_open_files_lists_every_document_and_goes_to_another() -> None:
    host = _PaneHost('{"a": }\n', "data.json")
    host._problems_pane_widget.shown = True
    host.document.name = "data.json"
    other = _Tab("[a]\nx=1\nx=2\n", "settings.ini")
    host._document_tabs = [SimpleNamespace(editor=host.editor, document=host.document), other]
    host._active_tab_index = 0
    selected: list[int] = []

    def select(index: int) -> None:
        selected.append(index)
        host._active_tab_index = index
        host.editor = host._document_tabs[index].editor

    host._select_tab = select
    host.tools_check_this_file()
    host._problems_set_all_files(True)
    pane = host._problems_pane_widget
    assert [p.document for p in pane.report.problems] == ["data.json", "settings.ini"]
    assert host.said[-1] == "2 problems"
    host._problems_pane_go_to(1)
    assert selected == [1]
    assert host.editor.caret == other.editor.text.index("x=2")
    host._problems_set_all_files(False)
    assert len(pane.report.problems) == 1 and host._problems_pane_origins is None


def test_view_problems_switches_for_now_and_shows_the_pane(
    no_settings_write: list[Any],
) -> None:
    host = _PaneHost('{"a": }' + chr(10), "data.json")
    host._problems_scope_ids = (11, 12)
    pane = host._problems_pane_widget
    chosen: list[bool] = []
    pane.set_all_files = chosen.append
    host.view_problems_all_files()
    assert pane.shown, "choosing from the menu shows a hidden pane"
    assert host._problems_all_files is True
    assert getattr(host.settings, "problems_all_open_files", False) is False, (
        "a switch is for now; the setting is the default"
    )
    assert chosen[0] is True
    assert host.said[-1].startswith("Problems pane shown, all open files.")
    host.view_problems_this_file()
    assert host._problems_all_files is False
    assert host.said[-1] == "1 problem"
    host._problems_switch_files()
    assert host._problems_all_files is True, "F in the list switches back"


def test_problems_submenu_rows_match_quill_lite() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS
    from quill.core.lite.parity import COMMAND_EQUIVALENTS

    rows = [r for r in COMMANDS if r[0] == "&View|&Problems" and r[3]]
    assert [(r[1], COMMAND_EQUIVALENTS[r[3]]) for r in rows] == [
        ("&Show Pane", "view.problems_pane"),
        ("&This File Only", "view.problems_this_file"),
        ("&All Open Files", "view.problems_all_files"),
    ]
    for row in rows:
        assert DEFAULT_KEYMAP[COMMAND_EQUIVALENTS[row[3]]] == row[2] == ""


def test_the_default_setting_decides_the_first_showing(no_settings_write: list[Any]) -> None:
    host = _PaneHost('{"a": }' + chr(10), "data.json")
    host.settings.problems_all_open_files = True
    host.view_toggle_problems_pane()
    assert host._problems_all_files is True
    assert host.said[-1].startswith("Problems pane shown, all open files.")
