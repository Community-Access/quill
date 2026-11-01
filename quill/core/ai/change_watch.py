"""Tell me when this changes: a foreground watch the person starts and stops (decision 25).

For a screen region in Studio or a video in Radio. The app calls
:meth:`ChangeWatch.tick` every few seconds while the watch is on; this module
decides, and the hard rules live here so no app can loosen them:

* **Local first.** A pixel difference on this computer decides whether
  anything changed at all; below the threshold nothing happens. When it did
  change, OCR on this computer is tried next: changed words are reported
  without asking anyone.
* **The model, rarely.** Asked only when the picture changed and OCR could not
  say how, at most once a minute and at most 30 times a watch. The 30th ask
  ends the watch, and the watch says so.
* **Every ask counted** (the *count_ask* callback feeds the usage view).
* **Refused in Safe Mode.**
* **Nothing after the window closes.** :meth:`ChangeWatch.window_closed` ends
  the watch, and no tick after it grabs, reads or sends.
* **One sentence, only when something changed.** A model answering "no
  change" says nothing.

The clock, the picture source, OCR and the ask are injected, so the rules are
tested without a screen, a video or a network. Each picture sent follows the
consent of 10B.4, which the app's ask callback owns. wx-free and strict-typed.
"""

from __future__ import annotations

import io
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass

from quill.core.error_codes import CodedError

__all__ = [
    "ASK_INTERVAL_S",
    "DEFAULT_THRESHOLD",
    "MAX_ASKS",
    "ChangeWatch",
    "WatchRefused",
    "WatchReport",
    "pixel_difference",
]

#: The fewest seconds between two asks.
ASK_INTERVAL_S = 60.0
#: The most asks one watch may make; the last one ends it.
MAX_ASKS = 30
#: The share of the picture that must change before anything happens.
DEFAULT_THRESHOLD = 0.02
#: How much one grey level must move to count as changed (out of 255).
_TOLERANCE = 24
_SAMPLE = 64

Grab = Callable[[], "bytes | None"]
OcrFn = Callable[[bytes], str]
AskFn = Callable[[bytes, bytes, str], str]

_PROMPT = (
    "The first picture is how {subject} looked before; the second is how it looks now. "
    "In one sentence, say what changed that matters to someone who cannot see it. "
    "If nothing meaningful changed, answer exactly: no change."
)
_NO_CHANGE = re.compile(r"^\W*no\s+(meaningful\s+)?change", re.IGNORECASE)


class WatchRefused(CodedError):
    """A watch could not start; the message is a sentence for a person."""

    code = "QUILL-AI-WATCH-REFUSED"


@dataclass(frozen=True, slots=True)
class WatchReport:
    """One thing to speak and braille: a sentence, and who said it."""

    sentence: str
    #: ``local`` (pixel difference and OCR), ``model``, or ``watch`` (the watch itself).
    source: str
    asks_used: int = 0


def pixel_difference(before: bytes, after: bytes, *, tolerance: int = _TOLERANCE) -> float:
    """The share (0 to 1) of a small grey sample that moved by more than *tolerance*."""
    from PIL import Image, ImageChops

    with Image.open(io.BytesIO(before)) as a, Image.open(io.BytesIO(after)) as b:
        small_a = a.convert("L").resize((_SAMPLE, _SAMPLE))
        small_b = b.convert("L").resize((_SAMPLE, _SAMPLE))
    diff = ImageChops.difference(small_a, small_b)
    moved = sum(diff.histogram()[tolerance + 1 :])
    return moved / float(_SAMPLE * _SAMPLE)


def _first_sentence(text: str) -> str:
    text = " ".join((text or "").split())
    match = re.match(r"(.+?[.!?])(\s|$)", text)
    sentence = match.group(1) if match else text
    return sentence if sentence.endswith((".", "!", "?")) else sentence + "."


def _words(text: str) -> str:
    return " ".join((text or "").split())


