"""Saved replace jobs: run one, and manage the list. One implementation, both editors.

QUILL reaches these through :mod:`quill.ui.main_frame_editor_parity`, QUILL Lite
through :mod:`quill.apps.lite_window_replace_jobs`. What a job does is
:mod:`quill.core.replace_jobs`; this module is the two commands, and the four
windows they open are :mod:`quill.ui.replace_jobs_windows`. A host supplies
the hooks named ``_replace_jobs_*``: where its jobs file is, how it speaks, how
it shows a modal window, and how it reads and writes the text it runs on.

A job runs on the selection when there is one and on the whole document when
there is not -- the rule every line tool in both editors follows -- and writes
once, so Control Z takes the whole job back in one step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.replace_jobs import (
    JOBS_FILE_NAME,
    ReplaceJobError,
    describe_run,
    load_replace_jobs,
    run_job,
    save_replace_jobs,
)

# The windows live in their own module (GATE-11); imported by name here, so a
# test replaces them in this module, where the commands look them up.
from quill.ui.replace_jobs_windows import (
    choose_replace_job,
    edit_replace_job,
    edit_replace_step,
    manage_replace_jobs,
)

__all__ = [
    "ReplaceJobsMixin",
    "choose_replace_job",
    "edit_replace_job",
    "edit_replace_step",
    "manage_replace_jobs",
]

# --------------------------------------------------------------------------- #
# The commands
# --------------------------------------------------------------------------- #


class ReplaceJobsMixin:
    """Run Replace Job and Manage Replace Jobs. Hosts override ``_replace_jobs_*``."""

    def _replace_jobs_dir(self) -> Path:
        raise NotImplementedError  # each editor keeps its jobs in its own folder

    def _replace_jobs_say(self, message: str) -> None:
        self._announce(message)  # type: ignore[attr-defined]

    def _replace_jobs_parent(self) -> Any:
        return self

    def _replace_jobs_show_modal(self, dialog: Any, title: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return show_modal_dialog(dialog, title)

    def _replace_jobs_read_only(self) -> bool:
        return False

    def _replace_jobs_span(self) -> tuple[str, int, int, bool]:
        """``(the text, start, end, in_selection)``: the selection, else the document."""
        raise NotImplementedError

    def _replace_jobs_confirm_whole(self) -> bool:
        """Rich text only: whether a whole-document rewrite may go ahead."""
        return True

    def _replace_jobs_write(self, start: int, end: int, text: str) -> None:
        """Write *text* over ``start..end`` as one undo step."""
        raise NotImplementedError

    def _replace_jobs_focus(self) -> None:
        """Put focus back in the document after a window closes."""

    def _replace_jobs_file(self) -> Path:
        return self._replace_jobs_dir() / JOBS_FILE_NAME

    def cmd_run_replace_job(self) -> None:
        """Choose a saved job and run its steps, in order, as one change."""
        if self._replace_jobs_read_only():
            self._replace_jobs_say("Document is read-only")
            return
        jobs = load_replace_jobs(self._replace_jobs_file())
        if not jobs:
            self._replace_jobs_say("There are no saved replace jobs. Manage Replace Jobs makes one")
            return
        text, start, end, in_selection = self._replace_jobs_span()
        index = choose_replace_job(
            self._replace_jobs_parent(),
            jobs,
            self._replace_jobs_show_modal,
            in_selection=in_selection,
        )
        self._replace_jobs_focus()
        if index is None:
            return
        job = jobs[index]
        try:
            updated, counts = run_job(text, job)
        except ReplaceJobError as error:
            # The sentence, not the code in brackets: the code is for a log.
            said = str(error.args[0]) if error.args else str(error)
            self._replace_jobs_say(f"{said} Nothing was changed")
            return
        if sum(counts):
            if not in_selection and not self._replace_jobs_confirm_whole():
                self._replace_jobs_say("Left unchanged")
                return
            self._replace_jobs_write(start, end, updated)
        self._replace_jobs_say(describe_run(job, counts, in_selection=in_selection))

    def cmd_manage_replace_jobs(self) -> None:
        """Make, edit, rename and delete saved replace jobs."""
        path = self._replace_jobs_file()
        jobs = load_replace_jobs(path)
        changed = manage_replace_jobs(
            self._replace_jobs_parent(), jobs, self._replace_jobs_show_modal
        )
        self._replace_jobs_focus()
        if changed is None:
            return
        try:
            save_replace_jobs(path, changed)
        except OSError as error:
            self._replace_jobs_say(f"Could not save the replace jobs: {error}")
            return
        count = len(changed)
        self._replace_jobs_say(f"Saved {count} replace {'job' if count == 1 else 'jobs'}")
