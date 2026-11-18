"""The second sweep of list-shaped settings, and the engine's repository and names fields."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import resource_engine as engine
from quill.core.github.resource_specs import spec_for
from quill.core.github.resource_specs_env import environment_spec
from quill.core.github.resource_specs_env_more import protection_apps
from quill.core.github.rest_transport import GitHubRestError, RestResponse


class _Api:
    def __init__(self, replies: dict[str, Any] | None = None) -> None:
        self.replies = replies or {}
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> RestResponse:
        self.sent.append((method, path, body))
        if f"{method} {path}" in self.replies:
            reply = self.replies[f"{method} {path}"]
            if isinstance(reply, Exception):
                raise reply
            return RestResponse(200, {}, reply)
        return RestResponse(200, {}, {} if method != "GET" else [])


def test_a_chosen_repository_is_added_by_name_and_said_by_name() -> None:
    api = _Api({"GET /repos/acme/site": {"id": 42, "full_name": "acme/site"}})
    said = engine.create(
        api, spec_for("org_immutable_release_repos"), "acme", {"repository": "site"}
    )
    assert api.sent[-1] == ("PUT", "/orgs/acme/settings/immutable-releases/repositories/42", {})
    assert said == "Added the repository acme/site."
    api = _Api({"GET /repos/other/x": GitHubRestError("no", status=404)})
    with pytest.raises(engine.ResourceError, match="other/x"):
        engine.create(api, spec_for("org_actions_repos"), "acme", {"repository": "other/x"})


def test_an_issue_field_sends_its_choices_as_named_options() -> None:
    api = _Api()
    engine.create(
        api,
        spec_for("org_issue_fields"),
        "acme",
        {
            "name": "Priority",
            "data_type": "single_select",
            "options": "High, Low",
            "visibility": "",
        },
    )
    method, path, body = api.sent[-1]
    assert (method, path) == ("POST", "/orgs/acme/issue-fields")
    assert body == {
        "name": "Priority",
        "data_type": "single_select",
        "options": [{"name": "High"}, {"name": "Low"}],
    }
    rows = engine.fetch(
        _Api({
            "GET /user/issue-fields": {
                "issue_fields": [
                    {
                        "id": 3,
                        "name": "Size",
                        "data_type": "single_select",
                        "options": [{"name": "S"}],
                    }
                ]
            }
        }),
        spec_for("my_issue_fields"),
        "",
    )
    assert rows[0].label == "Size, single select: S." and rows[0].key == "my_issue_fields:3"


@pytest.mark.parametrize(
    ("key", "raw", "said"),
    [
        (
            "my_installations",
            {
                "id": 1,
                "app_slug": "netlify",
                "account": {"login": "jeff"},
                "repository_selection": "all",
            },
            "netlify on jeff, all repositories.",
        ),
        (
            "org_failed_invitations",
            {
                "id": 1,
                "login": "kim",
                "failed_reason": "Invitation expired",
                "failed_at": "2026-11-01T00:00:00Z",
            },
            "kim: Invitation expired, 2026-11-01.",
        ),
        (
            "org_events",
            {
                "id": "9",
                "type": "PushEvent",
                "actor": {"login": "jeff"},
                "repo": {"name": "acme/site"},
            },
            "jeff: Push in acme/site.",
        ),
        (
            "repo_rule_insights",
            {"id": 4, "result": "fail", "actor_name": "kim", "ref": "refs/heads/main"},
            "Blocked: kim pushed to main.",
        ),
        (
            "codeowners_errors",
            {"line": 3, "message": "Unknown owner @ghost"},
            "Line 3: Unknown owner @ghost.",
        ),
        ("repo_property_values", {"property_name": "team", "value": "docs"}, "team is docs."),
    ],
)
def test_rows_read_as_sentences(key: str, raw: dict[str, Any], said: str) -> None:
    spec = spec_for(key)
    assert spec is not None and spec.sentence(raw) == said


def test_environment_policies_and_protection_apps() -> None:
    target = "o/r/environments/prod"
    policies = environment_spec("environment_branch_policies")
    assert policies is not None
    api = _Api({
        f"GET /repos/{target}/deployment-branch-policies": {
            "branch_policies": [{"id": 7, "name": "release/*", "type": "branch"}]
        }
    })
    assert engine.fetch(api, policies, target)[0].label == "Branches matching release/* may deploy."
    rules = environment_spec("environment_protection_rules")
    assert rules is not None
    api = _Api({
        f"GET /repos/{target}/deployment_protection_rules/apps": {
            "available_custom_deployment_protection_rule_integrations": [
                {"id": 11, "slug": "gatekeeper"}
            ]
        }
    })
    assert protection_apps(api, target) == [("11", "gatekeeper")]
    engine.create(api, rules, target, {"integration_id": "11"})
    assert api.sent[-1] == (
        "POST",
        f"/repos/{target}/deployment_protection_rules",
        {"integration_id": 11},
    )
    with pytest.raises(engine.ResourceError, match="number"):
        engine.create(api, rules, target, {"integration_id": "eleven"})
