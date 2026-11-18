"""Follow This Job and Alt+8 in the workflow jobs window (GitHub PRD 22.12)."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.workflow_models import GitHubWorkflowJob, GitHubWorkflowStep  # noqa: E402
from quill.ui.github_workflow_jobs_dialog import WorkflowJobsDialog  # noqa: E402
from tests.wx_session import patch_call_after  # noqa: E402


def _job(status: str, steps: list[tuple[str, str]], conclusion: str = "") -> GitHubWorkflowJob:
    return GitHubWorkflowJob(
        name="build",
        status=status,
        conclusion=conclusion,
        id=7,
        steps=tuple(
            GitHubWorkflowStep(name=f"s{i}", status=s, conclusion=c, number=i)
            for i, (s, c) in enumerate(steps, start=1)
        ),
    )


class _Provider:
    is_authenticated = True

    def __init__(self) -> None:
        self.answers = [
            [_job("in_progress", [("in_progress", ""), ("queued", "")])],
            [_job("in_progress", [("completed", "success"), ("in_progress", "")])],
            [_job("completed", [("completed", "success"), ("completed", "failure")], "failure")],
        ]

    def fetch_workflow_jobs(self, _repo: str, _run: int, **_kw: Any) -> list[GitHubWorkflowJob]:
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


class _SyncThread:
    def __init__(self, *, target: Any, daemon: bool) -> None:
        self._target = target

    def start(self) -> None:
        self._target()


@pytest.fixture
def jobs(wx_session_app, monkeypatch):
    monkeypatch.setattr("quill.ui.github_workflow_jobs_dialog.threading.Thread", _SyncThread)
    monkeypatch.setattr("quill.ui.github_workflow_job_follow.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch)
    said: list[str] = []
    frame = wx.Frame(None)
    dialog = WorkflowJobsDialog(
        frame, _Provider(), repo="o/r", run_id=1, run_label="CI #4", announce_cb=said.append
    )
    dialog._reload()
    dialog.said = said
    yield dialog
    dialog._stop_following()
    dialog.dialog.Destroy()
    frame.Destroy()


def test_following_says_each_step_and_the_end_then_stops(jobs) -> None:
    jobs._follow_box.SetValue(True)
    jobs._on_follow(None)
    assert jobs.said[-1] == "build: On step 1 of 2, s1; 0 done."
    assert jobs._follow_timer.IsRunning()
    jobs._follow_tick()
    assert jobs.said[-1] == "Step 1, s1, succeeded. Step 2, s2, started."
    jobs._follow_tick()
    assert jobs.said[-1] == "Step 2, s2, failed. build failed. Load Log reads its whole log."
    assert not jobs._follow_box.GetValue() and not jobs._follow_timer.IsRunning()
    assert jobs._list.GetString(0) == "failure: build"


def test_alt_8_says_how_far_along(jobs) -> None:
    jobs._say_progress()
    assert jobs.said[-1] == "build: On step 1 of 2, s1; 0 done."


def test_a_finished_job_has_nothing_to_follow(jobs) -> None:
    jobs._jobs = [_job("completed", [("completed", "success")], "success")]
    jobs._follow_box.SetValue(True)
    jobs._on_follow(None)
    assert not jobs._follow_box.GetValue()
    assert "nothing left to follow" in jobs.said[-1]


def test_unchecking_stops(jobs) -> None:
    jobs._follow_box.SetValue(True)
    jobs._on_follow(None)
    jobs._follow_box.SetValue(False)
    jobs._on_follow(None)
    assert jobs.said[-1] == "Stopped following." and not jobs._follow_timer.IsRunning()
