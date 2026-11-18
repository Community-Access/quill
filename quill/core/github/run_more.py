"""More for a workflow run: one job again, force cancel, logs, approvals, attempts (PRD 19).

Beside the run commands in :mod:`quill.core.github.run_actions`: re-run one
job (optionally with debug logging), force-cancel a run stuck cancelling,
download or delete its logs, hear who approved its deployments, and read an
earlier attempt. A run's logs download through
:meth:`~quill.core.github.items_provider.GitHubItemsProvider.download_artifact_to_file`,
which already follows GitHub's redirect without sending the token on, so no
new network call site is added. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.items_provider import GitHubArtifact
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "RunMoreError",
    "approvals",
    "attempt",
    "delete_logs",
    "force_cancel",
    "jobs",
    "logs_download",
    "rerun_job",
]


class RunMoreError(CodedError):
    code = "QUILL-GITHUB-RUN-REFUSED"


def _run(repo: str, run_id: int) -> str:
    return f"/repos/{repo}/actions/runs/{int(run_id)}"


def _refused(exc: GitHubRestError, doing: str) -> RunMoreError:
    if exc.status in (401, 403):
        return RunMoreError(f"GitHub refused to {doing}. It needs write access to Actions.")
    if exc.status == 404:
        return RunMoreError(f"GitHub found nothing to {doing}.")
    if exc.status == 409:
        return RunMoreError(f"GitHub could not {doing} in the run's present state.")
    return RunMoreError(f"Could not {doing}: {exc}")


def jobs(api: GitHubApi, repo: str, run_id: int) -> list[tuple[int, str]]:
    """(job id, "name: conclusion") for each job of the run's latest attempt."""
    try:
        data = api.rest("GET", f"{_run(repo, run_id)}/jobs", query={"per_page": "100"}).data
    except GitHubRestError as exc:
        raise _refused(exc, "list the run's jobs") from exc
    found = []
    for raw in data.get("jobs", []) if isinstance(data, Mapping) else []:
        if isinstance(raw, Mapping) and raw.get("id"):
            state = str(raw.get("conclusion") or raw.get("status") or "")
            found.append((int(raw["id"]), f"{raw.get('name') or 'A job'}: {state or 'unknown'}"))
    return found


def rerun_job(api: GitHubApi, repo: str, job_id: int, *, debug: bool = False) -> str:
    try:
        api.rest(
            "POST",
            f"/repos/{repo}/actions/jobs/{int(job_id)}/rerun",
            body={"enable_debug_logging": debug},
        )
    except GitHubRestError as exc:
        raise _refused(exc, "re-run the job") from exc
    return "GitHub started the job again" + (", with debug logging." if debug else ".")


def force_cancel(api: GitHubApi, repo: str, run_id: int) -> str:
    try:
        api.rest("POST", f"{_run(repo, run_id)}/force-cancel")
    except GitHubRestError as exc:
        raise _refused(exc, "force-cancel the run") from exc
    return "GitHub is force-cancelling the run, skipping its cleanup steps."


def delete_logs(api: GitHubApi, repo: str, run_id: int) -> str:
    try:
        api.rest("DELETE", f"{_run(repo, run_id)}/logs")
    except GitHubRestError as exc:
        raise _refused(exc, "delete the run's logs") from exc
    return "Deleted the run's logs. The run itself is kept."


def logs_download(repo: str, run_id: int, attempt_number: int = 0) -> GitHubArtifact:
    """The run's logs as a download the artifact downloader can stream to a zip file."""
    tail = f"/attempts/{int(attempt_number)}/logs" if attempt_number else "/logs"
    url = f"https://api.github.com{_run(repo, run_id)}{tail}"
    name = f"run-{int(run_id)}" + (f"-attempt-{int(attempt_number)}" if attempt_number else "")
    return GitHubArtifact(
        id=int(run_id), name=f"{name}-logs", size_bytes=0, expired=False, archive_download_url=url
    )


def approvals(api: GitHubApi, repo: str, run_id: int) -> list[str]:
    """Each approval or rejection of the run's deployments, one sentence each."""
    try:
        data = api.rest("GET", f"{_run(repo, run_id)}/approvals").data
    except GitHubRestError as exc:
        raise _refused(exc, "read the run's approvals") from exc
    said = []
    for raw in data or ():
        if not isinstance(raw, Mapping):
            continue
        user = raw.get("user") if isinstance(raw.get("user"), Mapping) else {}
        assert isinstance(user, Mapping)
        state = str(raw.get("state") or "reviewed")
        places = ", ".join(
            str(env.get("name") or "")
            for env in raw.get("environments") or ()
            if isinstance(env, Mapping)
        )
        comment = str(raw.get("comment") or "").strip()
        said.append(
            f"{user.get('login') or 'Someone'} {state} {places or 'a deployment'}"
            + (f": {comment}" if comment else "")
            + "."
        )
    return said


def attempt(api: GitHubApi, repo: str, run_id: int, number: int) -> str:
    """One earlier attempt of the run, as a sentence."""
    try:
        data = api.rest("GET", f"{_run(repo, run_id)}/attempts/{int(number)}").data
    except GitHubRestError as exc:
        raise _refused(exc, f"read attempt {number}") from exc
    if not isinstance(data, Mapping):
        return f"GitHub sent nothing about attempt {number}."
    result: Any = data.get("conclusion") or data.get("status") or "unknown"
    started = str(data.get("run_started_at") or "")[:16].replace("T", " at ")
    actor = (
        data.get("triggering_actor") if isinstance(data.get("triggering_actor"), Mapping) else {}
    )
    assert isinstance(actor, Mapping)
    who = f", started by {actor.get('login')}" if actor.get("login") else ""
    return f"Attempt {number}: {result}" + (f", {started}" if started else "") + f"{who}."
