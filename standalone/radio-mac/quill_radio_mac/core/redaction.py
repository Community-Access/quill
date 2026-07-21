"""Redaction of sensitive information from subprocess log lines.

Ported from upstream ``quill.stability.redaction``, trimmed to the one
entry point the radio app uses: :func:`format_args_for_log`, which the
recorder calls to log the ffmpeg command line it is about to launch.
The crash-bundle helpers (``redact_text_for_bundle`` and friends) are
not ported because this app has no crash-bundle/feedback-token flow.

The rules are deliberately conservative: anything that looks like a
secret (key=value, --token, Authorization headers, JWTs, long
hex/base64 tokens, prefixed API keys) is replaced wholesale; absolute
home-anchored paths are collapsed to ``[PATH]``; email addresses become
``[EMAIL]``. False positives are acceptable, false negatives are not.

ASCII note: upstream renders truncation with a Unicode ellipsis and the
arg count with an em dash; this port uses ``...`` and ``--`` instead,
per the project's ASCII-only output rule. Nothing parses these strings,
so only the log text changes.

Threading contract: pure functions over compiled module-level regexes;
safe from any thread (``re`` pattern matching is thread-safe).

macOS notes: the path patterns cover ``/Users/...`` (macOS) as well as
``/home/...`` and Windows drive paths, so logs redact correctly on every
platform the tests run on.
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
    # -H "Authorization: ..." or --header "..."
    r"(?:-{1,2}[A-Za-z_-]+\s+\"?[^\"]*(?:token|key|secret|password|auth|"
    r"bearer|cookie|signature)[^\"]*\"?)"
)

# Absolute Windows / POSIX paths. We replace only the *directory*
# portion so the trailing file name (often meaningful) remains, but
# the user-specific prefix is gone.
_WINDOWS_PATH_RE = re.compile(r"(?i)\b[A-Z]:\\(?:Users|Documents and Settings)\\[^\\\s\"']+")
_POSIX_PATH_RE = re.compile(r"\b/(?:home|Users)/[^/\s\"']+(?:/[^/\s\"']+)*")
_MACOS_PATH_RE = re.compile(r"\b/Users/[^/\s\"']+(?:/[^/\s\"']+)*")

# Simple email regex -- used to drop addresses from the log line.
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

# Microsoft-style account tokens (TDI / refresh / eyJ... JWT).
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")


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
        arg = arg[:200] + "..."
    return arg or original  # never return an empty string


def format_args_for_log(args: Sequence[str]) -> str:
    """Render a subprocess ``args`` list for safe logging.

    The executable basename is preserved (so support can see which tool
    was launched), the count of arguments is preserved, and every
    argument is run through :func:`redact_command_arg`. The output
    format is stable and easy to test::

        ffmpeg -i [REDACTED] out.mp3 -- 3 args
    """

    if not args:
        return "(no args)"
    exe = args[0]
    # Use only the basename, never a full path, to avoid leaking the
    # install location.
    exe_base = exe.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    rest = list(args[1:])
    # The macOS ``security`` CLI takes the secret as ``-w <secret>`` in
    # separate argv elements. ``-w`` itself has no secret-shaped keyword,
    # and a short/non-hex secret slips past redact_command_arg's token
    # regexes and leaks into the log. Redact the value that follows
    # ``-w`` before the generic per-arg pass so it can never appear.
    if exe_base == "security":
        for i, a in enumerate(rest):
            if a == "-w" and i + 1 < len(rest):
                rest[i + 1] = "[REDACTED]"
    rest = [redact_command_arg(a) for a in rest]
    if not rest:
        return f"{exe_base} -- 0 args"
    return f"{exe_base} {' '.join(rest)} -- {len(rest)} args"
