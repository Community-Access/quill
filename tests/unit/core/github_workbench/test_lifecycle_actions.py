"""Actions, end to end over recorded answers (complete.md 1.3, "Verify ... Actions").

Workflows, runs, jobs, logs, artifacts, caches, variables and secrets: list,
open, Properties, the writes the Workbench offers, and the three refusals:
GitHub says no (403), the thing is gone (404 or 410: a deleted run, a log or
artifact past its retention) and the account is Read Only in the Workbench.

Already proved elsewhere, and not repeated here: run writes hit their
endpoints and need GitHub to confirm (test_github_run_actions.py), one job
again, force cancel and logs (test_run_more.py), workflow on and off
(test_workflow_state_and_invitations.py), caches listed and deleted
(test_github_wave4_actions.py), a job log's redirect and bounds
(test_github_workflow_job_logs.py), artifacts downloaded
(ui/test_github_artifacts_dialog.py), variables made, changed and deleted
(ui/test_github_workbench_resources.py) and secrets kept write-only
(test_secrets_write_only.py, ui/test_github_workbench_secret_writes.py).
"""

from __future__ import annotations

import io
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from quill.core.github import resource_engine as engine
from quill.core.github import run_more
from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.items_provider import GitHubArtifact, GitHubItemsProvider
from quill.core.github.permissions import AccessLevel, ViewerContext, WriteTier
from quill.core.github.resource_specs import RESOURCE_SPECS
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.sheet_catalog import SHEETS, target_for
from quill.core.github.sheet_engine import load, locked_fields, save
from quill.core.github.workflow_state import WorkflowStateError, set_enabled
from quill.core.github.write_gate import command_refusal, gated_tier
from quill.core.workbench.properties import FieldChange
from tests.github_api_fake import FakeGitHubApi

REPO = "o/r"
ACT = f"/repos/{REPO}/actions"
SPECS = {spec.key: spec for spec in RESOURCE_SPECS}


def _refused(status: int, message: str = "Resource not accessible by integration") -> Exception:
    return GitHubRestError(message, status=status, data={"message": message})


# -- workflows ------------------------------------------------------------------------


def _workflow(state: str) -> dict[str, Any]:
    return {
        "id": 11,
        "name": "CI",
        "path": ".github/workflows/ci.yml",
        "state": state,
        "created_at": "2026-11-01T09:00:00Z",
        "updated_at": "2026-11-02T09:00:00Z",
        "html_url": "https://github.com/o/r/actions/workflows/ci.yml",
        "badge_url": "https://github.com/o/r/workflows/CI/badge.svg",
    }


def test_a_workflow_opens_and_turning_it_off_on_its_sheet_sends_disable_and_reads_back() -> None:
    api = FakeGitHubApi()
    state = {"now": "active"}
    api.on_write = lambda method, path, _body: state.update(
        now="disabled_manually" if path.endswith("/disable") else "active"
    )
    api.answer("GET", f"{ACT}/workflows/11", lambda: _workflow(state["now"]))
    ident = {"repo": REPO, "id": "11", "name": "CI"}
    sheet = SHEETS["workflow"]
    loaded = load(api, sheet, ident)
    assert loaded.values["enabled"] is True and loaded.values["path"].endswith("ci.yml")
    assert loaded.values["badge"].endswith("badge.svg")
    outcome = save(
        api, sheet, ident, [FieldChange("enabled", "Enabled", True, False)], loaded=loaded.values
    )
    assert api.writes() == [("PUT", f"{ACT}/workflows/11/disable", None)]
    assert [c.key for c in outcome.done] == ["enabled"] and not outcome.failed
    assert sheet.title(ident) == "Workflow CI"


def test_a_workflow_github_will_not_turn_off_is_reported_failed_not_done() -> None:
    api = FakeGitHubApi()
    api.answer("GET", f"{ACT}/workflows/11", _workflow("active"))
    api.answer("PUT", f"{ACT}/workflows/11/disable", _refused(403))
    ident = {"repo": REPO, "id": "11"}
    loaded = load(api, SHEETS["workflow"], ident)
    outcome = save(
        api,
        SHEETS["workflow"],
        ident,
        [FieldChange("enabled", "Enabled", True, False)],
        loaded=loaded.values,
    )
    assert outcome.done == [] and [c.key for c, _why in outcome.failed] == ["enabled"]


