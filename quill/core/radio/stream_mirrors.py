"""Count numbered mirrors of one stream as one row.

Big stations serve the same stream from ``ice1.example.org``, ``ice2``,
``ice3`` and on. Four rows that read the same sound like a broken scan, and
the listener cannot tell which to pick. So hosts that differ only by a number
in their first label, with the same path and any port written out the same,
count as one stream, and
the best-checked copy is kept: live before not checked before a file, and
https before http when they check the same.

Only the number may differ: ``ice1.example.org`` and ``ice2.example.org`` are
mirrors; ``ice1.example.org`` and ``ice.example.org``, or ``jazz1`` and
``rock1``, are not. A path or a port that differs is a different stream.

Collapsing numbered mirrors is an idea from Andre Louis's StreamSift
(https://github.com/OnjLouis/StreamSift), written here in QUILL's own code.

wx-free, network-free, strict-typed.
"""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Sequence

from quill.core.radio.page_links import PageStreamCandidate

__all__ = ["collapse_mirrors", "mirror_key"]

_NUMBERED = re.compile(r"^([a-z-]{0,30}?)(\d{1,6})$")
_RANK = {"live": 0, "not checked": 1, "": 1, "file": 2}


def mirror_key(url: str) -> str:
    """What numbered mirrors of one stream share, or "" for an unnumbered host."""
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    first, _, rest = host.partition(".")
    match = _NUMBERED.match(first)
    if not match or not rest:
        return ""
    try:
        port = parts.port
    except ValueError:
        return ""
    # The scheme, and with it the default port, is left out on purpose: an
    # http and an https mirror of the same stream are one too (the https one
    # is kept). A port written out must match.
    return f"{match.group(1)}#.{rest}:{port or ''}{parts.path.rstrip('/')}?{parts.query}"


def _rank(candidate: PageStreamCandidate) -> tuple[int, bool]:
    return _RANK.get(candidate.check, 1), not candidate.url.startswith("https://")


def collapse_mirrors(candidates: Sequence[PageStreamCandidate]) -> list[PageStreamCandidate]:
    """*candidates* with each set of numbered mirrors down to its best copy,
    kept where the first of them stood."""
    best: dict[str, PageStreamCandidate] = {}
    for candidate in candidates:
        key = mirror_key(candidate.url)
        if not key:
            continue
        held = best.get(key)
        if held is None or _rank(candidate) < _rank(held):
            best[key] = candidate
    out: list[PageStreamCandidate] = []
    placed: set[str] = set()
    for candidate in candidates:
        key = mirror_key(candidate.url)
        if not key:
            out.append(candidate)
        elif key not in placed:
            placed.add(key)
            out.append(best[key])
    return out
