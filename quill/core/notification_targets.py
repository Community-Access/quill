"""What a notification points back at, written down so Enter can follow it.

A notice records what happened; this records *what it was about*. Reading
"3 new episodes -- The Allusionist" with no way to reach the show is half a
feature: the list is a log rather than a door, and a way back to the thing
itself was the other half of the reason to keep one.

### Why the ids are prefixed

A show id and a stream URL are both opaque strings, and an app handed one
without being told which it has can only guess. The prefixes here are the two
:mod:`quill.core.radio.item_notes` already uses, for the same question --
``show:`` and ``stream:`` -- so "which row is this about" has one vocabulary
across the product rather than two that drift apart.

**A bare string is a show id.** The first 3.1.0 notices stored the show id with
no prefix and are still in people's files; reading one as a show is what keeps
Enter working on a notification written before this module existed.

wx-free, no I/O, no dependencies: every app that raises or follows a notice
reads the same three functions.
"""

from __future__ import annotations

__all__ = ["KIND_SHOW", "KIND_STREAM", "for_show", "for_stream", "parse"]

KIND_SHOW = "show"
KIND_STREAM = "stream"

_KINDS = (KIND_SHOW, KIND_STREAM)


def for_show(show_id: str) -> str:
    """The target for a podcast, or ``""`` when there is no id to point at."""
    cleaned = str(show_id or "").strip()
    return f"{KIND_SHOW}:{cleaned}" if cleaned else ""


def for_stream(stream_url: str) -> str:
    """The target for a station, or ``""`` when it has no address."""
    cleaned = str(stream_url or "").strip()
    return f"{KIND_STREAM}:{cleaned}" if cleaned else ""


def parse(target: str) -> tuple[str, str]:
    """``(kind, id)`` for *target*, or ``("", "")`` when there is nothing.

    Only the kinds named above are recognised as prefixes, which matters more
    than it looks: a stream URL begins ``https:``, so splitting on the first
    colon and trusting whatever came back would read every station target as a
    kind called "https" and open nothing at all.
    """
    text = str(target or "").strip()
    if not text:
        return ("", "")
    kind, separator, rest = text.partition(":")
    if separator and kind in _KINDS:
        rest = rest.strip()
        return (kind, rest) if rest else ("", "")
    return (KIND_SHOW, text)
