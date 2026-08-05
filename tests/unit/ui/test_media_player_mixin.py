"""Unit tests for the in-QUILL MediaPlayerMixin (no display required)."""

from __future__ import annotations

import pytest

from quill.ui.main_frame_media_player import MediaPlayerMixin


def test_open_media_player_launches_player(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    import quill.ui.companion_offer as companion_offer

    monkeypatch.setattr(companion_offer, "try_open_or_offer", lambda host, key: calls.append(key))
    MediaPlayerMixin().open_media_player()
    assert calls == ["player"]


def test_register_media_player_command_is_gated(monkeypatch: pytest.MonkeyPatch) -> None:
    registered: list[tuple[str, str]] = []

    class _Commands:
        def register(self, command_id: str, title: str, handler: object, binding: object) -> None:
            registered.append((command_id, title))

    class _Frame(MediaPlayerMixin):
        def __init__(self) -> None:
            self.commands = _Commands()

        def _binding_for(self, command_id: str) -> None:
            return None

    # Public build: the Media Player is a gated companion app, so its command is
    # NOT registered (never reaches the command palette).
    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    _Frame()._register_media_player_commands()
    assert registered == []

    # Developer build: the command IS registered.
    monkeypatch.setenv("QUILL_DEV_BUILD", "1")
    _Frame()._register_media_player_commands()
    assert registered == [("app.open_media_player", "Open the Media Player")]


def test_player_registered_in_launcher() -> None:
    from quill.core.app_launcher import APP_NAMES, build_launch_argv

    assert APP_NAMES["player"] == "Quill Media Player"
    argv = build_launch_argv("player")
    assert argv is not None
    assert argv[-2:] == ["-m", "quill.apps.player"]
