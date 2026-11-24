"""Move change by change through a difference written out as text (FUX-12).

The family's read-only diff views -- a file in a pull request, Compare
Branches, Compare Configuration, WordPress's Compare with Site -- write every
change as lines of text: where it is, then its lines, each marked in words
(:mod:`quill.core.diff_marks`). That reads well in speech and braille, but the
only way from one change to the next was line by line. This finds where each
change starts, so F8 and Shift+F8 can move there and say which one of how
many it is (:mod:`quill.ui.change_walk_keys`).

A change starts at a line the family's renderers write first:

* "Difference 2 of 5. ..." (QUILL's compare engine, which already counts);
* "At line 12:", "Lines 10 to 15:" or "A change:" (:func:`diff_marks.where`);
* "@@ -1,3 +1,4 @@" (a raw unified diff, where one is still shown; only a
  whole header, so prose or a Markdown line starting "@@ " is no stop).

No wx; strict-typed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["ChangeStop", "change_starts", "next_stop"]

_START = re.compile(
    r"^(Difference \d+ of \d+\.|At line \d+:|Lines \d+ to \d+:|A change:"
    r"|@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@)"
)
_COUNTED = re.compile(r"^Difference \d+ of \d+\.")
#: The engine's line goes on to quote the changed lines, which follow it
#: anyway; only its count and place are said.
_COUNT_AND_PLACE = re.compile(r"^(Difference \d+ of \d+\.[^.]*\.)")


@dataclass(frozen=True, slots=True)
class ChangeStop:
    """One change: its place in the order, the line it starts on, and what to say."""

    position: int  # 1-based
    total: int
    line: int  # 0-based line index in the text
    header: str

    def spoken(self) -> str:
        """ "Change 2 of 4. Lines 10 to 15:", or the engine's own count and place.

        The engine's line ("Difference 2 of 5. Text changed at line 41.
        old: ...") is cut after its place: the lines it quotes are the next
        lines of the text, there to be read.
        """
        if _COUNTED.match(self.header):
            found = _COUNT_AND_PLACE.match(self.header)
            return found.group(1) if found else self.header
        return f"Change {self.position} of {self.total}. {self.header}"


def change_starts(text: str) -> list[int]:
    """The 0-based index of every line where a change starts, in order."""
    return [index for index, line in enumerate(text.split("\n")) if _START.match(line)]


def next_stop(text: str, line: int, *, forward: bool = True) -> ChangeStop | None:
    """The change after (or before) line *line*, or None when there is no further one.

    Going forward from inside a change moves to the next change's start;
    going back from inside one moves to its own start first, as a reader
    expects of "previous".
    """
    starts = change_starts(text)
    if forward:
        found = [s for s in starts if s > line]
        target = found[0] if found else None
    else:
        found = [s for s in starts if s < line]
        target = found[-1] if found else None
    if target is None:
        return None
    header = text.split("\n")[target].strip()
    return ChangeStop(starts.index(target) + 1, len(starts), target, header)
