"""The Codespaces commands in the GitHub Workbench."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.codespaces import codespace_row
from quill.core.github.item_shortcuts import DELETE_COMMANDS, NEW_HERE
from quill.ui.github_workbench_codespaces import GitHubWorkbenchCodespacesMixin
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from tests.unit.core.github_workbench.test_codespaces import SPACE, Api

ROW = codespace_row(SPACE)


class _Window(GitHubWorkbenchCodespacesMixin):
    signed_in = True

    def __init__(self, api: Api, answers: list[Any], node: str = "") -> None:
        self.api, self.answers = api, list(answers)
        self.said: list[str] = []
        self.frame = SimpleNamespace(current=SimpleNamespace(key=node), reload=lambda: None)

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())

    def _choose(self, *_a: Any) -> int:
        return int(self.answers.pop(0))

    def _confirm(self, *_a: Any) -> bool:
        return bool(self.answers.pop(0))

    def _ask_text(self, *_a: Any, **_k: Any) -> str:
        return str(self.answers.pop(0))


def test_wired_everywhere() -> None:
    assert {"codespace_start", "codespace_new", "pull_codespace"} <= set(DEVELOPMENT_VERBS)
    assert NEW_HERE["repo_codespaces"] == "github.workbench.codespace_new"
    assert DELETE_COMMANDS["codespace"] == "github.workbench.codespace_delete"
    window = _Window(Api(), [], node="repo_codespaces")
    assert window._fits_codespace_start(ROW) and window._fits_codespace_new(None)


def test_delete_asks_first_and_no_sends_nothing() -> None:
    window = _Window(Api(), [False])
    window._do_codespace_delete(None, ROW)
    assert window.api.sent == []
    window = _Window(Api(), [True])
    window._do_codespace_delete(None, ROW)
    assert window.api.sent[-1][:2] == ("DELETE", "/user/codespaces/jeff-quill-abc")


def test_ctrl_n_asks_the_branch_and_machine_then_makes_it() -> None:
    api = Api({
        "GET /repos/o/r/codespaces/machines": {"machines": [{"name": "m1"}, {"name": "m2"}]},
        "POST /repos/o/r/codespaces": {"display_name": "neat robot"},
    })
    window = _Window(api, ["feature", 1], node="repo_codespaces")
    window._do_codespace_new(SimpleNamespace(instance="o/r"), None)
    assert api.sent[-1][2] == {"ref": "feature", "machine": "m2"}
    assert window.said[0].startswith("Making the codespace neat robot for o/r on feature.")
