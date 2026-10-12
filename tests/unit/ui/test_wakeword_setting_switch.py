"""The "Listen for 'Hey QUILL'" and "Keep listening across restarts" settings work.

Until 2026-10 the Settings check box was a second, dead switch: the Tools > Speech
command kept its own state and nothing read ``voice_wakeword_enabled``. These
drive the real command through the real mixin with only the microphone, the
speech provider and the save faked.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.settings import Settings
from quill.ui import wakeword_switch
from quill.ui.main_frame_speech_voice import VoiceInteractionMixin


class _Provider:
    def __init__(self, models: list[Any]) -> None:
        self._models = models

    def list_installed_models(self) -> list[Any]:
        return self._models

    def is_available(self) -> bool:
        return True


class _Host(VoiceInteractionMixin):
    def __init__(self, settings: Settings, *, models: bool = True, safe_mode: bool = False) -> None:
        self.settings = settings
        self._safe_mode = safe_mode
        self._provider = _Provider([SimpleNamespace(id="m")] if models else [])
        self.announced: list[str] = []
        self.listen_windows = 0
        self.status: list[str] = []

    def _voice_provider(self) -> _Provider:
        return self._provider

    def _check_installed_speech_models(self, provider, _title, on_ready) -> None:
        installed = provider.list_installed_models()
        if installed:
            on_ready(provider, installed)

    def _run_background_task(self, _label, work, on_success) -> None:
        on_success(work(lambda *_args: None))

    def _installed_or_prompt(self, provider: _Provider, title: str) -> list[Any] | None:
        return provider.list_installed_models() or None

    def _announce(self, message: str, **_kw: Any) -> None:
        self.announced.append(message)

    def _set_status_quiet(self, message: str) -> None:
        self.status.append(message)

    def _play_speech_sound(self, cue: str) -> None:
        pass

    def _wake_capture_window(self, *, for_command: bool = False) -> None:
        self.listen_windows += 1

    def _wake_stop_capture(self) -> None:
        pass


@pytest.fixture
def saved(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    calls: list[bool] = []
    monkeypatch.setattr(
        "quill.core.settings.save_settings",
        lambda s: calls.append(bool(s.voice_wakeword_enabled)),
    )
    monkeypatch.setattr("quill.core.speech.capture.capture_available", lambda: True)
    return calls


def _voice_on(**overrides: Any) -> Settings:
    settings = Settings()
    settings.voice_commands_enabled = True
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


def test_command_records_and_saves_the_switch(saved: list[bool]) -> None:
    host = _Host(_voice_on())
    host.voice_wakeword_toggle()
    assert wakeword_switch.wakeword_running(host)
    assert host.settings.voice_wakeword_enabled is True
    host.voice_wakeword_toggle()
    assert not wakeword_switch.wakeword_running(host)
    assert host.settings.voice_wakeword_enabled is False
    assert saved == [True, False]


def test_startup_listens_only_when_the_setting_is_on(saved: list[bool]) -> None:
    off = _Host(_voice_on(voice_wakeword_enabled=False))
    wakeword_switch.start_wakeword_if_enabled(off)
    assert not wakeword_switch.wakeword_running(off)

    on = _Host(_voice_on(voice_wakeword_enabled=True))
    wakeword_switch.start_wakeword_if_enabled(on)
    assert wakeword_switch.wakeword_running(on)
    assert on.listen_windows == 1
    assert saved == []  # starting from the saved value writes nothing


def test_startup_is_quiet_when_it_cannot_listen(saved: list[bool]) -> None:
    for host in (
        _Host(_voice_on(voice_wakeword_enabled=True), safe_mode=True),
        _Host(_voice_on(voice_wakeword_enabled=True), models=False),
        _Host(Settings(voice_wakeword_enabled=True)),  # voice commands off
    ):
        wakeword_switch.start_wakeword_if_enabled(host)
        assert not wakeword_switch.wakeword_running(host)
        assert host.announced == []


def test_startup_model_scan_does_not_block_the_event_handler(saved: list[bool]) -> None:
    entered, release, started = threading.Event(), threading.Event(), time.monotonic()
    host = _Host(_voice_on(voice_wakeword_enabled=True))

    def blocked_scan() -> list[Any]:
        entered.set()
        assert release.wait(2)
        return [SimpleNamespace(id="m")]

    host._provider.list_installed_models = blocked_scan

    def run_background_task(_label, work, on_success) -> None:
        def worker() -> None:
            on_success(work(lambda *_args: None))

        threading.Thread(target=worker, daemon=True).start()

    host._run_background_task = run_background_task
    wakeword_switch.start_wakeword_if_enabled(host)
    try:
        assert time.monotonic() - started < 0.2
        assert entered.wait(1)
        assert not wakeword_switch.wakeword_running(host)
    finally:
        release.set()

    deadline = time.monotonic() + 1
    while not wakeword_switch.wakeword_running(host) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert wakeword_switch.wakeword_running(host)


@pytest.mark.parametrize("persist", [False, True])
def test_restart_round_trip_honours_keep_listening(persist: bool, saved: list[bool]) -> None:
    host = _Host(_voice_on(voice_wakeword_persist=persist))
    host.voice_wakeword_toggle()
    from quill.core.settings_migration import from_versioned, to_versioned

    relaunched = _Host(from_versioned(to_versioned(host.settings)))
    relaunched.settings.voice_commands_enabled = True
    wakeword_switch.start_wakeword_if_enabled(relaunched)
    assert wakeword_switch.wakeword_running(relaunched) is persist


def test_settings_tick_box_starts_and_stops_listening(saved: list[bool]) -> None:
    host = _Host(_voice_on())
    wakeword_switch.start_wakeword_if_enabled(host)
    host.settings.voice_wakeword_enabled = True  # checked in Settings, OK pressed
    wakeword_switch.apply_wakeword_setting(host)
    assert wakeword_switch.wakeword_running(host)
    host.settings.voice_wakeword_enabled = False
    wakeword_switch.apply_wakeword_setting(host)
    assert not wakeword_switch.wakeword_running(host)


def test_tick_box_that_cannot_start_is_unticked_and_explained(saved: list[bool]) -> None:
    host = _Host(Settings(voice_wakeword_enabled=False))  # voice commands off
    wakeword_switch.start_wakeword_if_enabled(host)
    host.settings.voice_wakeword_enabled = True
    wakeword_switch.apply_wakeword_setting(host)
    assert not wakeword_switch.wakeword_running(host)
    assert host.settings.voice_wakeword_enabled is False
    assert any("Voice commands are off" in text for text in host.announced)


def test_unrelated_settings_ok_does_not_restart_a_stopped_listener(saved: list[bool]) -> None:
    host = _Host(_voice_on(voice_wakeword_enabled=True))
    wakeword_switch.start_wakeword_if_enabled(host)
    host._wake_run(host._wake.stop())  # stopped by itself (e.g. model removed)
    wakeword_switch.apply_wakeword_setting(host)  # OK pressed for something else
    assert not wakeword_switch.wakeword_running(host)