@pytest.mark.parametrize(
    ("status", "said"),
    [
        (
            403,
            "GitHub refused to turn CI off. It needs write access to Actions in this repository.",
        ),
        (
            404,
            "GitHub found nothing to turn CI off: it was deleted, or this account cannot see it.",
        ),
        (401, "Could not turn CI off: GitHub no longer accepts this sign-in. Sign in again."),
    ],
)
def test_turning_a_workflow_off_says_why_github_refused_in_plain_words(
    status: int, said: str
) -> None:
    api = FakeGitHubApi()
    api.answer("PUT", f"{ACT}/workflows/11/disable", _refused(status))
    with pytest.raises(WorkflowStateError) as caught:
        set_enabled(api, REPO, 11, "CI", False)
    assert caught.value.args[0] == said


class _Workflow:
    def __init__(self, error: Exception | None) -> None:
        self.error = error

    def create_dispatch(self, ref: str, inputs: dict[str, str]) -> bool:
        if self.error is not None:
            raise self.error
        return True


class _Repo:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.reran: list[int] = []

    def get_workflow(self, _workflow_id: str) -> _Workflow:
        return _Workflow(self.error)

    def get_workflow_run(self, run_id: int) -> Any:
        if self.error is not None:
            raise self.error
        return type("Run", (), {"rerun": lambda _self: self.reran.append(run_id)})()


def _provider(repo: _Repo, token: str | None = "tok") -> GitHubItemsProvider:
    provider = GitHubItemsProvider.__new__(GitHubItemsProvider)
    provider._token = token
    provider._repo = lambda _full_name: repo  # type: ignore[method-assign]
    return provider


def test_starting_a_workflow_without_a_dispatch_trigger_says_why() -> None:
    error = _refused(422, "Workflow does not have 'workflow_dispatch' trigger")
    with pytest.raises(GitHubItemsError) as caught:
        _provider(_Repo(error)).dispatch_workflow(REPO, "ci.yml", "main")
    assert caught.value.args[0] == (
        "GitHub could not start ci.yml on main in its present state: "
        "Workflow does not have 'workflow_dispatch' trigger."
    )
    _provider(_Repo()).dispatch_workflow(REPO, "ci.yml", "main")  # and starts when it does


def test_a_workflow_needs_a_signed_in_account_to_start_or_run_again() -> None:
    with pytest.raises(GitHubItemsError, match="signed-in GitHub account"):
        _provider(_Repo(), token=None).dispatch_workflow(REPO, "ci.yml", "main")
    with pytest.raises(GitHubItemsError, match="signed-in GitHub account"):
        _provider(_Repo(), token=None).rerun_workflow_run(REPO, 5)


# -- runs and jobs --------------------------------------------------------------------


def _run_api() -> FakeGitHubApi:
    api = FakeGitHubApi()
    api.answer(
        "GET",
        f"{ACT}/runs/5",
        {
            "name": "CI",
            "run_number": 42,
            "run_attempt": 2,
            "status": "completed",
            "conclusion": "failure",
            "event": "push",
            "head_branch": "main",
            "head_sha": "abc1234",
            "actor": {"login": "jeff"},
            "created_at": "2026-11-09T14:05:00Z",
            "html_url": "https://github.com/o/r/actions/runs/5",
        },
    )
    api.answer(
        "GET",
        f"{ACT}/runs/5/jobs",
        {"jobs": [{"name": "test", "conclusion": "failure"}, {"name": "lint", "status": "queued"}]},
    )
    api.answer(
        "GET", f"{ACT}/runs/5/artifacts", {"artifacts": [{"name": "wheel", "size_in_bytes": 4096}]}
    )
    api.answer("GET", f"{ACT}/runs/5/timing", {"run_duration_ms": 125_000})
    return api


def test_a_run_opens_with_its_jobs_artifacts_and_how_long_it_took() -> None:
    loaded = load(_run_api(), SHEETS["run"], {"repo": REPO, "id": "5", "number": "42"})
    values = loaded.values
    assert (values["number"], values["attempt"], values["conclusion"]) == (42, 2, "failure")
    assert values["actor"] == "jeff" and values["branch"] == "main"
    assert values["jobs"] == ("test, failure", "lint, queued")
    assert values["artifacts"] == ("wheel, 4 KB",)
    assert values["duration"] == "2 minutes 5 seconds"
    assert SHEETS["run"].writes == {}  # a run is changed by commands, never by its sheet


def test_a_run_whose_usage_github_hides_still_opens_and_says_what_is_missing() -> None:
    api = _run_api()
    api.answer("GET", f"{ACT}/runs/5/timing", _refused(403))
    loaded = load(api, SHEETS["run"], {"repo": REPO, "id": "5"})
    assert loaded.values["jobs"] and "duration" not in loaded.values
    assert loaded.missing == (ACT.replace(REPO, "{repo}") + "/runs/{id}/timing",)


