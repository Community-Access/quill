"""Recorded audio, fed at live pace through dictation's real worker.

Used by ``dictbench.py --latency`` (dict.md B-4) and by the soak test
(``tests/stability/test_dictation_soak.py``, B-3), so both measure the code
people use: :class:`~quill.core.windows_dictation.local_recognizer.LocalDictationRecognizer`
with its Silero voice detector, its worker thread, its lead-in history and its
watchdogs. Only the microphone is replaced, by :class:`RecordedStream`, which
hands the recogniser 512-sample blocks from WAV files on its own thread, at
the pace a microphone would.

**No engine hook was needed:** :func:`recorded_recognizer` subclasses the
recogniser and overrides the two methods that touch the sound card
(``_check_audio_stack`` and ``_open_stream``). If D-26 renames those, this is
the one place to follow.

Between recordings, and after the last, the stream sends a quiet hiss (about
-80 dB), never exact zeros: the recogniser's watchdog rightly calls three
seconds of exact zeros a lost microphone.

**Nothing here types anywhere.** The soak's document is
:class:`FakeTarget` behind the shared ``ExternalDocument``: it records what
would have been typed, and never sends a key.

Times are ``time.monotonic()``. Latency, as dict.md B-4 defines it:

* **state change** -- from the first sample of speech reaching the
  recogniser to ``on_speech_started`` (the target is 500 ms at p95);
* **text** -- from the last sample of speech reaching the recogniser to the
  phrase's text arriving (the target is 2 s at p95). It includes the pause
  dictation waits for (0.8 s by default), as a person experiences it.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "Clip",
    "FakeTarget",
    "LatencyListener",
    "RecordedStream",
    "Session",
    "UiThread",
    "correction_efficiency",
    "latency_report",
    "memory_is_flat",
    "percentile",
    "recorded_recognizer",
    "run_session",
]

RATE = 16_000
BLOCK = 512
_HISS = 1e-4


@dataclass
class Clip:
    """One recording in the plan, and when the stream played it."""

    name: str
    samples: Any
    reference: str = ""
    started: float = 0.0  # monotonic time its first block went in
    ended: float = 0.0  # ...and its last
    pace: float = 1.0  # set by the stream that played it

    def speech_bounds(self) -> tuple[int, int]:
        """First and last sample of *speech* in the recording: a voice's own
        file (SAPI's, a recorder's) has quiet at both ends, which is not the
        person pausing and must not count towards latency."""
        import numpy as np

        samples = np.asarray(self.samples, dtype=np.float32)
        window = 320  # 20 ms
        count = len(samples) // window
        if count == 0:
            return 0, len(samples)
        rms = np.sqrt(np.mean(samples[: count * window].reshape(count, window) ** 2, axis=1))
        loud = np.nonzero(rms > max(0.005, 0.05 * float(rms.max())))[0]
        if loud.size == 0:
            return 0, len(samples)
        return int(loud[0]) * window, int(loud[-1] + 1) * window

    def _at(self, sample: int) -> float:
        return self.started + sample / RATE / (self.pace if self.pace > 0 else 1.0)

    @property
    def speech_started(self) -> float:
        return self._at(self.speech_bounds()[0])

    @property
    def speech_ended(self) -> float:
        return self._at(self.speech_bounds()[1])


class RecordedStream:
    """A stand-in for ``sounddevice.InputStream``: plays *clips* into *callback*.

    *pace* 1.0 is live; 0 is as fast as possible (for tests with fake
    engines). *gap* seconds of hiss go before each clip, and *tail* seconds
    after the last; then hiss continues until :meth:`stop`.
    """

    def __init__(
        self,
        callback: Callable[..., None],
        clips: Sequence[Clip],
        *,
        pace: float = 1.0,
        gap: float = 2.5,
        tail: float = 3.0,
    ) -> None:
        import numpy as np

        self._callback = callback
        self.clips = list(clips)
        self._pace = pace
        self._gap = gap
        self._tail = tail
        self._random = np.random.default_rng(20261015)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.finished = threading.Event()  # every clip and the tail were played
        self.closed = False
        self.blocks = 0

    # the sounddevice surface the recogniser uses
    def start(self) -> None:
        self._thread = threading.Thread(target=self._play, name="recorded-microphone", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5.0)

    def close(self) -> None:
        self.stop()
        self.closed = True

    # playing
    def _hiss(self, seconds: float) -> Any:
        import numpy as np

        count = int(seconds * RATE)
        return (self._random.standard_normal(count) * _HISS).astype(np.float32)

    def _play(self) -> None:
        import numpy as np

        began = time.monotonic()
        sent = 0  # samples handed over, which sets the clock at pace > 0

        def send(samples: Any) -> bool:
            nonlocal sent
            for start in range(0, len(samples), BLOCK):
                if self._stop.is_set():
                    return False
                block = np.asarray(samples[start : start + BLOCK], dtype=np.float32)
                if block.size < BLOCK:
                    pad = (self._random.standard_normal(BLOCK - block.size) * _HISS).astype(
                        np.float32
                    )
                    block = np.concatenate([block, pad])
                if self._pace > 0:
                    due = began + sent / RATE / self._pace
                    wait = due - time.monotonic()
                    if wait > 0:
                        time.sleep(wait)
                self._callback(block.reshape(-1, 1), BLOCK, None, None)
                sent += BLOCK
                self.blocks += 1
            return True

        for clip in self.clips:
            if not send(self._hiss(self._gap)):
                return
            clip.pace = self._pace
            # When its first block is due: the clock the paced stream keeps.
            clip.started = began + sent / RATE / self._pace if self._pace > 0 else time.monotonic()
            if not send(clip.samples):
                return
            clip.ended = time.monotonic()
        if not send(self._hiss(self._tail)):
            return
        self.finished.set()
        self._pace = max(self._pace, 1.0)  # then at a microphone's pace, never a flood
        began, sent = time.monotonic(), 0
        while not self._stop.is_set():  # a microphone keeps delivering
            if not send(self._hiss(0.5)):
                return


def recorded_recognizer(
    listener: Any,
    engine_id: str,
    clips: Sequence[Clip],
    *,
    post: Callable[..., None],
    pace: float = 1.0,
    gap: float = 2.5,
    tail: float = 3.0,
    pause_seconds: float = 0.8,
    language: str = "en",
) -> Any:
    """The real recogniser, listening to *clips* instead of a microphone."""
    from quill.core.windows_dictation.local_recognizer import LocalDictationRecognizer

    class _Recorded(LocalDictationRecognizer):
        recorded: RecordedStream | None = None
        reopened = 0

        def _check_audio_stack(self) -> None:
            pass  # no sound card: the engine itself is still checked by _prepare_engine

        def _reader_gate(self) -> Any:
            # Never the process's own gate: that one starts capturing the
            # running screen reader's audio. This one hears nothing.
            from quill.core.windows_dictation.reader_gate import ReaderGate

            return ReaderGate()

        def _open_stream(self) -> Any:
            if self.recorded is None:
                self.recorded = RecordedStream(self._on_audio, clips, pace=pace, gap=gap, tail=tail)
                return self.recorded
            self.reopened += 1  # the watchdog reopened it: hiss only, and counted
            return RecordedStream(self._on_audio, [], pace=pace, gap=0.0, tail=0.0)

    return _Recorded(listener, engine_id, post=post, pause_seconds=pause_seconds, language=language)


class UiThread:
    """One thread that runs posted calls in order: ``wx.CallAfter`` without wx.
    The controller only ever runs on it, as it only ever runs on the UI thread."""

    def __init__(self) -> None:
        self._calls: queue.Queue[Any] = queue.Queue()
        self.errors: list[BaseException] = []
        self._thread = threading.Thread(target=self._run, name="fake-ui", daemon=True)
        self._thread.start()

    def post(self, function: Callable[..., Any], *args: Any) -> None:
        self._calls.put((function, args))

    def call(self, function: Callable[..., Any], *args: Any) -> Any:
        """Run *function* on the UI thread and wait for its answer."""
        done = threading.Event()
        box: list[Any] = []

        def run() -> None:
            try:
                box.append(function(*args))
            finally:
                done.set()

        self.post(run)
        done.wait(timeout=30)
        return box[0] if box else None

    def drain(self) -> None:
        """Wait until everything posted so far has run."""
        self.call(lambda: None)

    def close(self) -> None:
        self._calls.put(None)
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while True:
            item = self._calls.get()
            if item is None:
                return
            function, args = item
            try:
                function(*args)
            except BaseException as error:  # noqa: BLE001 - kept for the test to report
                self.errors.append(error)


@dataclass
class LatencyListener:
    """A recogniser listener that only notes when things happened."""

    speech: list[float] = field(default_factory=list)
    phrases: list[tuple[float, str]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    lost: int = 0

    def on_speech_started(self) -> None:
        self.speech.append(time.monotonic())

    def on_phrase(self, phrase: Any) -> None:
        self.phrases.append((time.monotonic(), str(getattr(phrase, "text", "") or "")))

    def on_failure(self, message: str) -> None:
        self.failures.append(message)

    def on_microphone_lost(self) -> None:
        self.lost += 1

    def on_microphone_back(self) -> None:
        pass


def percentile(values: Sequence[float], share: float) -> float | None:
    """Nearest-rank percentile (95 for p95); ``None`` for no values."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * share // 100))
    return round(ordered[int(rank) - 1], 3)


