"""Crash-time report payload assembly (#622).

When QUILL hits an unhandled exception, the excepthook in
:mod:`quill.__main__` writes a local traceback file and then offers
the user a dialog to send a report to the developers. This module is
the wx-free half of that flow: it builds the redacted, length-bounded
report body that the dialog shows in its "What we will send" preview
and that :func:`quill.core.issue_submit.submit_crash_issue` ships to
GitHub.

The module is intentionally dependency-light so the excepthook can
import it before ``wx`` is necessarily available. It reuses
:mod:`quill.stability.redaction` for the secret-scrubbing contract,
:mod:`quill.core.diagnostics` for the recent-actions log and the
document-snapshot / environment / redacted-settings helpers, and the
last 10 command ids the run-listener has been writing since the
editor started.

The local traceback file is the *input* to this module (it is saved
by the excepthook before the dialog appears), but the body it returns
is a *separate* document: a redacted, formatted summary that the
dialog lets the user review and that the submit path attaches to the
GitHub issue. The local file is preserved either way; nothing here
deletes it.
"""

from __future__ import annotations

import re
import traceback
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.stability.redaction import redact_command_arg, redact_text_for_bundle

# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

# Maximum number of traceback frames to include. A runaway error in a
# recursive descent can easily produce hundreds of frames; bounding the
# report keeps the body readable and the GitHub issue small.
_MAX_TB_FRAMES = 12

# Maximum number of recent command ids to include.
_MAX_RECENT_COMMANDS = 10

# Maximum number of lines of "what were you doing" text the user can
# paste into the final report. Re-run through redact_text_for_bundle
# so any accidentally-pasted credential is scrubbed before it leaves
# the machine.
_MAX_USER_DESCRIPTION_CHARS = 1500

# Maximum length of a single inline exception-value (truncated with an
# ellipsis when longer). Long exception values are common (e.g. a
# pickled object or a large data structure) and would dwarf the rest
# of the report.
_MAX_VALUE_CHARS = 240

# Header line for the "What we will send" preview.
_PREVIEW_HEADER = "QUILL crash report (redacted, ready to send)"


@dataclass(frozen=True, slots=True)
class CrashReportPayload:
    """A complete, redacted crash report ready for the submit path.

    Attributes:
        summary: Short title for the GitHub issue. Synthesized from
            the exception class name and a one-line summary of the
            value.
        body: Multi-line, redacted, length-bounded report body. Safe
            to attach to a public GitHub issue; every line has been
            passed through the bundle redaction contract.
        metadata: Side-channel dict for
            :func:`quill.core.issue_submit.submit_crash_issue` (e.g.
            ``quill_version``, ``portable``, ``screen_reader``,
            ``recent_commands``).
        local_crash_file: The on-disk traceback file the excepthook
            saved before calling this builder. The dialog mentions
            this path so the user can find the raw dump after the
            dialog closes.
    """

    summary: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)
    local_crash_file: Path | None = None


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def build_crash_report_payload(
    *,
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: Any,
    local_crash_file: Path | None,
    app_version: str,
    portable: bool,
    screen_reader_name: str | None,
    recent_commands: Sequence[str] | None,
    active_document: object | None,
) -> CrashReportPayload:
    """Assemble a redacted :class:`CrashReportPayload` for the dialog.

    The builder does no I/O: the local crash file is the caller's
    responsibility and is referenced by path only. The body is the
    redacted, formatted, length-bounded string the user reviews in
    the dialog and that :func:`quill.core.issue_submit.submit_crash_issue`
    sends to GitHub.
    """
    summary = _synthesise_summary(exc_type, exc_value)
    body_sections: list[str] = [_PREVIEW_HEADER, ""]
    body_sections.append("Environment")
    body_sections.append(f"  Quill version : {app_version or 'unknown'}")
    body_sections.append(f"  Portable      : {portable}")
    if screen_reader_name:
        body_sections.append(f"  Screen reader : {screen_reader_name}")
    body_sections.append("")

    body_sections.append("Active document")
    body_sections.extend(_format_active_document(active_document))
    body_sections.append("")

    body_sections.append("Recent commands (most recent first)")
    cmds = list(recent_commands or [])[-_MAX_RECENT_COMMANDS:]
    if not cmds:
        body_sections.append("  (no recent command log available)")
    else:
        for cid in reversed(cmds):
            body_sections.append(f"  - {cid}")
    body_sections.append("")

    body_sections.append("Traceback (last frames)")
    body_sections.extend(_format_traceback(exc_type, exc_value, exc_tb))
    body_sections.append("")

    body_sections.append("Local crash report")
    if local_crash_file is not None:
        body_sections.append(f"  {local_crash_file}")
    else:
        body_sections.append("  (not saved -- see the in-app dialog for the path)")

    body = "\n".join(body_sections) + "\n"
    # Re-run the body through the bundle redaction contract. This is
    # belt-and-braces: the section builders above already include
    # only the fields we know are safe, but a future field that
    # leaks a path or token gets a second scrub before it leaves
    # the machine.
    body = redact_text_for_bundle(body)

    metadata: dict[str, Any] = {
        "quill_version": app_version or "",
        "portable": portable,
        "exception_class": exc_type.__name__,
        "exception_value": str(exc_value)[:_MAX_VALUE_CHARS],
    }
    error_code = getattr(exc_value, "code", None)
    if error_code:
        metadata["error_code"] = error_code
    if screen_reader_name:
        metadata["screen_reader"] = screen_reader_name
    if recent_commands:
        # filter_recent_commands drops anything that does not look
        # like a real command id. Run it here so the metadata the
        # submit path ships is always well-formed.
        from quill.stability.redaction import filter_recent_commands

        metadata["recent_commands"] = filter_recent_commands(list(recent_commands))
    if active_document is not None:
        try:
            from quill.core.diagnostics import document_snapshot

            metadata["active_document"] = document_snapshot(
                active_document,  # type: ignore[arg-type]
                include_file_paths=False,
            )
        except Exception:  # noqa: BLE001 - document snapshot is best-effort
            metadata["active_document"] = {"error": "snapshot failed"}
    if local_crash_file is not None:
        # Redact the same way the body's "Local crash report" line is:
        # this metadata dict is serialized verbatim into the public GitHub
        # issue by feedback_hub, bypassing the body's redaction pass, and
        # an un-redacted path here leaks the reporter's OS username (#886).
        metadata["local_crash_file"] = redact_command_arg(str(local_crash_file))

    return CrashReportPayload(
        summary=summary,
        body=body,
        metadata=metadata,
        local_crash_file=local_crash_file,
    )


