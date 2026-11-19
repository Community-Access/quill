"""Release and deployment evidence, immutable releases and attestations (GX10, complete.md 1.3)."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from typing import Any

from quill.core.github import release_evidence as ev
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.sheet_engine import load
from quill.core.github.sheets_deploy import ENVIRONMENT
from quill.core.github.sheets_releases import RELEASE, RELEASE_ASSET

DIGEST = "sha256:" + "ab" * 32
SHA = "c0ffee" + "0" * 34


def _statement(predicate: str) -> dict[str, Any]:
    payload = base64.b64encode(json.dumps({"predicateType": predicate}).encode()).decode()
    return {"bundle": {"dsseEnvelope": {"payload": payload}}}


class FakeApi:
    """GET answers by path; an exception answer is raised. Every request is recorded."""

    def __init__(self, routes: Mapping[str, Any]) -> None:
        self.routes = dict(routes)
        self.asked: list[tuple[str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        assert method == "GET", "evidence only reads"
        self.asked.append((path, query))
        found = self.routes.get(path, GitHubRestError("Not Found", status=404))
        if isinstance(found, Exception):
            raise found
        return RestResponse(200, {}, found)

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        raise AssertionError("no GraphQL here")


def _release(**changes: Any) -> dict[str, Any]:
    release: dict[str, Any] = {
        "id": 7,
        "tag_name": "v1.0",
        "name": "One",
        "draft": False,
        "prerelease": False,
        "immutable": True,
        "published_at": "2026-11-01T10:00:00Z",
        "assets": [
            {"name": "app.zip", "digest": DIGEST, "size": 2048},
            {"name": "notes.txt", "size": 10},
        ],
    }
    release.update(changes)
    return release


def _routes(**more: Any) -> dict[str, Any]:
    routes: dict[str, Any] = {
        "/repos/o/r/releases/tags/v1.0": _release(),
        "/repos/o/r/commits/v1.0": {"sha": SHA},
        f"/repos/o/r/commits/{SHA}/status": {"statuses": [{"context": "lint", "state": "success"}]},
        f"/repos/o/r/commits/{SHA}/check-runs": {
            "check_runs": [
                {"name": "tests", "status": "completed", "conclusion": "success"},
                {"name": "docs", "status": "completed", "conclusion": "failure"},
            ]
        },
        "/repos/o/r/deployments": [
            {
                "id": 11,
                "environment": "production",
                "sha": SHA,
                "ref": "v1.0",
                "creator": {"login": "jeff"},
                "created_at": "2026-11-01T11:00:00Z",
            }
        ],
        "/repos/o/r/deployments/11/statuses": [
            {"state": "success", "created_at": "2026-11-01T11:05:00Z"}
        ],
        f"/repos/o/r/attestations/{DIGEST}": {
            "attestations": [_statement("https://slsa.dev/provenance/v1")]
        },
    }
    routes.update(more)
    return routes


def test_the_evidence_names_the_commit_checks_deployments_and_attestations() -> None:
    api = FakeApi(_routes())
    found = ev.load_release_evidence(api, "o/r", "v1.0")
    lines = found.lines()
    assert lines[0] == "One: release v1.0 in o/r."
    assert "Immutable: its tag and files cannot change." in lines
    assert f"Commit: {SHA}." in lines
    assert "Checks: 2 of 3 checks pass; failing: docs." in lines
    assert "Passed: lint, tests." in lines and "Failed: docs." in lines
    assert "production: success, 2026-11-01 11:05 by jeff (v1.0, commit c0ffee0)." in lines
    assert "app.zip (digest abababababab): 1 attestation: build provenance." in lines
    assert "notes.txt: GitHub gives no digest for it, so attestations cannot be looked up." in lines
    assert ev.VERIFY_NOTE in lines
    assert found.sentence == (
        "v1.0: Immutable; 2 of 3 checks pass; failing: docs; 1 deployments; 1 of 2 files attested."
    )
    assert ("/repos/o/r/deployments", {"sha": SHA, "per_page": "30"}) in api.asked


def test_not_immutable_none_deployed_and_no_attestations() -> None:
    api = FakeApi(
        _routes(**{
            "/repos/o/r/releases/tags/v1.0": _release(immutable=False),
            "/repos/o/r/deployments": [],
            f"/repos/o/r/attestations/{DIGEST}": GitHubRestError("nf", status=404),
        })
    )
    lines = ev.load_release_evidence(api, "o/r", "v1.0").lines()
    assert "Not immutable: its tag and files can still change." in lines
    assert "Deployments of this commit: none." in lines
    assert "app.zip (digest abababababab): no attestations." in lines
    assert ev.VERIFY_NOTE not in lines


def test_unreadable_is_said_as_unreadable_never_as_none() -> None:
    refused = GitHubRestError("Forbidden", status=403)
    api = FakeApi(
        _routes(**{
            "/repos/o/r/releases/tags/v1.0": _release(assets=[{"name": "a", "digest": DIGEST}]),
            "/repos/o/r/deployments": refused,
            f"/repos/o/r/commits/{SHA}/status": refused,
            f"/repos/o/r/attestations/{DIGEST}": refused,
        })
    )
    found = ev.load_release_evidence(api, "o/r", "v1.0")
    lines = found.lines()
    assert "Could not read the checks." in lines and "Could not read the deployments." in lines
    assert "Deployments of this commit: none." not in lines
    assert lines[-3].startswith("a (digest abababababab): attestations unreadable. It needs")


def test_a_draft_has_no_commit_yet_and_immutability_unsaid() -> None:
    draft = _release(draft=True, assets=[])
    draft.pop("immutable")
    api = FakeApi({"/repos/o/r/releases/tags/v1.0": draft})
    lines = ev.load_release_evidence(api, "o/r", "v1.0").lines()
    assert lines[0] == "One: draft v1.0 in o/r."
    assert "GitHub did not say whether it is immutable." in lines
    assert "Commit: the tag is not on GitHub yet." in lines and "Files: none." in lines
    assert all("/commits/" not in path for path, _q in api.asked)


def test_one_files_attestations_by_name() -> None:
    api = FakeApi(_routes())
    found = ev.attestations_for_asset(api, "o/r", "v1.0", "app.zip")
    assert found.attestations == 1 and found.kinds == ("build provenance",)
    gone = ev.attestations_for_asset(api, "o/r", "v1.0", "missing.bin")
    assert gone.line() == "v1.0 has no file called missing.bin now."


def test_an_environments_deployments_each_with_its_latest_state() -> None:
    api = FakeApi(
        _routes(**{"/repos/o/r/deployments/11/statuses": GitHubRestError("x", status=500)})
    )
    found = ev.environment_deployments(api, "o/r", "production", limit=5)
    assert ("/repos/o/r/deployments", {"environment": "production", "per_page": "5"}) in api.asked
    assert found[0].line() == (
        "production: status unreadable, 2026-11-01 11:00 by jeff (v1.0, commit c0ffee0)."
    )


def test_the_release_sheet_says_immutable_and_the_asset_sheet_its_digest() -> None:
    api = FakeApi(_routes(**{"/repos/o/r/releases/latest": _release()}))
    values = load(api, RELEASE, {"repo": "o/r", "tag": "v1.0"}).values
    assert values["immutable"] == "yes: its tag and files cannot change"
    asset = load(api, RELEASE_ASSET, {"repo": "o/r", "tag": "v1.0", "name": "app.zip"}).values
    assert asset["digest"] == DIGEST


def test_the_environment_sheet_counts_and_lists_its_protection() -> None:
    env = {
        "name": "production",
        "protection_rules": [{"type": "wait_timer", "wait_timer": 5}],
        "deployment_branch_policy": {"protected_branches": False},
    }
    api = FakeApi(
        _routes(**{
            "/repos/o/r/environments/production": env,
            "/repos/o/r/environments/production/secrets": {
                "total_count": 42,
                "secrets": [{"name": "TOKEN"}],
            },
            "/repos/o/r/environments/production/variables": {
                "total_count": 1,
                "variables": [{"name": "URL", "value": "https://x"}],
            },
            "/repos/o/r/environments/production/deployment_protection_rules": {
                "custom_deployment_protection_rules": [
                    {"enabled": True, "app": {"slug": "datadog"}}
                ]
            },
            "/repos/o/r/environments/production/deployment-branch-policies": {
                "branch_policies": [{"name": "release/*", "type": "branch"}]
            },
        })
    )
    values = load(api, ENVIRONMENT, {"repo": "o/r", "name": "production"}).values
    assert values["secret_count"] == 42 and values["secrets"] == ("TOKEN",)
    assert values["variable_count"] == 1
    assert values["custom_rules"] == ("datadog, on",)
    assert values["branch_policies"] == ("release/*, branch",)
    assert values["wait_timer"] == 5 and values["branches"] == "selected branches and tags"
    (deployed,) = values["deployments"]  # type: ignore[misc]
    assert str(deployed).startswith("v1.0, commit c0ffee0, by jeff, ")
    assert ("/repos/o/r/deployments", {"environment": "production", "per_page": "10"}) in api.asked