def test_a_deleted_run_does_not_open_as_an_empty_sheet() -> None:
    with pytest.raises(GitHubRestError) as caught:
        load(FakeGitHubApi(), SHEETS["run"], {"repo": REPO, "id": "5"})
    assert caught.value.status == 404


def test_a_job_opens_with_each_step_and_how_it_ended() -> None:
    api = FakeGitHubApi()
    api.answer(
        "GET",
        f"{ACT}/jobs/9",
        {
            "name": "test",
            "status": "completed",
            "conclusion": "failure",
            "runner_name": "ubuntu-latest 2",
            "steps": [
                {"number": 1, "name": "Set up job", "conclusion": "success"},
                {"number": 2, "name": "Run pytest", "conclusion": "failure"},
            ],
        },
    )
    values = load(api, SHEETS["job"], {"repo": REPO, "id": "9"}).values
    assert values["steps"] == ("1. Set up job, success", "2. Run pytest, failure")
    assert values["runner"] == "ubuntu-latest 2"


@pytest.mark.parametrize(
    ("call", "status", "said"),
    [
        (
            lambda api: run_more.rerun_job(api, REPO, 9),
            403,
            "GitHub refused to re-run the job. It needs write access to Actions.",
        ),
        (
            lambda api: run_more.delete_logs(api, REPO, 5),
            404,
            "GitHub found nothing to delete the run's logs.",
        ),
        (
            lambda api: run_more.jobs(api, REPO, 5),
            404,
            "GitHub found nothing to list the run's jobs.",
        ),
    ],
)
def test_run_commands_say_no_permission_and_not_found(call: Any, status: int, said: str) -> None:
    class Refusing(FakeGitHubApi):
        def rest(self, method: str, path: str, **_kw: Any) -> Any:
            raise _refused(status)

    with pytest.raises(run_more.RunMoreError) as caught:
        call(Refusing())
    assert caught.value.args[0] == said


def test_a_run_github_already_deleted_says_it_may_be_gone(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.github import run_actions
    from quill.core.github.run_actions import GitHubRunActionsMixin

    def gone(*_a: Any, **_k: Any) -> Any:
        raise _refused(404, "Not Found")

    monkeypatch.setattr(run_actions, "request_json", gone)

    class Provider(GitHubRunActionsMixin):
        _token = "tok"

        def _require_write_access(self, action: str) -> None:
            pass

    with pytest.raises(GitHubItemsError) as caught:
        Provider().delete_workflow_run(REPO, 5)
    assert "Could not delete the run." in str(caught.value)
    assert "it may already be gone" in str(caught.value)


def test_running_a_workflow_run_again_that_github_refuses_says_why() -> None:
    repo = _Repo(_refused(403))
    with pytest.raises(GitHubItemsError) as caught:
        _provider(repo).rerun_workflow_run(REPO, 5)
    assert caught.value.args[0] == (
        "GitHub refused to re-run workflow run 5. "
        "It needs write access to Actions in this repository."
    )
    _provider(ok := _Repo()).rerun_workflow_run(REPO, 5)
    assert ok.reran == [5]


# -- logs ------------------------------------------------------------------------------


class _Opener:
    def __init__(self, code: int) -> None:
        self.code = code

    def open(self, request: Any, timeout: float = 0) -> Any:
        raise urllib.error.HTTPError(request.full_url, self.code, "no", {}, io.BytesIO(b""))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("code", "said"),
    [
        (
            410,
            "GitHub found nothing to read the job's log: GitHub keeps logs only for the "
            "repository's retention period, and they may have been deleted, or the job has "
            "not started.",
        ),
        (
            403,
            "GitHub refused to read the job's log. It needs read access to this repository's "
            "Actions.",
        ),
    ],
)
def test_a_job_log_that_expired_or_is_refused_is_said_in_words(
    monkeypatch: pytest.MonkeyPatch, code: int, said: str
) -> None:
    from quill.core.github import workflow_job_logs as logs

    monkeypatch.setattr(logs.urllib.request, "build_opener", lambda *_a: _Opener(code))
    with pytest.raises(logs.GitHubJobLogError) as caught:
        logs.fetch_job_log("tok", REPO, 9)
    assert caught.value.args[0] == said


# -- artifacts -------------------------------------------------------------------------


def _artifacts_api() -> FakeGitHubApi:
    api = FakeGitHubApi()
    api.answer(
        "GET",
        f"{ACT}/artifacts",
        {
            "artifacts": [
                {"id": 7, "name": "wheel", "size_in_bytes": 4096, "created_at": "2026-11-09"},
                {"id": 8, "name": "old", "size_in_bytes": 10, "expired": True},
            ]
        },
    )
    api.answer(
        "GET",
        f"{ACT}/artifacts/7",
        {
            "name": "wheel",
            "size_in_bytes": 4096,
            "created_at": "2026-11-09T10:00:00Z",
            "expires_at": "2027-02-07T10:00:00Z",
            "expired": False,
        },
    )
    return api