class ChangeWatch:
    """One watch, from Start to Stop."""

    def __init__(
        self,
        *,
        grab: Grab,
        ask: AskFn,
        subject: str = "the picture",
        ocr: OcrFn | None = None,
        count_ask: Callable[[], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
        safe_mode: bool | None = None,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        self._grab = grab
        self._ask = ask
        self._ocr = ocr
        self._count = count_ask
        self._clock = clock
        self._safe_mode = (
            os.environ.get("QUILL_SAFE_MODE") == "1" if safe_mode is None else safe_mode
        )
        self._threshold = threshold
        self.subject = subject
        self.watching = False
        self.closed = False
        self.asks = 0
        self._last_ask: float | None = None
        self._baseline: bytes | None = None
        self._baseline_words = ""

    # -- start and stop --------------------------------------------------------- #

    def start(self) -> str:
        """Begin watching; the sentence to speak. Raises :class:`WatchRefused`."""
        if self._safe_mode:
            raise WatchRefused("Watching for changes is off in Safe Mode.")
        if self.closed:
            raise WatchRefused("This window has closed, so there is nothing to watch.")
        self.watching = True
        self.asks = 0
        self._last_ask = None
        self._baseline = None
        self._baseline_words = ""
        return f"Watching {self.subject} for changes."

    def stop(self, reason: str = "") -> str:
        """End the watch; the sentence to speak."""
        was = self.watching
        self.watching = False
        self._baseline = None
        if reason:
            return reason
        return f"Stopped watching {self.subject}." if was else "Nothing was being watched."

    def window_closed(self) -> None:
        """The window went: the watch ends and nothing more is grabbed or sent."""
        self.closed = True
        self.watching = False
        self._baseline = None

    # -- one tick --------------------------------------------------------------- #

    def _read(self, picture: bytes) -> str:
        if self._ocr is None:
            return ""
        try:
            return _words(self._ocr(picture))
        except Exception:  # noqa: BLE001 - no OCR means the model decides
            return ""

    def _rebase(self, picture: bytes, words: str) -> None:
        self._baseline = picture
        self._baseline_words = words

    def tick(self) -> WatchReport | None:
        """Look once. A report only when something changed (or the watch ended)."""
        if not self.watching or self.closed:
            return None
        picture = self._grab()
        if not picture:
            return None
        if self._baseline is None:
            self._rebase(picture, self._read(picture))
            return None
        if pixel_difference(self._baseline, picture) < self._threshold:
            return None
        words = self._read(picture)
        if words and words != self._baseline_words:
            shown = words if len(words) <= 160 else words[:157].rstrip() + "..."
            self._rebase(picture, words)
            return WatchReport(f"The words changed to: {shown}", "local", self.asks)
        now = self._clock()
        if self._last_ask is not None and now - self._last_ask < ASK_INTERVAL_S:
            return None  # keep the old baseline: the change is still there next minute
        return self._ask_model(picture, words, now)

    def _ask_model(self, picture: bytes, words: str, now: float) -> WatchReport | None:
        if self.closed:
            return None
        before = self._baseline or picture
        self.asks += 1
        self._last_ask = now
        if self._count is not None:
            self._count()
        try:
            answer = self._ask(before, picture, _PROMPT.format(subject=self.subject))
        except Exception as error:  # noqa: BLE001 - said once, and the watch ends
            sentence = self.stop(f"Stopped watching: the AI could not answer ({error}).")
            return WatchReport(sentence, "watch", self.asks)
        if self.closed:
            return None  # closed while the answer was on its way: say nothing
        self._rebase(picture, words)
        report = None
        if answer.strip() and not _NO_CHANGE.match(answer):
            report = WatchReport(_first_sentence(answer), "model", self.asks)
        if self.asks >= MAX_ASKS:
            ended = self.stop(
                f"Stopped watching: that was {MAX_ASKS} questions to the AI, the most one "
                "watch asks. Start again to keep watching."
            )
            if report is None:
                return WatchReport(ended, "watch", self.asks)
            return WatchReport(f"{report.sentence} {ended}", "model", self.asks)
        return report
