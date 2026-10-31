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

from collections.abc import Sequence
from dataclasses import dataclass

Box = tuple[int, int, int, int]  # x, y, width, height in frame pixels

#: The face's centre may sit anywhere in the middle band without advice.
CENTRE_BAND = 0.18
TOO_CLOSE = 0.42
TOO_FAR = 0.11
#: A changed sentence must hold for this many frames before it is spoken,
#: so a blink of the detector does not chatter.
STABLE_FRAMES = 2


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
        return Framing(0, "No face in view.")
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
    """

    def __init__(self, *, coarse: bool = False) -> None:
        self.coarse = coarse
        self._spoken: str | None = None
        self._candidate: str | None = None
        self._count = 0

    def _key(self, result: Framing) -> str:
        if not self.coarse:
            return result.sentence
        return "in" if result.in_view else "out"

    def feed(self, result: Framing) -> str | None:
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
