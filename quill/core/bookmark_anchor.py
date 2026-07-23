"""Edit-surviving bookmark anchors (wx-free domain logic).

A bookmark stored as a bare character offset silently drifts to the wrong place
the moment text is inserted or deleted above it: reopen the file after an edit
and "Introduction" now lands in the middle of a paragraph. This module makes a
bookmark capture *more than a number* -- a short snippet of the text around the
caret plus its line -- so it can be **re-anchored**: relocated to where that
text actually lives now, not merely clamped to the new length.

The resolver is deliberately conservative and layered:

1. If the exact stored offset still sits at the same snippet, use it (the
   common no-edit-above case -- zero search cost).
2. Otherwise find the snippet again, preferring the occurrence nearest the old
   offset (handles text inserted or removed above the mark).
3. If the snippet is gone entirely (the bookmarked text was deleted or rewritten),
   fall back to the clamped offset -- never worse than today's behavior.

The captured window is small and text-only, so anchors stay cheap to store in
the existing JSON document-memory file.
"""

from __future__ import annotations

from dataclasses import dataclass

#: How many characters on each side of the caret to remember. Big enough to be
#: distinctive, small enough to stay cheap and to keep matching after nearby
#: edits.
_WINDOW = 40


@dataclass(frozen=True, slots=True)
class BookmarkAnchor:
    """A bookmark position plus the structural context to relocate it."""

    offset: int
    #: Text immediately before the caret (up to ``_WINDOW`` chars).
    before: str
    #: Text immediately at/after the caret (up to ``_WINDOW`` chars).
    after: str
    #: 0-based line the caret was on when captured (a coarse fallback hint).
    line: int

    def to_dict(self) -> dict[str, object]:
        return {
            "offset": self.offset,
            "before": self.before,
            "after": self.after,
            "line": self.line,
        }

    @classmethod
    def from_dict(cls, raw: object) -> BookmarkAnchor | None:
        """Parse a persisted anchor dict, or None if it isn't one."""
        if not isinstance(raw, dict):
            return None
        offset = raw.get("offset")
        if not isinstance(offset, int):
            return None
        before = raw.get("before")
        after = raw.get("after")
        line = raw.get("line")
        return cls(
            offset=max(0, offset),
            before=before if isinstance(before, str) else "",
            after=after if isinstance(after, str) else "",
            line=line if isinstance(line, int) and line >= 0 else 0,
        )


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, min(offset, len(text))))


def capture_anchor(text: str, offset: int) -> BookmarkAnchor:
    """Capture an edit-surviving anchor for the caret at *offset* in *text*."""
    offset = max(0, min(offset, len(text)))
    before = text[max(0, offset - _WINDOW) : offset]
    after = text[offset : offset + _WINDOW]
    return BookmarkAnchor(offset=offset, before=before, after=after, line=_line_of(text, offset))


def resolve_anchor(text: str, anchor: BookmarkAnchor) -> int:
    """Return the best current offset for *anchor* in (possibly edited) *text*.

    Never raises and never returns an out-of-range value; worst case it returns
    the clamped stored offset, matching the old bare-offset behavior.
    """
    length = len(text)
    clamped = max(0, min(anchor.offset, length))

    # A caret with no surrounding context (start of an empty doc, or a legacy
    # anchor) has nothing to search for -- clamp and go.
    needle = anchor.before + anchor.after
    if not needle.strip():
        return clamped

    # 1) Fast path: the stored offset still has the same neighborhood.
    here_before = text[max(0, clamped - len(anchor.before)) : clamped]
    here_after = text[clamped : clamped + len(anchor.after)]
    if here_before == anchor.before and here_after == anchor.after:
        return clamped

    # 2) Search for the boundary between `before` and `after`. Prefer the
    #    `after` snippet (what the caret sits on); its start is the caret.
    #    Choose the occurrence whose position is nearest the old offset, so a
    #    repeated snippet re-anchors to the right one after edits above.
    candidates: list[int] = []
    if anchor.after.strip():
        candidates.extend(_all_indices(text, anchor.after))
    if candidates:
        return min(candidates, key=lambda pos: abs(pos - anchor.offset))

    # 3) The caret sat at end-of-text (no `after`); anchor to the end of the
    #    `before` snippet instead.
    if anchor.before.strip():
        ends = [pos + len(anchor.before) for pos in _all_indices(text, anchor.before)]
        if ends:
            return min(ends, key=lambda pos: abs(pos - anchor.offset))

    # 4) Nothing matched -- the bookmarked text is gone. Clamp.
    return clamped


def _all_indices(haystack: str, needle: str) -> list[int]:
    if not needle:
        return []
    out: list[int] = []
    start = 0
    while True:
        found = haystack.find(needle, start)
        if found == -1:
            return out
        out.append(found)
        start = found + 1
