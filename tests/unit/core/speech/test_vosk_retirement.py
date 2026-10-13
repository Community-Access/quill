"""Vosk leaves dictation and the voice features; Moonshine tiny takes over (2026-10-13).

Vosk stays as the bundled podcast chapter engine (``service.CHAPTER_PROVIDER_ID``);
everything here is about the roles it left: the saved-setting migrations, the
one-time notice, the dictation pickers, and the Moonshine tiny adapter that the
voice paths (Voice Command, Conversation Mode, Hey QUILL) now reach.
"""

from __future__ import annotations

import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.settings import Settings
from quill.core.speech import service
from quill.core.speech.provider import SpeechError, TranscriptionRequest
from quill.core.speech.providers import moonshine_tiny as mt

# --------------------------------------------------------------------------- #
# Saved-setting migrations
# --------------------------------------------------------------------------- #


def test_voice_engine_vosk_becomes_moonshine_tiny_with_the_voice_notice() -> None:
    loaded = Settings.from_dict({"voice_recognition_engine": "vosk"})
    assert loaded.voice_recognition_engine == "moonshine_tiny"
    assert loaded.vosk_retirement_notice == "voice"


def test_dictation_engine_vosk_becomes_the_default_with_the_dictation_notice() -> None:
    loaded = Settings.from_dict({"speech_provider": "vosk"})
    assert loaded.speech_provider == ""
    assert loaded.vosk_retirement_notice == "dictation"


def test_both_vosk_choices_say_the_voice_notice() -> None:
    loaded = Settings.from_dict({"speech_provider": "vosk", "voice_recognition_engine": "vosk"})
    assert loaded.speech_provider == ""
    assert loaded.voice_recognition_engine == "moonshine_tiny"
    assert loaded.vosk_retirement_notice == "voice"


def test_no_vosk_choice_leaves_no_notice() -> None:
    loaded = Settings.from_dict({"speech_provider": "whispercpp"})
    assert loaded.vosk_retirement_notice == ""
    assert Settings().vosk_retirement_notice == ""


def test_a_notice_already_said_is_never_rearmed() -> None:
    loaded = Settings.from_dict({
        "voice_recognition_engine": "vosk",
        "vosk_retirement_notice": "done",
    })
    assert loaded.voice_recognition_engine == "moonshine_tiny"
    assert loaded.vosk_retirement_notice == "done"


def test_an_unknown_notice_value_is_dropped() -> None:
    assert Settings.from_dict({"vosk_retirement_notice": "bogus"}).vosk_retirement_notice == ""


def test_legacy_dictation_engine_vosk_still_migrates_to_offline() -> None:
    assert Settings.from_dict({"dictation_engine": "vosk"}).dictation_engine == "offline"


def test_migrated_settings_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.settings import load_settings, save_settings

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    (tmp_path / "settings.json").write_text(
        '{"voice_recognition_engine": "vosk"}', encoding="utf-8"
    )
    loaded = load_settings()
    loaded.vosk_retirement_notice = "done"
    save_settings(loaded)
    again = load_settings()
    assert again.voice_recognition_engine == "moonshine_tiny"
    assert again.vosk_retirement_notice == "done"


# --------------------------------------------------------------------------- #
# The one-time notice
# --------------------------------------------------------------------------- #


class _Host:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.spoken: list[str] = []
        self.status: list[str] = []

    def _announce(self, message: str, **_kwargs: Any) -> None:
        self.spoken.append(message)

    def _set_status_quiet(self, message: str) -> None:
        self.status.append(message)


@pytest.fixture
def _no_save(monkeypatch: pytest.MonkeyPatch) -> list[Settings]:
    saved: list[Settings] = []
    monkeypatch.setattr("quill.core.settings.save_settings", saved.append)
    return saved


