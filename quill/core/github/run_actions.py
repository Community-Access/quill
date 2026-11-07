"""Workflow run and check actions for ``GitHubItemsProvider`` (Wave 1).

Rerun only the failed jobs, cancel or delete a run, re-request one check run,
approve a run from a fork, review a run's pending deployments, and read the
one-line combined status of a commit. PyGithub has no call for several of
these, so every one goes through :func:`~quill.core.github.rest_transport.request_json`,
which keeps the token on ``api.github.com``.

Each write states what GitHub actually confirmed. ``cancel`` is answered 202
(accepted, finishing in the background), so its caller says "GitHub is
cancelling", never "cancelled".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import (
    GitHubRestError,
    RestResponse,
    request_json,
    rest_failure_message,
)

_PASSING = frozenset({"success", "neutral", "skipped"})
_FAILING = frozenset({
    "failure",
    "error",
    "cancelled",
    "timed_out",
    "action_required",
    "startup_failure",
    "stale",
})


def repo_path(full_name: str) -> str:
    """``/repos/owner/name`` for a validated ``owner/name``."""
    parts = full_name.split("/")
    if (
        len(parts) != 2
        or not all(parts)
        or any(not all(char.isalnum() or char in "-_." for char in part) for part in parts)
    ):
        raise GitHubItemsError("Enter a repository as owner/repo first.")
    return f"/repos/{parts[0]}/{parts[1]}"


def _positive(value: int, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GitHubItemsError(f"This {what} has no GitHub ID.")
    return value


@dataclass(frozen=True, slots=True)
class PendingDeployment:
    """One environment a run is waiting on."""

    environment_id: int
    environment: str
    can_approve: bool
    reviewers: tuple[str, ...] = ()
    wait_timer_minutes: int = 0
    url: str = ""

    @property
    def label(self) -> str:
        who = ", ".join(self.reviewers) if self.reviewers else "no named reviewers"
        mine = "you can approve" if self.can_approve else "you cannot approve"
        wait = f"; wait timer {self.wait_timer_minutes} minutes" if self.wait_timer_minutes else ""
        return f"{self.environment}: {mine}; reviewers {who}{wait}"


def parse_pending_deployments(data: object) -> tuple[PendingDeployment, ...]:
    rows = data if isinstance(data, list) else []
    out: list[PendingDeployment] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        env = row.get("environment") if isinstance(row.get("environment"), dict) else {}
        reviewers: list[str] = []
        for entry in row.get("reviewers") or ():
            reviewer = entry.get("reviewer") if isinstance(entry, dict) else None
            if isinstance(reviewer, dict):
                name = reviewer.get("login") or reviewer.get("slug") or reviewer.get("name")
                if name:
                    reviewers.append(str(name))
        try:
            env_id = int(env.get("id") or 0) if isinstance(env, dict) else 0
            wait = int(row.get("wait_timer") or 0)
        except (TypeError, ValueError):
            env_id, wait = 0, 0
        out.append(
            PendingDeployment(
                environment_id=env_id,
                environment=str(env.get("name", "") if isinstance(env, dict) else "") or "unnamed",
                can_approve=bool(row.get("current_user_can_approve")),
                reviewers=tuple(reviewers),
                wait_timer_minutes=wait,
                url=str(env.get("html_url", "") if isinstance(env, dict) else ""),
            )
        )
    return tuple(out)


@dataclass(frozen=True, slots=True)
class CheckOutcome:
    name: str
    state: str  # "pass", "fail" or "pending"


@dataclass(frozen=True, slots=True)
class CombinedCheckStatus:
    """Statuses and check runs for one commit, folded into one sentence."""

    ref: str
    checks: tuple[CheckOutcome, ...]
    required: tuple[str, ...] = ()

    def _scope(self) -> tuple[list[CheckOutcome], list[str]]:
        if not self.required:
            return list(self.checks), []
        by_name = {check.name: check for check in self.checks}
        present = [by_name[name] for name in self.required if name in by_name]
        missing = [name for name in self.required if name not in by_name]
        return present, missing

    def one_line(self) -> str:
        scoped, missing = self._scope()
        total = len(scoped) + len(missing)
        word = ("required check" if self.required else "check") + ("" if total == 1 else "s")
        if total == 0:
            return "No checks have reported on this commit."
        passing = sum(1 for check in scoped if check.state == "pass")
        failing = [check.name for check in scoped if check.state == "fail"]
        pending = sum(1 for check in scoped if check.state == "pending")
        verb = "passes" if total == 1 else "pass"
        parts = [f"{passing} of {total} {word} {verb}"]
        if failing:
            parts.append("failing: " + ", ".join(failing))
        if pending:
            parts.append(f"{pending} still running")
        if missing:
            parts.append("not reported yet: " + ", ".join(missing))
        return "; ".join(parts) + "."


def _outcome(status: str, conclusion: str) -> str:
    if status and status != "completed":
        return "pending"
    if conclusion in _PASSING:
        return "pass"
    if conclusion in _FAILING:
        return "fail"
    return "pending"


def combine_check_status(
    ref: str, status_data: object, check_data: object, required: tuple[str, ...] = ()
) -> CombinedCheckStatus:
    """Fold ``GET /commits/{ref}/status`` and ``/check-runs`` into one result."""
    outcomes: dict[str, CheckOutcome] = {}
    statuses = status_data.get("statuses") if isinstance(status_data, dict) else None
    for row in statuses if isinstance(statuses, list) else ():
        if isinstance(row, dict) and row.get("context"):
            state = str(row.get("state") or "")
            mapped = "pass" if state == "success" else "pending" if state == "pending" else "fail"
            outcomes.setdefault(str(row["context"]), CheckOutcome(str(row["context"]), mapped))
    runs = check_data.get("check_runs") if isinstance(check_data, dict) else None
    for row in runs if isinstance(runs, list) else ():
        if isinstance(row, dict) and row.get("name"):
            name = str(row["name"])
            outcomes.setdefault(
                name,
                CheckOutcome(
                    name, _outcome(str(row.get("status") or ""), str(row.get("conclusion") or ""))
                ),
            )
    return CombinedCheckStatus(ref, tuple(outcomes.values()), tuple(dict.fromkeys(required)))


class _RunAccess(Protocol):
    _token: str | None

    def _require_write_access(self, action: str) -> None: ...


def _call(
    action: str, call: Callable[[], RestResponse], *, expect: tuple[int, ...]
) -> RestResponse:
    try:
        response = call()
    except GitHubRestError as exc:
        raise GitHubItemsError(rest_failure_message(action, exc)) from exc
    if response.status not in expect:
        raise GitHubItemsError(
            f"Could not {action}. GitHub answered HTTP {response.status} without confirming it."
        )
    return response


def _post(provider: _RunAccess, action: str, path: str, expect: tuple[int, ...]) -> int:
    provider._require_write_access(action)
    response = _call(action, lambda: request_json(provider._token, "POST", path), expect=expect)
    return response.status


class GitHubRunActionsMixin:
    """REST-only run and check writes, each confirmed by GitHub's status code."""

    def rerun_failed_jobs(self: _RunAccess, full_name: str, run_id: int) -> None:
        path = f"{repo_path(full_name)}/actions/runs/{_positive(run_id, 'run')}/rerun-failed-jobs"
        _post(self, "re-run the failed jobs", path, (201,))

    def cancel_workflow_run(self: _RunAccess, full_name: str, run_id: int) -> None:
        """GitHub answers 202: the cancel is accepted and finishes in the background."""
        path = f"{repo_path(full_name)}/actions/runs/{_positive(run_id, 'run')}/cancel"
        _post(self, "cancel the run", path, (202,))

    def approve_fork_run(self: _RunAccess, full_name: str, run_id: int) -> None:
        path = f"{repo_path(full_name)}/actions/runs/{_positive(run_id, 'run')}/approve"
        _post(self, "approve the run from a fork", path, (201,))

    def rerequest_check_run(self: _RunAccess, full_name: str, check_run_id: int) -> None:
        path = f"{repo_path(full_name)}/check-runs/{_positive(check_run_id, 'check')}/rerequest"
        _post(self, "re-request the check", path, (201,))

    def delete_workflow_run(self: _RunAccess, full_name: str, run_id: int) -> None:
        self._require_write_access("delete a workflow run")
        path = f"{repo_path(full_name)}/actions/runs/{_positive(run_id, 'run')}"
        _call("delete the run", lambda: request_json(self._token, "DELETE", path), expect=(204,))

    def fetch_pending_deployments(
        self: _RunAccess, full_name: str, run_id: int
    ) -> tuple[PendingDeployment, ...]:
        self._require_write_access("read pending deployments")
        path = f"{repo_path(full_name)}/actions/runs/{_positive(run_id, 'run')}/pending_deployments"
        response = _call(
            "load pending deployments",
            lambda: request_json(self._token, "GET", path),
            expect=(200,),
        )
        return parse_pending_deployments(response.data)

    def review_pending_deployments(
        self: _RunAccess,
        full_name: str,
        run_id: int,
        environment_ids: list[int],
        *,
        approve: bool,
        comment: str,
    ) -> tuple[str, ...]:
        """Approve or reject the chosen environments; return the ones GitHub confirmed."""
        verb = "approve" if approve else "reject"
        if not environment_ids:
            raise GitHubItemsError(f"Choose at least one environment to {verb}.")
        if not comment.strip():
            raise GitHubItemsError("GitHub needs a comment to go with the review.")
        self._require_write_access(f"{verb} deployments")
        path = f"{repo_path(full_name)}/actions/runs/{_positive(run_id, 'run')}/pending_deployments"
        body: dict[str, object] = {
            "environment_ids": [int(value) for value in environment_ids],
            "state": "approved" if approve else "rejected",
            "comment": comment.strip(),
        }
        response = _call(
            f"{verb} the deployments",
            lambda: request_json(self._token, "POST", path, body=body),
            expect=(200, 201),
        )
        rows = response.data if isinstance(response.data, list) else []
        names: list[str] = []
        for row in rows:
            env = row.get("environment") if isinstance(row, dict) else None
            name = env if isinstance(env, str) else env.get("name") if isinstance(env, dict) else ""
            if name:
                names.append(str(name))
        return tuple(names)

    def fetch_combined_check_status(
        self: _RunAccess, full_name: str, ref: str, *, required: tuple[str, ...] = ()
    ) -> CombinedCheckStatus:
        if not ref or len(ref) > 256 or any(ord(char) < 33 for char in ref):
            raise GitHubItemsError("This item has no commit to read checks for.")
        base = f"{repo_path(full_name)}/commits/{quote(ref, safe='')}"
        status: Any = _call(
            "read the commit status",
            lambda: request_json(self._token, "GET", f"{base}/status"),
            expect=(200,),
        ).data
        checks: Any = _call(
            "read the check runs",
            lambda: request_json(
                self._token, "GET", f"{base}/check-runs", query={"per_page": "100"}
            ),
            expect=(200,),
        ).data
        return combine_check_status(ref, status, checks, required)


__all__ = [
    "CheckOutcome",
    "CombinedCheckStatus",
    "GitHubRunActionsMixin",
    "PendingDeployment",
    "combine_check_status",
    "parse_pending_deployments",
    "repo_path",
]
