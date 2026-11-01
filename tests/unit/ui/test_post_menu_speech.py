"""UX-013: a menu command's outcome is spoken after the menu has closed.

The screen reader says where focus landed as a menu closes; a sentence
spoken at the same moment is cut off by it. These drive the shared
:class:`PostMenuSpeech` on a fake clock and timer, then the Studio commands
that start and stop things, through the same host the demonstration tests use.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from quill.ui.post_menu_speech import SETTLE_MS, STUCK_OPEN_S, PostMenuSpeech


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class Timers:
    def __init__(self) -> None:
        self.armed: list[tuple[int, object]] = []

    def schedule(self, wait, flush):
        timer = SimpleNamespace(wait=wait, flush=flush, IsRunning=lambda: False)
        self.armed.append((wait, flush))
        return timer

    def fire(self, clock: Clock) -> None:
        wait, flush = self.armed.pop(0)
        clock.now += wait / 1000
        flush()


def _speech():
    clock, timers = Clock(), Timers()
    return PostMenuSpeech(clock=clock, schedule=timers.schedule), clock, timers


def test_with_no_menu_a_sentence_is_spoken_at_once():
    speech, _clock, timers = _speech()
    said = []
    assert speech.say(lambda: said.append("Recording started.")) is False
    assert said == ["Recording started."] and timers.armed == []


def test_just_after_a_menu_closes_the_sentence_waits_for_focus_to_settle():
    speech, clock, timers = _speech()
    said = []
    speech.menu_opened()
    speech.menu_closed()
    clock.now += 0.05  # the command runs a moment after the menu closes
    assert speech.say(lambda: said.append("Recording started.")) is True
    assert speech.say(lambda: said.append("On air.")) is True
    assert said == [] and timers.armed[0][0] == SETTLE_MS - 50
    timers.fire(clock)
    assert said == ["Recording started.", "On air."]  # in order, nothing lost


def test_a_command_raised_while_the_menu_is_still_open_waits_for_it_to_close():
    speech, clock, timers = _speech()
    said = []
    speech.menu_opened()
    speech.say(lambda: said.append("Recording paused."))
    timers.fire(clock)  # still open: holds and re-arms
    assert said == [] and timers.armed
    speech.menu_closed()
    timers.fire(clock)  # the re-armed wait counts from the close
    assert said == ["Recording paused."] and timers.armed == []


def test_a_lost_close_event_never_holds_speech_for_ever():
    speech, clock, _timers = _speech()
    speech.menu_opened()
    clock.now += STUCK_OPEN_S + 1
    said = []
    assert speech.say(lambda: said.append("Broadcast ended.")) is False
    assert said == ["Broadcast ended."]


def test_watching_a_real_menu_follows_its_open_and_close_events(wx_session_app):
    speech, clock, _timers = _speech()
    menu = wx.Menu()
    speech.watch(menu)
    menu.ProcessEvent(wx.MenuEvent(wx.wxEVT_MENU_OPEN, 0, menu))
    assert speech.wait_ms() == SETTLE_MS
    menu.ProcessEvent(wx.MenuEvent(wx.wxEVT_MENU_CLOSE, 0, menu))
    clock.now += SETTLE_MS / 1000
    assert speech.wait_ms() == 0


# -- Studio's start and stop sentences ------------------------------------------------


@pytest.fixture
def parent(wx_session_app):
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()


class _Tasks:
    def __init__(self):
        self.jobs = []

    def submit(self, name, work, **kwargs):
        self.jobs.append((name, work, kwargs))


def _recorder():
    from quill.core.demo_recording import DemoPlan, SoundSource

    plan = DemoPlan(
        "display",
        "Display 1",
        (0, 0, 10, 10),
        "C:\\x",
        sources=(SoundSource("microphone", "Microphone", "microphone", enabled=True),),
    )
    recorder = SimpleNamespace(plan=plan, mic_muted=False, marks=[])
    recorder.set_microphone_muted = lambda muted: setattr(recorder, "mic_muted", muted) or True
    return recorder


def _host(parent):
    from quill.apps.studio_capture import StudioCaptureMixin
    from quill.stability.task_manager import UiLifetimeToken

    class Host(StudioCaptureMixin):
        def __init__(self):
            self.frame = parent
            self.spoken, self.status = [], []
            self._task_manager = _Tasks()
            self._capture_lifetime = UiLifetimeToken()
            self._protected_background_jobs = {}

        def _announce(self, text):
            self.spoken.append(text)

        def _set_status_quiet(self, text):
            self.status.append(text)

    host = Host()
    speech, clock, timers = _speech()
    host._post_menu_speech = speech
    return host, speech, clock, timers, _recorder


def test_studio_holds_a_menu_commands_sentence_but_shows_it_at_once(parent):
    host, speech, clock, timers, recorder = _host(parent)
    host._demo = recorder()
    speech.menu_opened()
    speech.menu_closed()
    host.mute_demonstration()
    assert host.spoken == []
    assert host.status[-1] == "Microphone muted in the recording."  # the eye is not kept waiting
    timers.fire(clock)
    assert host.spoken == ["Microphone muted in the recording."]


def test_broadcast_end_is_state_first_and_never_reads_the_path(parent):
    host, _speech_, _clock, _timers, _recorder = _host(parent)
    archive = "C:\\Users\\me\\Music\\Studio broadcasts\\show 2026-10-31 20-00.flac"
    stream = SimpleNamespace(archive_path=archive, stop=lambda: None)
    host._live = stream
    host._release_demo_microphone = lambda _lock: None
    host._demo_quiet_stop = lambda: None
    host.stop_broadcast()
    _name, work, kwargs = host._task_manager.jobs[-1]
    work()
    kwargs["on_success"](None, None)
    assert host.spoken == ["Broadcast ended. A copy was saved."]
    assert host.status[-1] == f"Broadcast ended. Saved copy: {archive}"


def test_stopping_a_recording_says_the_state_first(parent):
    host, _speech_, _clock, _timers, recorder = _host(parent)
    host._demo = recorder()
    host._demo_cleanup = lambda _recorder: None
    host.stop_demonstration()
    assert host.spoken == ["Recording stopped. Saving and checking it."]
