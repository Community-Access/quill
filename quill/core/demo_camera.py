"""Camera framing advice for a presenter who cannot see the preview.

The face detector (Windows' own, on the device) returns boxes; this turns
them into one short sentence -- "Face in view, centred", "Move a little to
your left", "No face in view" -- and decides when a change is worth saying.
Advice speaks from the presenter's side of the camera: a camera image is not
mirrored, so a face on the image's left means the presenter sits too far to
their right. ``mirrored`` flips that for cameras that deliver a mirror image.

wx-free and dependency-free, so every sentence is a unit test.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

Box = tuple[int, int, int, int]  # x, y, width, height in frame pixels

#: The face's centre may sit anywhere in the middle band without advice.
CENTRE_BAND = 0.18
TOO_CLOSE = 0.42
TOO_FAR = 0.11
#: A changed sentence must hold for this many frames before it is spoken,
#: so a blink of the detector does not chatter.
STABLE_FRAMES = 2
#: VIDEO-003: how long after the first frame actually read a camera is still
#: starting. A webcam takes about 0.58 s to its first frame and its first
#: pictures are often dark while exposure settles, so "no face" then means
#: "not yet", never "you left the view" (TG Drop Deck ``CLAUDE.md`` 489-497).
FIRST_FRAME_GRACE_S = 1.5
NO_FACE = "No face in view."


class FirstFrameGrace:
    """Whether a camera has been sending pictures long enough to judge them.

    Counted from frames actually read, not from when the camera was asked to
    start: however long a camera takes to open, the wait for its first frame
    is never a fault, and the grace only begins once a frame has arrived.
    ``frame_read`` may be called from the frame-reading thread; the state is
    two numbers written in order, read on another thread only as a whole.
    """

    def __init__(
        self,
        seconds: float = FIRST_FRAME_GRACE_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.seconds = seconds
        self._clock = clock
        self.frames = 0
        self._first: float | None = None

    def frame_read(self) -> None:
        if self._first is None:
            self._first = self._clock()
        self.frames += 1

    @property
    def settled(self) -> bool:
        first = self._first
        return first is not None and self._clock() - first >= self.seconds


@dataclass(frozen=True)
class Framing:
    faces: int
    sentence: str

    @property
    def in_view(self) -> bool:
        return self.faces > 0

    @property
    def good(self) -> bool:
        return self.sentence.startswith("Face in view")


def framing(
    faces: Sequence[Box], frame_width: int, frame_height: int, *, mirrored: bool = False
) -> Framing:
    if frame_width <= 0 or frame_height <= 0:
        return Framing(0, "The camera delivered no picture.")
    if not faces:
        return Framing(0, NO_FACE)
    if len(faces) > 1:
        return Framing(len(faces), f"{len(faces)} faces in view.")
    x, y, width, height = faces[0]
    advice: list[str] = []
    centre_x = (x + width / 2) / frame_width
    centre_y = (y + height / 2) / frame_height
    share = width / frame_width
    edge = 0.02
    cut = []
    if x <= frame_width * edge:
        cut.append("one side")
    elif x + width >= frame_width * (1 - edge):
        cut.append("one side")
    if y <= frame_height * edge:
        cut.append("the top")
    if y + height >= frame_height * (1 - edge):
        cut.append("the bottom")
    if share > TOO_CLOSE:
        advice.append("move back from the camera")
    elif share < TOO_FAR:
        advice.append("move closer to the camera")
    offset = centre_x - 0.5
    if abs(offset) > CENTRE_BAND:
        # Image left (offset < 0) is the presenter's right in an unmirrored image.
        to_left = offset < 0
        if mirrored:
            to_left = not to_left
        amount = "a little" if abs(offset) < 0.32 else ""
        side = "left" if to_left else "right"
        advice.append(f"move {amount + ' ' if amount else ''}to your {side}".strip())
    if centre_y < 0.22:
        advice.append("tilt the camera up or sit a little lower")
    elif centre_y > 0.62:
        advice.append("tilt the camera down or sit up taller")
    if cut:
        advice.insert(0, "your face is cut off at " + " and ".join(dict.fromkeys(cut)))
    if not advice:
        return Framing(1, "Face in view, centred.")
    text = "; ".join(advice)
    return Framing(1, f"Face in view: {text[0].upper()}{text[1:]}.")


class FramingAnnouncer:
    """Says a framing sentence only when it changes and has held steady.

    ``coarse`` speaks only in view / out of view changes -- the mode used
    during a recording, where moving about is normal and only losing the
    camera altogether is worth an interruption.

    ``grace`` (VIDEO-003) holds back a "no face" result until the camera
    has been sending frames for its grace period: a camera that is still
    starting is "not yet", and saying "your face left the view" then is a
    false alarm. A face found during the grace is taken as usual.
    """

    def __init__(self, *, coarse: bool = False, grace: FirstFrameGrace | None = None) -> None:
        self.coarse = coarse
        self.grace = grace
        self._spoken: str | None = None
        self._candidate: str | None = None
        self._count = 0

    def _key(self, result: Framing) -> str:
        if not self.coarse:
            return result.sentence
        return "in" if result.in_view else "out"

    def feed(self, result: Framing) -> str | None:
        grace = self.grace
        if grace is not None and result.sentence == NO_FACE and not grace.settled:
            return None  # Still starting: neither spoken nor counted towards a change.
        key = self._key(result)
        if key == self._candidate:
            self._count += 1
        else:
            self._candidate, self._count = key, 1
        if self._count < STABLE_FRAMES or key == self._spoken:
            return None
        first = self._spoken is None
        self._spoken = key
        if not self.coarse:
            return result.sentence
        if first and result.in_view:
            return None  # Starting in view is the expected state: say nothing.
        return "Face back in camera view." if result.in_view else "Your face left the camera view."
