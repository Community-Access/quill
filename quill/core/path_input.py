"""Normalize user-typed and pasted filesystem paths (hardening pass).

Copying a path from File Explorer's "Copy as path" gives ``"C:\\Users\\..."``
with quotes; pasting from a browser can add a ``file:///`` prefix or a
non-breaking space; power users type ``%APPDATA%\\Quill`` or ``~/notes``. A
sighted user notices the stray quote; a blind user hears "path not found" with
no clue why. Every path field should accept all of these, so the cleanup lives
in one shared function instead of per-dialog. wx-free, strict-typed.
"""

from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

__all__ = ["clean_typed_path"]


def clean_typed_path(value: str) -> str:
    """Return *value* cleaned into a usable filesystem path string.

    Strips whitespace and non-breaking spaces, removes one pair of matching
    surrounding quotes (straight or smart), converts a ``file://`` URL to its
    local path, and expands environment variables and ``~``. Never raises and
    never touches the filesystem; an empty or blank input returns "".
    """
    text = (value or "").replace("\u00a0", " ").strip()
    if not text:
        return ""
    pairs = (('"', '"'), ("'", "'"), ("\u201c", "\u201d"), ("\u2018", "\u2019"))
    for opening, closing in pairs:
        if len(text) >= 2 and text.startswith(opening) and text.endswith(closing):
            text = text[1:-1].strip()
            break
    if text.lower().startswith("file:"):
        parsed = urlparse(text)
        candidate = unquote(parsed.path or "")
        # file:///C:/dir -> /C:/dir on Windows; drop the leading slash.
        if len(candidate) >= 3 and candidate[0] == "/" and candidate[2] == ":":
            candidate = candidate[1:]
        if parsed.netloc and parsed.netloc.lower() != "localhost":
            candidate = f"//{parsed.netloc}{candidate}"  # UNC share
        text = candidate.replace("/", os.sep) if candidate else text
    text = os.path.expandvars(text)
    return os.path.expanduser(text)
