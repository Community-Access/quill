"""The commands on one Scribe job (PRD 7.4): Cancel Waiting, Retry, Enter
Password..., Remove from List and Ask for Human Review...

A mixin of :class:`quill.ui.scribe_controller.ScribeController`, kept apart
so each module stays under the 600-line cap (GATE-11). It uses the
controller's queue, service, host and ``_say``.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core import scribe
from quill.core.scribe import queue as q
from quill.core.scribe import sentences as say


class ScribeJobCommands:
    """Job commands, on the controller."""

    queue: Any
    host: Any
    app_name: str
    _service: Any
    _said_needs_you: set[tuple[str, str]]
    _speaker: Any

    def cancel_waiting(self, job_id: str) -> None:
        job = self.queue.get(job_id)
        if job is None or job.state in q.FINISHED:
            return
        stopped = self.queue.update(job_id, state=q.STOPPED, message="Stopped waiting")
        self._say(say.cancel_waiting_sentence(job, app_name=self.app_name))
        self._batch_finished(stopped or job)

    def retry(self, job_id: str) -> None:
        job = self.queue.get(job_id)
        if job is None:
            return
        if job.error_code == "QUILL-SCRIBE-SIGNIN" and not self.ensure_signed_in():
            return
        self.queue.update(
            job_id, respect_stop=False, state=q.QUEUED, message="", error_code="", password_tries=0
        )
        self._said_needs_you = {m for m in self._said_needs_you if m[0] != job_id}
        self._speaker.forget_job(job_id)  # its stages are said again as it runs again
        self.wake()

    def enter_password(self, job_id: str) -> None:
        job = self.queue.get(job_id)
        if job is None:
            return
        self.ensure_service()
        if self._service is None or not self._service.holding:
            holder = (self.queue.holder() or {}).get("app", "another app")
            self._say(
                f"{holder} is running this job; enter the password in its Conversions on This "
                "Computer window."
            )
            return
        from quill.ui.scribe_convert_password import ask_password

        password = ask_password(self.host.scribe_parent(), job, self.host.scribe_announce)
        if password:
            self._service.provide_password(job_id, password)

    def remove(self, job_id: str) -> None:
        self.queue.remove(job_id)

    def ask_for_review(self, document_id: str, title: str) -> None:
        if not document_id:
            return
        dialog = wx.TextEntryDialog(
            self.host.scribe_parent(),
            f"What is wrong with {title}? Scribe's people will look at it. Human review is "
            "Scribe's paid remediation; Scribe will tell you the cost.",
            "Ask for Human Review",
            style=wx.TE_MULTILINE | wx.OK | wx.CANCEL,
        )
        try:
            from quill.ui.dialog_contract import show_modal_dialog

            if show_modal_dialog(dialog, "Ask for Human Review") != wx.ID_OK:
                return
            comment = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not comment:
            return
        self._background(
            lambda: self.client().ask_for_review(document_id, comment),
            lambda _r: self._say(f"{title} was sent to {scribe.PRODUCT_NAME} for human review."),
        )


__all__ = ["ScribeJobCommands"]
