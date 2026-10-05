"""The recogniser's worker thread: voice detection, live engines, finishing,
and keeping up.

Moved out of :mod:`~quill.core.windows_dictation.local_recognizer` (GATE-11)
when the 2026-10-05 pass gave the worker four new duties:

* **Live engines** (:mod:`~quill.core.windows_dictation.streaming` for
  Nemotron, :mod:`~quill.core.windows_dictation.openai_recognizer` for OpenAI's
  live transcription): audio is fed to the engine *while* the voice detector
  hears speech, the provisional words go to the listener's ``on_partial``, and
  at the pause the engine's final words are the phrase. Engines without a live
  half are untouched: they transcribe each finished phrase, as before.
* **Finishing** (:meth:`WorkerMixin.finish`): letting go of the dictation key,
  or pressing it to stop, keeps the phrase being spoken. The detector is
  flushed, the last phrase is recognised and written, and only then is the
  listener told ``on_finished``, which closes the session. VS Code's stop does
  the same: the final transcript is applied.
* **The keep-up watchdog** (dict.md section 1,
  :class:`~quill.core.windows_dictation.keep_up.KeepUpWatchdog`): when audio
  waits longer than the engine can clear it, a downloaded model gives way to
  Moonshine for the rest of the session and the listener is told why, once.
* **Idle unloading**: :mod:`keep_up` again, from ``stop``.

Every result still crosses to the UI thread only through ``post``.
"""

from __future__ import annotations

import queue
import time
from typing import Any

from quill.core.windows_dictation.parser import RecognizedPhrase, words_from_text

__all__ = ["WorkerMixin"]

_BLOCK_SECONDS = 512 / 16_000


def _lr() -> Any:
    """local_recognizer, looked up at call time so tests' patches apply."""
    from quill.core.windows_dictation import local_recognizer

    return local_recognizer


