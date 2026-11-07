"""QUILL Lite's half of saved replace jobs: the hooks, and no commands of its own.

Run Replace Job and Manage Replace Jobs are
:class:`quill.ui.replace_jobs.ReplaceJobsMixin`'s, the same handlers QUILL runs.
What lives here is only where QUILL Lite keeps the jobs (its own data folder)
and how it reads and writes the text: the selection or the whole document, in
the control's own positions, written back with ``replace_as_one_undo`` so
Control Z takes the whole job back in one step. If this class ever grows a
command of its own, the feature has forked.
"""

from __future__ import annotations

from pathlib import Path

from quill.ui.atomic_edit import replace_as_one_undo
from quill.ui.replace_jobs import ReplaceJobsMixin

__all__ = ["DocumentReplaceJobsMixin"]


class DocumentReplaceJobsMixin(ReplaceJobsMixin):
    """The shared replace jobs, run on QUILL Lite's control."""

    def _replace_jobs_dir(self) -> Path:
        return Path(self.app.data_dir)  # type: ignore[attr-defined]

    def _replace_jobs_read_only(self) -> bool:
        return bool(getattr(self, "_read_only", False))

    def _replace_jobs_span(self) -> tuple[str, int, int, bool]:
        control = self.control  # type: ignore[attr-defined]
        start, end = control.GetSelection()
        in_selection = end > start
        if not in_selection:
            start, end = 0, control.GetLastPosition()
        return str(control.GetRange(start, end)), int(start), int(end), in_selection

    def _replace_jobs_confirm_whole(self) -> bool:
        from quill.ui.richedit_editing import RICH

        if getattr(self.editor, "mode", None) != RICH:  # type: ignore[attr-defined]
            return True
        return bool(self._confirm_rich_rewrite())  # type: ignore[attr-defined]

    def _replace_jobs_write(self, start: int, end: int, text: str) -> None:
        replace_as_one_undo(self.control, start, end, text)  # type: ignore[attr-defined]
        self._set_modified(True)  # type: ignore[attr-defined]
        self._touch_status()  # type: ignore[attr-defined]

    def _replace_jobs_focus(self) -> None:
        self.control.SetFocus()  # type: ignore[attr-defined]
