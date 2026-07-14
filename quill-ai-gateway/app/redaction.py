"""Scrubbing rules applied to anything that might get logged or stored.

Mirrors the intent of QUILL desktop client's own
``quill/stability/redaction.py`` (secret-scrubbing before a crash report
or log line is written), ported server-side: defense in depth so a
provider key or an obvious credential-shaped string can never end up in
a log line or a diagnostic record even if some future code path
accidentally tries to write one.
"""

from __future__ import annotations

import re

_OPENAI_KEY_RE = re.compile(r"sk-[A-Za-z0-9_-]{20,}")
_BEARER_TOKEN_RE = re.compile(r"Bearer\s+[A-Za-z0-9._-]{16,}", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

_MAX_DIAGNOSTIC_LENGTH = 2000
"""Diagnostic records (PRD §4.3/§5) are truncated, never a full document."""


def scrub(text: str) -> str:
    """Replace anything key-shaped, bearer-token-shaped, or email-shaped
    with a placeholder. Applied to every log line this service emits and
    to any opt-in diagnostic record before it's written (PRD §4.3)."""
    text = _OPENAI_KEY_RE.sub("[REDACTED-KEY]", text)
    text = _BEARER_TOKEN_RE.sub("Bearer [REDACTED-TOKEN]", text)
    text = _EMAIL_RE.sub("[REDACTED-EMAIL]", text)
    return text


def redact_for_diagnostic_record(text: str) -> str:
    """The stricter transform used specifically for
    :class:`app.models.DiagnosticRecord` rows (PRD §4.3's opt-in
    troubleshooting path): scrub, then hard-truncate. Truncating here,
    not just relying on the caller to have already shortened the text,
    means this function is the one place the "never store a whole
    document" guarantee for diagnostic records actually lives."""
    scrubbed = scrub(text)
    if len(scrubbed) > _MAX_DIAGNOSTIC_LENGTH:
        return scrubbed[:_MAX_DIAGNOSTIC_LENGTH] + " …[truncated]"
    return scrubbed
