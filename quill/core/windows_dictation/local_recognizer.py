"""The built-in engines: Moonshine or Whisper, on this computer, as you pause.

Microphone audio arrives on PortAudio's thread (``sounddevice``), goes through
Silero voice-activity detection to find where a phrase ends, and each finished
phrase is recognised by sherpa-onnx on a worker thread. Only the *result*
crosses to the UI thread, through the ``post`` function the caller supplies
(``wx.CallAfter`` in both editors) -- so the controller, and everything it
touches in the document, only ever runs on the UI thread.

**When a phrase ends.** After 0.8 seconds of quiet. Shorter splits a sentence at
every breath, and each fragment is then recognised without the words around
it, which is where every engine is at its worst -- the first thing measured to
matter when the Windows engine was being tuned. Longer makes a phrase land late.
A phrase is also cut at 20 seconds whatever happens, so somebody reading a long
paragraph without pausing still sees it arrive.

**Models are loaded once per session** and kept: Moonshine takes about a second
to load, Whisper a little less, and paying that on every Ctrl+F11 would make
starting dictation feel broken.

Needs ``sherpa-onnx``, ``numpy`` and ``sounddevice``, all imported lazily -- a
copy without them raises :class:`DictationStartError` with a sentence, never an
import error.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Any, Protocol

from quill.core.windows_dictation.controller import DictationStartError
from quill.core.windows_dictation.engines import (
    engine_info,
    model_dir,
    package_dirs,
    vad_model_path,
)
from quill.core.windows_dictation.parser import RecognizedPhrase, words_from_text

__all__ = [
    "LocalDictationRecognizer",
    "input_device_for",
    "list_input_names",
    "record_and_hear",
]

RATE = 16_000
_BLOCK = 512  # Silero's window at 16 kHz
_MIN_SILENCE_SECONDS = 0.8
_MAX_PHRASE_SECONDS = 20.0

#: What Whisper writes for noise it could not place: a cough, a chair, the tail
#: of a breath. Dropped only when it is the *whole* phrase, so somebody who
#: dictates "Thank you." after a real sentence still gets it.
_NOISE_PHRASES = frozenset({"", ".", "you", "you.", "thank you.", "thanks for watching!", "bye."})
_SHORT_SECONDS = 0.8
_LEAD_PAD_SECONDS = 0.2
#: Audio taken from before the moment speech was detected -- see _History.
_LEAD_IN_SECONDS = 0.4
_TAIL_PAD_SECONDS = 0.5

_cache_lock = threading.Lock()
_recognizers: dict[str, Any] = {}

Poster = Callable[..., None]


class _Listener(Protocol):
    def on_speech_started(self) -> None: ...

    def on_phrase(self, phrase: RecognizedPhrase) -> None: ...

    def on_failure(self, message: str) -> None: ...


# --------------------------------------------------------------------------- #
# Microphones
# --------------------------------------------------------------------------- #


def _mme_inputs() -> list[tuple[int, str]]:
    """``(index, name)`` for each input on the MME host API, Windows' own list.

    MME rather than every host API because sounddevice reports each physical
    microphone once per API (MME, DirectSound, WASAPI, WDM-KS), and a list with
    every headset in it four times is a list nobody can choose from.
    """
    import sounddevice as sd

    devices = []
    for index, device in enumerate(sd.query_devices()):
        if int(device.get("max_input_channels", 0)) <= 0:
            continue
        if sd.query_hostapis(device["hostapi"])["name"] != "MME":
            continue
        name = str(device["name"])
        if name.startswith("Microsoft Sound Mapper"):
            continue  # "the default", which the list already offers by name
        devices.append((index, name))
    return devices


def list_input_names() -> list[str]:
    """The microphones sounddevice can open, by name. Empty when it cannot."""
    try:
        return [name for _index, name in _mme_inputs()]
    except Exception:  # noqa: BLE001 - no audio stack is an empty list
        return []


def _same_device(saved: str, candidate: str) -> bool:
    """MME truncates names to 31 characters; Windows speech does not."""
    saved, candidate = saved.strip().lower(), candidate.strip().lower()
    return bool(saved and candidate) and (
        saved == candidate or saved.startswith(candidate) or candidate.startswith(saved)
    )


def input_device_for(microphone: str) -> int | None:
    """The device index for a saved microphone name; ``None`` for the default.

    Raises :class:`DictationStartError` when a *named* microphone is not here --
    listening on another one without saying so is the one thing that must not
    happen, because the user chose that microphone for a reason.
    """
    if not microphone or microphone.startswith("HKEY_"):
        return None  # the default, or a Windows speech token from an earlier build
    for index, name in _mme_inputs():
        if _same_device(microphone, name):
            return index
    raise DictationStartError(
        f"The microphone chosen in Dictation Settings ({microphone}) is not connected. "
        "Connect it, or choose another microphone in Dictation Settings."
    )


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


def _import_sherpa() -> Any:
    """``sherpa_onnx``, from the environment or from beside the models."""
    try:
        import sherpa_onnx

        return sherpa_onnx
    except ImportError:
        pass
    import sys

    for folder in package_dirs():
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    import sherpa_onnx

    return sherpa_onnx


def _load(engine_id: str) -> Any:
    """The sherpa-onnx recogniser for *engine_id*, loaded once per session."""
    with _cache_lock:
        cached = _recognizers.get(engine_id)
        if cached is not None:
            return cached
        folder = model_dir(engine_id)
        if folder is None:
            raise DictationStartError(
                f"{engine_info(engine_id).label.split(' (')[0]} is not included in this copy "
                "of QUILL. Choose another speech engine in Dictation Settings."
            )
        sherpa_onnx = _import_sherpa()

        if engine_id == "moonshine":
            recognizer = sherpa_onnx.OfflineRecognizer.from_moonshine(
                preprocessor=str(folder / "preprocess.onnx"),
                encoder=str(folder / "encode.int8.onnx"),
                uncached_decoder=str(folder / "uncached_decode.int8.onnx"),
                cached_decoder=str(folder / "cached_decode.int8.onnx"),
                tokens=str(folder / "tokens.txt"),
                num_threads=2,
            )
        else:
            recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=str(folder / "encoder.int8.onnx"),
                decoder=str(folder / "decoder.int8.onnx"),
                tokens=str(folder / "tokens.txt"),
                language="en",
                num_threads=2,
            )
        _recognizers[engine_id] = recognizer
        return recognizer


def _vad(pause_seconds: float = _MIN_SILENCE_SECONDS) -> Any:
    path = vad_model_path()
    if path is None:
        raise DictationStartError(
            "Part of dictation is missing from this copy of QUILL (the model that "
            "hears where a phrase ends). Reinstalling QUILL puts it back."
        )
    sherpa_onnx = _import_sherpa()
    config = sherpa_onnx.VadModelConfig()
    config.silero_vad.model = str(path)
    config.silero_vad.threshold = 0.5
    config.silero_vad.min_silence_duration = pause_seconds
    config.silero_vad.min_speech_duration = 0.25
    config.silero_vad.max_speech_duration = _MAX_PHRASE_SECONDS
    config.silero_vad.window_size = _BLOCK
    config.sample_rate = RATE
    return sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60)


def transcribe(engine_id: str, samples: Any) -> str:
    """One phrase of 16 kHz float samples as text, noise answers removed."""
    import numpy as np

    recognizer = _load(engine_id)
    stream = recognizer.create_stream()
    # Quiet on either side. Voice detection trims a phrase tight to the speech,
    # and Moonshine sizes its answer from the audio's length: without the tail,
    # "three o'clock" came back as "3 o'" on the first real test.
    padded = np.concatenate([
        np.zeros(int(RATE * _LEAD_PAD_SECONDS), dtype=np.float32),
        np.asarray(samples, dtype=np.float32),
        np.zeros(int(RATE * _TAIL_PAD_SECONDS), dtype=np.float32),
    ])
    stream.accept_waveform(RATE, padded)
    recognizer.decode_stream(stream)
    text = str(stream.result.text).strip()
    if text.lower() in _NOISE_PHRASES and len(samples) < RATE * _SHORT_SECONDS:
        return ""
    return "" if text.lower() in {"", "."} else text


class _History:
    """The last few seconds of microphone audio, so a phrase can start earlier.

    Voice detection decides speech has begun a moment *after* it has: the first
    syllable of a quietly started word -- "can", "so", "please" -- is below its
    threshold until the vowel arrives. A phrase cut at the point of detection
    therefore lost its first word, which is what the first real test reported
    ("Can you send me" came back as "You send me"). Each phrase is taken from a
    little before the detector's start instead.
    """

    def __init__(self) -> None:
        self._chunks: list[Any] = []
        self._first = 0  # absolute index of the first sample held
        self._held = 0

    def add(self, chunk: Any) -> None:
        self._chunks.append(chunk)
        self._held += len(chunk)
        limit = int(RATE * (_MAX_PHRASE_SECONDS + 2 * _LEAD_IN_SECONDS))
        while self._held - len(self._chunks[0]) > limit:
            dropped = self._chunks.pop(0)
            self._held -= len(dropped)
            self._first += len(dropped)

    def with_lead_in(self, segment: Any) -> Any:
        """*segment*'s samples, preceded by up to :data:`_LEAD_IN_SECONDS` more."""
        import numpy as np

        samples = np.asarray(segment.samples, dtype=np.float32)
        start = int(getattr(segment, "start", -1))
        if start < 0 or not self._chunks:
            return samples
        begin = max(self._first, start - int(RATE * _LEAD_IN_SECONDS))
        if begin >= start:
            return samples
        held = np.concatenate(self._chunks)
        lead = held[begin - self._first : start - self._first]
        return np.concatenate([lead, samples])


