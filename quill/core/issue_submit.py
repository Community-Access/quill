"""Headless crash-report issue submission (#210 follow-up).

Lets the Crash Recovery dialog file a GitHub issue directly, using QUILL's
resolved token (see :mod:`quill.core.feedback_token`). The Quill repository is
PUBLIC, so any log text is scrubbed through :mod:`quill.stability.redaction`
before it leaves the machine, and only a bounded tail of the newest log file is
included. The network call happens only after explicit user consent in the
dialog; see ``quill/tools/network_egress_audit.py``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_LOG_CHARS = 6000
_SCHEMA_PATH = Path(__file__).parent / "schemas" / "feedback.json"


def target_repo() -> str:
    """Return the GitHub ``owner/repo`` issues are filed against, or ""."""
    try:
        data = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str(data.get("github_repo", "")).strip()


def build_log_summary(logs_path: Path, *, max_chars: int = _MAX_LOG_CHARS) -> str:
    """Return a redacted, length-bounded tail of the newest log file, or "".

    The repo is public, so every line is passed through the bundle redaction
    contract before it is returned for inclusion in an issue body.
    """
    from quill.stability.redaction import redact_text_for_bundle

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
    return f"Newest log: {newest.name}\n\n{redacted}".strip()


def submit_crash_issue(
    *,
    summary: str,
    message: str,
    app_version: str,
    github_token: str,
    metadata: dict | None = None,
) -> tuple[str | None, str | None]:
    """Create a GitHub issue for a crash report. Returns ``(issue_url, error)``.

    ``issue_url`` is None on any failure, with a human-readable reason in
    ``error``. Never raises.
    """
    if not github_token:
        return None, "No GitHub token configured"
    repo = target_repo()
    if not repo:
        return None, "No target repository configured"
    try:
        from feedback_hub import submit
    except Exception as exc:  # noqa: BLE001 - missing/broken feedback_hub is non-fatal
        return None, f"feedback_hub is not available: {exc}"
    try:
        result: tuple[str | None, str | None] = submit(
            app="Quill",
            github_repo=repo,
            github_token=github_token,
            summary=summary,
            message=message,
            category="Bug Report",
            app_version=app_version,
            github_labels=["bug", "needs-triage", "crash"],
            metadata=metadata or {},
        )
    except Exception as exc:  # noqa: BLE001 - submission must never crash the caller
        logger.warning("Crash issue submission failed", exc_info=True)
        return None, str(exc)
    return result