def test_artifacts_list_open_their_sheet_and_delete() -> None:
    api = _artifacts_api()
    rows = engine.fetch(api, SPECS["artifacts"], REPO)
    assert [row.key for row in rows] == ["artifacts:7", "artifacts:8"]
    assert rows[1].label.startswith("old, 10 bytes, expired")
    target = target_for(rows[0], REPO)
    assert target is not None and target.kind == "artifact"
    values = load(api, target.sheet, target.ident).values
    assert (values["name"], values["size"], values["expired"]) == ("wheel", "4 KB", False)
    said = engine.delete(api, SPECS["artifacts"], REPO, "7")
    assert said == "Deleted the artifact 7."
    assert api.writes() == [("DELETE", f"{ACT}/artifacts/7", None)]


def test_an_artifact_github_will_not_delete_or_already_deleted_is_said() -> None:
    api = FakeGitHubApi()
    api.answer("DELETE", f"{ACT}/artifacts/7", _refused(403))
    with pytest.raises(engine.ResourceError, match="GitHub refused to delete the artifact"):
        engine.delete(api, SPECS["artifacts"], REPO, "7")
    api.answer("DELETE", f"{ACT}/artifacts/7", _refused(404))
    with pytest.raises(engine.ResourceError, match="GitHub found nothing to delete the artifact"):
        engine.delete(api, SPECS["artifacts"], REPO, "7")