# --------------------------------------------------------------------------- #
# The recogniser
# --------------------------------------------------------------------------- #


def record_and_hear(microphone: str, engine_id: str, seconds: float = 4.0) -> tuple[float, str]:
    """Dictation Settings' Test Microphone: record *seconds*, and report.

    Returns the loudest moment (0.0 to 1.0) and, for a built-in engine, what it
    heard -- empty for any other engine, or for silence. Blocking: run it on a
    worker. Raises :class:`DictationStartError` with a sentence when the
    microphone or the engine cannot be used.
    """
    try:
        import numpy as np
        import sounddevice as sd
    except Exception as error:  # noqa: BLE001 - any import failure is "not here"
        raise DictationStartError(
            "The microphone test needs the built-in speech engines, which are not "
            "included in this copy of QUILL."
        ) from error
    try:
        samples = sd.rec(
            int(RATE * seconds),
            samplerate=RATE,
            channels=1,
            dtype="float32",
            device=input_device_for(microphone),
        )
        sd.wait()
    except Exception as error:  # noqa: BLE001 - the microphone refused
        raise DictationStartError(
            "The microphone could not be opened. Check that it is connected, and "
            "that Windows Settings, Privacy and security, Microphone lets desktop "
            "apps use it."
        ) from error
    mono = np.asarray(samples, dtype=np.float32)[:, 0]
    peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    if engine_id not in {"moonshine", "whisper"} or peak < 0.02:
        return peak, ""
    return peak, transcribe(engine_id, mono)


