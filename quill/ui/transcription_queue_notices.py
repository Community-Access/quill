"""Notification persistence for durable file-transcription jobs."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

import wx

_NOTICE_WRITER = ThreadPoolExecutor(max_workers=1, thread_name_prefix="quill-transcription-notices")


def _after(function: Any, *args: Any) -> None:
    call_after = getattr(wx, "CallAfter", None)
    if callable(call_after):
        call_after(function, *args)
    else:
        function(*args)


def queue_notice(
    entry: Any,
    *,
    title: str,
    body: str,
    category: str,
    target: str = "",
    create: bool = False,
) -> Future[bool]:
    """Serialize notification-store I/O away from the UI thread."""

    def write() -> bool:
        try:
            from quill.core.notifications import add_notice, update_notice

            path = entry.host._dictation_notification_path()
            if create or not entry.notice_id:
                notices = add_notice(
                    app=entry.host._dictation_app_name(),
                    title=title,
                    body=body,
                    target=target,
                    category=category,
                    path=path,
                )
                if not notices:
                    raise OSError("The notification was not saved.")
                entry.notice_id = notices[-1].id
            elif not update_notice(
                entry.notice_id,
                title=title,
                body=body,
                target=target,
                category=category,
                path=path,
            ):
                raise OSError("The notification is no longer available.")
            entry.notice_error = ""
            return True
        except Exception as error:  # noqa: BLE001 - notice storage is separate from transcription
            entry.notice_error = f"{type(error).__name__}: notification could not be saved."
            return False

    try:
        future = _NOTICE_WRITER.submit(write)
    except RuntimeError:
        entry.notice_error = "RuntimeError: notification could not be saved."
        future = Future()
        future.set_result(False)
    entry.notice_future = future
    return future


def cancel_notice(entry: Any) -> None:
    future = queue_notice(
        entry,
        title=f"Transcription canceled: {entry.job.path.name}",
        body="Canceled before it started.",
        category="warning",
        create=entry.notice_future is None,
    )

    def report_failure(done: Future[bool]) -> None:
        if not done.result():
            _after(
                entry.host._dictation_say,
                f"The canceled transcription of {entry.job.path.name} could not be kept "
                f"in Notifications. {entry.notice_error}",
            )

    future.add_done_callback(report_failure)


def report_notice_failure(entry: Any, future: Future[bool], message: str) -> None:
    def completed(done: Future[bool]) -> None:
        if not done.result():
            _after(entry.host._dictation_say, f"{message} {entry.notice_error}")

    future.add_done_callback(completed)


__all__ = ["cancel_notice", "queue_notice", "report_notice_failure"]
