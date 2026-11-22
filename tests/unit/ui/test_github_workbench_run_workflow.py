"""Run Workflow on Branch in the GitHub Workbench runs the selected workflow, in its repository.

It used to hand off to the editor's Dispatch Workflow, which asked for the
repository and the workflow file again and ignored the row you were on.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.workflows import GitHubWorkflow
from quill.ui.github_workbench_actions import _EDITOR_VERBS
from quill.ui.github_workbench_runs import RUN_VERBS, GitHubWorkbenchRunsMixin

CI = GitHubWorkflow(id=77, name="CI", path=".github/workflows/ci.yml", state="active")


class _Items:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def dispatch_workflow(self, repo: str, workflow_id: str, ref: str) -> None:
        self.sent.append((repo, workflow_id, ref))


class _Window(GitHubWorkbenchRunsMixin):
    signed_in = True

    def __init__(self, answers: list[Any]) -> None:
        self.items, self.answers = _Items(), list(answers)
        self.said: list[str] = []
        self.asked: list[tuple[Any, ...]] = []
        self.frame = SimpleNamespace(reload=lambda: None)

    def _repo_for(self, ref: Any) -> str:
        return str(ref.instance)

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())

    def _confirm(self, *a: Any) -> bool:
        self.asked.append(a)
        return bool(self.answers.pop(0))

    def _ask_text(self, *_a: Any, **_k: Any) -> str:
        return str(self.answers.pop(0))


def test_run_workflow_is_the_workbench_s_own_verb_on_a_workflow_row() -> None:
    assert "run_workflow" not in _EDITOR_VERBS
    assert RUN_VERBS["run_workflow"] == frozenset({"workflow"})
    window = _Window([])
    assert window._fits_run_workflow(CI)
    window.signed_in = False
    assert not window._fits_run_workflow(CI)


def test_it_runs_the_selected_workflow_in_the_selected_repository() -> None:
    window = _Window(["feature", True])
    window._do_run_workflow(SimpleNamespace(instance="o/r"), CI)
    assert window.items.sent == [("o/r", "77", "feature")]
    assert window.asked[0][0] == "Run Workflow on Branch"
    assert "CI" in window.asked[0][1] and "feature" in window.asked[0][1]
    assert "o/r" in window.asked[0][1]
    assert window.said == ["GitHub accepted CI on feature; its run appears in Runs shortly."]


def test_no_or_a_blank_branch_runs_nothing() -> None:
    window = _Window(["feature", False])
    window._do_run_workflow(SimpleNamespace(instance="o/r"), CI)
    window2 = _Window([""])
    window2._do_run_workflow(SimpleNamespace(instance="o/r"), CI)
    assert window.items.sent == [] and window2.items.sent == []
    assert window.said == [] and window2.said == []