class WorkerMixin:
    """The ``_work`` loop and its helpers. Mixed into LocalDictationRecognizer,
    which supplies the attributes declared here."""

    _listener: Any
    _engine: str
    _language: str
    _post: Any
    _running: Any
    _audio: queue.Queue[Any]
    _generation: int
    _discard_requested: Any
    _silent_blocks: int
    #: The live half of a streaming engine, or ``None``.
    _live: Any = None
    _finish_requested: Any = None
    _watchdog: Any = None
    _last_partial: str = ""

    def _lose_microphone(self) -> None:  # provided by the recogniser
        raise NotImplementedError

    # -- finishing ---------------------------------------------------------- #

    def finish(self) -> None:
        """Recognise what is being said, write it, then report ``on_finished``."""
        import threading

        if self._finish_requested is None:
            self._finish_requested = threading.Event()
        self._finish_requested.set()
        self._audio.put(False)  # wake the worker if it is waiting for audio

    def _finishing(self) -> bool:
        return self._finish_requested is not None and self._finish_requested.is_set()

    # -- the loop ----------------------------------------------------------- #

    def _work(self, vad: Any) -> None:
        lr = _lr()
        was_speaking = False
        in_phrase = False
        history = lr._History()
        stalled = 0
        try:
            while self._running.is_set():
                if self._discard_requested.is_set():
                    self._discard_requested.clear()
                    self._drain()
                    lr._reset(vad)
                    history = lr._History()
                    was_speaking = in_phrase = False
                    self._live_call("clear")
                try:
                    chunk = self._audio.get(timeout=lr._POLL_SECONDS)
                except queue.Empty:
                    stalled += 1
                    if stalled * lr._POLL_SECONDS >= lr._STALL_SECONDS:
                        self._lose_microphone()
                    continue
                if chunk is None:
                    break
                if chunk is False:  # finish() woke us
                    if self._finishing():
                        self._finish_now(vad, history)
                        return
                    continue
                stalled = 0
                if self._silent_blocks >= lr._SILENCE_BLOCKS:
                    self._lose_microphone()
                    continue
                history.add(chunk)
                vad.accept_waveform(chunk)
                speaking = bool(vad.is_speech_detected())
                if speaking and not was_speaking:
                    self._post(self._listener.on_speech_started)
                    if self._live is not None and not in_phrase:
                        in_phrase = True
                        self._live_begin(history)
                elif in_phrase and self._live is not None:
                    self._live_feed(chunk, speaking)
                was_speaking = speaking
                if self._drain_segments(vad, history):
                    in_phrase = False
                self._keep_up()
                if self._finishing():
                    self._finish_now(vad, history)
                    return
        except Exception:  # noqa: BLE001 - reported as a sentence, never a traceback
            if self._running.is_set():
                self._running.clear()
                self._post(
                    self._listener.on_failure,
                    "Dictation stopped: the speech engine could not go on. Start "
                    "dictation again, or choose another engine in Dictation Settings.",
                )

    def _drain_segments(self, vad: Any, history: Any) -> bool:
        """Recognise every phrase the detector has finished. ``True`` if any."""
        any_done = False
        while not vad.empty():
            segment = vad.front
            samples = history.with_lead_in(segment)
            vad.pop()
            any_done = True
            generation = self._generation
            started = time.monotonic()
            if self._live is not None:
                mark, text = self._live_end()
            else:
                mark, text = "", self._transcribe_healing(samples)
            self._note_speed(time.monotonic() - started, len(samples))
            if generation != self._generation:
                continue  # Escape was pressed while this was being decoded
            if (text or mark) and self._running.is_set():
                self._post(
                    self._listener.on_phrase,
                    RecognizedPhrase(words_from_text(text), text=text, previous_mark=mark),
                )
        return any_done

    def _finish_now(self, vad: Any, history: Any) -> None:
        """Flush the detector, recognise what was left, then report finished."""
        flush = getattr(vad, "flush", None)
        if callable(flush):
            try:
                flush()
            except Exception:  # noqa: BLE001 - nothing left to flush is fine
                pass
        self._drain_segments(vad, history)
        self._finish_requested.clear()
        handler = getattr(self._listener, "on_finished", None)
        if callable(handler):
            self._post(handler)

    # -- the live engine ------------------------------------------------------ #

    def _live_call(self, name: str) -> None:
        method = getattr(self._live, name, None)
        if callable(method):
            try:
                method()
            except Exception:  # noqa: BLE001 - a live engine that fails here is reset later
                pass

    def _live_begin(self, history: Any) -> None:
        import numpy as np

        lr = _lr()
        lead = int(lr.RATE * lr._LEAD_IN_SECONDS)
        held = np.concatenate(history._chunks) if history._chunks else np.zeros(0, np.float32)
        self._live.begin(held[-lead:])

    def _live_feed(self, chunk: Any, speaking: bool) -> None:
        partial = self._live.feed(chunk, speaking=speaking)
        handler = getattr(self._listener, "on_partial", None)
        if partial and partial != self._last_partial and callable(handler):
            self._last_partial = partial
            self._post(handler, partial)

    def _live_end(self) -> tuple[str, str]:
        self._last_partial = ""
        mark, text = self._live.end()
        return str(mark or ""), str(text or "").strip()

    # -- keeping up ------------------------------------------------------------ #

    def _note_speed(self, seconds: float, samples: int) -> None:
        if self._watchdog is not None:
            self._watchdog.note_phrase(seconds, samples / 16_000)

    def _keep_up(self) -> None:
        """Give way to Moonshine when audio is waiting longer than it should."""
        watchdog = self._watchdog
        if watchdog is None:
            return
        backlog = self._audio.qsize() * _BLOCK_SECONDS
        if not watchdog.falling_behind(backlog):
            return
        self._watchdog = None
        lr = _lr()
        try:
            lr._load(lr.DEFAULT_ENGINE, self._language)
        except Exception:  # noqa: BLE001 - no faster engine to move to: carry on
            return
        self._live_call("close")
        self._live = None
        self._engine = lr.DEFAULT_ENGINE
        self._drain()  # the backlog itself is what made it late
        handler = getattr(self._listener, "on_engine_notice", None)
        if callable(handler):
            self._post(
                handler,
                "This computer is busy, so dictation switched to the faster built-in "
                "engine for now. Your choice in Dictation Settings is unchanged.",
            )

    # -- phrase engines -------------------------------------------------------- #

    def _transcribe_healing(self, samples: Any) -> str:
        """One phrase, with the engine reloaded and the phrase retried once if the
        first decode raises. A second failure propagates to the worker's handler."""
        lr = _lr()
        try:
            return str(lr.transcribe(self._engine, samples, self._language))
        except Exception:  # noqa: BLE001 - one retry, then it is reported
            with lr._cache_lock:
                lr._recognizers.pop((self._engine, self._language), None)
            return str(lr.transcribe(self._engine, samples, self._language))

    def _drain(self) -> None:
        while True:
            try:
                self._audio.get_nowait()
            except queue.Empty:
                return