class LocalDictationRecognizer:
    """One listening session on one microphone, with a built-in engine."""

    def __init__(
        self,
        listener: _Listener,
        engine_id: str,
        *,
        post: Poster,
        pause_seconds: float = _MIN_SILENCE_SECONDS,
    ) -> None:
        self._listener = listener
        self._engine = engine_id
        #: How long a silence ends a phrase (Dictation Settings, Pause before writing).
        self._pause = pause_seconds
        self._post = post
        self._running = threading.Event()
        self._audio: queue.Queue[Any] = queue.Queue()
        self._stream: Any = None
        self._worker: threading.Thread | None = None

    def start(self, microphone: str) -> None:
        try:
            _import_sherpa()
            import numpy  # noqa: F401
            import sounddevice as sd
        except Exception as error:  # noqa: BLE001 - any import failure is "not here"
            raise DictationStartError(
                "The built-in speech engines are not included in this copy of QUILL. "
                "Choose Windows speech recognition in Dictation Settings."
            ) from error
        _load(self._engine)  # before the microphone opens: fail cleanly, not mid-sentence
        vad = _vad(self._pause)
        device = input_device_for(microphone)
        try:
            self._stream = sd.InputStream(
                samplerate=RATE,
                channels=1,
                dtype="float32",
                blocksize=_BLOCK,
                device=device,
                callback=self._on_audio,
            )
            self._running.set()
            self._worker = threading.Thread(
                target=self._work, args=(vad,), name="dictation-recognizer", daemon=True
            )
            self._worker.start()
            self._stream.start()
        except Exception as error:  # noqa: BLE001 - the microphone refused
            self.stop()
            raise DictationStartError(
                "The microphone could not be opened. Check that it is connected, and "
                "that Windows Settings, Privacy and security, Microphone lets desktop "
                "apps use it."
            ) from error

    def stop(self) -> None:
        """Close the microphone and let the worker finish. Never raises."""
        self._running.clear()
        stream, self._stream = self._stream, None
        if stream is not None:
            for step in (stream.stop, stream.close):
                try:
                    step()
                except Exception:  # noqa: BLE001 - it is being released either way
                    pass
        worker, self._worker = self._worker, None
        if worker is not None and worker is not threading.current_thread():
            self._audio.put(None)
            worker.join(timeout=2.0)

    # -- threads ---------------------------------------------------------- #

    def _on_audio(self, data: Any, _frames: int, _time: Any, _status: Any) -> None:
        """PortAudio's thread: copy and hand over, nothing else."""
        if self._running.is_set():
            self._audio.put(data[:, 0].copy())

    def _work(self, vad: Any) -> None:
        was_speaking = False
        history = _History()
        try:
            while self._running.is_set():
                try:
                    chunk = self._audio.get(timeout=0.25)
                except queue.Empty:
                    continue
                if chunk is None:
                    break
                history.add(chunk)
                vad.accept_waveform(chunk)
                speaking = bool(vad.is_speech_detected())
                if speaking and not was_speaking:
                    self._post(self._listener.on_speech_started)
                was_speaking = speaking
                while not vad.empty():
                    segment = vad.front
                    samples = history.with_lead_in(segment)
                    vad.pop()
                    text = transcribe(self._engine, samples)
                    if text and self._running.is_set():
                        self._post(
                            self._listener.on_phrase,
                            RecognizedPhrase(words_from_text(text), text=text),
                        )
        except Exception:  # noqa: BLE001 - reported as a sentence, never a traceback
            if self._running.is_set():
                self._running.clear()
                self._post(
                    self._listener.on_failure,
                    "Dictation stopped: the speech engine could not go on. Start "
                    "dictation again, or choose another engine in Dictation Settings.",
                )
