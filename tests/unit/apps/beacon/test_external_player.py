"""Tests for external-player handoff command building (PRD 11.5, 44.3)."""

from quill.apps.beacon import external_player as ep


def test_vlc_command_with_start_time():
    cmd = ep.build_command("https://x/a.mp3", 90000, player=ep.PLAYER_VLC)
    assert cmd[0] == "vlc"
    assert "--start-time=90.0" in cmd
    assert cmd[-1] == "https://x/a.mp3"


def test_mpv_command_with_start_time():
    cmd = ep.build_command("https://x/a.mp3", 5000, player=ep.PLAYER_MPV)
    assert cmd[0] == "mpv"
    assert any(a.startswith("--start=5.0") for a in cmd)


def test_default_returns_none():
    assert ep.build_command("https://x/a", 1000, player=ep.PLAYER_DEFAULT) is None


def test_empty_url_returns_none():
    assert ep.build_command("", 1000, player=ep.PLAYER_VLC) is None


def test_zero_start_time():
    cmd = ep.build_command("https://x/a", 0, player=ep.PLAYER_VLC)
    assert "--start-time=0.0" in cmd


def test_launch_no_url_is_safe():
    res = ep.launch("", 0, player=ep.PLAYER_VLC)
    assert res["ok"] is False


def test_launch_missing_player_falls_back(monkeypatch):
    # vlc not installed -> should fall back to system default without raising.
    monkeypatch.setattr(
        ep.shutil, "which", lambda name: None if name == "vlc" else "/usr/bin/" + name
    )
    called = {}

    def fake_open(url):
        called["url"] = url
        return None

    monkeypatch.setattr(ep, "os_startfile", fake_open, raising=False)
    monkeypatch.setattr(ep.sys, "platform", "win32")
    res = ep.launch("https://x/a", 1000, player=ep.PLAYER_VLC)
    assert res["ok"] is True
    assert "fallback" in res
    assert called["url"] == "https://x/a"
