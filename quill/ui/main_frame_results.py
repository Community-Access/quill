"""QUILL's document results: Save All, exports and Batch Conversion (FUX-04).

The sentences come from :mod:`quill.core.action_feedback` and
:mod:`quill.core.document_results`; keeping them is the shared Activity log
(:mod:`quill.ui.outcome_report`, :func:`quill.ui.activity_window.report_result`),
so a result spoken while somebody was busy elsewhere is still there under
Repeat Last Result (F9) and Activity (Shift+F9), with Open Folder. Nothing here
opens a window when a job finishes: a delayed result must not take focus from
the document somebody is writing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["DocumentResultsMixin"]


class DocumentResultsMixin:
    """Mixed into MainFrame; uses its ``_announce``, tabs and ``save_file``."""

    _document_tabs: list[Any]
    document: Any

    def _report_written(self, action: str, done: str, path: Path, *, reason: str = "") -> None:
        """Say *done* with the file and its folder, and keep it with Open Folder."""
        from quill.core.action_feedback import written_result
        from quill.ui.outcome_report import report_outcome

        report_outcome(
            self,
            action,
            written_result(done, path),
            object_name=path.name,
            path=path,
            reason=reason,
        )

    def save_all_files(self) -> None:
        """Save every changed document; say which were saved and where it stopped.

        Returns to the document you were in: Save All selects each tab to save
        it, and finishing on the last one moved you away from your own place.
        """
        from quill.core.document_results import save_all_result

        start = int(getattr(self, "_active_tab_index", 0))
        saved: list[Path] = []
        stopped_at = ""
        left = 0
        for index in range(len(self._document_tabs)):
            self._select_tab(index)  # type: ignore[attr-defined]
            if not self.document.modified:
                continue
            if stopped_at:
                left += 1
                continue
            self.save_file()  # type: ignore[attr-defined]
            if self.document.modified or self.document.path is None:
                stopped_at = self.document.name
            else:
                saved.append(Path(self.document.path))
        if 0 <= start < len(self._document_tabs):
            self._select_tab(start)  # type: ignore[attr-defined]
        self._announce(save_all_result(saved, stopped_at=stopped_at, left=left))  # type: ignore[attr-defined]

    def _report_batch_conversion(self, report: Any) -> None:
        """Say how a batch ended and keep the per-file list in Activity."""
        from quill.core import activity
        from quill.core.document_results import (
            batch_conversion_details,
            batch_conversion_folder,
            batch_conversion_result,
        )
        from quill.ui.activity_window import report_result
        from quill.ui.persistence_reporting import open_folder_action

        if report.failed or report.cancelled:
            outcome = activity.PARTIAL if report.converted else activity.FAILED
        else:
            outcome = activity.COMPLETED
        actions = {}
        next_actions: tuple[activity.NextAction, ...] = ()
        if report.converted:
            next_actions = (activity.OPEN_FOLDER,)
            actions[activity.OPEN_FOLDER.id] = open_folder_action(
                Path(batch_conversion_folder(report))
            )
        report_result(
            self,
            activity.ActionResult(
                action="Batch conversion",
                object_name=report.plan.root.name,
                outcome=outcome,
                summary=batch_conversion_result(report),
                next_actions=next_actions,
                details=batch_conversion_details(report),
            ),
            actions,
        )
