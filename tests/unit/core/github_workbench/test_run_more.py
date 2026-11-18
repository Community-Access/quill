"""More on a workflow run: one job again, force cancel, logs, approvals, attempts."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import run_more as rm
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.workflow_models import GitHubWorkflowRun
from quill.ui.github_workbench_run_more import GitHubWorkbenchRunMoreMixin

RUNS = "/repos/o/r/actions/runs/5"


class Api:
    def __init__(self, answers: dict[str, Any] | None = None, fail: dict[str, int] | None = None):
        self.answers, self.fail = answers or {}, fail or {}
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        if f"{method} {path}" in self.fail:
            raise GitHubRestError("no", status=self.fail[f"{method} {path}"])
        return RestResponse(200, {}, self.answers.get(f"{method} {path}", {}))


def test_one_job_again_with_debug_logging() -> None:
    api = Api({f"GET {RUNS}/jobs": {"jobs": [{"id": 9, "name": "test", "conclusion": "failure"}]}})
    assert rm.jobs(api, "o/r", 5) == [(9, "test: failure")]
    assert (
        rm.rerun_job(api, "o/r", 9, debug=True)
        == "GitHub started the job again, with debug logging."
    )
    assert api.sent[-1] == (
        "POST",
        "/repos/o/r/actions/jobs/9/rerun",
        {"enable_debug_logging": True},
    )


def test_force_cancel_delete_logs_and_a_logs_download() -> None:
    api = Api()
    assert rm.force_cancel(api, "o/r", 5).startswith("GitHub is force-cancelling")
    assert rm.delete_logs(api, "o/r", 5) == "Deleted the run's logs. The run itself is kept."
    logs = rm.logs_download("o/r", 5, 2)
    assert logs.archive_download_url == f"https://api.github.com{RUNS}/attempts/2/logs"
    assert logs.name == "run-5-attempt-2-logs" and not logs.expired
    with pytest.raises(rm.RunMoreError, match="present state"):
        rm.force_cancel(Api(fail={f"POST {RUNS}/force-cancel": 409}), "o/r", 5)


def test_approvals_and_an_earlier_attempt_read_as_sentences() -> None:
    api = Api({
        f"GET {RUNS}/approvals": [
            {
                "user": {"login": "jeff"},
                "state": "approved",
                "environments": [{"name": "prod"}],
                "comment": "Ship it",
            }
        ],
        f"GET {RUNS}/attempts/1": {
            "conclusion": "failure",
            "run_started_at": "2026-11-17T09:30:00Z",
            "triggering_actor": {"login": "jeff"},
        },
    })
    assert rm.approvals(api, "o/r", 5) == ["jeff approved prod: Ship it."]
    assert (
        rm.attempt(api, "o/r", 5, 1) == "Attempt 1: failure, 2026-11-17 at 09:30, started by jeff."
    )


class _Window(GitHubWorkbenchRunMoreMixin):
    signed_in = True

    def __init__(self, api: Api, answers: list[Any]) -> None:
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

    def _repo_for(self, _ref: Any) -> str:
        return "o/r"


RUN = GitHubWorkflowRun("CI", "completed", "failure", run_number=12, id=5, run_attempt=2)


def test_the_row_commands_ask_then_act() -> None:
    api = Api({f"GET {RUNS}/jobs": {"jobs": [{"id": 9, "name": "test"}]}})
    window = _Window(api, [0, 0])
    assert window._fits_rerun_job(RUN) and window._fits_run_attempts(RUN)
    window._do_rerun_job(None, RUN)
    assert window.said == ["GitHub started the job again."]
    window = _Window(Api(), [False])
    window._do_force_cancel_run(None, RUN)
    assert window.api.sent == []
    window = _Window(Api({f"GET {RUNS}/attempts/1": {"conclusion": "success"}}), [0, 0])
    window._do_run_attempts(None, RUN)
    assert window.said == ["Attempt 1: success."]
    assert not window._fits_run_attempts(GitHubWorkflowRun("CI", "completed", id=5, run_attempt=1))
