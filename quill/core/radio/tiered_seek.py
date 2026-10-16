"""Tiered seek: how far one burst of presses on Rewind or Forward moves.

FreeRadio's best interaction idea (xradio2.md 4.4), and the same lesson
``section_move_to`` was written from -- a destination, not forty keystrokes.
A listener who cannot see a scrub bar should be able to say "a little",
"a minute" or "a lot" with one hand and no counting:

* **hold** the key: 5 seconds for every auto-repeat the keyboard sends;
* **one tap**: 12 seconds;
* **two taps**: one minute;
* **three or more**: five minutes.

**One seek per burst, sized for the final count -- taps do not add up.** Three
taps are five minutes, not 12 + 60 + 300 seconds. The burst ends when the key
has been quiet for :data:`SETTLE_SECONDS`, and only then does anything move, so
the count can settle first and the listener hears one position, not three.

Telling a hold from quick taps uses the gap between presses: a keyboard's
auto-repeat arrives every 30 to 40 milliseconds, far quicker than anybody taps.

Pure, wx-free and strict-typed -- the timer lives in the UI
(``quill/ui/radio/tiered_seek_ui.py``), and the clock is passed in.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Quiet time that ends a burst. Long enough for a deliberate double tap, short
#: enough that one tap does not feel slow.
SETTLE_SECONDS = 0.45

#: Presses closer together than this are the keyboard's auto-repeat, not taps.
REPEAT_GAP_SECONDS = 0.09

#: Seconds per auto-repeat while the key is held.
HOLD_STEP_SECONDS = 5

#: Seconds for one, two, and three-or-more taps.
TAP_STEPS: tuple[int, int, int] = (12, 60, 300)


def seconds_for_taps(taps: int) -> int:
    """How far *taps* deliberate presses move (pure). 0 for no presses."""
    if taps <= 0:
        return 0
    return TAP_STEPS[min(taps, len(TAP_STEPS)) - 1]


@dataclass(slots=True)
class SeekBurst:
    """The presses of one burst, in one direction, waiting to settle."""

    direction: int = 0
    presses: list[float] = field(default_factory=list)

    @property
    def active(self) -> bool:
        return bool(self.presses)

    def press(self, direction: int, now: float) -> None:
        """Record one press. The caller settles first if *direction* changed."""
        if not self.presses:
            self.direction = 1 if direction > 0 else -1
        self.presses.append(now)

    def is_hold(self) -> bool:
        """Whether this burst is a held key (auto-repeat) rather than taps."""
        pairs = zip(self.presses, self.presses[1:], strict=False)
        gaps = [later - earlier for earlier, later in pairs]
        return any(gap < REPEAT_GAP_SECONDS for gap in gaps)

    def seconds(self) -> int:
        """The signed distance this burst moves (pure).

        A hold moves 5 seconds per press it delivered; taps move by the tier
        their count reaches.
        """
        if not self.presses:
            return 0
        size = (
            HOLD_STEP_SECONDS * len(self.presses)
            if self.is_hold()
            else seconds_for_taps(len(self.presses))
        )
        return size * self.direction

    def take(self) -> int:
        """The burst's distance, and start a fresh burst."""
        amount = self.seconds()
        self.presses = []
        self.direction = 0
        return amount
