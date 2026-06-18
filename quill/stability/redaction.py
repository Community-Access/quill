"""Helpers for redacting sensitive information from logs and bundles.

This module is the single point through which the crash-bundle builder
(H-2) and the safe-subprocess logger (H-1) pass strings that might
contain secrets, file paths, or other personally identifying
information. Keeping the redaction rules in one place is the only
way to make the bundle redaction contract (``SECURITY.md``) testable.

The module is intentionally dependency-free and platform-neutral so it
can be imported from ``quill.core`` (wx-free) and from the early-startup
logging configuration in ``quill/__main__.py``.

Implements: ROADMAP SEC-13 (broad diagnostics secret redaction,
covering ``token``, ``password``, and ``NAME_KEY`` assignment
patterns) and the redaction contract in ``SECURITY.md:81``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

# Patterns that are almost always sensitive when they appear as
# command-line arguments or environment variables. We match the
# "name=value" form *or* the long/short flag form.
_SECRET_NAME_RE = re.compile(
    r"(?i)"
    r"(?:"
    # name=value
    r"(?:api[_-]?key|token|secret|password|passphrase|auth(?:orization)?|"
    r"access[_-]?key|client[_-]?secret|cookie|session|signature|hmac|"
    r"ssh[_-]?key|private[_-]?key|bearer)"
    r"\s*[=:]\s*"
    # value (stop at whitespace, quote, or end)
    r"[^\s\"'\\]+"
    r")"
    r"|"
    # -H "Authorization: …" or --header "…"
    r"(?:-{1,2}[A-Za-z_-]+\s+\"?[^\"]*(?:token|key|secret|password|auth|"
    r"bearer|cookie|signature)[^\"]*\"?)"
)

# Absolute Windows / POSIX paths. We replace only the *directory*
# portion so the trailing file name (often meaningful) remains, but
# the user-specific prefix is gone.
_WINDOWS_PATH_RE = re.compile(r"(?i)\b[A-Z]:\\(?:Users|Documents and Settings)\\[^\\\s\"']+")
_POSIX_PATH_RE = re.compile(r"\b/(?:home|Users)/[^/\s\"']+(?:/[^/\s\"']+)*")
_MACOS_PATH_RE = re.compile(r"\b/Users/[^/\s\"']+(?:/[^/\s\"']+)*")

# Simple email regex — used to drop addresses from the bundle.
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# Hex / base64-looking long tokens (>=32 chars of [0-9a-fA-F-_]).
_TOKEN_RE = re.compile(r"\b[A-Fa-f0-9_\-]{32,}\b")

# Modern API key prefixes that contain non-hex characters and would escape
# _TOKEN_RE: GitHub PATs (ghp_/gho_/github_pat_), OpenAI (sk-),
# AWS access keys (AKIA), Slack (xoxb-/xoxp-), generic long alphanumeric keys.
_PREFIXED_KEY_RE = re.compile(
    r"(?:ghp_|gho_|github_pat_|sk-|AKIA)[A-Za-z0-9_\-]{16,}"
    r"|"
    r"xox[bp]-[A-Za-z0-9_\-]{20,}"
    r"|"
    r"\b[A-Za-z0-9_\-]{36,}\b"
)

# Microsoft-style account tokens (TDI / refresh / eyJ… JWT).
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")

_MAX_LINE_BYTES = 4096


def redact_source_tokens(text: str) -> str:
    """Replace known API key patterns in *text* with ``[TOKEN]``.

    Lighter than :func:`redact_text_for_bundle`: only tokens are
    replaced, paths and emails are preserved. Used for console history
    so code structure is readable but accidental key pastes are masked.
    """
    text = _TOKEN_RE.sub("[TOKEN]", text)
    text = _JWT_RE.sub("[JWT]", text)
    text = _PREFIXED_KEY_RE.sub("[TOKEN]", text)
    return text


def redact_command_arg(arg: str) -> str:
    """Return a redacted form of a single command-line argument.

    The redaction rules are intentionally simple: anything that looks
    like a secret value (key=, --token, etc.) is replaced wholesale.
    Long hex/base64-looking tokens are shortened. Paths are stripped
    down to their trailing component. Each argument is also length-
    capped to keep log lines readable.
    """

    if not arg:
        return arg
    original = arg
    if _SECRET_NAME_RE.search(arg):
        return "[REDACTED]"
    # Drop the JWT / long token first to avoid double work.
    if _JWT_RE.search(arg) or _TOKEN_RE.search(arg) or _PREFIXED_KEY_RE.search(arg):
        arg = _TOKEN_RE.sub("[TOKEN]", arg)
        arg = _JWT_RE.sub("[JWT]", arg)
        arg = _PREFIXED_KEY_RE.sub("[TOKEN]", arg)
    arg = _WINDOWS_PATH_RE.sub("[PATH]", arg)
    arg = _POSIX_PATH_RE.sub("[PATH]", arg)
    arg = _MACOS_PATH_RE.sub("[PATH]", arg)
    arg = _EMAIL_RE.sub("[EMAIL]", arg)
    if len(arg) > 200:
        arg = arg[:200] + "…"
    return arg or original  # never return an empty string


def format_args_for_log(args: Sequence[str]) -> str:
    """Render a subprocess ``args`` list for safe logging.

    The executable basename is preserved (so support can see which tool
    was launched), the count of arguments is preserved, and every
    argument is run through :func:`redact_command_arg`. The output
    format is stable and easy to test::

        piper --model en_US-amy-medium.onnx --output_file out.wav — 4 args
    """

    if not args:
        return "(no args)"
    exe = args[0]
    # Use only the basename, never a full path, to avoid leaking the
    # install location.
    exe_base = exe.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    rest = [redact_command_arg(a) for a in args[1:]]
    if not rest:
        return f"{exe_base} — 0 args"
    return f"{exe_base} {' '.join(rest)} — {len(rest)} args"


def redact_text_for_bundle(
    text: str,
    *,
    line_cap: int = _MAX_LINE_BYTES,
) -> str:
    """Redact every line of ``text`` for inclusion in a crash bundle.

    The bundle redaction contract (H-2) says that before any text
    file is added to the diagnostic zip, every line must be
    passed through this helper. The redaction rules are:

    - apply :func:`redact_command_arg` to the line as a whole (so
      command-style "args=…" log lines are sanitized);
    - drop the line entirely if it matches a known-secret regex;
    - truncate the line to ``line_cap`` bytes with a tail marker.

    Returns the redacted text and a count of dropped/truncated lines
    in a side channel via the :class:`BundleRedactionStats` returned
    alongside (use :func:`redact_text_for_bundle_with_stats`).
    """

    redacted, _stats = redact_text_for_bundle_with_stats(text, line_cap=line_cap)
    return redacted


class BundleRedactionStats:
    """Tally of redaction actions taken by :func:`redact_text_for_bundle_with_stats`."""

    __slots__ = ("lines_in", "lines_dropped", "lines_truncated", "tokens_dropped")

    def __init__(self) -> None:
        self.lines_in = 0
        self.lines_dropped = 0
        self.lines_truncated = 0
        self.tokens_dropped = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "lines_in": self.lines_in,
            "lines_dropped": self.lines_dropped,
            "lines_truncated": self.lines_truncated,
            "tokens_dropped": self.tokens_dropped,
        }


def _line_is_pure_secret(line: str) -> bool:
    """A line is "pure secret" if it is, or contains, a secret value
    that should be dropped entirely. The check is intentionally
    conservative: false positives are fine (the user can run
    "redaction_receipt" to see what was dropped), false negatives
    are not (we promised to drop secrets)."""

    stripped = line.strip()
    if not stripped:
        return False
    if _SECRET_NAME_RE.search(stripped):
        return True
    if _JWT_RE.search(stripped):
        return True
    # A whole-line base64 token with a known-secret header.
    if stripped.startswith(("Bearer ", "Basic ", "Authorization:", "X-API-Key:")):
        return True
    return False


def redact_text_for_bundle_with_stats(
    text: str,
    *,
    line_cap: int = _MAX_LINE_BYTES,
) -> tuple[str, BundleRedactionStats]:
    """Redact ``text`` line-by-line and return (text, stats)."""

    stats = BundleRedactionStats()
    out: list[str] = []
    for line in text.splitlines():
        stats.lines_in += 1
        if _line_is_pure_secret(line):
            stats.lines_dropped += 1
            stats.tokens_dropped += 1
            continue
        redacted = redact_command_arg(line)
        if redacted != line:
            stats.tokens_dropped += 1
        if len(redacted) > line_cap:
            stats.lines_truncated += 1
            redacted = redacted[:line_cap] + "…[truncated]"
        out.append(redacted)
    return ("\n".join(out) + ("\n" if text.endswith("\n") else ""), stats)


# Command-id grammar used by the crash-bundle contract (H-3):
# "Only well-formed command ids (e.g. "open_file", "save", "find") are
# stored in recent_commands. Drop anything that doesn't match."
_COMMAND_ID_RE = re.compile(r"^[a-z][a-z0-9_.\-]{0,63}$")


def filter_recent_commands(commands: Sequence[str] | None) -> list[str]:
    """Validate ``recent_commands`` for inclusion in the crash bundle.

    Any string that does not match the command-id grammar is dropped.
    The caller is expected to use the return value as the bundle's
    ``recent_commands`` list, and to log the dropped count if it
    matters.
    """

    if not commands:
        return []
    return [c for c in commands if isinstance(c, str) and _COMMAND_ID_RE.match(c)]
