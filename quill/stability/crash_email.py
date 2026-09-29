"""Crash reports as email to support (2026-09-26).

Until 2026-09-26 QUILL filed crash reports as public GitHub issues with a
token bundled in the installer. Now both crash paths -- the excepthook's
Report Crash dialog and Crash Recovery's Email Support button -- write a
:class:`~quill.core.support_message.SupportMessage` to
``support@community-access.org`` and hand it to the user's own mail program
through :func:`quill.ui.support_dialog.send_by_mail`, the same handoff as
Help > Get Help from Support. Nothing here sends anything.

This module is the wx-free half: the message itself, and the two log readers
the unclean-exit report quotes (moved here from the deleted
``quill/core/issue_submit.py``). Every quoted line is redacted through
:mod:`quill.stability.redaction`; the local log files are never modified.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.support_message import SupportMessage
from quill.stability.redaction import redact_text_for_bundle

#: Spelled once so a scripted edit cannot turn it into a real line break.
NEWLINE = chr(10)


def build_crash_support_message(
    *,
    summary: str,
    body: str,
    app_version: str,
    platform_name: str = "",
    screen_reader_name: str = "",
    extra: dict[str, str] | None = None,
) -> SupportMessage:
    """The crash report as a message to support, ready for the mail program.

    *body* should already be redacted (``crash_submit.build_crash_report_payload``
    and ``redact_user_description`` do that); it is scrubbed once more here
    because this is the last step before the text leaves QUILL's hands.
    """
    product = f"QUILL {app_version}".strip()
    return SupportMessage(
        product=product,
        summary=f"Crash report: {summary}" if summary else "Crash report",
        message=redact_text_for_bundle(body),
        category="Something is broken",
        platform=platform_name,
        screen_reader=screen_reader_name,
        extra={key: value for key, value in (extra or {}).items() if value},
    )


#: How much of the newest log an unclean-exit report quotes.
_MAX_LOG_CHARS = 6000


def build_log_summary(logs_path: Path, *, max_chars: int = _MAX_LOG_CHARS) -> str:
    """Return a redacted, length-bounded tail of the newest log file, or "".

    Every line is passed through the bundle redaction contract before it is
    returned for inclusion in a support email.
    """
    try:
        logs = sorted(logs_path.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return ""
    if not logs:
        return ""
    newest = logs[0]
    try:
        text = newest.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    redacted = redact_text_for_bundle(text[-max_chars:])
    return f"Newest log: {newest.name}{NEWLINE}{NEWLINE}{redacted}".strip()


#: Log lines that mean the UI thread stopped answering. An unclean exit with one
#: of these behind it is a hang; one without is something else entirely, and
#: knowing which is the difference between a report that can be worked and a
#: report that can only be closed (#1464, #1466, #1480).
_STALL_MARKERS = (
    "UI appears blocked",
    "wx UI heartbeat",
    "capturing stacks",
    "hard-exit watchdog",
)


def find_stall_evidence(logs_path: Path, *, max_lines: int = 6) -> str:
    """The last few UI-stall lines from the newest log, or "".

    An unclean-exit report carries a log *tail*, and a tail is mostly
    five-minute idle-sweep heartbeats -- the only real signal, a six-second UI
    stall, can be buried in the middle of a hundred lines of routine logging.
    Pulling the stall lines to the top of the report is the difference between
    "here is a hang, with the moment it started" and "here is a log".

    Redacted like every other quoted log line.
    """
    try:
        logs = sorted(logs_path.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return ""
    if not logs:
        return ""
    try:
        text = logs[0].read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    hits = [line for line in text.splitlines() if any(m in line for m in _STALL_MARKERS)]
    if not hits:
        return ""
    return redact_text_for_bundle(NEWLINE.join(hits[-max_lines:]))
