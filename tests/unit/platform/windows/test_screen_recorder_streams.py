"""One stream's failure never ends the others (REC-024).

The recorder's monitor is driven by hand over fake FFmpeg processes and fake
sound sources, so no screen, camera or device is opened. The acceptance is
the PRD's own: killing the camera's FFmpeg leaves the screen and every sound
source recording, and the failure is held against the camera by name.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.demo_recording import CameraSetup, DemoPlan, SoundSource
from quill.core.demo_recording_ffmpeg import Capabilities
from quill.platform.windows import screen_recorder


class FakeProcess:
    instances: list[FakeProcess] = []

    def __init__(self, command, **_kwargs):
        self.command = command
        self.alive = False
        self.stopping = False
        self.tail: list[str] = []
        self.returncode = None
        self.last_stats = None
        self.launched = 1000.0
        self.start = SimpleNamespace(start=1000.0)
        FakeProcess.instances.append(self)

    @property
    def running(self) -> bool:
        return self.alive

    def launch(self) -> None:
        self.alive = True

    def die(self, line: str) -> None:
        self.alive = False
        self.returncode = 1
        self.tail = [line]

    def stop(self, timeout: float = 10.0):
        self.stopping = True
        self.alive = False
        return 0

    def kill(self) -> None:
        self.alive = False


class FakeSource:
    def __init__(self, source, on_event, *, studio_pid):
        self.source = source
        self.label = source.label
        self.on_event = on_event
        self.recording = False
        self.closed = False

    def open(self):
        return ""

    def begin_segment(self, _path):
        self.recording = True

    def end_segment(self, _stop_at):
        self.recording = False
        return None

    def close(self):
        self.closed = True
        self.recording = False


@pytest.fixture
def recorder_for(tmp_path, monkeypatch):
    FakeProcess.instances = []
    monkeypatch.setattr(screen_recorder, "FFmpegProcess", FakeProcess)
    monkeypatch.setattr(screen_recorder, "make_source", FakeSource)
    monkeypatch.setattr(screen_recorder, "choose_backend", lambda plan, caps: (plan, "gdigrab"))
    monkeypatch.setattr(screen_recorder, "free_bytes", lambda _folder: -1)
    monkeypatch.setattr(screen_recorder.DemoRecorder, "_displays_unchanged", lambda self: True)

    def build(*, sound: bool = True, camera: bool = True):
        plan = DemoPlan(
            target_kind="display",
            target_label="Display 1",
            bounds=(0, 0, 1280, 720),
            display_bounds=(0, 0, 1280, 720),
            folder=str(tmp_path),
            sources=(SoundSource("application", "Tone", "app-tone", enabled=sound),),
            camera=CameraSetup(enabled=camera, device="Cam", face_alerts=False),
        )
        events: list[tuple[str, bool]] = []
        recorder = screen_recorder.DemoRecorder(
            plan,
            ffmpeg="ffmpeg",
            caps=Capabilities(),
            on_event=lambda text, failure: events.append((text, failure)),
        )
        stops: list[str] = []
        recorder.auto_stop = stops.append
        with recorder._lock:
            recorder._start_segment()
            recorder.state = "recording"
        return recorder, events, stops

    return build


def test_killing_the_camera_leaves_the_screen_and_sound_recording(recorder_for):
    recorder, events, stops = recorder_for()
    screen, camera = recorder._screen, recorder._camera
    camera.die("Could not read frame")
    recorder._check_once()
    recorder._check_once()  # said once, not every second
    assert stops == [] and recorder.stop_reason == ""
    assert screen.running and all(source.recording for source in recorder.sources)
    assert recorder.session.stream_failures == {
        "Camera": "Camera capture stopped: Could not read frame. The rest is still recording."
    }
    assert [text for text, failure in events if failure] == [
        "Camera capture stopped: Could not read frame. The rest is still recording."
    ]


def test_a_dead_screen_does_not_stop_the_sound(recorder_for):
    recorder, _events, stops = recorder_for(camera=False)
    recorder._screen.die("ddagrab: device lost")
    recorder._check_once()
    assert stops == []
    assert "Screen" in recorder.session.stream_failures
    assert all(source.recording for source in recorder.sources)


def test_the_last_stream_standing_stops_the_recording(recorder_for):
    recorder, _events, stops = recorder_for(sound=False, camera=False)
    recorder._screen.die("disk full")
    recorder._check_once()
    assert stops == ["Screen capture stopped unexpectedly: disk full"]
    assert recorder.session.stream_failures["Screen"].startswith("Screen capture stopped")


def test_a_sound_source_failure_is_held_against_that_source(recorder_for):
    recorder, events, _stops = recorder_for(camera=False)
    source = recorder.sources[0]
    source.on_event("Tone stopped delivering sound.", True)
    source.on_event("Tone reconnected and recording.", False)
    assert recorder.session.stream_failures == {"Tone": "Tone stopped delivering sound."}
    assert recorder._screen.running
    assert events[-1] == ("Tone reconnected and recording.", False)


def test_a_camera_that_cannot_start_does_not_stop_the_screen(recorder_for, monkeypatch):
    def refuse(self):
        if "dshow" in self.command:
            raise OSError("device busy")
        self.alive = True

    monkeypatch.setattr(FakeProcess, "launch", refuse)
    recorder, _events, stops = recorder_for()
    assert recorder._camera is None and recorder._screen.running
    assert recorder.session.stream_failures["Camera"] == "The camera could not start: device busy."
    assert stops == []


def test_a_stream_that_failed_does_not_shorten_the_segment(recorder_for, monkeypatch):
    recorder, _events, _stops = recorder_for(camera=False)
    recorder._screen.last_stats = SimpleNamespace(seconds=2.0, frames=60, dropped=0)
    recorder._screen.die("lost")
    recorder._check_once()
    monkeypatch.setattr(screen_recorder.time, "time", lambda: 1010.0)
    with recorder._lock:
        recorder._close_segment()
    assert recorder.session.segments[0].duration == pytest.approx(10.0)