def render_crash_report_preview(payload: CrashReportPayload) -> str:
    """Return the dialog's "What we will send" preview text.

    Pure text formatter; no I/O. The dialog wraps the returned string
    in a read-only StaticText. The body produced by
    :func:`build_crash_report_payload` already starts with the
    :data:`_PREVIEW_HEADER` line; this function adds it when the body
    was hand-built (tests, future callers) so the dialog always
    shows a recognisable header.
    """
    if not payload.body:
        return _PREVIEW_HEADER + "\n\n(empty report)\n"
    if _PREVIEW_HEADER in payload.body:
        return payload.body
    return f"{_PREVIEW_HEADER}\n\n{payload.body}"


def redact_user_description(text: str) -> str:
    """Run a user-supplied description through the bundle redaction contract.

    Used by the dialog to scrub the "What were you doing" / "Triggering
    command" / "Expected behaviour" fields before merging them into
    the final body. Caps the length so a paste of a multi-page log
    cannot blow up the GitHub issue.
    """
    if not text:
        return ""
    capped = (
        text
        if len(text) <= _MAX_USER_DESCRIPTION_CHARS
        else (text[:_MAX_USER_DESCRIPTION_CHARS] + "\n…[truncated by QUILL]")
    )
    return redact_text_for_bundle(capped)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _synthesise_summary(exc_type: type[BaseException], exc_value: BaseException) -> str:
    """Build the GitHub issue title: ``ClassName: short value``.

    The value is bounded and the trailing colon-collapse strips the
    empty case (``Exception: ''`` becomes just ``Exception``).
    """
    name = getattr(exc_type, "__name__", "Exception")
    raw = str(exc_value or "").strip()
    if not raw:
        return name
    short = raw if len(raw) <= _MAX_VALUE_CHARS else raw[:_MAX_VALUE_CHARS] + "…"
    # Collapse newlines so the summary is always a single line.
    short = re.sub(r"\s+", " ", short)
    return f"{name}: {short}"


def _format_traceback(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_tb: Any,
) -> list[str]:
    """Return up to ``_MAX_TB_FRAMES`` redacted traceback lines."""
    try:
        formatted = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    except Exception:  # noqa: BLE001 - never let a bad tb crash the builder
        return ["  (traceback could not be formatted)"]
    lines = formatted.splitlines()
    if len(lines) > _MAX_TB_FRAMES:
        lines = lines[-_MAX_TB_FRAMES:]
        return ["  …", *(f"  {ln}" for ln in lines)]
    return [f"  {ln}" for ln in lines]


def _format_active_document(active_document: object | None) -> list[str]:
    """Return one-line-per-field active document description, or a fallback."""
    if active_document is None:
        return ["  (no active document)"]
    try:
        from quill.core.diagnostics import document_snapshot

        snap = document_snapshot(
            active_document,  # type: ignore[arg-type]
            include_file_paths=False,
        )
    except Exception:  # noqa: BLE001 - document snapshot is best-effort
        return ["  (active document snapshot failed)"]
    name = str(snap.get("name") or "").strip() or "(untitled)"
    encoding = str(snap.get("encoding") or "").strip() or "unknown"
    line_ending = str(snap.get("line_ending") or "").strip() or "unknown"
    return [
        f"  Name         : {name}",
        f"  Encoding     : {encoding}",
        f"  Line ending  : {line_ending}",
    ]