def attribute(clips: Sequence[Clip], at: float) -> int | None:
    """The clip an event at *at* belongs to: the last one started by then."""
    found = None
    for index, clip in enumerate(clips):
        if clip.started and clip.started <= at:
            found = index
    return found


def latency_report(clips: Sequence[Clip], listener: LatencyListener) -> dict[str, Any]:
    """Per clip: what was heard, and its two latencies; and the p95 of each."""
    rows: list[dict[str, Any]] = []
    for index, clip in enumerate(clips):
        next_start = clips[index + 1].started if index + 1 < len(clips) else float("inf")
        starts = [t for t in listener.speech if attribute(clips, t) == index]
        phrases = [(t, text) for t, text in listener.phrases if attribute(clips, t) == index]
        row: dict[str, Any] = {
            "name": clip.name,
            "heard": " ".join(text for _t, text in phrases).strip(),
            "state_change_seconds": round(starts[0] - clip.speech_started, 3) if starts else None,
            "text_seconds": round(phrases[-1][0] - clip.speech_ended, 3) if phrases else None,
            "late": bool(phrases and phrases[-1][0] > next_start),
        }
        rows.append(row)
    state = [r["state_change_seconds"] for r in rows if r["state_change_seconds"] is not None]
    text = [r["text_seconds"] for r in rows if r["text_seconds"] is not None]
    return {
        "files": rows,
        "state_change_p95_seconds": percentile(state, 95),
        "text_p95_seconds": percentile(text, 95),
        "state_change_target_seconds": 0.5,
        "text_target_seconds": 2.0,
        "phrases_heard": len(listener.phrases),
        "clips_with_no_text": sum(1 for r in rows if r["text_seconds"] is None),
        "microphone_lost": listener.lost,
        "recogniser_failures": list(listener.failures),
    }


