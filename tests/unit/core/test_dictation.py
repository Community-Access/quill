from __future__ import annotations

from quill.core.dictation import (
    DictationController,
    DictationSettings,
    list_dictation_devices,
)


def test_stop_returns_joined_segments_and_resets_state() -> None:
    controller = DictationController()
    controller._segments = ["first", " ", "second"]  # type: ignore[attr-defined]
    result = controller.stop()
    assert result == "first second"
    assert controller.state == "idle"


def test_default_engine_is_windows() -> None:
    # Only the OS dictation panel is functional today; the default reflects that
    # rather than promising an offline recognizer that is not wired up (S0).
    assert DictationSettings().engine == "windows"


def test_list_dictation_devices_is_empty_placeholder() -> None:
    # Capture (and real device enumeration) arrives with the #617 speech engine.
    assert list_dictation_devices() == []
