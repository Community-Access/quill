"""Lyrics is reachable: a key, a menu row that shows it, the palette, and F1."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.apps import radio_playback_extras
from quill.core import app_keymaps
from quill.core.media import surface_help as media_help
from quill.core.radio import surface_help as radio_help


def test_radio_lyrics_has_a_key_no_other_radio_command_claims() -> None:
    radio = app_keymaps.APP_KEYMAPS["radio"]
    assert radio["radio.lyrics"] == "Ctrl+Alt+B"
    claimants = [cmd for cmd, key in radio.items() if key.lower() == "ctrl+alt+b"]
    assert claimants == ["radio.lyrics"]


class _Menu:
    def __init__(self) -> None:
        self.rows: list[str] = []

    def Append(self, _id: Any, label: str) -> None:  # noqa: N802 - wx's name
        self.rows.append(label)


def test_the_playback_menu_row_follows_song_history_and_shows_its_key() -> None:
    import wx

    radio = app_keymaps.APP_KEYMAPS["radio"]
    bound: list[Any] = []
    app = SimpleNamespace(
        _menu_label=lambda title, cmd: f"{title}\t{radio[cmd]}" if radio.get(cmd) else title,
        frame=SimpleNamespace(Bind=lambda *a, **k: bound.append(k.get("id"))),
    )
    menu = _Menu()

    ids = radio_playback_extras.append_song_items(app, menu, wx)

    assert menu.rows == ["&Song History...\tCtrl+Shift+H", "L&yrics...\tCtrl+Alt+B"]
    assert len(ids) == 2 and bound == list(ids)


def test_the_palette_offers_lyrics_and_it_runs_the_command(monkeypatch) -> None:
    from quill.ui.radio import (
        lineups_commands,
        local_media_commands,
        lyrics_commands,
        palette_commands,
        transport_keys,
    )

    for module, name in (
        (local_media_commands, "register"),
        (lineups_commands, "register"),
        (transport_keys, "register_commands"),
    ):
        monkeypatch.setattr(module, name, lambda *a, **k: None)
    called: list[Any] = []
    monkeypatch.setattr(lyrics_commands, "lyrics_for_playing", called.append)
    registered: dict[str, Any] = {}

    class _Commands:
        def try_register(self, command_id: str, _title: str, handler: Any, *_a, **_k) -> None:
            registered[command_id] = handler

    class _Host:
        commands = _Commands()

        def __getattr__(self, name: str) -> Any:
            return lambda *a, **k: ""

    host = _Host()
    palette_commands.register_radio_commands(host)

    registered["radio.lyrics"]()
    assert called == [host]


def test_every_lyrics_window_title_answers_f1_in_both_apps() -> None:
    title = "Lyrics: Your Song by Elton John"
    assert radio_help.is_known_title(title)
    assert media_help.is_known_title(title)
    assert "LRCLIB" in radio_help.purpose_for_title(title)
    assert "Follow playback" in media_help.purpose_for_title(title)
