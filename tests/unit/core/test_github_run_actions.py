"""Workflow run and check actions: endpoints, confirmation of success, combined status."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import run_actions
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.run_actions import (
    GitHubRunActionsMixin,
    combine_check_status,
    parse_pending_deployments,
)


class _Provider(GitHubRunActionsMixin):
    def __init__(self, token: str | None = "tok") -> None:
        self._token = token

    def _require_write_access(self, action: str) -> None:
        if not self._token:
            raise GitHubItemsError(f"To {action} you need a signed-in GitHub account.")


class _Api:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []
        self.replies: dict[tuple[str, str], RestResponse] = {}

    def __call__(self, token, method, path, *, body=None, query=None, **_kw):
        self.calls.append((method, path, body))
        return self.replies.get((method, path), RestResponse(200, {}, None))


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> _Api:
    fake = _Api()
    monkeypatch.setattr(run_actions, "request_json", fake)
    return fake


RUN = "/repos/o/r/actions/runs/9"


@pytest.mark.parametrize(
    ("method_name", "method", "path", "status"),
    [
        ("rerun_failed_jobs", "POST", RUN + "/rerun-failed-jobs", 201),
        ("cancel_workflow_run", "POST", RUN + "/cancel", 202),
        ("approve_fork_run", "POST", RUN + "/approve", 201),
        ("delete_workflow_run", "DELETE", RUN, 204),
    ],
)
def test_run_writes_hit_their_endpoint_and_need_github_to_confirm(
    api: _Api, method_name: str, method: str, path: str, status: int
) -> None:
    api.replies[(method, path)] = RestResponse(status, {}, None)
    getattr(_Provider(), method_name)("o/r", 9)
    assert api.calls == [(method, path, None)]
    api.replies[(method, path)] = RestResponse(200, {}, None)
    with pytest.raises(GitHubItemsError, match="without confirming"):
        getattr(_Provider(), method_name)("o/r", 9)


def test_rerequest_check_run(api: _Api) -> None:
    api.replies[("POST", "/repos/o/r/check-runs/55/rerequest")] = RestResponse(201)
    _Provider().rerequest_check_run("o/r", 55)
    assert api.calls[-1][1] == "/repos/o/r/check-runs/55/rerequest"


def test_writes_refuse_bad_ids_bad_repos_and_signed_out(api: _Api) -> None:
    with pytest.raises(GitHubItemsError, match="no GitHub ID"):
        _Provider().cancel_workflow_run("o/r", 0)
    with pytest.raises(GitHubItemsError, match="owner/repo"):
        _Provider().cancel_workflow_run("o/r/../x", 1)
    with pytest.raises(GitHubItemsError, match="signed-in"):
        _Provider(token=None).delete_workflow_run("o/r", 1)
    assert api.calls == []


def test_failure_carries_the_next_step(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a, **_k):
        raise GitHubRestError("Resource not accessible", status=403, data={"message": "nope"})

    monkeypatch.setattr(run_actions, "request_json", refuse)
    with pytest.raises(GitHubItemsError) as caught:
        _Provider().cancel_workflow_run("o/r", 3)
    text = str(caught.value)
    assert "Could not cancel the run." in text
    assert "token permissions" in text and "GitHub said: nope" in text


def test_pending_deployments_are_listed_and_reviewed(api: _Api) -> None:
    api.replies[("GET", RUN + "/pending_deployments")] = RestResponse(
        200,
        {},
        [
            {
                "environment": {"id": 7, "name": "production", "html_url": "u"},
                "wait_timer": 5,
                "current_user_can_approve": True,
                "reviewers": [{"type": "User", "reviewer": {"login": "jeff"}}],
            }
        ],
    )
    api.replies[("POST", RUN + "/pending_deployments")] = RestResponse(
        200, {}, [{"environment": "production"}]
    )
    (pending,) = _Provider().fetch_pending_deployments("o/r", 9)
    assert pending.environment_id == 7 and pending.can_approve
    assert pending.label == "production: you can approve; reviewers jeff; wait timer 5 minutes"
    confirmed = _Provider().review_pending_deployments(
        "o/r", 9, [7], approve=False, comment=" not today "
    )
    assert confirmed == ("production",)
    assert api.calls[-1] == (
        "POST",
        RUN + "/pending_deployments",
        {"environment_ids": [7], "state": "rejected", "comment": "not today"},
    )


def test_review_needs_a_comment_and_an_environment(api: _Api) -> None:
    with pytest.raises(GitHubItemsError, match="needs a comment"):
        _Provider().review_pending_deployments("o/r", 9, [1], approve=True, comment=" ")
    with pytest.raises(GitHubItemsError, match="at least one environment"):
        _Provider().review_pending_deployments("o/r", 9, [], approve=True, comment="ok")
    assert api.calls == []


def test_parse_pending_tolerates_partial_rows() -> None:
    (row,) = parse_pending_deployments([{"environment": None}, "junk"][:1])
    assert row.environment == "unnamed" and not row.can_approve


STATUS = {"statuses": [{"context": "lint", "state": "success"}]}
CHECKS = {
    "check_runs": [
        {"name": "build", "status": "completed", "conclusion": "success"},
        {"name": "test", "status": "completed", "conclusion": "failure"},
        {"name": "docs", "status": "in_progress", "conclusion": None},
    ]
}


def test_combined_status_counts_required_checks() -> None:
    status = combine_check_status("abc", STATUS, CHECKS, ("lint", "build", "test", "deploy"))
    assert status.one_line() == (
        "2 of 4 required checks pass; failing: test; not reported yet: deploy."
    )


def test_combined_status_without_required_counts_everything() -> None:
    status = combine_check_status("abc", STATUS, CHECKS)
    assert status.one_line() == "2 of 4 checks pass; failing: test; 1 still running."
    assert combine_check_status("abc", {}, {}).one_line() == (
        "No checks have reported on this commit."
    )


def test_fetch_combined_status_reads_both_endpoints(api: _Api) -> None:
    base = "/repos/o/r/commits/abc"
    api.replies[("GET", base + "/status")] = RestResponse(200, {}, STATUS)
    api.replies[("GET", base + "/check-runs")] = RestResponse(200, {}, CHECKS)
    line = _Provider().fetch_combined_check_status("o/r", "abc", required=("lint",)).one_line()
    assert line == "1 of 1 required check passes."
