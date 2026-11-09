"""Layer 4 in the editors (quill.ui.language_servers, and the language-server
paths through quill.ui.suggestion_list and quill.ui.problems_commands), with a
stand-in pool: every switch, the merged list, problems, Quick Fix and hints."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.lsp.convert import QuickFix, ServerCompletion
from quill.core.problems.model import Problem
from quill.ui import language_servers as ls_module
from quill.ui.language_servers import LanguageServerMixin
from tests.unit.ui.test_suggestion_list import _WX, _Editor, _Host, _key, _Popup


class _Pool:
    """Records what was asked; answers like a running TypeScript server."""

    def __init__(self) -> None:
        self.asked: list[str] = []
        self.started: list[Path] = []
        self.live = ["TypeScript server"]

    def running(self) -> list[str]:
        return list(self.live)

    def client_for(self, path: Path, root: Path) -> Any:
        self.started.append(path)
        return object()

    def complete(self, path, root, text, offset, fragment) -> list[ServerCompletion]:
        self.asked.append("complete")
        return [ServerCompletion("countWords", "countWords", "method", "(s: string) => number")]

    def problems(self, path, root, text) -> list[Problem]:
        self.asked.append("problems")
        return [Problem(1, 5, "error", "Type 'string' is not assignable", "typescript")]

    def signature(self, path, root, text, offset) -> str:
        self.asked.append("signature")
        return "Parameter 2 of 2, b. f(a, b)"

    def fixes(self, path, root, text, problem) -> list[QuickFix]:
        self.asked.append("fixes")
        return [QuickFix("Use const", ((0, 3, "const"),), True)]


@pytest.fixture
def pool(monkeypatch) -> _Pool:
    fake = _Pool()
    monkeypatch.setattr(ls_module, "shared_pool", lambda: fake)
    monkeypatch.setattr(ls_module, "resolve_server", lambda spec: object())
    return fake


@pytest.fixture(autouse=True)
def _quiet(monkeypatch) -> list[str]:
    said: list[str] = []
    monkeypatch.setattr("quill.ui.main_frame_intellisense.announce", said.append)
    return said


class _LsHost(_Host):
    def __init__(self, text: str, caret: int, tmp: Path, **switches: Any) -> None:
        super().__init__(text, caret)
        (tmp / ".git").mkdir(exist_ok=True)
        self.document = SimpleNamespace(path=str(tmp / "app.ts"))
        for name, value in switches.items():
            setattr(self.settings, name, value)
        self.jobs: list[Any] = []

    def _suggest_in_background(self, work: Any, done: Any) -> bool:
        done(work())
        return True


def test_a_running_server_answers_first_with_its_kind(pool, tmp_path, _quiet) -> None:
    host = _LsHost("const count = 1;\ncou", 20, tmp_path)
    assert host._show_intellisense_popup(manual=True)
    assert pool.asked == ["complete"]
    rows = host._intellisense_popup.suggestions
    assert (rows[0].label, rows[0].kind) == ("countWords", "method")
    assert "count" in [row.label for row in rows], "layer 1 fills the rest"
    assert _quiet[-1].endswith("countWords, method")


def test_the_first_press_warms_the_server_and_answers_from_this_file(pool, tmp_path) -> None:
    pool.live = []
    host = _LsHost("const count = 1;\ncou", 20, tmp_path)
    assert host._show_intellisense_popup(manual=True)
    assert pool.asked == [] and pool.started, "started in the background for next time"
    assert host._intellisense_popup.suggestions[0].label == "count"


def test_an_answer_for_text_that_has_changed_is_dropped(pool, tmp_path, monkeypatch) -> None:
    host = _LsHost("cou", 3, tmp_path)
    held: list[Any] = []
    host._suggest_in_background = lambda work, done: held.append((work, done)) or True
    host._show_intellisense_popup(manual=True)
    host.editor.text = "coun"
    work, done = held.pop()
    done(work())
    assert not host._intellisense_popup.visible


@pytest.mark.parametrize(
    "switches",
    [
        {"language_servers_enabled": False},
        {"language_server_completions": False},
        {"language_servers_off": ["TypeScript server"]},
    ],
)
def test_every_off_switch_means_no_server_is_asked_or_started(pool, tmp_path, switches) -> None:
    pool.live = []
    host = _LsHost("const count = 1;\ncou", 20, tmp_path, **switches)
    host._show_intellisense_popup(manual=True)
    assert pool.asked == [] and pool.started == []


def test_problems_from_the_server_join_the_checkers(pool, tmp_path) -> None:
    host = _LsHost("x", 0, tmp_path)
    found = host._ls_problems_for(host.document.path, "let a: number = 'x'")
    assert found and found[0].source == "typescript"
    host.settings.language_server_problems = False
    assert host._ls_problems_for(host.document.path, "x") is None


def test_parameter_hints_say_the_parameter_or_why_not(pool, tmp_path, _quiet) -> None:
    host = _LsHost("f(1, ", 5, tmp_path)
    host._ls_parameter_hints()
    assert _quiet[-1] == "Parameter 2 of 2, b. f(a, b)"
    host.document = SimpleNamespace(path=str(tmp_path / "notes.txt"))
    host._ls_parameter_hints()
    assert host.status[-1] == "No parameter hints: no language server for this file"


def test_hints_as_you_type_only_after_a_bracket_or_comma_and_only_when_on(
    pool, tmp_path, _quiet
) -> None:
    host = _LsHost("f(", 2, tmp_path)
    host._ls_after_char()
    assert pool.asked == [], "off by default"
    host.settings.parameter_hints_as_you_type = True
    host._ls_after_char()
    assert pool.asked == ["signature"]
    host.editor = _Editor("fx", 2)
    host._ls_after_char()
    assert pool.asked == ["signature"]


def test_the_settings_hook_is_required() -> None:
    with pytest.raises(NotImplementedError):
        LanguageServerMixin()._ls_settings()


def test_status_words_for_the_window() -> None:
    from quill.core.lsp.servers import server_for_path

    spec = server_for_path("a.json")
    assert ls_module.server_status(spec) in {"bundled with QUILL", "not found"}
    assert _WX and _key and _Popup  # the shared stand-ins this file builds on
