"""Accessible workflow job list with selected plain-text job logs."""

from __future__ import annotations

import threading
import webbrowser
from typing import TYPE_CHECKING

from quill.core.github.items_provider import (
    GitHubItemsError,
    GitHubWorkflowAnnotation,
    GitHubWorkflowJob,
)
from quill.core.github.workflow_job_logs import GitHubJobLogError, fetch_job_log
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    dialog_alive,
    show_modal_dialog,
)
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name

if TYPE_CHECKING:
    from collections.abc import Callable

    from quill.core.github.items_provider import GitHubItemsProvider


class WorkflowJobsDialog:
    """One run's jobs and readable logs, shared by QUILL and Lite."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        *,
        repo: str,
        run_id: int,
        run_label: str,
        run_attempt: int = 0,
        head_sha: str = "",
        run_url: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repo = repo
        self._run_id = run_id
        self._run_label = run_label
        self._run_attempt = run_attempt
        self._selected_attempt = run_attempt
        self._head_sha = head_sha
        self._run_url = run_url
        self._announce = announce_cb or (lambda _message: None)
        self._jobs: list[GitHubWorkflowJob] = []
        self._jobs_token = 0
        self._log_token = 0
        self._annotation_token = 0
        self._loaded_log: str | None = None
        self._annotations: tuple[GitHubWorkflowAnnotation, ...] | None = None
        self._annotations_truncated = False
        self.dialog = wx.Dialog(
            parent, title=f"Jobs for {run_label}", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 680, 480))
        self.dialog.SetSize(dip_size(self.dialog, 800, 620))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        attempt_row = wx.BoxSizer(wx.HORIZONTAL)
        attempt_row.Add(
            wx.StaticText(panel, label="&Attempt:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._attempt_truncated = run_attempt > 20
        self._attempt_numbers = (
            list(range(run_attempt, max(0, run_attempt - 20), -1)) if run_attempt > 0 else [0]
        )
        attempt_labels = [
            f"Attempt {attempt} (current)" if attempt == run_attempt else f"Attempt {attempt}"
            for attempt in self._attempt_numbers
        ]
        if not run_attempt:
            attempt_labels = ["Current attempt (number unavailable)"]
        self._attempt_choice = wx.Choice(panel, choices=attempt_labels)
        self._attempt_choice.SetName("Workflow run attempt")
        self._attempt_choice.SetSelection(0)
        attempt_row.Add(self._attempt_choice, 0)
        if self._attempt_truncated:
            attempt_row.Add(
                wx.StaticText(panel, label="Showing the most recent 20 attempts"),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
                8,
            )
        root.Add(attempt_row, 0, wx.EXPAND | wx.ALL, 8)
        root.Add(wx.StaticText(panel, label="Workflow jobs"), 0, wx.ALL, 8)
        self._list = wx.ListBox(panel, choices=[])
        self._list.SetName("Workflow jobs; select a job to read status or load its log")
        set_spoken_name(self._list, "Workflow jobs")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        root.Add(wx.StaticText(panel, label="Job details and log"), 0, wx.ALL, 8)
        self._detail = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP | wx.TE_RICH2
        )
        self._detail.SetName("Selected workflow job details and plain-text log")
        root.Add(self._detail, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._status = wx.StaticText(panel, label="Loading jobs...")
        self._status.SetName("Workflow job status")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)
        actions = wx.BoxSizer(wx.HORIZONTAL)
        self._log_btn = wx.Button(panel, label="Load &Log")
        self._log_btn.SetName("Load selected job's text log")
        self._annotations_btn = wx.Button(panel, label="Load A&nnotations")
        self._annotations_btn.SetName("Load selected job's check annotations")
        self._open_btn = wx.Button(panel, label="Open &Job on GitHub")
        self._open_btn.SetName("Open selected workflow job in browser")
        self._open_run_btn = wx.Button(panel, label="Open &Run on GitHub")
        self._open_run_btn.SetName("Open this workflow run in browser")
        close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close workflow jobs")
        actions.Add(self._log_btn, 0, wx.RIGHT, 6)
        actions.Add(self._annotations_btn, 0, wx.RIGHT, 6)
        actions.Add(self._open_btn, 0, wx.RIGHT, 6)
        actions.Add(self._open_run_btn, 0, wx.RIGHT, 6)
        actions.AddStretchSpacer()
        actions.Add(close_btn)
        root.Add(actions, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self._list.Bind(wx.EVT_LISTBOX, self._select)
        self._attempt_choice.Bind(wx.EVT_CHOICE, self._on_attempt_changed)
        apply_listbox_activation(self._list, self._load_log)
        self._log_btn.Bind(wx.EVT_BUTTON, self._load_log)
        self._annotations_btn.Bind(wx.EVT_BUTTON, self._load_annotations)
        self._open_btn.Bind(wx.EVT_BUTTON, self._open_job)
        self._open_run_btn.Bind(wx.EVT_BUTTON, self._open_run)
        self._log_btn.Enable(False)
        self._annotations_btn.Enable(False)
        self._open_btn.Enable(False)
        self._open_run_btn.Enable(bool(run_url))

    def show(self) -> None:
        wx = self._wx
        self._reload()
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, "Workflow Jobs", announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _reload(self) -> None:
        self._jobs_token += 1
        token = self._jobs_token
        self._status.SetLabel("Loading workflow jobs...")

        def worker() -> None:
            wx = self._wx
            try:
                attempt = (
                    self._selected_attempt
                    if self._selected_attempt > 0 and self._selected_attempt != self._run_attempt
                    else None
                )
                if attempt is None:
                    jobs = self._provider.fetch_workflow_jobs(self._repo, self._run_id)
                else:
                    jobs = self._provider.fetch_workflow_jobs(
                        self._repo, self._run_id, attempt_number=attempt
                    )
            except GitHubItemsError as exc:
                wx.CallAfter(self._loaded, token, None, str(exc))
                return
            wx.CallAfter(self._loaded, token, jobs, "")

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: job list fetch.

    def _loaded(self, token: int, jobs: list[GitHubWorkflowJob] | None, error: str) -> None:
        if token != self._jobs_token or not dialog_alive(self.dialog):
            return
        self._jobs = jobs or []
        self._list.Set([f"{job.conclusion or job.status}: {job.name}" for job in self._jobs])
        message = f"Could not load jobs: {error}" if error else f"{len(self._jobs)} jobs loaded."
        self._status.SetLabel(message)
        self._announce(message)
        if self._jobs:
            self._list.SetSelection(0)
            self._select(None)

    def _selected(self) -> GitHubWorkflowJob | None:
        index = self._list.GetSelection()
        return self._jobs[index] if 0 <= index < len(self._jobs) else None

    def _on_attempt_changed(self, _event: object) -> None:
        index = self._attempt_choice.GetSelection()
        if not 0 <= index < len(self._attempt_numbers):
            return
        attempt = self._attempt_numbers[index]
        if attempt == self._selected_attempt:
            return
        self._selected_attempt = attempt
        self._reload()

    def _select(self, _event: object) -> None:
        job = self._selected()
        if job is None:
            return
        self._log_token += 1
        self._annotation_token += 1
        self._loaded_log = None
        self._annotations = None
        self._annotations_truncated = False
        self._render_detail(job)
        self._log_btn.Enable(job.id > 0)
        self._annotations_btn.Enable((job.check_run_id or job.id) > 0)
        self._open_btn.Enable(bool(job.url))

    def _load_log(self, _event: object) -> None:
        job = self._selected()
        if job is None or job.id <= 0:
            self._announce("Select a workflow job with a GitHub job ID first.")
            return
        self._log_token += 1
        token = self._log_token
        self._status.SetLabel(f"Loading log for {job.name}...")

        def worker() -> None:
            wx = self._wx
            try:
                content = fetch_job_log(self._provider.token, self._repo, job.id)
            except GitHubJobLogError as exc:
                wx.CallAfter(self._log_loaded, token, None, str(exc))
                return
            wx.CallAfter(self._log_loaded, token, content, "")

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: job log fetch.

    def _load_annotations(self, _event: object) -> None:
        job = self._selected()
        check_run_id = (job.check_run_id or job.id) if job is not None else 0
        if job is None or check_run_id <= 0:
            self._announce("Select a workflow job with a check-run ID first.")
            return
        self._annotation_token += 1
        token = self._annotation_token
        self._status.SetLabel(f"Loading annotations for {job.name}...")

        def worker() -> None:
            wx = self._wx
            try:
                annotations, truncated = self._provider.fetch_workflow_job_annotations(
                    self._repo, check_run_id
                )
            except GitHubItemsError as exc:
                wx.CallAfter(self._annotations_loaded, token, None, False, str(exc))
                return
            wx.CallAfter(self._annotations_loaded, token, annotations, truncated, "")

        threading.Thread(
            target=worker, daemon=True
        ).start()  # GATE-40-OK: bounded read-only check-run annotations.

    def _annotations_loaded(
        self,
        token: int,
        annotations: tuple[GitHubWorkflowAnnotation, ...] | None,
        truncated: bool,
        error: str,
    ) -> None:
        if token != self._annotation_token or not dialog_alive(self.dialog):
            return
        if error:
            message = f"Could not load workflow annotations: {error}"
            self._status.SetLabel(message)
            self._announce(message)
            return
        self._annotations = annotations or ()
        self._annotations_truncated = truncated
        job = self._selected()
        if job is not None:
            self._render_detail(job)
        count = len(self._annotations)
        message = f"Loaded {count} workflow annotation(s)."
        self._status.SetLabel(message)
        self._announce(message)

    def _log_loaded(self, token: int, content: str | None, error: str) -> None:
        if token != self._log_token or not dialog_alive(self.dialog):
            return
        if error:
            self._status.SetLabel(f"Could not load job log: {error}")
            self._announce(f"Could not load job log: {error}")
            return
        self._loaded_log = content or ""
        job = self._selected()
        if job is not None:
            self._render_detail(job)
        self._detail.SetFocus()
        self._status.SetLabel("Job log loaded.")
        self._announce("Job log loaded; read it in the details field.")

    def _open_job(self, _event: object) -> None:
        job = self._selected()
        if job and job.url:
            self._announce(
                "Opened workflow job on GitHub."
                if webbrowser.open(job.url)
                else "Could not open workflow job in browser."
            )

    def _open_run(self, _event: object) -> None:
        if self._run_url:
            self._announce(
                "Opened workflow run on GitHub."
                if webbrowser.open(self._run_url)
                else "Could not open workflow run in browser."
            )

    def _job_details(self, job: GitHubWorkflowJob) -> str:
        lines = [
            f"Run: {self._run_label}",
            f"Job: {job.name}",
            f"Status: {job.status}",
            f"Conclusion: {job.conclusion or 'not reported'}",
            f"Started: {job.started_at or 'not reported'}",
            f"Finished: {job.completed_at or 'not reported'}",
        ]
        if self._selected_attempt > 0:
            lines.append(f"Run attempt: {self._selected_attempt}")
        if self._head_sha:
            lines.append(f"Head SHA: {self._head_sha}")
        if job.steps:
            lines.append("Steps:")
            lines.extend(
                f"  {step.number}. {step.name}: {step.conclusion or step.status}"
                for step in job.steps
            )
        else:
            lines.append("Step details are unavailable.")
        lines.extend((f"Job URL: {job.url}", f"Run URL: {self._run_url}"))
        return "\n".join(lines)

    def _render_detail(self, job: GitHubWorkflowJob) -> None:
        parts = [self._job_details(job)]
        if self._annotations is not None:
            if not self._annotations:
                parts.append("Annotations:\nNo annotations were returned for this job.")
            else:
                lines = [
                    f"{item.path}:{item.start_line}-{item.end_line} "
                    f"[{item.level or 'notice'}] {item.title or 'Annotation'}: {item.message}"
                    for item in self._annotations
                ]
                lines.extend(
                    f"  Details: {item.details}" for item in self._annotations if item.details
                )
                if self._annotations_truncated:
                    lines.append(
                        "Showing the first 100 annotations; open the run on GitHub for the rest."
                    )
                parts.append(f"Annotations ({len(self._annotations)}):\n" + "\n".join(lines))
        if self._loaded_log is not None:
            parts.append("Job log:\n" + (self._loaded_log or "Job log is empty."))
        else:
            parts.append("Activate Load Log to read the job's plain-text log.")
        self._detail.SetValue("\n\n".join(parts))
