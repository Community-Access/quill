"""Classify and safety-check a "run target at cursor" (EDS-19).

Run Target at Cursor runs the URL, email address, or file path under the cursor (or
in the selection). QUILL routes that through the same conservative safety bar as
the executable-path validation (SEC-1): only ``http``/``https`` URLs, ``mailto:``
addresses, bare email addresses, and existing non-executable file paths are ever
launched. Anything that could run arbitrary code (``.exe``, ``.bat``, ``.cmd``,
``.com``, ``.ps1``, ``.sh``, ``.msi``, ``.scr``, ``.vbs``, ``.js``, ...) or that
uses an unexpected URL scheme is rejected.

This module is UI-framework agnostic so the classification and the security-reject
decision can be unit-tested without ``wx``.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = [
    "DANGEROUS_SUFFIXES",
    "RunTarget",
    "classify_target",
    "is_dangerous_executable",
    "target_at_cursor",
]

# Extensions that can execute code on launch. A path ending in one of these is
# never opened by the run-target command, even if the file exists.
DANGEROUS_SUFFIXES: frozenset[str] = frozenset({
    ".exe",
    ".bat",
    ".cmd",
    ".com",
    ".ps1",
    ".psm1",
    ".sh",
    ".bash",
    ".zsh",
    ".msi",
    ".scr",
    ".vbs",
    ".vbe",
    ".js",
    ".jse",
    ".wsf",
    ".wsh",
    ".hta",
    ".jar",
    ".pif",
    ".reg",
    ".lnk",
    ".dll",
    # Windows types that execute or navigate on open despite not looking like
    # programs: internet shortcuts, shell command files, compiled help (can
    # embed script), control-panel applets, management consoles, ClickOnce
    # references, settings shortcuts, scriptlets, and macro-enabled Office.
    ".url",
    ".scf",
    ".chm",
    ".cpl",
    ".msc",
    ".appref-ms",
    ".settingcontent-ms",
    ".wsc",
    ".docm",
    ".xlsm",
    ".pptm",
})

_ALLOWED_URL_SCHEMES: frozenset[str] = frozenset({"http", "https", "mailto"})

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Characters that terminate a target token when scanning out from the cursor.
_BOUNDARY = set(" \t\r\n\"'<>(){}[]|")


class RunTarget:
    """A classified run target.

    ``kind`` is one of ``"url"``, ``"email"``, ``"path"``, or ``"unknown"``.
    ``safe`` is ``True`` only when the target may be launched. ``reason`` explains
    a rejection (empty when ``safe``).
    """

    __slots__ = ("kind", "reason", "safe", "value")

    def __init__(self, value: str, kind: str, *, safe: bool, reason: str = "") -> None:
        self.value = value
        self.kind = kind
        self.safe = safe
        self.reason = reason

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"RunTarget(value={self.value!r}, kind={self.kind!r}, "
            f"safe={self.safe!r}, reason={self.reason!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RunTarget):
            return NotImplemented
        return (
            self.value == other.value
            and self.kind == other.kind
            and self.safe == other.safe
            and self.reason == other.reason
        )


def is_dangerous_executable(path: str) -> bool:
    """Return ``True`` when ``path`` ends in an executable/script extension."""
    try:
        suffix = Path(path).suffix.lower()
    except (ValueError, OSError):
        return True
    return suffix in DANGEROUS_SUFFIXES


def target_at_cursor(text: str, cursor: int, selection: str = "") -> str:
    """Return the run-target token under ``cursor`` (or the trimmed selection).

    A non-empty ``selection`` wins. Otherwise the token is the run of
    non-whitespace, non-bracket characters surrounding the cursor. Trailing
    sentence punctuation is stripped so ``"see https://x.org."`` yields the bare
    URL.
    """
    if selection.strip():
        return selection.strip()
    if not text:
        return ""
    cursor = max(0, min(cursor, len(text)))
    start = cursor
    while start > 0 and text[start - 1] not in _BOUNDARY:
        start -= 1
    end = cursor
    while end < len(text) and text[end] not in _BOUNDARY:
        end += 1
    return text[start:end].strip().rstrip(".,;:!?")


def classify_target(token: str) -> RunTarget:
    """Classify ``token`` and decide whether it is safe to launch."""
    value = token.strip()
    if not value:
        return RunTarget("", "unknown", safe=False, reason="No target at cursor")

    lowered = value.lower()
    # A single-letter "scheme" followed by a slash is a Windows drive (C:\, D:/),
    # not a URL scheme, so fall through to path handling.
    is_windows_drive = bool(re.match(r"^[a-z]:[\\/]", lowered))
    scheme_match = None if is_windows_drive else re.match(r"^([a-z][a-z0-9+.-]*):", lowered)
    if scheme_match:
        scheme = scheme_match.group(1)
        if scheme == "mailto":
            return RunTarget(value, "email", safe=True)
        if scheme in _ALLOWED_URL_SCHEMES:
            return RunTarget(value, "url", safe=True)
        # file: and any other scheme (javascript:, vbscript:, ...) are rejected.
        return RunTarget(value, "url", safe=False, reason=f"Unsupported URL scheme: {scheme}")

    if _EMAIL_RE.match(value):
        return RunTarget(value, "email", safe=True)

    if value.lower().startswith("www.") and " " not in value:
        return RunTarget(f"https://{value}", "url", safe=True)

    # Treat anything else as a filesystem path.
    if is_dangerous_executable(value):
        return RunTarget(
            value,
            "path",
            safe=False,
            reason="Refusing to launch an executable or script for safety",
        )
    return RunTarget(value, "path", safe=True)
