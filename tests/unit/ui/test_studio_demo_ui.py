"""Record a Demonstration: the setup dialog, status, sounds mixer and the Studio flow.

Native controls only, driven without a screen, camera, microphone or FFmpeg:
every device and the task manager are doubles, so what is tested is what the
listener meets -- the privacy defaults, the spoken check gating Start, the
state column, the confirmations, and what Studio says while it records.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import wx

from quill.apps.studio_capture import StudioCaptureMixin
from quill.core.demo_recording import DemoPlan, SoundSource
from quill.core.studio_capture import CaptureTarget
from quill.stability.task_manager import CancellationToken, UiLifetimeToken
from quill.ui.studio_demo_dialog import DemoCallbacks, RecordDemoDialog, recordable

DESKTOP = CaptureTarget("desktop", "Full desktop (all displays)", (0, 0, 1920, 1080), device="t")
DISPLAY = CaptureTarget(
    "display",
    "Display 1: \\\\.\\DISPLAY1; 1920 by 1080; origin 0, 0; primary",
    (0, 0, 1920, 1080),
    device="\\\\.\\DISPLAY1",
)
EDGE = CaptureTarget(
    "window", "Edge - Microsoft Edge", (10, 10, 811, 611), 111, 222, application="msedge.exe"
)
ACTIVE = CaptureTarget("active_window", "Active window after the delay")


@pytest.fixture
def parent(wx_session_app):
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()


def _callbacks(**changes):
    calls = {"check": [], "test": [], "camera": [], "confirm": True}

    def check(plan, done):
        calls["check"].append((plan, done))

    values = dict(
        check=check,
        test=lambda plan: calls["test"].append(plan),
        camera_check=lambda device, mirrored: calls["camera"].append((device, mirrored)),
        sounds=lambda: None,
        assign_keys=lambda: None,
        choose_program=lambda: (333, "vlc.exe"),
        list_targets=lambda: [DESKTOP, DISPLAY, EDGE],
        cameras=["Surface Camera Front"],
        microphones=["Microphone (Logi USB Headset)"],
        readers=[("jfw.exe", 444)],
        studio_pid=999,
        display_info=lambda bounds: ("\\\\.\\DISPLAY1", (0, 0, 1920, 1080)),
        confirm=lambda text, title: calls["confirm"],
        choose_folder=lambda parent, current: None,
    )
    values.update(changes)
    return DemoCallbacks(**values), calls


def _dialog(parent, tmp_path, **changes):
    callbacks, calls = _callbacks(**changes)
    dialog = RecordDemoDialog(
        parent, [DESKTOP, DISPLAY, EDGE, ACTIVE], callbacks, {}, str(tmp_path)
    )
    return dialog, calls


def _row(dialog, kind):
    return next(i for i, s in enumerate(dialog.sources) if s.kind == kind)


def test_only_window_display_and_desktop_are_offered(parent, tmp_path):
    dialog, _ = _dialog(parent, tmp_path)
    try:
        assert [t.kind for t in dialog.targets] == ["desktop", "display", "window"]
        assert recordable([ACTIVE]) == []
        # A named window is the first choice when one exists.
        assert dialog.target.GetStringSelection() == EDGE.friendly_label
    finally:
        dialog.Destroy()


def test_privacy_defaults_app_on_reader_mic_system_off(parent, tmp_path):
    dialog, _ = _dialog(parent, tmp_path)
    try:
        states = {s.kind: s.enabled for s in dialog.sources}
        assert states == {
            "application": True,
            "system": False,
            "microphone": False,
            "screen_reader": False,
        }
        reader = dialog.sources[_row(dialog, "screen_reader")]
        assert reader.label == "JAWS speech" and reader.process_id == 444
        assert dialog.source_list.GetItemText(_row(dialog, "microphone"), 1) == "Left out"
        assert not dialog.camera_on.GetValue()
        assert not dialog.start_button.IsEnabled()
    finally:
        dialog.Destroy()


def test_space_toggles_state_and_reader_needs_confirmation(parent, tmp_path):
    dialog, calls = _dialog(parent, tmp_path)
    try:
        mic = _row(dialog, "microphone")
        dialog.source_list.Select(mic)
        dialog._toggle_source()
        assert dialog.sources[mic].enabled
        assert dialog.source_list.GetItemText(mic, 1) == "In the recording"
        reader = _row(dialog, "screen_reader")
        dialog.source_list.Select(reader)
        calls["confirm"] = False
        dialog.callbacks.confirm = lambda text, title: calls["confirm"]
        dialog._toggle_source()
        assert not dialog.sources[reader].enabled
        dialog.callbacks.confirm = lambda text, title: True
        dialog._toggle_source()
        assert dialog.sources[reader].enabled
    finally:
        dialog.Destroy()


def test_level_and_added_program(parent, tmp_path):
    dialog, _ = _dialog(parent, tmp_path)
    try:
        dialog.source_list.Select(0)
        dialog.level.SetValue(-6)
        dialog._level_changed(None)
        assert dialog.sources[0].level_db == -6
        dialog._add_program(None)
        added = dialog.sources[-1]
        assert added.source_id == "added-vlc.exe" and added.enabled and added.process_id == 333
        assert dialog.remove.IsEnabled()
        dialog._remove_program(None)
        assert not any(s.source_id == "added-vlc.exe" for s in dialog.sources)
    finally:
        dialog.Destroy()


def test_plan_leaves_reader_out_of_system_sound(parent, tmp_path):
    dialog, _ = _dialog(parent, tmp_path)
    try:
        system = _row(dialog, "system")
        dialog.source_list.Select(system)
        dialog._toggle_source()
        plan = dialog.build_plan()
        source = plan.source("system")
        assert source.exclude_process_id == 444 and source.exclude_name == "jfw.exe"
        assert plan.target_kind == "window" and plan.window_handle == 111
        assert plan.studio_process_id == 999
        assert plan.screen_reader == "jfw.exe"
    finally:
        dialog.Destroy()


def test_check_gates_start_and_any_change_makes_it_stale(parent, tmp_path):
    dialog, calls = _dialog(parent, tmp_path)
    try:
        dialog._check(None)
        plan, done = calls["check"][0]
        assert isinstance(plan, DemoPlan)
        done("Stop: something.", False)
        assert not dialog.start_button.IsEnabled()
        dialog._check(None)
        _plan, done = calls["check"][1]
        done("No problems found.", True)
        assert dialog.start_button.IsEnabled()
        assert dialog.checked_plan is not None
        assert dialog.summary.GetValue() == "No problems found."
        dialog.pointer.SetValue(False)
        dialog._stale(None)
        assert not dialog.start_button.IsEnabled()
        assert dialog.checked_plan is None
        assert "check again" in dialog.summary.GetValue().lower()
    finally:
        dialog.Destroy()


def test_invalid_folder_is_a_stop_without_running_the_check(parent, tmp_path):
    dialog, calls = _dialog(parent, tmp_path)
    try:
        dialog.folder.SetValue("relative\\folder")
        dialog._check(None)
        assert calls["check"] == []
        assert dialog.summary.GetValue().startswith("Stop:")
    finally:
        dialog.Destroy()


def test_camera_controls_follow_the_checkbox_and_check_button(parent, tmp_path):
    dialog, calls = _dialog(parent, tmp_path)
    try:
        assert not dialog.camera_panel.IsEnabled()
        dialog.camera_on.SetValue(True)
        dialog._camera_toggled(None)
        assert dialog.camera_panel.IsEnabled()
        dialog._camera_check(None)
        assert calls["camera"] == [("Surface Camera Front", False)]
        plan = dialog.build_plan()
        assert plan.camera.enabled and plan.camera.device == "Surface Camera Front"
    finally:
        dialog.Destroy()


def test_no_camera_keeps_it_off(parent, tmp_path):
    dialog, _ = _dialog(parent, tmp_path, cameras=[])
    try:
        dialog.camera_on.SetValue(True)
        dialog._camera_toggled(None)
        assert "No camera was found" in dialog.summary.GetValue()
        assert not dialog.build_plan().camera.enabled
    finally:
        dialog.Destroy()


def test_studio_itself_never_becomes_a_source(parent, tmp_path):
    studio = CaptureTarget(
        "window", "QUILL Studio", (0, 0, 500, 500), 5, 999, application="python.exe"
    )
    callbacks, _ = _callbacks()
    dialog = RecordDemoDialog(parent, [studio], callbacks, {}, str(tmp_path))
    try:
        app = _row(dialog, "application")
        assert not dialog.sources[app].enabled
        dialog.source_list.Select(app)
        dialog._toggle_source()
        assert not dialog.sources[app].enabled
    finally:
        dialog.Destroy()


# -- status window and sounds mixer ---------------------------------------------------


def test_status_frame_updates_and_close_only_hides(wx_session_app):
    from quill.ui.studio_demo_status import RecordingStatusFrame

    calls = []
    frame = RecordingStatusFrame(
        None,
        status=lambda: "Recording, 00:00:05",
        pause=lambda: calls.append("pause"),
        marker=lambda: calls.append("marker"),
        mute=lambda: calls.append("mute"),
        speak_status=lambda: calls.append("status"),
        stop=lambda: calls.append("stop"),
        discard=lambda: calls.append("discard"),
        has_microphone=False,
    )
    try:
        assert frame.text.GetValue() == "Recording, 00:00:05"
        assert not frame.mute_button.IsEnabled()
        frame.set_paused(True)
        assert frame.pause_button.GetLabel() == "&Resume"
        frame.Close()
        assert not frame.IsShown()
    finally:
        frame.finish()


def test_mixer_mutes_sets_volume_and_moves_a_program(parent, monkeypatch):
    from quill.platform.windows import audio_routing, audio_sessions
    from quill.ui.studio_mixer import StudioMixerDialog

    session = audio_sessions.AudioSession(321, "vlc.exe", False, 0.8, 0.2)
    speakers = audio_routing.AudioDevice("{spk}", "Speakers", 0, True, True)
    headset = audio_routing.AudioDevice("{hs}", "Headset", 0)
    mic = audio_routing.AudioDevice("{mic}", "Microphone", 1, True, True)
    calls = []
    monkeypatch.setattr(audio_sessions, "list_sessions", lambda: [session])
    monkeypatch.setattr(
        audio_sessions, "set_process_mute", lambda pid, muted: calls.append(("mute", pid, muted))
    )
    monkeypatch.setattr(
        audio_sessions, "set_process_volume", lambda pid, level: calls.append(("vol", pid, level))
    )
    monkeypatch.setattr(
        audio_routing,
        "list_devices",
        lambda flow=0: [speakers, headset] if flow == audio_routing.RENDER else [mic],
    )
    monkeypatch.setattr(audio_routing, "app_output", lambda pid: "")
    monkeypatch.setattr(
        audio_routing, "set_app_output", lambda pid, device: calls.append(("card", pid, device))
    )
    monkeypatch.setattr(audio_routing, "input_level", lambda device: (0.5, False))
    monkeypatch.setattr(
        audio_routing,
        "set_default_device",
        lambda device, communications=False: calls.append(("default", device, communications)),
    )
    dialog = StudioMixerDialog(parent, announce=lambda _t: None)
    try:
        assert dialog.programs.GetItemText(0, 1) == "Yes, 80 percent"
        assert dialog.programs.GetItemText(0, 3) == "Windows default"
        dialog._toggle_mute()
        assert dialog.programs.GetItemText(0, 1) == "Muted"
        dialog.volume.SetValue(50)
        dialog._volume_changed(None)
        dialog.card.SetSelection(2)  # Headset
        dialog._card_changed(None)
        assert dialog.programs.GetItemText(0, 3) == "Headset"
        dialog.playback.Select(1)
        dialog._make_default(0, False)
        assert calls == [
            ("mute", 321, True),
            ("vol", 321, 0.5),
            ("card", 321, "{hs}"),
            ("default", "{hs}", False),
        ]
        assert dialog.recording.GetItemText(0, 2) == "50 percent"
    finally:
        dialog.Destroy()


# -- the Studio flow ----------------------------------------------------------------


class Tasks:
    def __init__(self):
        self.jobs = []

    def submit(self, name, work, **kwargs):
        self.jobs.append((name, work, kwargs))
        return SimpleNamespace(cancellation_token=CancellationToken())


class Host(StudioCaptureMixin):
    def __init__(self, frame):
        self.frame = frame
        self._safe_mode = False
        self.spoken = []
        self.status = []
        self._task_manager = Tasks()
        self._capture_lifetime = UiLifetimeToken()
        self._protected_background_jobs = {}

    def _announce(self, text):
        self.spoken.append(text)

    def _set_status_quiet(self, text):
        self.status.append(text)

    _set_status = _set_status_quiet

    def _refresh_statusbar(self):
        pass

    def _restore_from_tray(self):
        pass

    def _update_tray_tooltip(self, _text):
        pass

    def _show_message_box(self, *_args):
        return wx.YES


class FakeRecorder:
    def __init__(self, *, reader=False, microphone=True):
        sources = [SoundSource("application", "Edge sound", "app", enabled=True)]
        if microphone:
            sources.append(SoundSource("microphone", "Microphone", "microphone", enabled=True))
        if reader:
            sources.append(SoundSource("screen_reader", "JAWS speech", "reader", enabled=True))
        self.plan = DemoPlan(
            "display", "Display 1", (0, 0, 10, 10), "C:\\x", sources=tuple(sources)
        )
        self.state = "recording"
        self.mic_muted = False
        self.markers = SimpleNamespace(markers=[])
        self.marks = []

    def mark(self, label, failure=False):
        self.marks.append(label)
        self.markers.markers.append(label)
        return 62.0

    def set_microphone_muted(self, muted):
        if self.plan.source("microphone") is None:
            return False
        self.mic_muted = muted
        return True

    def status_line(self):
        return "Recording, 00:01:02."


def test_nothing_recording_is_said_plainly(parent):
    host = Host(parent)
    host.pause_demonstration()
    host.mark_demonstration()
    host.mute_demonstration()
    host.speak_demonstration_status()
    assert host.spoken == ["No demonstration is recording."] * 4


def test_marker_mute_and_status_are_spoken(parent):
    host = Host(parent)
    host._demo = FakeRecorder()
    host.mark_demonstration()
    host.mute_demonstration()
    host.speak_demonstration_status()
    assert host.spoken == [
        "Marker 1 at 1 minute 2 seconds.",
        "Microphone muted in the recording.",
        "Recording, 00:01:02.",
    ]
    assert host._demo.mic_muted


def test_while_reader_speech_is_recorded_only_failures_and_requests_speak(parent, monkeypatch):
    from quill.ui import sound_manager

    sounds = []
    monkeypatch.setattr(sound_manager, "post_sound", lambda event: sounds.append(event))
    host = Host(parent)
    host._demo = FakeRecorder(reader=True)
    host.mark_demonstration()
    host._demo_event("Microphone stopped: the device was disconnected.", True)
    host._demo_face("Your face left the camera view.")
    host.speak_demonstration_status()
    assert host.spoken == [
        "Microphone stopped: the device was disconnected.",
        "Recording, 00:01:02.",
    ]
    assert sounds == ["notification"]


def test_tray_offers_recording_controls_without_restoring(parent):
    host = Host(parent)
    host._menu_label = lambda label, _command: label
    host._keep_menu_ids = lambda *_ids: None
    menu = wx.Menu()
    host._append_demo_tray(menu)
    assert [i.GetItemLabelText() for i in menu.GetMenuItems() if not i.IsSeparator()] == [
        "Record a demonstration..."
    ]
    host._demo = FakeRecorder()
    menu = wx.Menu()
    host._append_demo_tray(menu)
    labels = [i.GetItemLabelText() for i in menu.GetMenuItems() if not i.IsSeparator()]
    assert labels[:2] == ["Stop and save the recording", "Pause recording"]


def test_recovery_notice_is_spoken_not_modal(parent, tmp_path, monkeypatch):
    import quill.apps.studio_demo_finish as studio_demo

    host = Host(parent)
    monkeypatch.setattr(host, "_demo_folders", lambda: [tmp_path])
    monkeypatch.setattr(studio_demo, "find_unfinished", lambda folders: [tmp_path / "x"])
    host._offer_demo_recovery()
    assert host.status == [
        "1 unfinished recording found. Use Capture, Recover unfinished recordings."
    ]


def test_microphone_lock_refusal_stops_the_start(parent, monkeypatch):
    from quill.core import dictation_owner

    class Lock:
        def __init__(self, *_a, **_k):
            pass

        def take(self):
            return "Quill Inkwell is dictating."

    monkeypatch.setattr(dictation_owner, "MicrophoneLock", Lock)
    host = Host(parent)
    plan = FakeRecorder().plan
    assert host._take_demo_microphone(plan) is False
    assert host.spoken == ["Quill Inkwell is dictating."]


def test_preferences_file_is_read_safely(parent, tmp_path, monkeypatch):
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    (Path(tmp_path) / "studio-demo-recording.json").write_text("[1, 2]", encoding="utf-8")
    assert Host(parent)._demo_preferences() == {}


def test_picture_video_window_builds_a_plan_with_markers(parent, tmp_path):
    from PIL import Image

    from quill.ui.studio_picture_video import PictureVideoDialog

    picture = tmp_path / "cover.png"
    Image.new("RGB", (20, 20)).save(picture)
    sound = tmp_path / "Show 4.m4a"
    sound.write_bytes(b"x")
    (tmp_path / "Show 4.markers.txt").write_text("00:00:30.0  Part two\n", encoding="utf-8")
    dialog = PictureVideoDialog(
        parent, choose_file=lambda *_a: None, picture=str(picture), sound=str(sound)
    )
    try:
        assert dialog.chapters.IsEnabled() and dialog.chapters.GetValue()
        assert dialog.title_field.GetValue() == "Show 4"
        dialog.wave.SetValue(True)
        dialog.shape.SetSelection(1)
        plan = dialog.build_plan()
        assert plan.output.name == "Show 4 - video.mp4" and plan.shape == "square" and plan.wave
        assert plan.chapters[0].title == "Part two"
    finally:
        dialog.Destroy()
