"""Ctrl+N, Change and Delete through the resource engine (GitHub PRD section 19)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.item_shortcuts import DELETE_COMMANDS, NEW_HERE
from quill.core.github.resource_engine import fetch
from quill.core.github.resource_specs import RESOURCE_SPECS, spec_for
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_resources import GitHubWorkbenchResourcesMixin
from tests.unit.core.github_workbench.test_resource_engine import FakeApi


class _Window(GitHubWorkbenchResourcesMixin):
    signed_in = True

    def __init__(
        self, node: str, picks: list[int], texts: list[str], secret: str | None = "v"
    ) -> None:
        self.api = FakeApi({"variables": [{"name": "CHANNEL", "value": "beta"}]})
        self.picks, self.texts, self.secret = list(picks), list(texts), secret
        self.said: list[str] = []
        self.asked: list[str] = []
        self.frame = SimpleNamespace(
            current=SimpleNamespace(key=node), reload=lambda: self.said.append("(reloaded)")
        )

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, *_a: Any) -> int:
        return self.picks.pop(0)

    def _confirm(self, _title: str, question: str) -> bool:
        self.asked.append(question)
        return True

    def _ask_text(self, *_a: Any, **_k: Any) -> str:
        return self.texts.pop(0)

    def _ask_secret(self, *_a: Any) -> str | None:
        return self.secret

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


REF = SimpleNamespace(instance="o/r")


def test_wired_for_every_list_that_can_grow() -> None:
    assert set(("resource_new", "resource_edit", "resource_delete")) <= set(DEVELOPMENT_VERBS)
    assert DELETE_COMMANDS["resource"] == "github.workbench.resource_delete"
    for spec in RESOURCE_SPECS:
        assert (NEW_HERE.get(spec.key) == "github.workbench.resource_new") == bool(spec.create)


def test_new_variable_then_change_and_delete_it() -> None:
    window = _Window("actions_variables", [], ["CHANNEL", "beta"])
    assert window._fits_resource_new(None)
    window._do_resource_new(REF, None)
    assert window.api.sent[-1] == (
        "POST",
        "/repos/o/r/actions/variables",
        {"name": "CHANNEL", "value": "beta"},
    )
    row = fetch(window.api, spec_for("actions_variables"), "o/r")[0]
    window.texts = ["stable"]
    assert window._fits_resource_edit(row)
    window._do_resource_edit(REF, row)
    assert window.api.sent[-1][2] == {"value": "stable"}
    window._do_resource_delete(REF, row)
    assert window.asked == ["Delete: CHANNEL is beta."]
    assert window.api.sent[-1][:2] == ("DELETE", "/repos/o/r/actions/variables/CHANNEL")


def test_a_cancelled_secret_sends_nothing_and_a_chosen_one_is_sealed() -> None:
    window = _Window("actions_secrets", [], ["TOKEN"], secret=None)
    window._do_resource_new(REF, None)
    assert window.api.sent == []
    window = _Window("actions_secrets", [], ["TOKEN"], secret="s3cret")
    window._do_resource_new(REF, None)
    assert window.api.sent[-1][1] == "/repos/o/r/actions/secrets/TOKEN"
    assert all("s3cret" not in said for said in window.said)


def test_yes_or_no_and_choices() -> None:
    window = _Window("org_issue_types", [1], ["Bug", ""])
    window._do_resource_new(SimpleNamespace(instance="acme"), None)
    assert window.api.sent[-1][2] == {"name": "Bug", "is_enabled": False}


def test_repositories_allowed_checks_the_current_ones_and_saves_the_difference() -> None:
    from tests.unit.core.github_workbench.test_resource_engine import RepoApi

    window = _Window("org_actions_secrets", [], [])
    window.api = RepoApi()
    row = SimpleNamespace(kind="resource", key="org_actions_secrets:TOKEN", label="TOKEN")
    seen: dict[str, Any] = {}

    def choose(_title: str, _prompt: str, labels: list[str], checked: set[int]) -> list[int]:
        seen.update(labels=labels, checked=checked)
        return [1]

    window._choose_repositories = choose  # type: ignore[method-assign]
    window._row_spec = lambda _row: (spec_for("org_actions_secrets"), "TOKEN")  # type: ignore[method-assign]
    assert window._fits_resource_repositories(row)
    window._do_resource_repositories(SimpleNamespace(instance="acme"), row)
    assert seen == {"labels": ["acme/one", "acme/two"], "checked": {0}}
    assert window.said[0] == "Added 1 repository and removed 1 repository for TOKEN."


def test_cancelling_repositories_allowed_changes_nothing() -> None:
    from tests.unit.core.github_workbench.test_resource_engine import RepoApi

    window = _Window("org_actions_secrets", [], [])
    window.api = RepoApi()
    window._choose_repositories = lambda *_a: None  # type: ignore[method-assign]
    window._row_spec = lambda _row: (spec_for("org_actions_secrets"), "TOKEN")  # type: ignore[method-assign]
    window._do_resource_repositories(SimpleNamespace(instance="acme"), None)
    assert not any(method in ("PUT", "DELETE") for method, _p, _b in window.api.sent)
