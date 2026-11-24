"""Back to Where I Was: the one place before a jump, in a player (FUX-01).

Go to Position and the chapter jumps move a long way at once, and a listener
who jumped to check something had no way back to where they were except to
remember a time they may never have been told. A sighted listener glances at
the scrubber; there is no equivalent, so it is a command.

One place, not a history: the time before the last jump in the item that is
playing. Going back swaps it with where you are now, so pressing it again
returns -- the "there and back" a listener actually does, and a pair that can
never strand you. Starting a different episode or file forgets it, because a
time in one recording says nothing about another.

The editors' Go Back (``quill.core.locations``, Alt+Left) is the same idea for
text, and the players use the same key. wx-free; QUILL Cast and Media Player
share it.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.media.timecode import format_spoken

__all__ = ["MIN_JUMP_MS", "NOTHING_TO_GO_BACK_TO", "JumpBack", "back_sentence"]

#: Said when there is no place to go back to: nothing has jumped yet in this
#: recording.
NOTHING_TO_GO_BACK_TO = "No earlier place to go back to."

#: Jumps shorter than this are not worth a place: a skip of a few seconds is
#: undone by the skip keys, and remembering it would overwrite the real one.
MIN_JUMP_MS = 2000


@dataclass(slots=True)
class JumpBack:
    """The place before the last jump, for one player."""

    _item: str = ""
    _position_ms: int | None = None

    def before_jump(self, item: str, position_ms: int, target_ms: int) -> bool:
        """Note where you are, in *item*, just before jumping to *target_ms*.

        ``False`` when nothing was noted: no item, or a nudge too small to keep.
        """
        if not item or abs(int(target_ms) - int(position_ms)) < MIN_JUMP_MS:
            return False
        self._item = item
        self._position_ms = max(0, int(position_ms))
        return True

    def back(self, item: str, position_ms: int) -> int | None:
        """Where to go back to in *item*, keeping *position_ms* for the return trip."""
        if not item or item != self._item or self._position_ms is None:
            return None
        target = self._position_ms
        self._position_ms = max(0, int(position_ms))
        return target

    def forget(self) -> None:
        self._item = ""
        self._position_ms = None


def back_sentence(position_ms: int) -> str:
    """What going back says: where it landed, once."""
    return f"Back to {format_spoken(position_ms)}."
