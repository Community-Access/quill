"""A cue when the caret arrives on a line that carries an inline note (wx-free).

An inline note (:mod:`quill.core.inline_notes`, :mod:`quill.core.inline_notes_file`)
was silent until somebody pressed Alt+Shift+J to look for one: arrowing down a
document gave no sign that the line just read had a note on it. A sighted
reviewer sees a margin mark; a listener now hears one.

The rules, the same in both editors because both call this module:

* **On arrival only.** The cue plays when the caret enters a noted line from
  somewhere else, and never while it moves along that line -- Left, Right,
  Home, End and Ctrl+arrow inside it are silent. A note on a selection that
  spans several lines counts as one place: entering it cues once.
* **Sound, speech or off** (``inline_note_line_cue``, default ``sound``). A
  sound with no clip in the loaded pack speaks "note" instead, the
  ``action_feedback`` rule (:func:`quill.core.action_feedback.resolve`): the
  setting chooses between two kinds of cue, never down to none. ``off`` is
  silent throughout.
* **Braille parity.** When the cue is a sound, "note" also goes to a braille
  display -- written, never spoken -- because a tone does not reach somebody
  reading in braille without speech. When it is speech, the screen reader's
  own braille mirror shows the word already.

Nothing here reads the editor: the editors hand in the text, the caret and the
note rows, and get back whether to play, speak and write braille.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass, field

from quill.core.action_feedback import resolve
from quill.core.inline_notes import line_bounds

__all__ = [
    "NOTE_LINE_CUE_CHOICES",
    "NOTE_LINE_CUE_DEFAULT",
    "NOTE_LINE_CUE_LABELS",
    "NOTE_WORD",
    "NoteLineCue",
    "coerce_note_line_cue",
    "cue_channels",
    "noted_spans",
]

#: The setting's values, in the order a chooser lists them.
NOTE_LINE_CUE_CHOICES: tuple[str, ...] = ("sound", "speech", "off")
NOTE_LINE_CUE_DEFAULT = "sound"
#: Wording for any chooser, so the two editors never retype it.
NOTE_LINE_CUE_LABELS: dict[str, str] = {
    "sound": "Play a sound",
    "speech": 'Say "note"',
    "off": "Nothing",
}
#: What is said, and written to braille.
NOTE_WORD = "note"


def coerce_note_line_cue(value: object) -> str:
    """A stored value back into range; anything unknown is the default."""
    text = str(value or "").strip().lower()
    return text if text in NOTE_LINE_CUE_CHOICES else NOTE_LINE_CUE_DEFAULT


def cue_channels(mode: object, *, has_sound: bool) -> tuple[bool, bool, bool]:
    """``(play, speak, braille)`` for one arrival under *mode*."""
    chosen = coerce_note_line_cue(mode)
    if chosen == "off":
        return (False, False, False)
    play, speak = resolve("speech" if chosen == "speech" else "sound", has_sound=has_sound)
    return (play, speak, play and not speak)


def noted_spans(text: str, ranges: Iterable[tuple[int, int | None]]) -> list[tuple[int, int]]:
    """The ``[start, end]`` stretches of whole lines that carry a note.

    *ranges* is each located note's ``(position, end)``. Every note covers the
    lines from its first character's line to its last's. Overlapping
    stretches merge (two notes on one line are one place); neighbouring lines
    with notes of their own stay apart, so each one is announced.
    """
    spans: list[tuple[int, int]] = []
    for position, end in ranges:
        start, _ = line_bounds(text, position)
        last = position if end is None else max(position, end)
        _, stop = line_bounds(text, last)
        spans.append((start, stop))
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, stop in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], stop))
        else:
            merged.append((start, stop))
    return merged


@dataclass(slots=True)
class NoteLineCue:
    """Remembers where the caret was, so a cue happens on arrival only.

    :meth:`arrive` answers whether moving the caret to *caret* entered a noted
    stretch it was not already in. :meth:`settle` records a position without
    a cue -- for a command that has just said the note itself (Next Inline
    Note), where a tone on top would be the same news twice.
    """

    spans: list[tuple[int, int]] = field(default_factory=list)
    _starts: list[int] = field(default_factory=list)
    _inside: int | None = None

    def use(self, spans: list[tuple[int, int]]) -> None:
        """Replace the noted stretches (the text or the notes changed)."""
        self.spans = list(spans)
        self._starts = [start for start, _ in self.spans]

    def _span_at(self, caret: int) -> int | None:
        index = bisect_right(self._starts, caret) - 1
        if index >= 0 and caret <= self.spans[index][1]:
            return self.spans[index][0]
        return None

    def arrive(self, caret: int) -> bool:
        here = self._span_at(caret)
        entered = here is not None and here != self._inside
        self._inside = here
        return entered

    def settle(self, caret: int) -> None:
        self._inside = self._span_at(caret)

    def forget(self) -> None:
        """A different document: nothing is "already here" in it."""
        self._inside = None
