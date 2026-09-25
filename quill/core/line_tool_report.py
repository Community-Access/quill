"""What a line tool says it did, counted the way the tool worked (bad.md N2).

A line tool that announces its own past tense and nothing else -- "Sorted lines
ascending" -- tells a listener that a key was pressed, which they knew, and not
what happened to the document, which they cannot see. Worse, it says the same
sentence when nothing changed at all: running Remove Duplicate Lines on a file
that has none is indistinguishable from running it on one that had twelve.

Two numbers are available and they are not interchangeable:

* **How much changed** is right for a tool that removes or rewrites. "Removed 2
  lines" is the fact, and it is what tells somebody whether to reach for undo.
* **How much the tool was given** is right for a *reordering*, where nothing was
  added or taken away. Counting the lines that happened to land somewhere else
  understates a sort of forty lines as "moved 38" and sends the reader hunting
  for the two that did not move.

QUILL Lite had both, chosen per call site by hand. Here the choice is derived --
a transform whose output is a permutation of its input is a reordering -- so a
new tool cannot forget to declare it, and both editors read one module.

wx-free and directly tested.
"""

from __future__ import annotations

__all__ = [
    "changed_size",
    "count_for",
    "describe_result",
    "is_reordering",
    "nothing_changed",
    "scope_size",
]


def _lines(text: str) -> list[str]:
    """*text* as lines, without counting a terminal newline as one.

    A file that ends the way files end has a trailing empty string after the
    split, and counting it makes "Sorted 4 lines" the answer for three.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def scope_size(text: str, *, unit: str = "line") -> int:
    """How much the tool was handed, counted in *unit*."""
    if unit != "line":
        return len(text)
    return len(_lines(text))


def changed_size(before: str, after: str, *, unit: str = "line") -> int:
    """How much differs between *before* and *after*, counted in *unit*.

    Lines when the tool works on lines, characters when it works on characters:
    a count of "1" for a sort of forty lines would be technically true of the
    string and useless to the person who ran it.
    """
    if unit == "line":
        old, new = before.split("\n"), after.split("\n")
        return abs(len(old) - len(new)) or sum(1 for a, b in zip(old, new, strict=False) if a != b)
    if len(before) != len(after):
        return max(len(before), len(after))
    return sum(1 for a, b in zip(before, after, strict=True) if a != b)


def is_reordering(before: str, after: str) -> bool:
    """True when *after* holds exactly the lines of *before*, in another order.

    Sort, reverse and shuffle answer True here; remove, trim and rewrite answer
    False. This is the test that picks which of the two counts to say, so a new
    tool gets the right one without declaring anything.
    """
    return before != after and sorted(_lines(before)) == sorted(_lines(after))


def count_for(before: str, after: str, *, unit: str = "line") -> int:
    """The number this result should be announced with."""
    if is_reordering(before, after):
        return scope_size(before, unit=unit)
    return changed_size(before, after, unit=unit)


def nothing_changed(unit: str = "line") -> str:
    """What to say when the tool ran and the document is identical."""
    return f"No {unit}s to change"


def describe_result(status: str, count: int, unit: str = "line") -> str:
    """*status* with the count appended: "Sorted lines ascending, 12 lines"."""
    plural = "" if count == 1 else "s"
    return f"{status}, {count} {unit}{plural}"
