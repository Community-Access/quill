"""Headless tests for the External Player settings dialog (PRD 11.5, 44.3)."""

import tempfile

import pytest

wx = pytest.importorskip("wx")

from quill.apps.beacon import external_player as ep


@pytest.fixture
def frame(monkeypatch):
    data_dir = tempfile.mkdtemp()
    monkeypatch.setenv("QUILLBEACON_DATA", data_dir)
    app = wx.App(False)
    from quill.apps.beacon.app import BeaconFrame

    f = BeaconFrame()
    yield f
    f.Destroy()
    try:
        app.Destroy()
    except Exception:
        pass


def test_dialog_seeds_from_settings(frame):
    from quill.apps.beacon.dialogs import PlayerSettingsDialog

    s = ep.PlayerSettings(
        default_player=ep.PLAYER_VLC,
        custom_path={"vlc": "/opt/vlc"},
        per_type={"radioStream": ep.PLAYER_MPV},
    )
    dlg = PlayerSettingsDialog(frame, settings=s)
    try:
        assert dlg.default_combo.GetValue() == ep.PLAYER_VLC
        assert dlg.vlc_path.GetValue() == "/opt/vlc"
        assert dlg._type_combos["radioStream"].GetValue() == ep.PLAYER_MPV
    finally:
        dlg.Destroy()


def test_dialog_result_round_trips(frame):
    from quill.apps.beacon.dialogs import PlayerSettingsDialog

    dlg = PlayerSettingsDialog(frame, settings=ep.PlayerSettings())
    try:
        dlg.default_combo.SetValue(ep.PLAYER_MPV)
        dlg.mpv_path.SetValue("/usr/bin/mpv")
        dlg._type_combos["video"].SetValue(ep.PLAYER_VLC)
        r = dlg.result()
    finally:
        dlg.Destroy()
    assert r.default_player == ep.PLAYER_MPV
    assert r.custom_path == {"mpv": "/usr/bin/mpv"}
    assert r.per_type == {"video": ep.PLAYER_VLC}


def test_dialog_result_drops_default_per_type(frame):
    from quill.apps.beacon.dialogs import PlayerSettingsDialog

    dlg = PlayerSettingsDialog(frame, settings=ep.PlayerSettings())
    try:
        dlg._type_combos["radioStream"].SetValue(ep.PLAYER_DEFAULT)
        r = dlg.result()
    finally:
        dlg.Destroy()
    assert "radioStream" not in r.per_type


def test_frame_handler_saves_settings(frame):
    from quill.apps.beacon.dialogs import PlayerSettingsDialog

    s = ep.PlayerSettings(default_player=ep.PLAYER_VLC, custom_path={"vlc": "/opt/vlc"})
    dlg = PlayerSettingsDialog(frame, settings=s)
    try:
        dlg.default_combo.SetValue(ep.PLAYER_MPV)
        new = dlg.result()
    finally:
        dlg.Destroy()
    assert ep.save_settings(frame.data_dir, new) is True
    loaded = ep.load_settings(frame.data_dir)
    assert loaded.default_player == ep.PLAYER_MPV
    assert loaded.custom_path == {"vlc": "/opt/vlc"}
