"""The model engines -- built in or downloaded -- on this computer, as you pause.

Microphone audio arrives on PortAudio's thread (``sounddevice``), goes through
Silero voice-activity detection to find where a phrase ends, and each finished
phrase is recognised by sherpa-onnx on a worker thread. Only the *result*
crosses to the UI thread, through the ``post`` function the caller supplies
(``wx.CallAfter`` in both editors) -- so the controller, and everything it
touches in the document, only ever runs on the UI thread.

**When a phrase ends.** After 0.8 seconds of quiet: shorter splits a sentence at
every breath, and a fragment recognised without the words around it is where
every engine is at its worst; longer makes a phrase land late. A phrase is also
cut at 20 seconds, so a long paragraph read without pausing still arrives.

**Models are loaded on the first start** and kept while dictation is in use,
keyed by engine *and* language (Spanish loads multilingual Whisper;
``engines.model_for``), then unloaded a few minutes after the last session
(``keep_up.IdleUnloader``). Nemotron runs live -- words while you speak --
through ``streaming.py``; the worker loop is ``recognizer_worker.py``. A
downloaded model is built by :mod:`~quill.core.windows_dictation.model_loader`;
if it is missing or will not load, the built-in engine takes over and
:attr:`LocalDictationRecognizer.fallback_notice` says so in one sentence.

Needs ``sherpa-onnx``, ``numpy`` and ``sounddevice``, imported lazily: a copy
without them raises :class:`DictationStartError` with a sentence.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable
from typing import Any, Protocol

from quill.core.windows_dictation.controller import DictationStartError
from quill.core.windows_dictation.engines import (
    DEFAULT_ENGINE,
    is_model_engine,
    language_model_problem,
    model_dir,
    model_for,
    package_dirs,
    vad_model_path,
)
from quill.core.windows_dictation.keep_up import IdleUnloader, KeepUpWatchdog
from quill.core.windows_dictation.model_catalog import downloadable
from quill.core.windows_dictation.parser import RecognizedPhrase
from quill.core.windows_dictation.recognizer_worker import WorkerMixin
from quill.core.windows_dictation.speech_language import coerce_speech_language

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
#: The Spanish ones are what multilingual Whisper makes of the same noises.
_NOISE_PHRASES = frozenset({"", ".", "you", "you.", "thank you.", "thanks for watching!", "bye."})
_NOISE_PHRASES |= {"gracias.", "¡gracias!", "gracias por ver el video.", "adiós."}
_SHORT_SECONDS = 0.8
_LEAD_PAD_SECONDS = 0.2
#: Audio taken from before the moment speech was detected -- see _History.
_LEAD_IN_SECONDS = 0.4
_TAIL_PAD_SECONDS = 0.5
#: The microphone watchdog (dict.md 2.3). Blocks are 512 samples at 16 kHz,
#: about 31 a second: three seconds of exact zeros, or two seconds of no blocks
#: at all, is a device that has gone, and the watcher tries it again every two.
_SILENCE_BLOCKS = int(3.0 * RATE / _BLOCK)
_POLL_SECONDS = 0.25
_STALL_SECONDS = 2.0
_RETRY_SECONDS = 2.0

_cache_lock = threading.Lock()
#: ``(engine, language) -> recogniser``.
_recognizers: dict[tuple[str, str], Any] = {}


def _unload_all() -> None:
    """Give the models' memory back (keep_up.IdleUnloader, dict.md section 1)."""
    with _cache_lock:
        _recognizers.clear()


_UNLOADER = IdleUnloader(lambda: _unload_all())

Poster = Callable[..., None]


class _Listener(Protocol):
    def on_speech_started(self) -> None: ...

    def on_phrase(self, phrase: RecognizedPhrase) -> None: ...

    def on_failure(self, message: str) -> None: ...

    # The microphone watchdog's two events. Optional: a listener without them
    # (an older host, a test double) simply never hears about the device.
    def on_microphone_lost(self) -> None: ...

    def on_microphone_back(self) -> None: ...


# --------------------------------------------------------------------------- #
# Microphones
# --------------------------------------------------------------------------- #