def test_voice_notice_is_said_once_and_remembered(_no_save: list[Settings]) -> None:
    from quill.ui.vosk_retirement_notice import VOICE_NOTICE, surface_vosk_retirement_notice

    host = _Host(Settings.from_dict({"voice_recognition_engine": "vosk"}))
    assert surface_vosk_retirement_notice(host) is True
    assert host.spoken == [VOICE_NOTICE]
    assert host.status == [VOICE_NOTICE]
    assert host.settings.vosk_retirement_notice == "done"
    assert _no_save and _no_save[-1].vosk_retirement_notice == "done"
    # The next start (and the one after) says nothing.
    assert surface_vosk_retirement_notice(host) is False
    assert host.spoken == [VOICE_NOTICE]


def test_dictation_notice_wording(_no_save: list[Settings]) -> None:
    from quill.ui.vosk_retirement_notice import DICTATION_NOTICE, surface_vosk_retirement_notice

    host = _Host(Settings.from_dict({"speech_provider": "vosk"}))
    assert surface_vosk_retirement_notice(host) is True
    assert host.spoken == [
        "Vosk is no longer a dictation engine. Dictation now uses your default engine."
    ]
    assert host.spoken == [DICTATION_NOTICE]


def test_voice_notice_wording() -> None:
    from quill.ui.vosk_retirement_notice import VOICE_NOTICE

    assert VOICE_NOTICE == (
        "Vosk is no longer used for voice commands or dictation. Voice commands and "
        "Hey QUILL now use Moonshine tiny, which is already installed. Podcast "
        "chapters still use Vosk."
    )
    assert VOICE_NOTICE.isascii()


def test_nothing_is_said_without_a_migration(_no_save: list[Settings]) -> None:
    from quill.ui.vosk_retirement_notice import surface_vosk_retirement_notice

    host = _Host(Settings())
    assert surface_vosk_retirement_notice(host) is False
    assert host.spoken == [] and host.status == [] and _no_save == []


def test_the_notice_runs_with_the_startup_live_settings(
    monkeypatch: pytest.MonkeyPatch, _no_save: list[Settings]
) -> None:
    from quill.ui import settings_live_switches, wakeword_switch

    monkeypatch.setattr(settings_live_switches, "remember_shell_verbs", lambda host: None)
    monkeypatch.setattr(wakeword_switch, "start_wakeword_if_enabled", lambda host: None)
    host = _Host(Settings.from_dict({"voice_recognition_engine": "vosk"}))
    settings_live_switches.at_startup(host)
    settings_live_switches.at_startup(host)
    assert len(host.spoken) == 1


# --------------------------------------------------------------------------- #
# Dictation pickers no longer offer Vosk; chapters still reach it
# --------------------------------------------------------------------------- #


class _Fake:
    def __init__(self, pid: str, installed: bool = True) -> None:
        self.id = pid
        self.display_name = pid
        self._installed = installed

    def is_available(self) -> bool:
        return True

    def list_installed_models(self) -> list[object]:
        return [SimpleNamespace(id="m")] if self._installed else []


def _registry(*ids: str) -> Any:
    from quill.core.speech.registry import SpeechProviderRegistry

    registry = SpeechProviderRegistry()
    for pid in ids:
        registry.register(_Fake(pid))  # type: ignore[arg-type]
    return registry


def test_dictation_providers_drop_vosk() -> None:
    providers = [_Fake("whispercpp"), _Fake("vosk"), _Fake("parakeet")]
    assert [p.id for p in service.dictation_providers(providers)] == ["whispercpp", "parakeet"]


def test_the_dictation_ladder_ignores_a_vosk_choice() -> None:
    registry = _registry("whispercpp", "vosk")
    assert service.preferred_dictation_provider_id(registry, "vosk") == service.DEFAULT_PROVIDER_ID


def test_chapters_still_prefer_vosk() -> None:
    registry = _registry("whispercpp", "vosk")
    assert service.preferred_chapter_provider_id(registry) == "vosk"
    assert service.CHAPTER_PROVIDER_ID == "vosk"


