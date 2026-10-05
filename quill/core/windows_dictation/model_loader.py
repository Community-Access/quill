"""Loading a downloaded speech model, and the one shape every engine answers in.

**The pipeline, engine-neutral** (the owner's architecture, 2026-10-05)::

    microphone -> audio and voice detection -> speech engine -> normaliser
               -> QUILL's command processor -> the document

* Microphone, voice detection and phrase cutting:
  :mod:`~quill.core.windows_dictation.local_recognizer`.
* **The speech engine is this module's business.** Every engine, bundled or
  downloaded, is handed to the recogniser in one shape -- sherpa-onnx's offline
  contract, ``create_stream()`` / ``stream.accept_waveform(rate, samples)`` /
  ``decode_stream(stream)`` / ``stream.result.text`` -- described as
  :class:`DictationEngine`. A streaming model (Nemotron) is wrapped by
  :class:`PhraseModeOnline` so it answers in the same shape, a phrase at a
  time.
* The normaliser (:mod:`~quill.core.windows_dictation.parser`, ``composer``,
  ``options``) and the command processor (``vocabulary``, ``controller``) never
  see which engine spoke, so changing the engine never changes a command.

**Streaming.** Nemotron is a streaming model, and sherpa-onnx runs it as one.
Live dictation feeds it while you speak (:mod:`~quill.core.windows_dictation.streaming`,
wired into the recogniser's worker in 2026-10): the provisional words are the
live preview, and the phrase is written at the pause. :class:`PhraseModeOnline`
remains for anything that hands Nemotron a whole phrase (Test Microphone, the
benchmark); :class:`StreamingSession` is the one-utterance form.

**CPU only.** Every loader asks sherpa-onnx for its ``cpu`` provider by name;
the sherpa-onnx wheel QUILL ships is a CPU build, and nothing here looks for a
graphics card.

wx-free. sherpa-onnx is passed in, never imported here, so a test hands in a
fake.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Protocol

from quill.core.windows_dictation.model_catalog import DownloadableModel, downloadable

__all__ = [
    "DictationEngine",
    "PhraseModeOnline",
    "StreamingSession",
    "build",
    "close_sentence",
    "fallback_sentence",
    "online",
]

_PROVIDER = "cpu"
#: Nemotron 3.5's feature size (128 mel bins, not the 80 of older transducers).
_NEMOTRON_FEATURES = 128
_TAIL_SECONDS = 0.4


class DictationEngine(Protocol):
    """What the recogniser needs from any engine: sherpa-onnx's offline shape.

    No engine offered today takes a text prompt, so the rolling context (the
    words just written, :meth:`PhraseHistory.recent_text
    <quill.core.windows_dictation.history.PhraseHistory.recent_text>`) is kept
    by the command processor and is ready for the first one that does.
    """

    def create_stream(self) -> Any: ...

    def decode_stream(self, stream: Any) -> None: ...


class _Result:
    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text


class _OnlinePhrase:
    """One phrase for :class:`PhraseModeOnline`: an online stream that answers
    ``result.text`` the way an offline one does."""

    def __init__(self, stream: Any) -> None:
        self.stream = stream
        self.result = _Result("")

    def accept_waveform(self, rate: int, samples: Any) -> None:
        self.stream.accept_waveform(rate, samples)


class PhraseModeOnline:
    """A streaming (online) recogniser driven a phrase at a time.

    Each phrase gets a fresh stream pinned to the dictation language, the whole
    phrase plus a little quiet, ``input_finished``, and every chunk decoded.
    """

    def __init__(self, recognizer: Any, language: str = "") -> None:
        self._recognizer = recognizer
        self._language = language

    @property
    def online(self) -> Any:
        """The streaming recogniser itself, for the live preview (streaming.py)."""
        return self._recognizer

    def create_stream(self) -> _OnlinePhrase:
        stream = self._recognizer.create_stream()
        if self._language and hasattr(stream, "set_option"):
            stream.set_option("language", self._language)
        return _OnlinePhrase(stream)

    def decode_stream(self, phrase: _OnlinePhrase) -> None:
        import numpy as np

        phrase.stream.accept_waveform(16_000, np.zeros(int(16_000 * _TAIL_SECONDS), np.float32))
        phrase.stream.input_finished()
        while self._recognizer.is_ready(phrase.stream):
            self._recognizer.decode_stream(phrase.stream)
        text = _text(self._recognizer.get_result(phrase.stream))
        phrase.result = _Result(close_sentence(text, self._language or "en"))


def close_sentence(text: str, language: str = "en") -> str:
    """*text* closed with a mark when it ends in a word.

    Nemotron punctuates inside a phrase but, given one phrase on its own, leaves
    the end open (measured 2026-10-05: one closing mark in ten phrases). Every
    other engine closes a phrase at a pause, and the composer and "scratch
    that" both expect it to, so the phrase is closed here: with a question mark
    when it opens like a question, a full stop otherwise
    (:func:`quill.core.windows_dictation.preview.close_sentence`). Live
    dictation goes further and takes the mark Nemotron writes once it hears the
    next phrase (:mod:`~quill.core.windows_dictation.streaming`).
    """
    from quill.core.windows_dictation.preview import close_sentence as close

    return close(text, language)


def _text(result: Any) -> str:
    """sherpa-onnx answers ``get_result`` with a string or with an object."""
    return result if isinstance(result, str) else str(getattr(result, "text", result))


class StreamingSession:
    """The engine half of the live preview (dict.md 4.4): words while you speak.

    :meth:`accept` takes audio as it arrives, :meth:`partial` says the words so
    far (provisional -- they may still change), :meth:`finish` the final ones.
    Thread-safe: audio arrives on the worker and the preview may be read from
    anywhere.
    """

    def __init__(self, recognizer: Any, language: str = "") -> None:
        self._recognizer = recognizer
        self._lock = threading.Lock()
        self._stream = recognizer.create_stream()
        if language and hasattr(self._stream, "set_option"):
            self._stream.set_option("language", language)
        self._finished = False

    def accept(self, samples: Any) -> None:
        with self._lock:
            if self._finished:
                return
            self._stream.accept_waveform(16_000, samples)
            while self._recognizer.is_ready(self._stream):
                self._recognizer.decode_stream(self._stream)

    def partial(self) -> str:
        with self._lock:
            return _text(self._recognizer.get_result(self._stream)).strip()

    def finish(self) -> str:
        """Flush the last chunk and return the final words. Idempotent."""
        import numpy as np

        with self._lock:
            if not self._finished:
                self._finished = True
                tail = np.zeros(int(16_000 * _TAIL_SECONDS), np.float32)
                self._stream.accept_waveform(16_000, tail)
                self._stream.input_finished()
                while self._recognizer.is_ready(self._stream):
                    self._recognizer.decode_stream(self._stream)
            return _text(self._recognizer.get_result(self._stream)).strip()


def fallback_sentence(engine_id: str) -> str:
    """The one sentence said when a downloaded model gives way to the built-in
    engine: never a silent switch (the owner's rule, 2026-10-05)."""
    from quill.core.windows_dictation.model_store import installed

    model = downloadable(engine_id)
    name = model.name if model is not None else "The chosen speech model"
    if model is not None and not installed(model):
        return (
            f"{name} is not on this computer, so dictation is using the built-in "
            "engine; download it again in Dictation Settings, Speech Models."
        )
    return (
        f"{name} could not be loaded, so dictation is using the built-in engine; "
        "removing and downloading it again in Dictation Settings, Speech Models may help."
    )


def _files(model: DownloadableModel, folder: Path) -> dict[str, str]:
    return {item.role: str(folder / item.name) for item in model.files}


def build(
    model: DownloadableModel,
    folder: Path,
    sherpa_onnx: Any,
    *,
    language: str = "en",
    threads: int = 2,
) -> Any:
    """The recogniser for downloaded *model* in *folder*, in the offline shape.

    Raises whatever sherpa-onnx raises for a model it cannot load; the
    recogniser turns that into one plain sentence and the bundled engine.
    """
    files = _files(model, folder)
    if model.kind == "whisper":
        return sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=files["encoder"],
            decoder=files["decoder"],
            tokens=files["tokens"],
            language=language if language in model.languages else "en",
            num_threads=threads,
            provider=_PROVIDER,
        )
    if model.kind == "moonshine_v2":
        return sherpa_onnx.OfflineRecognizer.from_moonshine_v2(
            encoder=files["encoder"],
            decoder=files["decoder"],
            tokens=files["tokens"],
            num_threads=threads,
            provider=_PROVIDER,
        )
    if model.kind == "nemo_transducer":
        return sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=files["encoder"],
            decoder=files["decoder"],
            joiner=files["joiner"],
            tokens=files["tokens"],
            num_threads=threads,
            model_type="nemo_transducer",
            provider=_PROVIDER,
        )
    if model.kind == "nemotron":
        return PhraseModeOnline(online(model, folder, sherpa_onnx, threads=threads), language)
    raise ValueError(f"Unknown model kind: {model.kind}")


def online(model: DownloadableModel, folder: Path, sherpa_onnx: Any, *, threads: int = 2) -> Any:
    """Nemotron as sherpa-onnx's streaming recogniser (for :class:`StreamingSession`)."""
    files = _files(model, folder)
    return sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=files["tokens"],
        encoder=files["encoder"],
        decoder=files["decoder"],
        joiner=files["joiner"],
        num_threads=threads,
        sample_rate=16_000,
        feature_dim=_NEMOTRON_FEATURES,
        decoding_method="greedy_search",
        provider=_PROVIDER,
    )