def _mme_inputs() -> list[tuple[int, str]]:
    """``(index, name)`` for each input on the MME host API, Windows' own list.

    MME only: sounddevice reports each microphone once per host API, and a list
    with every headset in it four times is a list nobody can choose from.
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


def _load(engine_id: str, language: str = "en") -> Any:
    """The sherpa-onnx recogniser for *engine_id* in *language*, loaded once per session."""
    language = coerce_speech_language(language)
    key = (engine_id, language)
    with _cache_lock:
        cached = _recognizers.get(key)
        if cached is not None:
            return cached
        model = model_for(engine_id, language)
        folder = model_dir(engine_id, language)
        if folder is None:
            raise DictationStartError(
                language_model_problem(engine_id, language)
                or f"{model.label.split(' (')[0]} is not included in this copy "
                "of QUILL. Choose another speech engine in Dictation Settings."
            )
        sherpa_onnx = _import_sherpa()
        if (downloaded := downloadable(model.id)) is not None:
            from quill.core.windows_dictation.model_loader import build

            recognizer = build(downloaded, folder, sherpa_onnx, language=language)
        elif model.id == "moonshine":
            recognizer = sherpa_onnx.OfflineRecognizer.from_moonshine(
                preprocessor=str(folder / "preprocess.onnx"),
                encoder=str(folder / "encode.int8.onnx"),
                uncached_decoder=str(folder / "uncached_decode.int8.onnx"),
                cached_decoder=str(folder / "cached_decode.int8.onnx"),
                tokens=str(folder / "tokens.txt"),
                num_threads=2,
                provider="cpu",
            )
        else:
            recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=str(folder / "encoder.int8.onnx"),
                decoder=str(folder / "decoder.int8.onnx"),
                tokens=str(folder / "tokens.txt"),
                language=language,
                num_threads=2,
                provider="cpu",
            )
        _recognizers[key] = recognizer
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


def transcribe(engine_id: str, samples: Any, language: str = "en") -> str:
    """One phrase of 16 kHz float samples as text, noise answers removed."""
    import numpy as np

    recognizer = _load(engine_id, language)
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

    Voice detection decides speech has begun a moment *after* it has, so a
    phrase cut there lost a quietly started first word ("Can you send me" came
    back as "You send me"). Each phrase starts a little before instead.
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


def record_and_hear(
    microphone: str, engine_id: str, seconds: float = 4.0, *, language: str = "en"
) -> tuple[float, str]:
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
    if not is_model_engine(engine_id) or peak < 0.02:
        return peak, ""
    return peak, transcribe(engine_id, mono, language)


class LocalDictationRecognizer(WorkerMixin):
    """One listening session on one microphone, with a model engine.

    From the 2026-09-28 reliability pass (dict.md 2.2, 2.3, 2.7):

    * :meth:`discard` throws away the phrase being heard -- queued audio, the
      detector's half-finished segment, and a transcription already under way
      (a generation counter, checked after the engine answers).
    * The **microphone watchdog**: no blocks, or digital silence (exact zeros,
      which a quiet room never produces), for a few seconds is a lost device;
      a watcher tries it every two seconds and reports it back.
    * The engine is **reloaded once** when a transcription raises, and the same
      phrase is tried again, so one bad decode costs nothing anyone hears.
    """

    def __init__(
        self,
        listener: _Listener,
        engine_id: str,
        *,
        post: Poster,
        pause_seconds: float = _MIN_SILENCE_SECONDS,
        language: str = "en",
    ) -> None:
        self._listener = listener
        self._engine = engine_id
        self._language = coerce_speech_language(language)
        #: How long a silence ends a phrase (Dictation Settings, Pause before writing).
        self._pause = pause_seconds
        self._post = post
        self._running = threading.Event()
        self._audio: queue.Queue[Any] = queue.Queue()
        self._stream: Any = None
        self._worker: threading.Thread | None = None
        self._microphone = ""
        self._generation = 0  # bumped by discard(); an older transcription is dropped
        self._discard_requested = threading.Event()
        self._silent_blocks = 0  # consecutive all-zero blocks from the device
        self._device_lost = threading.Event()
        self._watcher: threading.Thread | None = None
        #: Set by :meth:`start` when a downloaded model gave way to the built-in one.
        self.fallback_notice = ""
        self._live: Any = None  # a streaming engine's live half (streaming.py)
        self._finish_requested: Any = None
        self._watchdog: Any = None
        self._in_session = False

    def start(self, microphone: str) -> None:
        self._check_audio_stack()
        self._prepare_engine()
        self._listen(microphone)

    def _check_audio_stack(self) -> None:
        try:
            _import_sherpa()
            import numpy  # noqa: F401
            import sounddevice as sd  # noqa: F401
        except Exception as error:  # noqa: BLE001 - any import failure is "not here"
            raise DictationStartError(
                "The built-in speech engines are not included in this copy of QUILL. "
                "Choose Windows speech recognition in Dictation Settings."
            ) from error

    def _prepare_engine(self) -> None:
        try:  # before the microphone opens: fail cleanly
            _load(self._engine, self._language)
        except Exception:
            if downloadable(self._engine) is None:
                raise
            from quill.core.windows_dictation.model_loader import fallback_sentence

            self.fallback_notice = fallback_sentence(self._engine)
            self._engine = DEFAULT_ENGINE
            _load(self._engine, self._language)
        self._prepare_live()

    def _listen(self, microphone: str) -> None:
        """Open the microphone and start the worker."""
        vad = _vad(self._pause)
        self._microphone = microphone
        try:
            self._running.set()
            self._stream = self._open_stream()
            self._worker = threading.Thread(
                target=self._work, args=(vad,), name="dictation-recognizer", daemon=True
            )
            self._worker.start()
            self._stream.start()
            _UNLOADER.busy()
            self._in_session = True
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
        self._close_stream()
        worker, self._worker = self._worker, None
        if worker is not None and worker is not threading.current_thread():
            self._audio.put(None)
            worker.join(timeout=2.0)
        watcher, self._watcher = self._watcher, None
        if watcher is not None and watcher is not threading.current_thread():
            watcher.join(timeout=0.5)
        live, self._live = self._live, None
        if live is not None:
            live.close()
        if self._in_session:
            self._in_session = False
            _UNLOADER.idle()

    def _prepare_live(self) -> None:
        """Nemotron runs live (streaming.py); a downloaded model is watched for
        keeping up (keep_up.py). The built-in engines are neither."""
        model = downloadable(self._engine)
        if model is None:
            return
        self._watchdog = KeepUpWatchdog()
        online = getattr(_load(self._engine, self._language), "online", None)
        if model.kind == "nemotron" and online is not None:
            from quill.core.windows_dictation.streaming import NemotronLive

            self._live = NemotronLive(online, self._language)

    def discard(self) -> None:
        """Throw away the phrase being heard (Escape). Nothing already written moves."""
        self._generation += 1
        self._discard_requested.set()

    # -- the device --------------------------------------------------------- #

    def _open_stream(self) -> Any:
        import sounddevice as sd

        return sd.InputStream(
            samplerate=RATE,
            channels=1,
            dtype="float32",
            blocksize=_BLOCK,
            device=input_device_for(self._microphone),
            callback=self._on_audio,
        )

    def _close_stream(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            for step in (stream.stop, stream.close):
                try:
                    step()
                except Exception:  # noqa: BLE001 - it is being released either way
                    pass

    def _lose_microphone(self) -> None:
        """The worker's verdict: the device is gone. Say so once, then watch for it."""
        if self._device_lost.is_set() or not self._running.is_set():
            return
        self._device_lost.set()
        self._silent_blocks = 0
        self._close_stream()
        self._post(self._microphone_event, "on_microphone_lost")
        self._watcher = threading.Thread(
            target=self._watch_for_device, name="dictation-microphone-watch", daemon=True
        )
        self._watcher.start()

    def _watch_for_device(self) -> None:
        """Try the microphone every couple of seconds until a stream opens."""
        while self._running.is_set() and self._device_lost.is_set():
            time.sleep(_RETRY_SECONDS)
            if not self._running.is_set():
                return
            try:
                stream = self._open_stream()
                stream.start()
            except Exception:  # noqa: BLE001 - not back yet
                continue
            self._stream = stream
            self._silent_blocks = 0
            self._device_lost.clear()
            self._post(self._microphone_event, "on_microphone_back")
            return

    def _microphone_event(self, name: str) -> None:
        """Deliver a watchdog event to a listener that has it; the controller does."""
        handler = getattr(self._listener, name, None)
        if callable(handler):
            handler()

    # -- threads ------------------------------------------------------------ #

    def _on_audio(self, data: Any, _frames: int, _time: Any, _status: Any) -> None:
        """PortAudio's thread: copy and hand over, nothing else -- plus one
        comparison, for the silence floor."""
        if not self._running.is_set():
            return
        chunk = data[:, 0].copy()
        # Exact zeros only. A muted or unplugged input on some drivers keeps
        # delivering blocks of nothing; a quiet room never produces them.
        self._silent_blocks = self._silent_blocks + 1 if not chunk.any() else 0
        self._audio.put(chunk)


def _reset(vad: Any) -> None:
    """Forget the segment the voice detector is in the middle of, if it can."""
    reset = getattr(vad, "reset", None)
    if callable(reset):
        try:
            reset()
        except Exception:  # noqa: BLE001 - a detector that cannot reset just carries on
            pass
    while not vad.empty():
        vad.pop()
