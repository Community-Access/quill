"""UX-014: controls shown for a list selection never write back to it.

TG Drop Deck's mixer muted every source the user arrowed past, because the
mute check box's ``SetValue`` raised the same event a user's click does. These
tests make every programmatic write raise its change event, as it can on some
builds, and prove that arrowing through the Studio Mixer, the broadcast
window's sound list and the guard itself changes nothing.
"""

from __future__ import annotations

import pytest
import wx

from quill.ui.sync_guard import SyncGuard


@pytest.fixture
def parent(wx_session_app):
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()


def _raise_on_write(control, method: str, event_type) -> None:
    """Make ``control.<method>`` raise *event_type* the way a user change does."""
    original = getattr(control, method)

    def write(*args, **kwargs):
        result = original(*args, **kwargs)
        event = wx.CommandEvent(event_type, control.GetId())
        event.SetEventObject(control)
        control.GetEventHandler().ProcessEvent(event)
        return result

    setattr(control, method, write)


def test_sync_guard_is_reentrant():
    guard = SyncGuard()
    assert not guard
    with guard:
        with guard:
            assert guard
        assert guard
    assert not guard


def test_arrowing_through_the_mixer_changes_no_mute_volume_or_card(parent, monkeypatch):
    from quill.platform.windows import audio_routing, audio_sessions
    from quill.ui.studio_mixer import StudioMixerDialog

    sessions = [
        audio_sessions.AudioSession(321, "vlc.exe", False, 0.8, 0.2),
        audio_sessions.AudioSession(654, "msedge.exe", True, 0.3, 0.0),
        audio_sessions.AudioSession(987, "zoom.exe", False, 1.0, 0.5),
    ]
    speakers = audio_routing.AudioDevice("{spk}", "Speakers", 0, True, True)
    headset = audio_routing.AudioDevice("{hs}", "Headset", 0)
    mic = audio_routing.AudioDevice("{mic}", "Microphone", 1, True, True)
    line_in = audio_routing.AudioDevice("{line}", "Line in", 1)
    writes: list[tuple] = []
    monkeypatch.setattr(audio_sessions, "list_sessions", lambda: list(sessions))
    for name in ("set_process_mute", "set_process_volume"):
        monkeypatch.setattr(audio_sessions, name, lambda *a, n=name: writes.append((n, *a)))
    monkeypatch.setattr(
        audio_routing,
        "list_devices",
        lambda flow=0: [speakers, headset] if flow == audio_routing.RENDER else [mic, line_in],
    )
    cards = {321: "", 654: "{hs}", 987: None}
    monkeypatch.setattr(audio_routing, "app_output", lambda pid: cards[pid])
    levels = {"{mic}": (0.5, False), "{line}": (0.9, True)}
    monkeypatch.setattr(audio_routing, "input_level", lambda device: levels[device])
    for name in ("set_app_output", "set_input_level", "set_input_mute", "set_default_device"):
        monkeypatch.setattr(audio_routing, name, lambda *a, n=name, **k: writes.append((n, *a)))

    dialog = StudioMixerDialog(parent, announce=lambda _t: None)
    try:
        _raise_on_write(dialog.volume, "SetValue", wx.wxEVT_SPINCTRL)
        _raise_on_write(dialog.card, "SetSelection", wx.wxEVT_CHOICE)
        _raise_on_write(dialog.input_level, "SetValue", wx.wxEVT_SPINCTRL)
        _raise_on_write(dialog.input_mute, "SetValue", wx.wxEVT_CHECKBOX)
        for row in (1, 2, 0, 2, 1):  # Down, Down, Home, End, Up
            dialog.programs.Select(row)
            dialog._program_selected(None)
            assert dialog.volume.GetValue() == round(sessions[row].volume * 100)
        for row in (1, 0, 1):
            dialog.recording.Select(row)
            dialog._input_selected(None)
        assert dialog.input_mute.GetValue() is True  # shown for Line in, not written
        dialog.refresh()  # a refresh reselects and reshows a row too
        assert writes == []
        assert [dialog.programs.GetItemText(r, 1) for r in range(3)] == [
            "Yes, 80 percent",
            "Muted",
            "Yes, 100 percent",
        ]
        # The guard covers only the app's own writes: a change outside it, which
        # is what a user's click is, still lands on the selected row.
        dialog.programs.Select(0)
        dialog._program_selected(None)
        assert writes == []
        dialog.input_mute.SetValue(True)
        dialog._volume_changed(None)
        assert writes == [("set_input_mute", "{mic}", True), ("set_process_volume", 321, 0.8)]
    finally:
        dialog.Destroy()


def test_arrowing_the_broadcast_sound_list_keeps_the_check_and_levels(parent):
    from quill.core.streaming import StreamSettings, StreamSource
    from quill.ui.studio_go_live import GoLiveDialog

    sources = (
        StreamSource("microphone", "Mic", on=True, level_db=-6.0),
        StreamSource("system", "System sound", on=True, level_db=3.0),
    )
    dialog = GoLiveDialog(
        parent,
        StreamSettings(host="h.example", sources=sources),
        "pw",
        check=lambda *_a: None,
        test=lambda *_a: None,
        confirm=lambda *_a: True,
    )
    try:
        _raise_on_write(dialog.level, "SetValue", wx.wxEVT_SPINCTRL)
        dialog.checked = ("settings", "pw")  # as after a check that passed
        dialog.go.Enable(True)
        for row in (1, 0, 1):
            dialog.list.Select(row)
            dialog._show_level()
        assert [s.level_db for s in dialog.sources] == [-6.0, 3.0]
        assert dialog.checked is not None and dialog.go.IsEnabled()
    finally:
        dialog.Destroy()
