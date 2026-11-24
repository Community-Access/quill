"""What a structural move says when it lands (FUX-14).

"Next chapter", "next bookmark", "next group": every family app that moves by
meaningful structure rather than by seconds or rows says the same three things
on arrival, in the same order, once -- the name of what it reached, what kind
of thing that is, and where it sits in the whole::

    Interview with the author, chapter 3 of 12.
    Where the storm starts, bookmark 2 of 5, 14 minutes 3 seconds.
    Pull requests, group 2 of 4, 7 items.

Quill Radio has said its chapters this way since 2026-10; this module is that
sentence, given a name so the other apps say it the same way instead of
inventing "Chapter: title" or "Chapter 3: title" each time.

A structure the app worked out, rather than one a person published, says so:
``estimated`` follows the position. A listener who jumps to an inferred chapter
boundary must not take it for the publisher's own (FUX-14: "clearly label
model-generated structure").

Pure and wx-free. The caller speaks the result through its own announcer, which
is what keeps it said once: nothing here repeats, and the caller announces only
the move the person asked for, never the playback that crosses a boundary on
its own.
"""

from __future__ import annotations

__all__ = ["describe_landing", "describe_boundary"]


def describe_landing(
    kind: str,
    name: str,
    index: int,
    total: int,
    *,
    estimated: bool = False,
    detail: str = "",
) -> str:
    """The one sentence a structural move says on arrival.

    *index* is zero-based. *name* falls back to the kind ("Untitled chapter")
    so the sentence never starts with a comma. *detail* is one short extra
    fact the landing alone knows -- a bookmark's time, a group's item count --
    appended last.
    """
    title = " ".join(str(name or "").split()) or f"Untitled {kind}"
    parts = [title, f"{kind} {index + 1} of {total}"]
    if estimated:
        parts.append("estimated")
    if detail:
        parts.append(detail)
    return ", ".join(parts) + "."


def describe_boundary(kind: str, *, forward: bool) -> str:
    """What a move past the last (or before the first) of a kind says."""
    return f"This is the {'last' if forward else 'first'} {kind}."
