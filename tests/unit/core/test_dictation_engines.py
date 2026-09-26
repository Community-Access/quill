"""Dictation's engine choice, model lookup, and the built-in engines' plumbing.

Nothing here loads a model or opens a microphone: sherpa-onnx, the voice
detector and sounddevice are replaced, and what is tested is everything around
them -- where models are looked for, which microphone is chosen by name, what
counts as noise, and that a phrase reaches the listener on the poster.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation import engines, local_recognizer
from quill.core.windows_dictation.controller import DictationPreferences, DictationStartError

# The built-in engines hand audio to sherpa-onnx as numpy arrays. numpy ships
# in the live-dictation extra, not in [dev], so CI's unit job has none.
needs_numpy = pytest.mark.skipif(
    importlib.util.find_spec("numpy") is None, reason="numpy (live-dictation extra) not installed"
)


def _fill(folder: Path, engine_id: str) -> None:
    info = engines.engine_info(engine_id)
    (folder / info.folder).mkdir(parents=True)
    for item in info.files:
        (folder / info.folder / item.name).write_bytes(b"x")


# -- engines ----------------------------------------------------------------- #


def test_the_default_engine_is_moonshine_and_unknown_names_fall_back_to_it() -> None:
    assert engines.DEFAULT_ENGINE == "moonshine"
    assert engines.coerce_engine("WHISPER") == "whisper"
    assert engines.coerce_engine("windows") == "windows"
    assert engines.coerce_engine("dragon") == "moonshine"
    assert engines.coerce_engine(None) == "moonshine"


def test_preferences_carry_the_engine() -> None:
    class Settings:
        windows_dictation_engine = "whisper"

    assert DictationPreferences.from_settings(Settings()).engine == "whisper"
    assert DictationPreferences.from_settings(object()).engine == "moonshine"


def test_every_model_file_is_pinned_to_a_digest() -> None:
    for engine in engines.ENGINES:
        for item in engine.files:
            assert len(item.sha256) == 64, (engine.id, item.name)
    assert len(engines.VAD_MODEL.sha256) == 64


def test_models_are_found_beside_the_launcher_before_the_checkout(tmp_path, monkeypatch) -> None:
    launcher = tmp_path / "installed"
    _fill(launcher / engines.MODELS_FOLDER, "moonshine")
    monkeypatch.delenv("QUILL_DICTATION_MODELS", raising=False)
    monkeypatch.setenv("QUILL_LAUNCHER_DIR", str(launcher))
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "runtime"))
    found = engines.model_dir("moonshine")
    assert found == launcher / engines.MODELS_FOLDER / "moonshine-tiny-en"


def test_a_portable_copy_finds_them_under_its_own_folder(tmp_path, monkeypatch) -> None:
    portable = tmp_path / "QuillLite"
    _fill(portable / engines.MODELS_FOLDER, "whisper")
    monkeypatch.delenv("QUILL_DICTATION_MODELS", raising=False)
    monkeypatch.delenv("QUILL_LAUNCHER_DIR", raising=False)
    monkeypatch.setenv("QUILL_APP_ROOT", str(portable))
    assert engines.model_dir("whisper") == portable / engines.MODELS_FOLDER / "whisper-tiny-en"


def test_an_incomplete_model_folder_is_not_a_model(tmp_path, monkeypatch) -> None:
    root = tmp_path / "models"
    _fill(root, "moonshine")
    (root / "moonshine-tiny-en" / "tokens.txt").unlink()
    monkeypatch.setattr(engines, "model_roots", lambda: [root])
    assert engines.model_dir("moonshine") is None
    assert engines.model_dir("windows") is None  # needs no model at all


# -- microphones --------------------------------------------------------------- #


@pytest.fixture
def microphones(monkeypatch):
    devices = [(3, "Microphone (Logi USB Headset)"), (5, "Microphone Array (Realtek High ")]
    monkeypatch.setattr(local_recognizer, "_mme_inputs", lambda: devices)
    return devices


def test_a_microphone_is_found_by_name(microphones) -> None:
    assert local_recognizer.input_device_for("Microphone (Logi USB Headset)") == 3


def test_a_name_cut_short_by_windows_still_matches(microphones) -> None:
    """MME stops at 31 characters; the name Windows speech saved does not."""
    full = "Microphone Array (Realtek High Definition Audio)"
    assert local_recognizer.input_device_for(full) == 5


def test_the_default_and_an_old_speech_token_both_mean_the_default(microphones) -> None:
    assert local_recognizer.input_device_for("") is None
    assert local_recognizer.input_device_for("HKEY_LOCAL_MACHINE\\SOFTWARE\\x") is None


def test_an_unplugged_microphone_is_refused_not_replaced(microphones) -> None:
    with pytest.raises(DictationStartError) as caught:
        local_recognizer.input_device_for("Blue Yeti")
    assert "Blue Yeti" in str(caught.value)


# -- the built-in engines' plumbing --------------------------------------------- #


class _Result:
    def __init__(self, text: str) -> None:
        self.text = text


class _Stream:
    def __init__(self, text: str) -> None:
        self.result = _Result(text)
        self.samples = 0

    def accept_waveform(self, _rate: int, samples: Any) -> None:
        self.samples = len(samples)


class _Recognizer:
    def __init__(self, text: str) -> None:
        self.text = text
        self.streams: list[_Stream] = []

    def create_stream(self) -> _Stream:
        stream = _Stream(self.text)
        self.streams.append(stream)
        return stream

    def decode_stream(self, _stream: _Stream) -> None:
        pass


@pytest.fixture
def recognizer(monkeypatch):
    fake = _Recognizer("Hello there.")
    monkeypatch.setattr(local_recognizer, "_load", lambda _engine: fake)
    return fake


@needs_numpy
def test_a_phrase_is_padded_so_its_last_word_survives(recognizer) -> None:
    samples = [0.0] * 16_000
    assert local_recognizer.transcribe("moonshine", samples) == "Hello there."
    assert recognizer.streams[0].samples > len(samples)


@needs_numpy
def test_whispers_noise_answers_are_dropped_only_when_short(recognizer) -> None:
    recognizer.text = "Thank you."
    assert local_recognizer.transcribe("whisper", [0.0] * 4_000) == ""
    assert local_recognizer.transcribe("whisper", [0.0] * 40_000) == "Thank you."


class _Segment:
    def __init__(self, samples: list[float]) -> None:
        self.samples = samples


class _Vad:
    """Speech in the first chunk, a finished phrase after the second."""

    def __init__(self) -> None:
        self.chunks = 0
        self.queue: list[_Segment] = []

    def accept_waveform(self, _chunk: Any) -> None:
        self.chunks += 1
        if self.chunks == 2:
            self.queue.append(_Segment([0.0] * 16_000))

    def is_speech_detected(self) -> bool:
        return self.chunks == 1

    def empty(self) -> bool:
        return not self.queue

    @property
    def front(self) -> _Segment:
        return self.queue[0]

    def pop(self) -> None:
        self.queue.pop(0)


@needs_numpy
def test_a_finished_phrase_reaches_the_listener_through_the_poster(recognizer) -> None:
    heard: list[Any] = []
    posted: list[str] = []

    class Listener:
        def on_speech_started(self) -> None:
            heard.append("speech")

        def on_phrase(self, phrase: Any) -> None:
            heard.append(phrase.text)

        def on_failure(self, message: str) -> None:
            heard.append("failed: " + message)

    def post(function: Any, *args: Any) -> None:
        posted.append(function.__name__)
        function(*args)

    engine = local_recognizer.LocalDictationRecognizer(Listener(), "moonshine", post=post)
    engine._running.set()
    engine._audio.put([0.0] * 512)
    engine._audio.put([0.0] * 512)
    engine._audio.put(None)
    engine._work(_Vad())
    assert heard == ["speech", "Hello there."]
    assert posted == ["on_speech_started", "on_phrase"]


def test_an_engine_failure_is_a_sentence_on_the_poster(monkeypatch) -> None:
    def broken(_engine: str) -> Any:
        raise RuntimeError("onnx exploded")

    monkeypatch.setattr(local_recognizer, "_load", broken)
    failures: list[str] = []

    class Listener:
        def on_speech_started(self) -> None: ...

        def on_phrase(self, _phrase: Any) -> None: ...

        def on_failure(self, message: str) -> None:
            failures.append(message)

    engine = local_recognizer.LocalDictationRecognizer(
        Listener(), "moonshine", post=lambda f, *a: f(*a)
    )
    engine._running.set()
    engine._audio.put([0.0] * 512)
    engine._audio.put([0.0] * 512)
    engine._work(_Vad())
    assert failures and "could not go on" in failures[0]
    assert "onnx" not in failures[0]


def test_a_missing_model_says_which_and_what_to_do(monkeypatch) -> None:
    local_recognizer._recognizers.pop("whisper", None)
    monkeypatch.setattr(local_recognizer, "model_dir", lambda _engine: None)
    with pytest.raises(DictationStartError) as caught:
        local_recognizer._load("whisper")
    assert "Whisper" in str(caught.value) and "Dictation Settings" in str(caught.value)


def test_stopping_twice_never_raises() -> None:
    engine = local_recognizer.LocalDictationRecognizer(
        object(),  # type: ignore[arg-type]
        "moonshine",
        post=lambda f, *a: f(*a),
    )
    engine.stop()
    engine.stop()


@needs_numpy
def test_a_phrase_starts_a_little_before_the_detector_said_so() -> None:
    """Reported 2026-09-25: the first word of a phrase was missing. Detection
    lags a quietly started word, so each phrase takes 0.4 s from before it."""
    import numpy as np

    history = local_recognizer._History()
    audio = np.arange(32_000, dtype=np.float32)
    for index in range(0, len(audio), 512):
        history.add(audio[index : index + 512])

    class Detected:
        start = 16_000
        samples = audio[16_000:24_000]

    phrase = history.with_lead_in(Detected())
    lead = int(local_recognizer.RATE * local_recognizer._LEAD_IN_SECONDS)
    assert len(phrase) == 8_000 + lead
    assert phrase[0] == 16_000 - lead
    assert phrase[lead] == 16_000


@needs_numpy
def test_the_lead_in_never_reaches_before_the_microphone_opened() -> None:
    import numpy as np

    history = local_recognizer._History()
    history.add(np.zeros(1_000, dtype=np.float32))

    class Early:
        start = 100
        samples = np.ones(500, dtype=np.float32)

    assert len(history.with_lead_in(Early())) == 600