class FakeTarget:
    """What another program's field would hold: typing and backspaces are
    recorded, and no key is ever sent anywhere. Plug its two methods into
    ``ExternalDocument(type_text=..., backspace=...)``."""

    def __init__(self) -> None:
        self.text = ""
        self.typed: list[str] = []
        self.erased: list[int] = []
        self._lock = threading.Lock()

    def type_text(self, text: str, *_hush: Any) -> bool:
        with self._lock:
            self.typed.append(text)
            self.text += text
        return True

    def backspace(self, count: int) -> bool:
        with self._lock:
            self.erased.append(count)
            self.text = self.text[: max(0, len(self.text) - count)]
        return True


def correction_efficiency(corrections: Sequence[dict[str, Any]], final_text: str) -> dict[str, Any]:
    """dict.md B-5: utterances spent per error corrected.

    Each correction names the ``wrong`` words a phrase wrote, the ``right``
    words it should have written, and the ``utterances`` spent correcting it
    (a "scratch that" and the phrase said again is two). It counts as
    corrected when the final text has the right words and not the wrong ones.
    Run the same session with each method (scratch and say again; the D-1
    command word; D-10's correct-that; D-19's alternates) to compare them.
    """
    folded = " ".join(final_text.lower().split())
    corrected = [
        c
        for c in corrections
        if " ".join(c["right"].lower().split()) in folded
        and " ".join(c["wrong"].lower().split()) not in folded
    ]
    spent = sum(len(c["utterances"]) for c in corrected)
    return {
        "errors": len(corrections),
        "corrected": len(corrected),
        "utterances_per_corrected_error": round(spent / len(corrected), 2) if corrected else None,
    }


# --------------------------------------------------------------------------- #
# A whole session: recorded audio -> real worker -> real controller -> fake field
# --------------------------------------------------------------------------- #


