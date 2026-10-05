"""Loading downloaded models, CPU only; streaming; falling back; the speed check."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation import model_loader, speed_check
from quill.core.windows_dictation.model_catalog import downloadable

np = pytest.importorskip("numpy")


class _Sherpa:
    """Records which factory was asked for what."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        outer = self

        class OfflineRecognizer:
            @staticmethod
            def from_whisper(**kw):
                outer.calls.append(("whisper", kw))
                return "whisper"

            @staticmethod
            def from_moonshine_v2(**kw):
                outer.calls.append(("moonshine_v2", kw))
                return "moonshine_v2"

            @staticmethod
            def from_transducer(**kw):
                outer.calls.append(("transducer", kw))
                return "transducer"

        class OnlineRecognizer:
            @staticmethod
            def from_transducer(**kw):
                outer.calls.append(("online", kw))
                return _Online("Hello there")

        self.OfflineRecognizer = OfflineRecognizer
        self.OnlineRecognizer = OnlineRecognizer


class _OnlineStream:
    def __init__(self) -> None:
        self.options: dict[str, str] = {}
        self.samples = 0
        self.finished = False

    def set_option(self, key: str, value: str) -> None:
        self.options[key] = value

    def accept_waveform(self, _rate: int, samples: Any) -> None:
        self.samples += len(samples)

    def input_finished(self) -> None:
        self.finished = True


class _Online:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pending = 0
        self.streams: list[_OnlineStream] = []

    def create_stream(self) -> _OnlineStream:
        stream = _OnlineStream()
        self.streams.append(stream)
        return stream

    def is_ready(self, stream: _OnlineStream) -> bool:
        return stream.samples > self.pending

    def decode_stream(self, stream: _OnlineStream) -> None:
        self.pending = stream.samples

    def get_result(self, stream: _OnlineStream) -> str:
        if stream.samples < 16_000:
            return ""
        return self.text if not stream.finished else self.text


@pytest.mark.parametrize(
    ("model_id", "factory"),
    [
        ("whisper_small", "whisper"),
        ("moonshine_base", "moonshine_v2"),
        ("parakeet", "transducer"),
        ("parakeet_unified", "transducer"),
        ("nemotron", "online"),
    ],
)
def test_each_kind_loads_through_its_factory_on_the_cpu(model_id, factory, tmp_path) -> None:
    sherpa = _Sherpa()
    model = downloadable(model_id)
    model_loader.build(model, tmp_path, sherpa, language="en", threads=2)
    name, kwargs = sherpa.calls[-1]
    assert name == factory
    assert kwargs["provider"] == "cpu", "never a graphics-card provider"
    assert kwargs["num_threads"] == 2
    for value in kwargs.values():
        if isinstance(value, str) and value.endswith((".onnx", ".ort", ".txt")):
            assert Path(value).parent == tmp_path
    if factory == "transducer":
        assert kwargs["model_type"] == "nemo_transducer"
    if factory == "online":
        assert kwargs["feature_dim"] == 128


def test_an_english_only_whisper_is_never_asked_for_spanish(tmp_path) -> None:
    sherpa = _Sherpa()
    model_loader.build(downloadable("whisper_small_en"), tmp_path, sherpa, language="es")
    assert sherpa.calls[-1][1]["language"] == "en"
    model_loader.build(downloadable("whisper_small"), tmp_path, sherpa, language="es")
    assert sherpa.calls[-1][1]["language"] == "es"


def test_nemotron_in_phrase_mode_pins_the_language_and_closes_the_sentence(tmp_path) -> None:
    engine = model_loader.build(downloadable("nemotron"), tmp_path, _Sherpa(), language="es")
    stream = engine.create_stream()
    stream.accept_waveform(16_000, np.zeros(20_000, np.float32))
    engine.decode_stream(stream)
    assert stream.stream.options == {"language": "es"}
    assert stream.stream.finished
    assert stream.result.text == "Hello there."


def test_close_sentence_leaves_marks_alone() -> None:
    assert model_loader.close_sentence("It is") == "It is."
    assert model_loader.close_sentence("Is it") == "Is it?"  # opens like a question
    assert model_loader.close_sentence("Is it?") == "Is it?"
    assert model_loader.close_sentence("Es así", "es") == "Es así."
    assert model_loader.close_sentence("  ") == ""


def test_a_streaming_session_shows_words_while_you_speak_then_the_final_ones() -> None:
    recognizer = _Online("Hello there")
    session = model_loader.StreamingSession(recognizer, "en")
    session.accept(np.zeros(8_000, np.float32))
    assert session.partial() == ""
    session.accept(np.zeros(9_000, np.float32))
    assert session.partial() == "Hello there"
    assert session.finish() == "Hello there"
    assert session.finish() == "Hello there"  # idempotent
    session.accept(np.zeros(100, np.float32))  # ignored once finished
    assert recognizer.streams[0].options == {"language": "en"}


