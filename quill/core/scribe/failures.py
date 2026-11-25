"""What a job becomes when its run ends in an error (PRD 7.4, 11).

The runner (:mod:`quill.core.scribe.runner`) catches what went wrong and
asks :func:`failure_changes` for the job's new state and message, and which
event to report: ``error`` for a job that has ended, ``needs_you`` for one
that waits for the person (sign in again, its password). Kept apart from
the runner so each module stays under the 600-line cap (GATE-11).

wx-free.
"""

from __future__ import annotations

from typing import Any

from quill.core.scribe import queue as q
from quill.core.scribe.errors import (
    ScribeError,
    ScribeGoneError,
    ScribeNotDocumentError,
    ScribePagesError,
    ScribePasswordError,
    ScribeSaveError,
    ScribeSignInError,
)
from quill.core.scribe.inputs import not_a_document_sentence

#: Wrong passwords before a job stops asking.
MAX_PASSWORD_TRIES = 3

__all__ = ["MAX_PASSWORD_TRIES", "failure_changes"]


def failure_changes(job: q.Job, error: BaseException) -> tuple[dict[str, Any], str]:
    """The job's changes for *error*, and the event to report."""
    if isinstance(error, ScribeSignInError):
        return {"state": q.NEEDS_SIGNIN, "message": error.message, "error_code": error.code}, (
            "needs_you"
        )
    if isinstance(error, ScribePasswordError):
        tries = job.password_tries + (1 if error.reason == "invalid_password" else 0)
        if tries >= MAX_PASSWORD_TRIES:
            return {
                "state": q.FAILED,
                "password_tries": tries,
                "message": f"{job.display_name} was not sent: password not accepted",
                "error_code": error.code,
            }, "error"
        return {
            "state": q.NEEDS_PASSWORD,
            "password_tries": tries,
            "message": error.message,
            "error_code": error.code,
        }, "needs_you"
    if isinstance(error, ScribePagesError):
        return {
            "state": q.FAILED,
            "message": error.message,
            "error_code": error.code,
            "purchase_url": error.purchase_url,
        }, "error"
    if isinstance(error, ScribeGoneError):
        return {"state": q.GONE, "message": error.message, "error_code": error.code}, "error"
    if isinstance(error, ScribeNotDocumentError):
        # Scribe's not_a_document gets the sentence that says what it takes.
        checked = error.reason == "checked_before_upload"
        message = error.message if checked else not_a_document_sentence(job.display_name)
        return {"state": q.FAILED, "message": message, "error_code": error.code}, "error"
    if isinstance(error, ScribeError):
        return {"state": q.FAILED, "message": error.message, "error_code": error.code}, "error"
    return {
        "state": q.FAILED,
        "message": f"A file could not be read or written: {error}",
        "error_code": ScribeSaveError.code,
    }, "error"
