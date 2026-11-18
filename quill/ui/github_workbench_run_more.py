"""More on a workflow run's row: one job again, force cancel, logs, approvals, attempts (PRD 19).

The code is in :mod:`quill.core.github.run_more`; this mixin asks and says.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.github.workflow_models import GitHubWorkflowRun

__all__ = ["RUN_MORE_REASONS", "RUN_MORE_VERBS", "GitHubWorkbenchRunMoreMixin"]

_RUN = frozenset({"run"})

RUN_MORE_VERBS: dict[str, frozenset[str]] = {
    "rerun_job": _RUN,
    "force_cancel_run": _RUN,
    "download_run_logs": _RUN,
    "delete_run_logs": _RUN,
    "run_approvals": _RUN,
    "run_attempts": _RUN,
}

RUN_MORE_REASONS: dict[str, str] = {
    "rerun_job": "Re-run One Job is for a workflow run, while you are signed in.",
    "force_cancel_run": "Force Cancel is for a workflow run, while you are signed in.",
    "download_run_logs": "Download Logs is for a workflow run, while you are signed in.",
    "delete_run_logs": "Delete Logs is for a workflow run, while you are signed in.",
    "run_approvals": "Approvals is for a workflow run, while you are signed in.",
    "run_attempts": "Earlier Attempts is for a run that has been re-run.",
}


class GitHubWorkbenchRunMoreMixin:
    items: Any
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _repo_for: Callable[[Any], str]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _fits_more_run(self, row: object) -> bool:
        return self.signed_in and isinstance(row, GitHubWorkflowRun) and bool(row.id)

    _fits_rerun_job = _fits_more_run
    _fits_force_cancel_run = _fits_more_run
    _fits_download_run_logs = _fits_more_run
    _fits_delete_run_logs = _fits_more_run
    _fits_run_approvals = _fits_more_run

    def _fits_run_attempts(self, row: object) -> bool:
        return self._fits_more_run(row) and getattr(row, "run_attempt", 0) > 1

    @staticmethod
    def _words(row: GitHubWorkflowRun) -> str:
        return f"{row.name} run {row.run_number}" if row.run_number else row.name

    def _do_rerun_job(self, ref: Any, row: object) -> None:
        from quill.core.github.run_more import jobs, rerun_job

        assert isinstance(row, GitHubWorkflowRun)
        repo, run_id, api = self._repo_for(ref), row.id, self.github_api()

        def chosen(found: Any) -> None:
            found = list(found)
            if not found:
                self._say("GitHub lists no jobs for this run.")
                return
            picked = self._choose("Re-run One Job", "Which job?", [label for _i, label in found])
            if picked < 0:
                return
            how = self._choose(
                "Re-run One Job", "How?", ["Re-run it", "Re-run it with debug logging"]
            )
            if how < 0:
                return
            job_id = found[picked][0]
            self._background(
                "re-run the job",
                lambda: rerun_job(api, repo, job_id, debug=how == 1),
                lambda said: self._say(str(said)),
            )

        self._background("list the run's jobs", lambda: jobs(api, repo, run_id), chosen)

    def _do_force_cancel_run(self, ref: Any, row: object) -> None:
        from quill.core.github.run_more import force_cancel

        assert isinstance(row, GitHubWorkflowRun)
        repo, run_id = self._repo_for(ref), row.id
        if not self._confirm(
            "Force Cancel",
            f"Force-cancel {self._words(row)}? Use it only when Cancel has not stopped the run; "
            "cleanup steps such as always() are skipped.",
        ):
            return
        api = self.github_api()
        self._background(
            "force-cancel the run",
            lambda: force_cancel(api, repo, run_id),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _do_delete_run_logs(self, ref: Any, row: object) -> None:
        from quill.core.github.run_more import delete_logs

        assert isinstance(row, GitHubWorkflowRun)
        repo, run_id = self._repo_for(ref), row.id
        if not self._confirm(
            "Delete Logs", f"Delete every log of {self._words(row)}? This cannot be undone."
        ):
            return
        api = self.github_api()
        self._background(
            "delete the logs", lambda: delete_logs(api, repo, run_id), lambda s: self._say(str(s))
        )

    def _do_download_run_logs(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflowRun)
        self._save_logs(self._repo_for(ref), row.id)

    def _save_logs(self, repo: str, run_id: int, attempt_number: int = 0) -> None:
        from quill.core.github.run_more import logs_download
        from quill.ui.dialog_contract import show_modal_dialog

        logs = logs_download(repo, run_id, attempt_number)
        wx = self.frame._wx
        title = "Download Logs"
        with wx.FileDialog(
            self.frame.frame,
            title,
            defaultFile=f"{logs.name}.zip",
            wildcard="Zip files (*.zip)|*.zip",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as box:
            if show_modal_dialog(box, title) != wx.ID_OK:
                return
            where = Path(box.GetPath())
        self._background(
            "download the logs",
            lambda: self.items.download_artifact_to_file(logs, where),
            lambda _done: self._say(f"Saved the logs to {where.name}."),
        )

    def _do_run_approvals(self, ref: Any, row: object) -> None:
        from quill.core.github.run_more import approvals

        assert isinstance(row, GitHubWorkflowRun)
        repo, run_id, api = self._repo_for(ref), row.id, self.github_api()
        self._background(
            "read the approvals",
            lambda: approvals(api, repo, run_id),
            lambda said: self._say(
                " ".join(said)
                if said
                else "Nobody has approved or rejected this run's deployments."
            ),
        )

    def _do_run_attempts(self, ref: Any, row: object) -> None:
        from quill.core.github.run_more import attempt

        assert isinstance(row, GitHubWorkflowRun)
        repo, run_id, api = self._repo_for(ref), row.id, self.github_api()
        numbers = list(range(row.run_attempt - 1, 0, -1))
        picked = self._choose(
            "Earlier Attempts", "Which attempt?", [f"Attempt {n}" for n in numbers]
        )
        if picked < 0:
            return
        number = numbers[picked]
        what = self._choose(
            "Earlier Attempts", f"Attempt {number}:", ["Say how it went", "Download its logs..."]
        )
        if what == 1:
            self._save_logs(repo, run_id, number)
            return
        if what < 0:
            return
        self._background(
            f"read attempt {number}",
            lambda: attempt(api, repo, run_id, number),
            lambda said: self._say(str(said)),
        )