def test_a_missing_download_falls_back_with_one_sentence(monkeypatch) -> None:
    pytest.importorskip("sounddevice")
    from quill.core.windows_dictation import local_recognizer

    loaded: list[str] = []

    def load(engine: str, _language: str = "en") -> object:
        if engine == "nemotron":
            raise local_recognizer.DictationStartError("missing")
        loaded.append(engine)
        return object()

    class _Stream:
        def start(self) -> None: ...
        def stop(self) -> None: ...
        def close(self) -> None: ...

    monkeypatch.setattr(local_recognizer, "_import_sherpa", lambda: object())
    monkeypatch.setattr(local_recognizer, "_load", load)
    monkeypatch.setattr(local_recognizer, "_vad", lambda _pause: object())
    monkeypatch.setattr(
        local_recognizer.LocalDictationRecognizer, "_open_stream", lambda s: _Stream()
    )
    monkeypatch.setattr(local_recognizer.LocalDictationRecognizer, "_work", lambda s, v: None)
    recognizer = local_recognizer.LocalDictationRecognizer(
        object(), "nemotron", post=lambda *a: None
    )
    recognizer.start("")
    recognizer.stop()
    assert loaded == ["moonshine"]
    assert "NVIDIA Nemotron" in recognizer.fallback_notice
    assert "built-in engine" in recognizer.fallback_notice
    notice = recognizer.fallback_notice
    assert notice.endswith(".") and ". " not in notice, "one sentence"


def test_a_built_in_engine_that_fails_is_never_swapped_silently(monkeypatch) -> None:
    pytest.importorskip("sounddevice")
    from quill.core.windows_dictation import local_recognizer

    def load(_engine: str, _language: str = "en") -> object:
        raise local_recognizer.DictationStartError("Whisper is not included")

    monkeypatch.setattr(local_recognizer, "_import_sherpa", lambda: object())
    monkeypatch.setattr(local_recognizer, "_load", load)
    recognizer = local_recognizer.LocalDictationRecognizer(
        object(), "whisper", post=lambda *a: None
    )
    with pytest.raises(local_recognizer.DictationStartError):
        recognizer.start("")


def test_the_controller_says_the_fallback_once_and_still_starts() -> None:
    from quill.core.windows_dictation.controller import DictationController, DictationState
    from quill.core.windows_dictation.preferences import DictationPreferences
    from tests.unit.core.test_windows_dictation import FakeDocument, FakeFeedback, FakeRecognizer

    recognizer = FakeRecognizer("")
    recognizer.fallback_notice = (
        "Nemotron is not on this computer, so dictation is using the built-in engine."
    )
    feedback = FakeFeedback()
    controller = DictationController(
        recognizer=lambda _c, _p: recognizer,
        document=FakeDocument(),
        feedback=feedback,
        preferences=lambda: DictationPreferences(engine="nemotron"),
    )
    controller.start()
    assert controller.state is DictationState.LISTENING
    assert feedback.said[0] == recognizer.fallback_notice
    assert feedback.said.count(recognizer.fallback_notice) == 1


def test_the_rolling_context_is_the_last_words_dictated() -> None:
    from quill.core.windows_dictation.history import DictatedPhrase, PhraseHistory

    history = PhraseHistory()
    history.push(DictatedPhrase("Hello there.", 0, 12))
    history.push(DictatedPhrase(" How are you?", 12, 25))
    assert history.recent_text() == "Hello there. How are you?"
    assert history.recent_text(8) == "are you?"


def test_the_speed_check_warns_plainly_about_a_heavy_model() -> None:
    nemotron = downloadable("nemotron")
    moonshine_base = downloadable("moonshine_base")
    slow = speed_check.SpeedCheck(tiny=0.2, cores=2, memory_gb=4.0)
    fast = speed_check.SpeedCheck(tiny=0.01, cores=12, memory_gb=32.0)
    assert speed_check.LAG_SENTENCE in speed_check.verdict(nemotron, slow)
    assert "keep up comfortably" in speed_check.verdict(moonshine_base, fast)
    middling = speed_check.SpeedCheck(tiny=0.05, cores=4, memory_gb=8.0)
    assert "screen reader" in speed_check.verdict(nemotron, middling)
    assert speed_check.verdict(nemotron, None) == ""


def test_the_speed_check_falls_back_to_the_hardware_when_it_cannot_time(monkeypatch) -> None:
    def broken() -> float:
        raise RuntimeError("no engine")

    check = speed_check.run(broken)
    assert check.tiny is None and check.cores >= 1
    weak = speed_check.SpeedCheck(tiny=None, cores=2, memory_gb=4.0)
    assert speed_check.LAG_SENTENCE in speed_check.verdict(downloadable("whisper_large_v3"), weak)
    assert speed_check.run(lambda: 0.05).tiny == 0.05
