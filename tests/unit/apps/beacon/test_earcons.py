"""QuillBeacon's two earcons reach a sound sink (#1302).

Beacon is not an ``AppShellFrame``: it builds its own announcement service, so
until now it had Speech, Braille and Visual sinks and nowhere for a cue to
land. These tests pin both halves -- the service really installs a
``SoundSink``, and ``say(..., sound=...)`` carries the event through to it --
without any audio hardware or a wx frame.
"""

from __future__ import annotations

from typing import Any

from quill.apps.beacon.announce import Announcer
from quill.core.announce.message import Channel
from quill.core.sound_events import SoundEvent


class _Frame:
    """The two methods Announcer touches on its frame, plus a fake engine."""

    def __init__(self) -> None:
        self.status: list[str] = []
        self._announcement_engine = _Engine()

    def GetStatusBar(self) -> Any:  # noqa: N802 - wx naming
        return object()

    def SetStatusText(self, text: str) -> None:  # noqa: N802 - wx naming
        self.status.append(text)


class _Engine:
    def announce(self, _text: str, *, force_speech: bool = False) -> None: ...


def _announcer(cues: list[str]) -> Announcer:
    announcer = Announcer(_Frame())
    service = announcer._service()
    sinks = [s for s in service._sinks if s.channel is Channel.SOUND]
    assert sinks, "Beacon's service must install a SoundSink"
    sinks[0]._play = cues.append
    sinks[0]._is_enabled = None
    return announcer


def test_the_service_installs_a_sound_sink_first() -> None:
    announcer = Announcer(_Frame())
    channels = [sink.channel for sink in announcer._service()._sinks]
    assert channels[0] is Channel.SOUND


def test_a_capture_carries_the_captured_cue() -> None:
    cues: list[str] = []
    announcer = _announcer(cues)
    announcer.say("Captured: A Good Page", "normal", sound=SoundEvent.BEACON_CAPTURED)
    assert cues == [SoundEvent.BEACON_CAPTURED]


def test_a_finished_sync_carries_the_sync_complete_cue() -> None:
    cues: list[str] = []
    announcer = _announcer(cues)
    announcer.say("Synced. Pushed 2, pulled 1.", sound=SoundEvent.BEACON_SYNC_COMPLETE)
    assert cues == [SoundEvent.BEACON_SYNC_COMPLETE]


def test_an_ordinary_announcement_makes_no_sound() -> None:
    cues: list[str] = []
    announcer = _announcer(cues)
    announcer.say("12 results")
    assert cues == []


def test_a_message_the_verbosity_suppresses_makes_no_sound() -> None:
    cues: list[str] = []
    announcer = _announcer(cues)
    announcer.set_verbosity("minimal")
    announcer.say("Captured: A Good Page", "verbose", sound=SoundEvent.BEACON_CAPTURED)
    assert cues == []