def test_the_guided_picker_and_engine_radio_offer_no_vosk() -> None:
    from quill.core.speech import guided_setup
    from quill.ui.speech_setup_dialog import build_engine_descriptors

    ids = [o.engine_id for o in guided_setup.offline_speech_engine_options()]
    assert "vosk" not in ids
    rows = build_engine_descriptors(
        [_Fake("whispercpp"), _Fake("vosk")], whispercpp_ok=True, faster_whisper_ok=False
    )
    assert not any("Vosk" in row["label"] for row in rows)
    assert all(row["provider"] is None or row["provider"].id != "vosk" for row in rows)


def test_voice_capture_never_falls_back_to_vosk() -> None:
    from quill.ui.media.voice_capture import preferred_provider_ids, resolve_provider_and_model

    assert "vosk" not in preferred_provider_ids("vosk")
    provider, _model = resolve_provider_and_model(_RegistryWithOnly("vosk"))
    assert provider is None


class _RegistryWithOnly:
    def __init__(self, pid: str) -> None:
        self._providers = [_Fake(pid)]

    def available(self) -> list[_Fake]:
        return self._providers


def test_voice_engine_setting_offers_moonshine_tiny_not_vosk() -> None:
    from quill.core.settings_specs import SETTING_SPECS

    spec = next(s for s in SETTING_SPECS if s.key == "voice_recognition_engine")
    assert spec.choices == (
        ("", "Follow main engine"),
        ("whispercpp", "whisper.cpp (accurate)"),
        ("moonshine_tiny", "Moonshine tiny (fast, light)"),
    )
    assert "vosk" not in " ".join(spec.keywords).lower()


# --------------------------------------------------------------------------- #
# The Moonshine tiny adapter
# --------------------------------------------------------------------------- #


def _wav(path: Path, seconds: float, rate: int = 16_000) -> Path:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x00" * int(rate * seconds))
    return path


class _FakeRecognizer:
    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.lengths: list[int] = []

    def __call__(self, samples: Any) -> str:
        self.lengths.append(len(samples))
        return self.answers.pop(0) if self.answers else ""


def _adapter(tmp_path: Path, recognizer: _FakeRecognizer | None = None) -> mt.MoonshineTinyProvider:
    return mt.MoonshineTinyProvider(
        transcriber=recognizer or _FakeRecognizer("hey quill"),
        folder=lambda: tmp_path,
        sherpa_present=lambda: True,
    )


def test_adapter_lists_the_bundled_model(tmp_path: Path) -> None:
    provider = _adapter(tmp_path)
    assert provider.id == "moonshine_tiny"
    assert provider.is_available() is True
    (model,) = provider.list_installed_models()
    assert model.id == mt.MODEL_ID and model.path == tmp_path
    assert model.provider_id == "moonshine_tiny"
    assert provider.list_supported_models() == []  # nothing to download


def test_adapter_is_unavailable_without_the_bundled_model() -> None:
    provider = mt.MoonshineTinyProvider(
        transcriber=_FakeRecognizer(), folder=lambda: None, sherpa_present=lambda: True
    )
    assert provider.is_available() is False
    assert provider.list_installed_models() == []
    assert provider.get_install_status().installed is False


def test_adapter_is_unavailable_without_sherpa(tmp_path: Path) -> None:
    provider = mt.MoonshineTinyProvider(
        transcriber=_FakeRecognizer(), folder=lambda: tmp_path, sherpa_present=lambda: False
    )
    assert provider.is_available() is False
    assert provider.list_installed_models() == []


def test_adapter_never_downloads_or_removes(tmp_path: Path) -> None:
    provider = _adapter(tmp_path)
    with pytest.raises(SpeechError):
        provider.download_model(mt.MODEL_ID)
    with pytest.raises(SpeechError):
        provider.remove_model(mt.MODEL_ID)


def test_adapter_transcribes_a_recording(tmp_path: Path) -> None:
    recognizer = _FakeRecognizer("Open the file.")
    provider = _adapter(tmp_path, recognizer)
    wav = _wav(tmp_path / "command.wav", 1.5)
    result = provider.transcribe_file(TranscriptionRequest(source_path=wav, model_id=mt.MODEL_ID))
    assert result.full_text == "Open the file."
    assert result.provider_id == "moonshine_tiny"
    assert result.language == "en"
    assert recognizer.lengths == [24_000]


