"""#617 Speech S2 UI: the SpeechCommandsMixin resolves the offline provider."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from types import SimpleNamespace

from quill.ui.main_frame_speech import SpeechCommandsMixin
from quill.ui.main_frame_speech_models import SpeechModelsMixin


class _Host(SpeechCommandsMixin, SpeechModelsMixin):
    def __init__(self) -> None:
        self.settings = SimpleNamespace(speech_whisper_path="")


def test_speech_provider_is_whispercpp() -> None:
    provider = _Host()._speech_provider()
    assert provider is not None
    assert provider.id == "whispercpp"
    # The provider exposes the model catalog without needing the binary installed.
    assert any(m.id == "small" for m in provider.list_supported_models())


class _Model:
    def __init__(self, model_id: str) -> None:
        self.id = model_id


def test_default_model_id_prefers_the_saved_default_when_installed() -> None:
    host = _Host()
    host.settings.speech_default_model_id = "small"
    installed = [_Model("tiny"), _Model("small"), _Model("base")]
    assert host._default_model_id(installed) == "small"


def test_default_model_id_falls_back_when_the_saved_default_is_not_installed() -> None:
    from quill.core.speech.catalog import RECOMMENDED_MODEL_ID

    host = _Host()
    host.settings.speech_default_model_id = "not-installed-model"
    installed = [_Model("tiny"), _Model(RECOMMENDED_MODEL_ID)]
    assert host._default_model_id(installed) == RECOMMENDED_MODEL_ID


def test_default_model_id_falls_back_when_nothing_is_saved() -> None:
    from quill.core.speech.catalog import RECOMMENDED_MODEL_ID

    host = _Host()
    host.settings.speech_default_model_id = ""
    installed = [_Model("tiny"), _Model(RECOMMENDED_MODEL_ID)]
    assert host._default_model_id(installed) == RECOMMENDED_MODEL_ID


def _run_in_worker(host: _Host, work, on_success) -> None:
    def run() -> None:
        result = work(lambda *_args: None)
        on_success(result)

    threading.Thread(target=run, daemon=True).start()


def test_installed_model_enumeration_does_not_block_the_command_thread() -> None:
    host = _Host()
    entered, release, ready = threading.Event(), threading.Event(), threading.Event()

    class Provider:
        id = "whispercpp"

        def list_installed_models(self):
            entered.set()
            assert release.wait(2)
            return [_Model("small")]

    host._run_background_task = lambda _label, work, success: _run_in_worker(  # type: ignore[attr-defined]
        host, work, success
    )
    started = time.monotonic()
    host._check_installed_speech_models(Provider(), "test", lambda _provider, _models: ready.set())
    assert time.monotonic() - started < 0.2
    assert entered.wait(1)
    release.set()
    assert ready.wait(1)


def test_microphone_enumeration_does_not_block_the_command_thread(monkeypatch) -> None:
    from quill.core.speech import capture

    host = _Host()
    entered, release = threading.Event(), threading.Event()

    def blocked_devices():
        entered.set()
        assert release.wait(2)
        return []

    monkeypatch.setattr(capture, "list_input_devices", blocked_devices)
    host._run_background_task = lambda _label, work, _success: _run_in_worker(  # type: ignore[attr-defined]
        host, work, lambda _result: None
    )
    started = time.monotonic()
    host.choose_dictation_microphone()
    assert time.monotonic() - started < 0.2
    assert entered.wait(1)
    release.set()


def test_caption_text_write_runs_off_the_command_thread(monkeypatch, tmp_path: Path) -> None:
    from quill.core import storage

    host = _Host()
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()

    def blocked_write(*_args, **_kwargs):
        entered.set()
        assert release.wait(2)

    monkeypatch.setattr(storage, "write_text_atomic", blocked_write)
    host._run_background_task = lambda _label, work, success: _run_in_worker(  # type: ignore[attr-defined]
        host, work, lambda result: (success(result), finished.set())
    )
    host._announce = lambda _message: None  # type: ignore[attr-defined]
    started = time.monotonic()
    host._save_caption_text(tmp_path / "caption.srt", "caption text")
    assert time.monotonic() - started < 0.2
    assert entered.wait(1)
    release.set()
    assert finished.wait(1)


def test_voice_service_availability_does_not_enumerate_models(monkeypatch) -> None:
    from quill.core.speech import capture
    from quill.ui.voice_services import VoiceServices

    class Provider:
        def list_installed_models(self):
            raise AssertionError("model enumeration belongs in the transcription worker")

    monkeypatch.setattr(capture, "capture_available", lambda: True)
    assert VoiceServices(stt_provider=Provider()).input_available()