def resident_mb() -> float | None:
    """This process's resident memory now (psutil, or Windows' own counter)."""
    try:
        import psutil  # type: ignore[import-untyped,import-not-found,unused-ignore]
    except ImportError:
        return None
    return round(psutil.Process().memory_info().rss / 1_048_576, 1)


def memory_is_flat(
    samples: Sequence[float], *, share: float = 0.15, slack_mb: float = 40.0
) -> bool:
    """dict.md B-3's "flat memory": the last third's median is within *share*
    (plus *slack_mb*) of the first third's. Too few samples cannot show growth."""
    if len(samples) < 6:
        return True
    third = len(samples) // 3
    first = sorted(samples[:third])[third // 2]
    last = sorted(samples[-third:])[third // 2]
    return last <= first * (1 + share) + slack_mb


class _CountingListener:
    """Stands between the recogniser and the controller: counts phrases, and
    notes when each arrived, then hands every event on unchanged."""

    def __init__(self, controller: Any) -> None:
        self._controller = controller
        self.phrases: list[tuple[float, str]] = []

    def on_phrase(self, phrase: Any) -> None:
        self.phrases.append((time.monotonic(), str(getattr(phrase, "text", "") or "")))
        self._controller.on_phrase(phrase)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._controller, name)


class _QuietFeedback:
    """The controller's feedback port, recording what it would say."""

    def __init__(self) -> None:
        self.said: list[str] = []

    def has_cue(self, _moment: Any) -> bool:
        return False

    def cue(self, _moment: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, _text: str) -> None:
        pass

    def show(self, _text: str) -> None:
        pass

    def state_changed(self, _state: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass


@dataclass
class Session:
    """What a recorded session did, for the soak's assertions."""

    target: FakeTarget
    said: list[str]
    phrases: list[tuple[float, str]]
    clips: list[Clip]
    memory_mb: list[float]
    microphone_closed: bool
    reopened: int
    ui_errors: list[BaseException]

    def phrases_per_clip(self) -> list[int]:
        counts = [0] * len(self.clips)
        for at, _text in self.phrases:
            index = attribute(self.clips, at)
            if index is not None:
                counts[index] += 1
        return counts


def run_session(
    clips: Sequence[Clip],
    *,
    engine: str = "moonshine",
    pace: float = 1.0,
    gap: float = 2.5,
    tail: float = 3.0,
    pause: float = 0.8,
    language: str = "en",
    memory_every: float = 30.0,
    settle: float = 3.0,
) -> Session:
    """Play *clips* through the real recogniser and controller into a
    :class:`FakeTarget` behind the shared ``ExternalDocument``, then stop."""
    from quill.core.windows_dictation import DictationController, DictationPreferences
    from quill.ui.windows_dictation_external import ExternalDocument

    ui = UiThread()
    target = FakeTarget()
    feedback = _QuietFeedback()
    document = ExternalDocument(
        problem=lambda: "",
        where=lambda: ("soak", 1, "edit"),
        type_text=target.type_text,
        backspace=target.backspace,
    )
    made: dict[str, Any] = {}

    def make(controller: Any, _preferences: Any) -> Any:
        listener = _CountingListener(controller)
        recognizer = recorded_recognizer(
            listener,
            engine,
            clips,
            post=ui.post,
            pace=pace,
            gap=gap,
            tail=tail,
            pause_seconds=pause,
            language=language,
        )
        made.update(listener=listener, recognizer=recognizer)
        return recognizer

    controller = DictationController(
        recognizer=make,
        document=document,
        feedback=feedback,
        preferences=lambda: DictationPreferences(phrase_feedback="silent", engine=engine),
    )
    memory: list[float] = []
    try:
        ui.call(controller.start)
        recognizer = made["recognizer"]
        stream = recognizer.recorded
        while not stream.finished.wait(memory_every):
            sample = resident_mb()
            if sample is not None:
                memory.append(sample)
        time.sleep(settle)
        ui.drain()
        ui.call(controller.stop)
        ui.drain()
        closed = (
            stream.closed
            and recognizer._stream is None
            and recognizer._worker is None
            and not controller.microphone_open
        )
    finally:
        ui.call(controller.shut_down)
        ui.close()
    return Session(
        target=target,
        said=feedback.said,
        phrases=made["listener"].phrases,
        clips=list(clips),
        memory_mb=memory,
        microphone_closed=closed,
        reopened=recognizer.reopened,
        ui_errors=ui.errors,
    )
