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
