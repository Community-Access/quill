"""Tests for configurable external-player settings (PRD 11.5, 44.3).

Covers PlayerSettings resolution, custom-path honoring in build_command/launch,
per-type overrides, load/save round-trip, and the launch fallback when a custom
path does not exist.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import external_player as ep

# -- PlayerSettings ----------------------------------------------------------


def test_player_for_per_type_overrides_default():
    s = ep.PlayerSettings(default_player=ep.PLAYER_VLC, per_type={"radioStream": ep.PLAYER_MPV})
    assert s.player_for("radioStream") == ep.PLAYER_MPV
    assert s.player_for("podcastEpisode") == ep.PLAYER_VLC
    assert s.player_for(None) == ep.PLAYER_VLC


def test_exe_for_honors_custom_path():
    s = ep.PlayerSettings(custom_path={"vlc": "/opt/vlc/vlc"})
    assert s.exe_for("vlc") == "/opt/vlc/vlc"
    assert s.exe_for("mpv") == "mpv"


def test_round_trip_dict():
    s = ep.PlayerSettings(
        default_player=ep.PLAYER_MPV,
        custom_path={"vlc": "/x/vlc"},
        per_type={"video": ep.PLAYER_VLC},
    )
    d = s.to_dict()
    s2 = ep.PlayerSettings.from_dict(d)
    assert s2.default_player == ep.PLAYER_MPV
    assert s2.custom_path == {"vlc": "/x/vlc"}
    assert s2.per_type == {"video": ep.PLAYER_VLC}


# -- load/save ---------------------------------------------------------------


def test_load_defaults_when_missing(tmp_path):
    s = ep.load_settings(tmp_path)
    assert isinstance(s, ep.PlayerSettings)
    assert s.default_player == ep.PLAYER_DEFAULT


def test_load_corrupt_returns_defaults(tmp_path):
    (tmp_path / ep.SETTINGS_FILE).write_text("not json", encoding="utf-8")
    s = ep.load_settings(tmp_path)
    assert s.default_player == ep.PLAYER_DEFAULT


def test_save_then_load(tmp_path):
    s = ep.PlayerSettings(
        default_player=ep.PLAYER_VLC,
        custom_path={"vlc": "/x/vlc"},
        per_type={"radioStream": ep.PLAYER_MPV},
    )
    assert ep.save_settings(tmp_path, s) is True
    data = json.loads((tmp_path / ep.SETTINGS_FILE).read_text(encoding="utf-8"))
    assert data["default_player"] == ep.PLAYER_VLC
    s2 = ep.load_settings(tmp_path)
    assert s2.custom_path == {"vlc": "/x/vlc"}
    assert s2.per_type == {"radioStream": ep.PLAYER_MPV}


# -- build_command / launch --------------------------------------------------


def test_build_command_uses_custom_path():
    cmd = ep.build_command(
        "https://x/a", 5000, player=ep.PLAYER_VLC, custom_path={"vlc": "/opt/vlc"}
    )
    assert cmd[0] == "/opt/vlc"
    assert "--start-time=5.0" in cmd
    assert cmd[-1] == "https://x/a"


def test_build_command_default_returns_none():
    assert ep.build_command("https://x/a", 0, player=ep.PLAYER_DEFAULT) is None


def test_launch_uses_settings_per_type(monkeypatch):
    launched = {}

    def fake_popen(cmd, **kw):
        launched["cmd"] = cmd
        return object()

    monkeypatch.setattr(ep.subprocess, "Popen", fake_popen)
    # Make the custom path "exist" so shutil.which returns it.
    monkeypatch.setattr(ep.shutil, "which", lambda exe: exe if exe == "/opt/vlc/vlc" else None)
    s = ep.PlayerSettings(
        default_player=ep.PLAYER_DEFAULT,
        custom_path={"vlc": "/opt/vlc/vlc"},
        per_type={"radioStream": ep.PLAYER_VLC},
    )
    res = ep.launch("https://x/a", 1000, settings=s, resource_type="radioStream")
    assert res["ok"] is True
    assert launched["cmd"][0] == "/opt/vlc/vlc"
    assert "--start-time=1.0" in launched["cmd"]


def test_launch_falls_back_when_custom_path_missing(monkeypatch):
    monkeypatch.setattr(ep.shutil, "which", lambda exe: None)
    monkeypatch.setattr(
        ep,
        "_open_default",
        lambda url: {"ok": True, "message": "default", "player": ep.PLAYER_DEFAULT},
    )
    s = ep.PlayerSettings(default_player=ep.PLAYER_VLC, custom_path={"vlc": "/nope/vlc"})
    res = ep.launch("https://x/a", 0, settings=s)
    assert res["ok"] is True
    assert "fallback" in res


def test_launch_no_url():
    res = ep.launch("   ", 0, settings=ep.PlayerSettings())
    assert res["ok"] is False and res["message"] == "no URL"