def test_adapter_decodes_a_long_recording_in_twenty_second_pieces(tmp_path: Path) -> None:
    recognizer = _FakeRecognizer("one", "two")
    provider = _adapter(tmp_path, recognizer)
    wav = _wav(tmp_path / "long.wav", 25)
    result = provider.transcribe_file(TranscriptionRequest(source_path=wav, model_id=mt.MODEL_ID))
    assert result.full_text == "one two"
    assert recognizer.lengths == [320_000, 80_000]


def test_adapter_refuses_audio_it_cannot_read(tmp_path: Path) -> None:
    provider = _adapter(tmp_path)
    wav = _wav(tmp_path / "fast.wav", 1, rate=44_100)
    with pytest.raises(SpeechError, match="16 kHz"):
        provider.transcribe_file(TranscriptionRequest(source_path=wav, model_id=mt.MODEL_ID))


def test_adapter_wraps_a_recognizer_failure(tmp_path: Path) -> None:
    def broken(_samples: Any) -> str:
        raise RuntimeError("no engine")

    provider = mt.MoonshineTinyProvider(
        transcriber=broken, folder=lambda: tmp_path, sherpa_present=lambda: True
    )
    wav = _wav(tmp_path / "x.wav", 1)
    with pytest.raises(SpeechError, match="Moonshine tiny"):
        provider.transcribe_file(TranscriptionRequest(source_path=wav, model_id=mt.MODEL_ID))


# --------------------------------------------------------------------------- #
# The voice paths reach the adapter
# --------------------------------------------------------------------------- #


def _voice_host(engine: str, main: object) -> Any:
    from quill.ui.main_frame_speech import SpeechCommandsMixin
    from quill.ui.main_frame_speech_models import SpeechModelsMixin

    class Host(SpeechCommandsMixin, SpeechModelsMixin):
        def __init__(self) -> None:
            self.settings = Settings.from_dict({"voice_recognition_engine": engine})

        def _speech_registry(self) -> object:
            return _registry("whispercpp")

        def _speech_provider(self) -> object:
            return main

    return Host()


def test_voice_provider_resolves_moonshine_tiny(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(mt, "_bundled_folder", lambda: tmp_path)
    monkeypatch.setattr(mt, "_sherpa_present", lambda: True)
    host = _voice_host("moonshine_tiny", main=object())
    assert isinstance(host._voice_provider(), mt.MoonshineTinyProvider)
    # A saved Vosk choice lands on the same adapter.
    assert isinstance(
        _voice_host("vosk", main=object())._voice_provider(), mt.MoonshineTinyProvider
    )


def test_voice_provider_falls_back_to_the_main_engine_without_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mt, "_bundled_folder", lambda: None)
    main = object()
    assert _voice_host("moonshine_tiny", main=main)._voice_provider() is main


def test_command_and_wake_paths_transcribe_through_the_adapter(tmp_path: Path) -> None:
    """``_transcribe_recording`` is what Voice Command, Conversation Mode and the
    Hey QUILL wake window all call with ``_voice_provider()``'s answer."""
    host = _voice_host("moonshine_tiny", main=object())
    recognizer = _FakeRecognizer("open settings", "hey quill")
    provider = _adapter(tmp_path / "model", recognizer)

    def progress(*_args: object) -> None:
        return None

    command = host._transcribe_recording(provider, _wav(tmp_path / "c.wav", 1), progress)
    assert command.full_text == "open settings"
    # The wake window passes a finish function that keeps only the text.
    wake = host._transcribe_recording(
        provider,
        _wav(tmp_path / "w.wav", 2),
        progress,
        lambda result: (getattr(result, "full_text", "") or "").strip(),
    )
    assert wake == "hey quill"
    # Both recordings are discarded once heard.
    assert not (tmp_path / "c.wav").exists() and not (tmp_path / "w.wav").exists()
