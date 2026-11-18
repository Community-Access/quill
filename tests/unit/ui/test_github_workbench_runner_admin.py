"""What a runner row, and Ctrl+N in Runners, can do (GitHub PRD 14.2)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.runners_sbom import runner_row
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_runner_admin import GitHubWorkbenchRunnerAdminMixin
from tests.unit.core.github_workbench.test_runner_admin import TOKEN, FakeApi

ROW = runner_row("o/r", {"id": 3, "name": "lab-1", "status": "online", "os": "Linux"})
REF = SimpleNamespace(instance="o/r")


class _Window(GitHubWorkbenchRunnerAdminMixin):
    signed_in = True

    def __init__(self, picks: list[int], texts: list[str] | None = None) -> None:
        self.api, self.picks, self.texts = FakeApi(), list(picks), list(texts or [])
        self.said: list[str] = []
        self.copied: list[str] = []
        self.frame = SimpleNamespace(
            current=SimpleNamespace(key="runners"),
            copy_text=self.copied.append,
            reload=lambda: self.said.append("(reloaded)"),
        )

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, *_a: Any) -> int:
        return self.picks.pop(0)

    def _confirm(self, *_a: Any) -> bool:
        return True

    def _ask_text(self, *_a: Any, **_k: Any) -> str:
        return self.texts.pop(0)

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def test_registered() -> None:
    assert {"new_runner", "runner_labels", "remove_runner"} <= set(DEVELOPMENT_VERBS)


def test_new_runner_copies_the_commands_and_never_says_the_token() -> None:
    window = _Window([0])
    assert window._fits_new_runner(None)
    window._do_new_runner(REF, None)
    assert TOKEN in window.copied[0]
    assert all(TOKEN not in said for said in window.said)
    assert "Copied the setup commands for Linux x64" in window.said[0]


def test_labels_offer_only_what_can_be_removed() -> None:
    window = _Window([1])
    window._do_runner_labels(REF, ROW)
    assert window.api.sent[-1][:2] == ("DELETE", "/repos/o/r/actions/runners/3/labels/gpu")
    window = _Window([0], ["gpu2"])
    window._do_runner_labels(REF, ROW)
    assert window.api.sent[-1][2] == {"labels": ["gpu2"]}


def test_remove_runner_names_it_and_asks() -> None:
    window = _Window([])
    window._do_remove_runner(REF, ROW)
    assert window.api.sent[-1][:2] == ("DELETE", "/repos/o/r/actions/runners/3")
    assert window.said[0].startswith("Removed the runner lab-1.")
