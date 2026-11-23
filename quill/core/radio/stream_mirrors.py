"""Count numbered mirrors of one stream as one row.

Big stations serve the same stream from ``ice1.example.org``, ``ice2``,
``ice3`` and on. Four rows that read the same sound like a broken scan, and
the listener cannot tell which to pick. So **live** rows whose hosts differ
only by a number in their first label, with the same path and any port written
out the same, and which sent the same stream name and codec, count as one
stream; the https copy is kept. A row that was not checked is never merged,
because nothing proves it is the same stream. The status line (shown, not
spoken) says how many copies were shown as one.

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
from dataclasses import dataclass

from quill.core.radio.page_links import PageStreamCandidate

__all__ = ["Collapsed", "collapse_mirrors", "mirror_key", "mirrors_sentence"]

_NUMBERED = re.compile(r"^([a-z-]{0,30}?)(\d{1,6})$")


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


def _key(candidate: PageStreamCandidate) -> str:
    """The row's mirror group: only a **live** row, and only with the name and
    codec it sent, so two copies are merged only when they were heard to be
    the same stream. A row that was not checked is never merged."""
    if candidate.check != "live":
        return ""
    where = mirror_key(candidate.url)
    if not where:
        return ""
    return f"{where}|{candidate.stream_name.casefold()}|{candidate.codec}"


@dataclass(frozen=True, slots=True)
class Collapsed:
    """The rows left, and how many copies were shown as one, in how many groups."""

    rows: list[PageStreamCandidate]
    copies: int = 0
    groups: int = 0


def collapse_mirrors(candidates: Sequence[PageStreamCandidate]) -> Collapsed:
    """*candidates* with each set of live numbered mirrors down to one row,
    https first, kept where the first of them stood."""
    best: dict[str, PageStreamCandidate] = {}
    sizes: dict[str, int] = {}
    for candidate in candidates:
        key = _key(candidate)
        if not key:
            continue
        sizes[key] = sizes.get(key, 0) + 1
        held = best.get(key)
        if held is None or (
            held.url.startswith("http://") and candidate.url.startswith("https://")
        ):
            best[key] = candidate
    out: list[PageStreamCandidate] = []
    placed: set[str] = set()
    for candidate in candidates:
        key = _key(candidate)
        if not key:
            out.append(candidate)
        elif key not in placed:
            placed.add(key)
            out.append(best[key])
    merged = [size for size in sizes.values() if size > 1]
    return Collapsed(out, sum(merged), len(merged))


def mirrors_sentence(copies: int, groups: int) -> str:
    """The status line's note (shown, never spoken), or "" when none merged."""
    if not groups:
        return ""
    if groups == 1:
        return f"Showed {copies} numbered copies of the same stream as one."
    return f"Showed {copies} numbered copies of {groups} streams as one row each."
