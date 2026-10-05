"""Words while you speak: Nemotron run as the streaming model it is.

Nemotron 3.5 ASR Streaming recognises in 1.12-second chunks *while* you talk,
so the words of a phrase exist before the phrase ends. This feeds it the
microphone as the voice detector hears speech, hands the provisional words to
the live preview, and at the pause gives the phrase's final words to the same
normaliser and commands as every other engine.

**One stream for the whole session, not one per phrase.** Measured 2026-10-05
on Nemotron itself: given a phrase on its own, it leaves the end open (a
question came back "Can you send me the report by Friday" -- no mark at all);
kept running into the next phrase, it writes the right mark at the start of
what it hears next ("?  The meeting moved to Thursday"), and it got the
question mark, the full stop and the exclamation mark right on all five test
sentences. So a phrase is written at the pause, closed with a full stop or --
when it opens like a question -- a question mark
(:func:`~quill.core.windows_dictation.preview.close_sentence`), and the mark
Nemotron puts in front of the next phrase is passed on as
``previous_mark``, which :mod:`~quill.core.windows_dictation.live` uses to
correct the last phrase's ending in place.

**Only speech is decoded.** Between phrases the stream is fed at most
:data:`TAIL_SECONDS` of quiet -- what Nemotron needs to finish the last word,
and measured as the length that keeps its punctuation (1.2 seconds of quiet
made it start afresh, unpunctuated) -- and then nothing until the next speech,
so a silent room costs nothing, which matters on a dual-core computer.

wx-free; sherpa-onnx's online recogniser is handed in.
"""

from __future__ import annotations

from typing import Any

from quill.core.windows_dictation.preview import close_sentence

__all__ = ["TAIL_SECONDS", "NemotronLive", "split_previous_mark"]

#: Quiet fed after each phrase. See the module docstring.
TAIL_SECONDS = 0.6
_RATE = 16_000
#: A long session is restarted on a fresh stream after this many phrases, so
#: its state does not grow without end. One phrase's ending loses its context.
_PHRASES_PER_STREAM = 40
_MARKS = ".?!,;:" + chr(0x2026)


def split_previous_mark(text: str) -> tuple[str, str]:
    """``(mark, rest)``: a leading mark belongs to the phrase before."""
    stripped = text.lstrip()
    if stripped[:1] and stripped[0] in _MARKS:
        return stripped[0], stripped[1:].strip()
    return "", stripped.strip()


def _text(result: Any) -> str:
    return result if isinstance(result, str) else str(getattr(result, "text", result))


class NemotronLive:
    """The worker's live engine for Nemotron: begin, feed, end, clear, close."""

    def __init__(self, recognizer: Any, language: str = "en") -> None:
        self._recognizer = recognizer
        self._language = language
        self._stream: Any = None
        self._committed = ""
        self._phrases = 0
        self._quiet = 0  # samples of silence fed since speech
        self._fresh()

    def _fresh(self) -> None:
        self._stream = self._recognizer.create_stream()
        if self._language and hasattr(self._stream, "set_option"):
            self._stream.set_option("language", self._language)
        self._committed = ""
        self._phrases = 0

    def _accept(self, samples: Any) -> None:
        self._stream.accept_waveform(_RATE, samples)
        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)

    def _full(self) -> str:
        return _text(self._recognizer.get_result(self._stream))

    def _new(self) -> str:
        full = self._full()
        return full[len(self._committed) :] if full.startswith(self._committed) else full

    def begin(self, lead_in: Any) -> None:
        """Speech started; *lead_in* is the audio just before it was detected."""
        self._quiet = 0
        if lead_in is not None and len(lead_in):
            self._accept(lead_in)

    def feed(self, samples: Any, *, speaking: bool) -> str:
        """More of the phrase; the provisional words so far ('' if none)."""
        if speaking:
            self._quiet = 0
        else:
            if self._quiet >= int(TAIL_SECONDS * _RATE):
                return ""
            self._quiet += len(samples)
        self._accept(samples)
        return split_previous_mark(self._new())[1]

    def end(self) -> tuple[str, str]:
        """The pause: ``(previous_mark, final_text)``, the text closed with a mark."""
        import numpy as np

        missing = int(TAIL_SECONDS * _RATE) - self._quiet
        if missing > 0:
            self._accept(np.zeros(missing, dtype=np.float32))
            self._quiet += missing
        mark, text = split_previous_mark(self._new())
        self._committed = self._full()
        self._phrases += 1
        if self._phrases >= _PHRASES_PER_STREAM:
            self._fresh()
        return mark, close_sentence(text, self._language)

    def clear(self) -> None:
        """Escape: forget the phrase being heard, and its context."""
        self._fresh()

    def close(self) -> None:
        self._stream = None
