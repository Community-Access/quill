"""Alt+Enter on a GitHub reference in a document opens its sheet (GH-R-036).

The Workbench's half: ``properties:<json>`` from the editor opens that object's
Properties sheet, and a bare ``#42`` is read first so GitHub says whether it is
an issue or a pull request. Both editors' key handlers ask the one shared call.
"""

from __future__ import annotations

import inspect
import json
from types import SimpleNamespace
from typing import Any

from quill.ui.github_workbench_reference_sheet import open_reference_sheet


class _Window:
    def __init__(self, is_pr: bool = False) -> None:
        self.opened: list[Any] = []
        self.said: list[str] = []
        self.items = SimpleNamespace(
            fetch_item=lambda repo, number: _item(repo, number, is_pr),
        )

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _with_me(self, target: Any) -> Any:
        return target

    def _open_one(self, target: Any) -> None:
        self.opened.append(target)

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


class GitHubItem(SimpleNamespace):
    """Named as the Items row is: the sheet catalogue reads rows by class name."""


def _item(repo: str, number: int, is_pr: bool) -> Any:
    return GitHubItem(repo=repo, number=number, is_pr=is_pr, url="")


def _payload(kind: str, ident: dict[str, str]) -> str:
    return json.dumps([kind, ident])


def test_a_known_kind_opens_its_sheet() -> None:
    window = _Window()
    open_reference_sheet(window, _payload("person", {"login": "ada"}))
    open_reference_sheet(window, _payload("commit", {"repo": "o/r", "sha": "abc1234"}))
    assert [(t.kind, dict(t.ident)) for t in window.opened] == [
        ("person", {"login": "ada"}),
        ("commit", {"repo": "o/r", "sha": "abc1234"}),
    ]


def test_a_bare_number_asks_github_whether_it_is_a_pull_request() -> None:
    for is_pr, kind in ((False, "issue"), (True, "pull_request")):
        window = _Window(is_pr=is_pr)
        open_reference_sheet(window, _payload("item", {"repo": "o/r", "number": "12"}))
        assert [(t.kind, dict(t.ident)) for t in window.opened] == [
            (kind, {"repo": "o/r", "number": "12"})
        ]


def test_nonsense_is_said_not_raised() -> None:
    window = _Window()
    open_reference_sheet(window, "not json")
    open_reference_sheet(window, _payload("nothing", {}))
    assert len(window.said) == 2 and window.opened == []


def test_both_editors_ask_the_one_shared_call_before_anything_else_takes_alt_enter() -> None:
    """Rule 10: QUILL Lite never ahead, never behind; the same call in both."""
    from quill.apps import lite_github_line, lite_window_typing
    from quill.ui import main_frame, main_frame_github_line

    for module in (lite_github_line, main_frame_github_line):
        assert "alt_enter_on_reference(" in inspect.getsource(module)
    assert "_github_alt_enter(event)" in inspect.getsource(
        main_frame.MainFrame._on_editor_char_hook
    )
    assert "github_alt_enter(event)" in inspect.getsource(lite_window_typing)
