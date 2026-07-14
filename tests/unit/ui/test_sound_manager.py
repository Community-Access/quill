"""Tests for :mod:`quill.ui.sound_manager`.

Covers the #332 surface-level guarantees:

* ``set_volume`` is called on the public :class:`SoundPlayer.set_volume` (no
  private ``_backend._output`` reach-in from outside sound_player).
* The QSP path-traversal guard is the public
  :func:`quill.core.sound_pack.is_unsafe_path` (no private import).
* The indent tone overlay unregisters its events on every reload, including
  clearing the overlay with ``load_indent_tone_pack("")``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from quill.core import sound_pack as sound_pack_mod
from quill.core.sound_pack import is_unsafe_path
from quill.ui import sound_manager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _StubPlayer:
    """Drop-in stand-in for :class:`SoundPlayer` that records calls."""

    def __init__(self) -> None:
        self.events: dict[str, bytes] = {}
        self.set_volume_calls: list[float] = []
        self.unregister_calls: list[frozenset[str]] = []
        self.unregister_single_calls: list[str] = []
        self.set_disabled_calls: list[frozenset[str]] = []
        self.set_muted_calls: list[bool] = []
        self.shutdown_called: bool = False

    def set_volume(self, volume: float) -> None:
        self.set_volume_calls.append(volume)

    def set_disabled(self, disabled: frozenset[str]) -> None:
        self.set_disabled_calls.append(disabled)

    def set_muted(self, muted: bool) -> None:
        self.set_muted_calls.append(muted)

    def register_event(self, event_id: str, wav: bytes) -> None:
        self.events[event_id] = wav

    def unregister_event(self, event_id: str) -> None:
        self.events.pop(event_id, None)
        self.unregister_single_calls.append(event_id)

    def unregister_events(self, event_ids: frozenset[str]) -> None:
        self.unregister_calls.append(event_ids)
        for eid in event_ids:
            self.events.pop(eid, None)

    def loaded_event_ids(self) -> frozenset[str]:
        return frozenset(self.events.keys())

    def shutdown(self, timeout: float = 2.0) -> None:
        self.shutdown_called = True


def _stub_settings(
    *,
    enabled: bool = True,
    pack_path: str = "",
    volume: int = 80,
    disabled: str = "",
    indent_scale: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        sound_enabled=enabled,
        sound_pack_path=pack_path,
        sound_volume=volume,
        sound_events_disabled=disabled,
        indent_tone_scale=indent_scale,
    )


@pytest.fixture
def player(monkeypatch: pytest.MonkeyPatch) -> _StubPlayer:
    stub = _StubPlayer()
    # Bypass the platform import in _SoundManager.__init__.
    monkeypatch.setattr(
        "quill.platform.sound_player.SoundPlayer",
        lambda: stub,
    )
    return stub


# ---------------------------------------------------------------------------
# Public-API hygiene: no private reach-ins
# ---------------------------------------------------------------------------


def test_sound_manager_does_not_reach_into_private_backend_output(
    player: _StubPlayer,
) -> None:
    """The volume route must go through the public ``set_volume`` method."""
    mgr = sound_manager._SoundManager(_stub_settings(volume=42))
    assert mgr.player is player
    # _apply_volume should have called set_volume(0.42) on construction.
    assert player.set_volume_calls == [0.42]


def test_sound_manager_uses_public_is_unsafe_path(player: _StubPlayer) -> None:
    """Sound manager must import the public guard, not the private alias."""
    src = sound_manager.__file__  # type: ignore[attr-defined]
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    # Public name is used inside register_quillin_sounds.
    assert "is_unsafe_path" in text
    # The legacy private name is no longer imported.
    assert "from quill.core.sound_pack import _path_is_unsafe" not in text


def test_sound_pack_exposes_public_is_unsafe_path() -> None:
    """is_unsafe_path and the private alias must agree on every input."""
    cases = [
        "ok.wav",
        "sub/dir/ok.wav",
        "../escape.wav",
        "/etc/passwd",
        "\\windows\\system32",
        "C:/abs.wav",
        "C:\\abs.wav",
    ]
    for case in cases:
        assert is_unsafe_path(case) == sound_pack_mod._path_is_unsafe(case), case


# ---------------------------------------------------------------------------
# Indent tone overlay: events are unregistered on every reload
# ---------------------------------------------------------------------------


def test_load_indent_tone_pack_unregisters_on_clear(player: _StubPlayer) -> None:
    """Calling load_indent_tone_pack("") removes the previously registered
    overlay events from the player."""
    mgr = sound_manager._SoundManager(_stub_settings(indent_scale=""))
    fake_pack = SimpleNamespace(events={"indent_level_1_up": b"WAV", "indent_level_1_down": b"WAV"})
    with patch("quill.core.sound_pack.load_sound_pack", return_value=fake_pack):
        mgr.load_indent_tone_pack("pentatonic")
    assert "indent_level_1_up" in player.events
    assert "indent_level_1_down" in player.events

    # Switching to a different scale drops the prior overlay events first.
    with patch("quill.core.sound_pack.load_sound_pack", return_value=fake_pack):
        mgr.load_indent_tone_pack("diatonic")
    assert frozenset({"indent_level_1_up", "indent_level_1_down"}) in player.unregister_calls
    assert "indent_level_1_up" in player.events  # re-registered by the new pack

    # Clearing the overlay drops them again.
    mgr.load_indent_tone_pack("")
    assert "indent_level_1_up" not in player.events
    assert "indent_level_1_down" not in player.events
    assert mgr.get_loaded_events() == frozenset()


def test_load_indent_tone_pack_missing_pack_still_unregisters_old(
    player: _StubPlayer,
) -> None:
    """If the new pack can't be located, the previous overlay must still be
    cleared so stale events do not leak into the next reload."""
    mgr = sound_manager._SoundManager(_stub_settings(indent_scale=""))
    fake_pack = SimpleNamespace(events={"indent_level_2_up": b"WAV"})
    with patch("quill.core.sound_pack.load_sound_pack", return_value=fake_pack):
        mgr.load_indent_tone_pack("pentatonic")
    assert "indent_level_2_up" in player.events

    # Now ask for a scale whose pack directory does not exist.
    mgr._bundled_indent_path = staticmethod(lambda scale: None)  # type: ignore[method-assign]
    mgr.load_indent_tone_pack("whole_tone")

    assert "indent_level_2_up" not in player.events
    assert frozenset({"indent_level_2_up"}) in player.unregister_calls


def test_apply_settings_clears_overlay_when_scale_set_to_empty(
    player: _StubPlayer,
) -> None:
    """When the user turns the indent overlay off in preferences, the previous
    overlay events are unregistered from the player."""
    fake_pack = SimpleNamespace(events={"indent_level_3_up": b"WAV"})
    mgr = sound_manager._SoundManager(_stub_settings(indent_scale="pentatonic"))
    with patch("quill.core.sound_pack.load_sound_pack", return_value=fake_pack):
        mgr.load_indent_tone_pack("pentatonic")
    assert "indent_level_3_up" in player.events

    mgr.apply_settings(_stub_settings(indent_scale=""))
    assert "indent_level_3_up" not in player.events
