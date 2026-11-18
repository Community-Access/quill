"""Environments: rows, their secrets and variables through the resource engine, and Delete."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github import environments as envs
from quill.core.github import resource_engine as engine
from quill.core.github.item_shortcuts import DELETE_COMMANDS
from quill.core.github.resource_specs_env import environment_spec, environment_target
from quill.ui.github_workbench_environments import GitHubWorkbenchEnvironmentsMixin
from tests.unit.core.github_workbench.test_resource_engine import FakeApi

ENV = {
    "name": "production",
    "protection_rules": [{"type": "required_reviewers"}, {"type": "wait_timer", "wait_timer": 5}],
}


class EnvApi(FakeApi):
    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        from quill.core.github.rest_transport import RestResponse

        if method == "GET" and path == "/repos/o/r/environments":
            self.sent.append((method, path, body))
            return RestResponse(200, {}, {"environments": [ENV]})
        if method == "GET" and path.endswith("/variables"):
            self.sent.append((method, path, body))
            return RestResponse(200, {}, {"variables": [{"name": "URL", "value": "https://x"}]})
        return super().rest(method, path, body=body, query=query)


def test_an_environment_reads_its_rules_and_opens_its_sheet() -> None:
    from quill.core.github.sheet_catalog import target_for

    row = envs.fetch_environments(EnvApi(), "o/r")[0]
    assert row.label == "production: needs a reviewer, waits 5 minutes."
    target = target_for(row)
    assert target is not None and target.kind == "environment"
    assert target.ident == {"repo": "o/r", "name": "production"}
    assert DELETE_COMMANDS["environment"] == "github.workbench.environment_delete"


def test_an_environments_secret_is_sealed_against_the_environments_own_key() -> None:
    spec = environment_spec("environment_secrets")
    assert spec is not None
    api = FakeApi()
    target = environment_target("o/r", "production")
    said = engine.create(api, spec, target, {"name": "TOKEN", "value": "s3cret"})
    assert said == "Added the secret TOKEN."
    assert api.sent[-2][1] == "/repos/o/r/environments/production/secrets/public-key"
    assert api.sent[-1][:2] == ("PUT", "/repos/o/r/environments/production/secrets/TOKEN")


class _Window(GitHubWorkbenchEnvironmentsMixin):
    signed_in = True

    def __init__(self, api: Any, answers: list[Any]) -> None:
        self.api, self.answers, self.said = api, list(answers), []
        self.frame = SimpleNamespace(reload=lambda: None)

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _background(self, _n: str, work: Any, done: Any) -> None:
        done(work())

    def _choose(self, *_a: Any) -> int:
        return int(self.answers.pop(0))

    def _confirm(self, *_a: Any) -> bool:
        return bool(self.answers.pop(0))

    def _ask_fields(self, _title: str, _fields: Any) -> dict[str, str] | None:
        return self.answers.pop(0)


def test_variables_list_then_change_one_and_delete_the_environment() -> None:
    row = envs.environment_row(ENV, "o/r")
    window = _Window(EnvApi(), [1, 0, {"value": "https://y"}])
    window._do_environment_variables(None, row)
    assert window.api.sent[-1] == (
        "PATCH",
        "/repos/o/r/environments/production/variables/URL",
        {"value": "https://y"},
    )
    window = _Window(EnvApi(), [True])
    window._do_environment_delete(None, row)
    assert window.api.sent[-1][:2] == ("DELETE", "/repos/o/r/environments/production")
    assert window.said == ["Deleted the environment production, with its secrets and variables."]
