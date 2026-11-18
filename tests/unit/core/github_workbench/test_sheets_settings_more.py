"""More settings on the Repository and Organization sheets (GitHub PRD sections 15 and 19)."""

from __future__ import annotations

from typing import Any

from quill.core.github import sheets_settings_more as more
from quill.core.github.rest_transport import RestResponse
from quill.core.github.sheet_catalog import SHEETS
from quill.core.github.sheet_engine import load, plan
from quill.core.workbench.properties import FieldChange

REPO = {"repo": "o/r", "owner": "o", "name": "r"}
ORG = {"org": "acme"}


class Answers:
    """GitHub's answers by path; anything else answers with nothing set."""

    def __init__(self, found: dict[str, Any]) -> None:
        self.found = found

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        return RestResponse(200, {}, self.found.get(path, {}))

    def graphql(self, *_a: Any) -> Any:
        return {}


def _change(key: str, before: Any, after: Any) -> FieldChange:
    return FieldChange(key, key, before, after)


def test_both_sheets_gain_their_pages_and_every_new_field_can_be_saved() -> None:
    for kind in ("repository", "organization"):
        sheet = SHEETS[kind]
        keys = [one.key for one in sheet.sheet.pages]
        for page in more.extra_pages(kind):
            assert page.key in keys
            for spec in page.fields:
                assert spec.key in sheet.writes, (kind, spec.key)
    assert more.with_more_settings(SHEETS["issue"]) is SHEETS["issue"]


def test_the_repository_settings_read_in_words() -> None:
    api = Answers({
        "/repos/o/r/actions/permissions/artifact-and-log-retention": {"days": 30},
        "/repos/o/r/actions/permissions/fork-pr-contributor-approval": {
            "approval_policy": "first_time_contributors"
        },
        "/repos/o/r/actions/permissions/selected-actions": {
            "github_owned_allowed": True,
            "verified_allowed": False,
            "patterns_allowed": ["octo-org/*"],
        },
        "/repos/o/r/immutable-releases": {"enabled": True},
        "/repos/o/r/code-scanning/default-setup": {"state": "not-configured"},
    })
    values = load(api, SHEETS["repository"], REPO).values
    assert values["retention_days"] == 30
    assert values["fork_approval"] == "first time contributors"
    assert values["patterns_allowed"] == ("octo-org/*",)
    assert values["immutable_releases"] is True
    assert values["scanning_setup"] == "not configured"


def test_repository_changes_become_github_s_own_requests() -> None:
    sheet = SHEETS["repository"]
    found = plan(
        sheet,
        REPO,
        [
            _change("retention_days", 90, "30"),
            _change("fork_approval", "first time contributors", "all outside contributors"),
            _change("github_owned_allowed", False, True),
            _change("patterns_allowed", (), ("octo-org/*",)),
            _change("immutable_releases", False, True),
            _change("scanning_setup", "not configured", "configured"),
        ],
    )
    sent = {(r.method, r.path): r.body for r in found}
    assert sent[("PUT", "/repos/o/r/actions/permissions/artifact-and-log-retention")] == {
        "days": 30
    }
    assert sent[("PUT", "/repos/o/r/actions/permissions/fork-pr-contributor-approval")] == {
        "approval_policy": "all_external_contributors"
    }
    assert sent[("PUT", "/repos/o/r/actions/permissions/selected-actions")] == {
        "github_owned_allowed": True,
        "patterns_allowed": ["octo-org/*"],
    }
    assert ("PUT", "/repos/o/r/immutable-releases") in sent
    assert sent[("PATCH", "/repos/o/r/code-scanning/default-setup")] == {"state": "configured"}


def test_organization_changes_and_lifting_an_interaction_limit() -> None:
    sheet = SHEETS["organization"]
    found = plan(
        sheet,
        ORG,
        [
            _change("org_token_permission", "read", "write"),
            _change("self_hosted_repositories", "all", "selected"),
            _change("org_interaction_limit", "none", "existing users"),
        ],
    )
    sent = {(r.method, r.path): r.body for r in found}
    assert sent[("PUT", "/orgs/acme/actions/permissions/workflow")] == {
        "default_workflow_permissions": "write"
    }
    assert sent[("PUT", "/orgs/acme/actions/permissions/self-hosted-runners")] == {
        "enabled_repositories": "selected"
    }
    assert sent[("PUT", "/orgs/acme/interaction-limits")] == {
        "limit": "existing_users",
        "expiry": "one_week",
    }
    lifted = plan(sheet, ORG, [_change("org_interaction_limit", "existing users", "none")])
    assert [(r.method, r.path) for r in lifted] == [("DELETE", "/orgs/acme/interaction-limits")]


def test_an_organization_without_a_limit_reads_none() -> None:
    values = load(Answers({}), SHEETS["organization"], ORG).values
    assert values["org_interaction_limit"] == "none"