def test_an_artifact_gone_since_the_list_was_read_is_said_when_downloading(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from quill.core.github import items_provider

    monkeypatch.setattr(items_provider.urllib.request, "build_opener", lambda *_a: _Opener(410))
    artifact = GitHubArtifact(
        id=7,
        name="wheel",
        size_bytes=4096,
        expired=False,
        archive_download_url="https://api.github.com/repos/o/r/actions/artifacts/7/zip",
    )
    with pytest.raises(GitHubItemsError) as caught:
        _provider(_Repo()).download_artifact_to_file(artifact, tmp_path / "wheel.zip")
    assert caught.value.args[0] == (
        "GitHub found nothing to download the artifact: it was deleted, it expired after the "
        "repository's retention period, or this account cannot see it."
    )
    assert not (tmp_path / "wheel.zip").exists()


# -- caches ----------------------------------------------------------------------------


def test_a_cache_opens_from_the_same_page_the_list_read() -> None:
    api = FakeGitHubApi()
    api.answer(
        "GET",
        f"{ACT}/caches",
        {
            "actions_caches": [
                {
                    "id": 31,
                    "key": "pip-linux",
                    "ref": "refs/heads/main",
                    "size_in_bytes": 2048,
                    "last_accessed_at": "2026-11-09T10:00:00Z",
                }
            ]
        },
    )
    row = ExploreRow("pip-linux", "", "", REPO, "cache", "31")
    target = target_for(row, REPO)
    assert target is not None and target.kind == "cache"
    values = load(api, target.sheet, target.ident).values
    assert (values["key"], values["size"]) == ("pip-linux", "2 KB")
    reads = [call for call in api.calls if call[1] == f"{ACT}/caches"]
    assert len(reads) == 1  # and the page asked for is the list's own (below)
    read = target.sheet.reads[0]
    assert read.query is not None and read.query(target.ident) == {
        "per_page": "100",
        "sort": "last_accessed_at",
        "direction": "desc",
    }


# -- variables and secrets -------------------------------------------------------------


def test_a_variable_row_opens_its_sheet_and_a_new_value_is_saved_and_read_back() -> None:
    api = FakeGitHubApi()
    state = {"value": "beta", "updated_at": "2026-11-01T09:00:00Z"}
    api.on_write = lambda _m, _p, body: state.update(value=str((body or {}).get("value")))
    api.answer("GET", f"{ACT}/variables/CHANNEL", lambda: {"name": "CHANNEL", **state})
    row = ExploreRow("CHANNEL", "", "", REPO, "resource", "actions_variables:CHANNEL")
    target = target_for(row, REPO)
    assert target is not None and target.kind == "variable"
    loaded = load(api, target.sheet, target.ident)
    assert loaded.values["value"] == "beta"
    outcome = save(
        api,
        target.sheet,
        target.ident,
        [FieldChange("value", "Value", "beta", "stable")],
        loaded=loaded.values,
    )
    assert api.writes() == [("PATCH", f"{ACT}/variables/CHANNEL", {"value": "stable"})]
    assert [c.after for c in outcome.done] == ["stable"]


def test_a_secret_row_opens_the_write_only_secret_sheet() -> None:
    row = ExploreRow("TOKEN", "", "", REPO, "resource", "actions_secrets:TOKEN")
    target = target_for(row, REPO)
    assert target is not None and target.kind == "secret"
    assert target.ident == {"repo": REPO, "name": "TOKEN"}
    assert target_for(ExploreRow("x", "", "", REPO, "resource", "dependabot_secrets:T")) is None


def test_a_variable_that_is_gone_or_refused_is_said() -> None:
    spec = SPECS["actions_variables"]
    api = FakeGitHubApi()
    api.answer("PATCH", f"{ACT}/variables/CHANNEL", _refused(404))
    with pytest.raises(engine.ResourceError, match="GitHub found nothing to change the variable"):
        engine.edit(api, spec, REPO, "CHANNEL", {"value": "stable"})
    api.answer("POST", f"{ACT}/variables", _refused(403))
    with pytest.raises(engine.ResourceError, match="GitHub refused to add the variable"):
        engine.create(api, spec, REPO, {"name": "CHANNEL", "value": "beta"})
    api.answer("GET", f"{ACT}/variables", _refused(403))
    with pytest.raises(engine.ResourceError, match="GitHub refused to list the variables"):
        engine.fetch(api, spec, REPO)


# -- Read Only, Organize and the sheet locks -------------------------------------------

_P = "github.workbench."
ACTIONS_WRITES = {
    f"{_P}workflow_state": WriteTier.VISIBLE,
    f"{_P}run_workflow": WriteTier.VISIBLE,
    "github.dispatch_workflow": WriteTier.VISIBLE,
    f"{_P}rerun": WriteTier.VISIBLE,
    f"{_P}rerun_failed": WriteTier.VISIBLE,
    f"{_P}rerun_job": WriteTier.VISIBLE,
    f"{_P}cancel_run": WriteTier.VISIBLE,
    f"{_P}force_cancel_run": WriteTier.VISIBLE,
    f"{_P}approve_fork": WriteTier.ACCESS,
    f"{_P}delete_run": WriteTier.DESTRUCTIVE,
    f"{_P}delete_run_logs": WriteTier.DESTRUCTIVE,
    f"{_P}delete_cache": WriteTier.DESTRUCTIVE,
    f"{_P}resource_new": WriteTier.VISIBLE,
    f"{_P}resource_edit": WriteTier.VISIBLE,
    f"{_P}resource_delete": WriteTier.DESTRUCTIVE,
}


@pytest.mark.parametrize("command_id", sorted(ACTIONS_WRITES))
def test_every_actions_write_is_declared_and_refused_at_read_only(command_id: str) -> None:
    assert gated_tier(command_id) == ACTIONS_WRITES[command_id]
    said = command_refusal(command_id, lambda: AccessLevel.READ_ONLY)
    assert said.startswith("Cannot run ") and "this account is Read Only" in said
    at_organize = command_refusal(command_id, lambda: AccessLevel.ORGANIZE)
    assert bool(at_organize) == (ACTIONS_WRITES[command_id] > WriteTier.VISIBLE)
    assert command_refusal(command_id, lambda: AccessLevel.FULL) == ""


@pytest.mark.parametrize("command_id", [f"{_P}download_run_logs", f"{_P}artifacts"])
def test_reading_logs_and_artifacts_is_never_refused(command_id: str) -> None:
    assert command_refusal(command_id, lambda: AccessLevel.READ_ONLY) == ""


@pytest.mark.parametrize("kind", ["workflow", "variable", "secret"])
def test_every_editable_actions_field_is_locked_with_a_reason_at_read_only(kind: str) -> None:
    sheet = SHEETS[kind]
    read_only = ViewerContext(repo_role="admin", level=AccessLevel.READ_ONLY)
    locked = locked_fields(sheet, read_only)
    assert set(locked) == set(sheet.writes) and locked
    assert all("read only in the Workbench" in reason for reason in locked.values())
    assert locked_fields(sheet, ViewerContext(repo_role="admin", level=AccessLevel.FULL)) == {}


def test_without_write_access_a_workflow_cannot_be_turned_off_on_its_sheet() -> None:
    reader = ViewerContext(repo_role="read", level=AccessLevel.FULL)
    assert "enabled" in locked_fields(SHEETS["workflow"], reader)
    assert set(locked_fields(SHEETS["variable"], reader)) == {"value"}
