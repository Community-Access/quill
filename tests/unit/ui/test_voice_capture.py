"""Tests for media hands-free capture glue (quill.ui.media.voice_capture)."""

from __future__ import annotations

from quill.ui.media.voice_capture import (
    VoiceCommandEvent,
    VoiceFeedback,
    dispatch_transcript,
    event_style,
    preferred_provider_ids,
    resolve_provider_and_model,
)


class FakePlayer:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self._playing = False

    def play(self) -> None:
        self._playing = True
        self.calls.append("play")

    def is_playing(self) -> bool:
        return self._playing

    def playhead_ms(self) -> int:
        return 0

    def length_ms(self) -> int:
        return 600_000

    def seek_to(self, ms: int) -> None:
        self.calls.append(f"seek:{ms}")


class FakeHost:
    def __init__(self) -> None:
        self._player = FakePlayer()
        self.hooks: list[str] = []

    def voice_next_chapter(self) -> None:
        self.hooks.append("next")


def test_empty_transcript_is_no_speech() -> None:
    fb = dispatch_transcript(FakeHost(), "   ")
    assert fb.event is VoiceCommandEvent.NO_SPEECH


def test_recognized_command_executes() -> None:
    host = FakeHost()
    fb = dispatch_transcript(host, "next chapter")
    assert fb.event is VoiceCommandEvent.RECOGNIZED_EXECUTED
    assert fb.message == "Next chapter"
    assert host.hooks == ["next"]


def test_recognized_play() -> None:
    host = FakeHost()
    fb = dispatch_transcript(host, "play")
    assert fb.event is VoiceCommandEvent.RECOGNIZED_EXECUTED
    assert host._player.calls == ["play"]


def test_unrecognized_echoes_what_was_heard() -> None:
    fb = dispatch_transcript(FakeHost(), "make me a sandwich")
    assert fb.event is VoiceCommandEvent.NOT_RECOGNIZED
    assert "make me a sandwich" in fb.message


def test_event_style_success_queues_and_failures_interrupt() -> None:
    force_ok, sound_ok = event_style(VoiceCommandEvent.RECOGNIZED_EXECUTED)
    assert force_ok is False and sound_ok  # queue politely, has an earcon
    force_err, _ = event_style(VoiceCommandEvent.NOT_RECOGNIZED)
    force_listen, _ = event_style(VoiceCommandEvent.LISTENING_START)
    assert force_err is True and force_listen is True


def test_every_event_has_a_style() -> None:
    for event in VoiceCommandEvent:
        force, sound = event_style(event)
        assert isinstance(force, bool)
        assert isinstance(sound, str) and sound


def test_feedback_is_frozen() -> None:
    fb = VoiceFeedback(VoiceCommandEvent.ERROR, "x")
    try:
        fb.message = "y"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("VoiceFeedback should be immutable")


# -- engine selection (Whisper + Nemotron + Vosk, honouring the saved choice) --


class FakeModel:
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id


class FakeProvider:
    def __init__(self, provider_id: str, models: list[str]) -> None:
        self.id = provider_id
        self._models = models

    def is_available(self) -> bool:
        return True

    def list_installed_models(self) -> list[FakeModel]:
        return [FakeModel(m) for m in self._models]


class FakeRegistry:
    def __init__(self, providers: list[FakeProvider]) -> None:
        self._providers = providers

    def available(self) -> list[FakeProvider]:
        return list(self._providers)


def test_preferred_provider_ids_puts_saved_first_and_dedupes() -> None:
    order = preferred_provider_ids("nemotron")
    assert order[0] == "nemotron"
    assert order.count("nemotron") == 1
    assert "whispercpp" in order and "vosk" in order


def test_preferred_provider_ids_default_order() -> None:
    assert preferred_provider_ids("")[0] == "whispercpp"


def test_resolve_defaults_to_whispercpp_small_model() -> None:
    registry = FakeRegistry([
        FakeProvider("whispercpp", ["small", "base"]),
        FakeProvider("nemotron", ["nemotron-en"]),
    ])
    provider, model = resolve_provider_and_model(registry, "")
    assert provider.id == "whispercpp"
    assert model == "base"  # small tier preferred for short commands


def test_resolve_honours_saved_nemotron() -> None:
    registry = FakeRegistry([
        FakeProvider("whispercpp", ["small"]),
        FakeProvider("nemotron", ["nemotron-en"]),
    ])
    provider, model = resolve_provider_and_model(registry, "nemotron")
    assert provider.id == "nemotron"
    assert model == "nemotron-en"


def test_resolve_skips_providers_without_installed_models() -> None:
    registry = FakeRegistry([
        FakeProvider("whispercpp", []),  # nothing installed
        FakeProvider("vosk", ["vosk-small-en"]),
    ])
    provider, model = resolve_provider_and_model(registry, "")
    assert provider.id == "vosk"
    assert model == "vosk-small-en"


def test_resolve_returns_none_when_no_models() -> None:
    registry = FakeRegistry([FakeProvider("whispercpp", [])])
    provider, model = resolve_provider_and_model(registry, "")
    assert provider is None and model == ""
