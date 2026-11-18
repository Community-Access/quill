"""Follow This Job, and Alt+8 for how far along it is, in the workflow jobs window.

Split from :mod:`quill.ui.github_workflow_jobs_dialog` (GATE-11). While Follow
This Job is checked, the selected job is read again every
:data:`~quill.core.github.job_follow.FOLLOW_SECONDS` seconds off the UI
thread, and each step that starts or finishes is said once, as it happens;
the job's end is said and following stops. Alt+8 says how far along the
selected job is at any time. The sentences are
:mod:`quill.core.github.job_follow`'s.
"""

from __future__ import annotations

import threading
from typing import Any

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.job_follow import FOLLOW_SECONDS, finished, progress_sentence, step_changes
from quill.ui.dialog_contract import dialog_alive

__all__ = ["WorkflowJobFollowMixin"]


class WorkflowJobFollowMixin:
    _wx: Any
    dialog: Any
    _provider: Any
    _repo: str
    _run_id: int
    _jobs: list[Any]
    _list: Any
    _announce: Any

    def _build_follow(self, panel: Any, row: Any) -> None:
        wx = self._wx
        self._following: Any = None
        self._follow_timer = wx.Timer(self.dialog)
        self._follow_box = wx.CheckBox(panel, label="Follo&w This Job")
        self._follow_box.SetName("Follow this job")
        self._follow_box.SetHelpText(
            "While checked, QUILL reads the selected job again every few seconds and says "
            "each step as it starts and finishes, and the job's end. Alt+8 says how far "
            "along it is at any time."
        )
        row.Add(self._follow_box, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self._follow_box.Bind(wx.EVT_CHECKBOX, self._on_follow)
        self.dialog.Bind(wx.EVT_TIMER, self._follow_tick, self._follow_timer)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._follow_keys)
        self.dialog.Bind(wx.EVT_WINDOW_DESTROY, self._stop_following)

    def _follow_keys(self, event: Any) -> None:
        wx = self._wx
        if event.GetKeyCode() == ord("8") and event.GetModifiers() == wx.MOD_ALT:
            self._say_progress()
            return
        event.Skip()

    def _say_progress(self) -> None:
        job = self._selected()
        self._announce(progress_sentence(job) if job is not None else "Select a job first.")

    def _selected(self) -> Any:
        raise NotImplementedError

    def _on_follow(self, _event: object) -> None:
        if not self._follow_box.GetValue():
            self._stop_following()
            self._announce("Stopped following.")
            return
        job = self._selected()
        if job is None:
            self._follow_box.SetValue(False)
            self._announce("Select a job to follow first.")
            return
        if finished(job):
            self._follow_box.SetValue(False)
            self._announce(f"{progress_sentence(job)} There is nothing left to follow.")
            return
        self._following = job
        self._announce(progress_sentence(job))
        self._follow_timer.Start(FOLLOW_SECONDS * 1000)

    def _stop_following(self, event: Any = None) -> None:
        self._following = None
        try:
            self._follow_timer.Stop()
        except Exception:  # noqa: BLE001 - the window may already be going
            pass
        if event is not None:
            event.Skip()

    def _follow_tick(self, _event: object = None) -> None:
        followed = self._following
        if followed is None:
            return
        wx = self._wx

        def worker() -> None:
            try:
                jobs = self._provider.fetch_workflow_jobs(self._repo, self._run_id)
            except GitHubItemsError as exc:
                wx.CallAfter(self._follow_landed, followed.id, None, str(exc))
                return
            wx.CallAfter(self._follow_landed, followed.id, jobs, "")

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: follow poll.

    def _follow_landed(self, job_id: int, jobs: list[Any] | None, error: str) -> None:
        if not dialog_alive(self.dialog) or self._following is None:
            return
        if self._following.id != job_id:
            return
        if jobs is None:
            self._announce(f"Could not read the job again: {error}. Still following.")
            return
        now = next((job for job in jobs if job.id == job_id), None)
        if now is None:
            self._stop_following()
            self._follow_box.SetValue(False)
            self._announce("The job is no longer in this run; stopped following.")
            return
        said = step_changes(self._following, now)
        self._following = now
        self._jobs = list(jobs)
        index = next(i for i, job in enumerate(self._jobs) if job.id == job_id)
        self._list.SetString(index, f"{now.conclusion or now.status}: {now.name}")
        if self._list.GetSelection() == index:
            self._render_detail(now)
        if said:
            self._announce(" ".join(said))
        if finished(now):
            self._stop_following()
            self._follow_box.SetValue(False)

    def _render_detail(self, job: Any) -> None:
        raise NotImplementedError
