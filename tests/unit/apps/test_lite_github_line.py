"""QUILL Lite's GitHub > From This Line rows (PRD 22.3).

Every handler is called here (GATE-LITE-COVER counts a call, by AST), against
the real mixin with a small fake control; each must hand the shared command
(quill/ui/github_editor_line.py) a host that describes this window truly.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.apps.lite_github_line import GitHubLineLiteMixin
from quill.ui import github_editor_line as gel


class _Control:
    def __init__(self, text: str, selection: tuple[int, int], caret: int) -> None:
        self._text, self._selection, self._caret = text, selection, caret

    def GetValue(self) -> str:  # noqa: N802 - wx's name
        return self._text

    def GetSelection(self) -> tuple[int, int]:  # noqa: N802
        return self._selection

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self._caret


class _Window(GitHubLineLiteMixin):
    def __init__(self, control: _Control, *, safe_mode: bool = False) -> None:
        self.app = SimpleNamespace(safe_mode=safe_mode)
        self.path = Path("C:/work/engine/src/app.py")
        self.control = control
        self.said: list[str] = []
        self.opened: list[dict[str, Any]] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _set_clipboard_text(self, _text: str) -> bool:
        return True

    def _github_provider(self, _retry: Any) -> Any:
        return SimpleNamespace(token="t")

    def open_github_items(self, **kwargs: Any) -> None:
        self.opened.append(kwargs)


TEXT = "one\ntwo\nthree\nfour\n"


@pytest.fixture
def hosts(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, gel.LineHost]]:
    """Each shared command records the host it was given, by name."""
    seen: list[tuple[str, gel.LineHost]] = []
    for name in (
        "copy_line_link",
        "who_changed_line",
        "open_line_pull",
        "open_line",
        "issue_from_selection",
        "issues_mentioning_file",
        "comment_on_line",
        "open_reference_at_cursor",
    ):
        monkeypatch.setattr(gel, name, lambda host, name=name: seen.append((name, host)))
    return seen


def test_every_row_runs_its_shared_command(hosts) -> None:
    window = _Window(_Control(TEXT, (0, 0), 5))
    window.cmd_github_copy_line_link()
    window.cmd_github_who_changed_line()
    window.cmd_github_open_line_pull()
    window.cmd_github_open_line()
    window.cmd_github_issue_from_selection()
    window.cmd_github_issues_mentioning_file()
    window.cmd_github_comment_on_line()
    window.cmd_github_open_reference_at_cursor()
    assert [name for name, _host in hosts] == [
        "copy_line_link",
        "who_changed_line",
        "open_line_pull",
        "open_line",
        "issue_from_selection",
        "issues_mentioning_file",
        "comment_on_line",
        "open_reference_at_cursor",
    ]


def test_the_host_reads_the_caret_line_and_the_file(hosts) -> None:
    window = _Window(_Control(TEXT, (0, 0), 5))
    window.cmd_github_copy_line_link()
    host = hosts[0][1]
    assert host.span() == (2, 2, "")
    assert Path(host.file_path()) == window.path
    assert host.text_and_offset() == (TEXT, 5)
    assert host.safe_mode is False


def test_a_selection_ending_at_a_line_start_does_not_take_that_line(hosts) -> None:
    # "two\nthree\n" selected: lines 2 and 3, not 4.
    start, end = TEXT.index("two"), TEXT.index("four")
    window = _Window(_Control(TEXT, (start, end), end))
    window.cmd_github_issue_from_selection()
    assert hosts[0][1].span() == (2, 3, "two\nthree\n")


def test_the_host_opens_the_workbench_with_the_request(hosts) -> None:
    window = _Window(_Control(TEXT, (0, 0), 0), safe_mode=True)
    window.cmd_github_issues_mentioning_file()
    host = hosts[0][1]
    assert host.safe_mode is True
    host.open_workbench("ada/engine", "search:x")
    host.open_reference("ref", "filter:#3")
    assert window.opened == [{"then": "search:x"}, {"reference": "ref", "then": "filter:#3"}]
    host.announce("hello")
    assert window.said == ["hello"]
