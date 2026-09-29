"""Choosing a sound card is a family capability, not Quill Radio's alone.

Quill Radio has been able to send its audio to a chosen device since #1253,
because it can play through libmpv, which has an ``audio-device`` property.
Every other QuillVille app played through ``wx.media``, which has no device API
at all, so ``ui/media/output_device`` answered them with a sentence and a link
to Windows' own per-app Sound settings -- an honest answer, and the only one
available at the time.

The modern Windows Media engine (``Windows.Media.Playback.MediaPlayer``, 3.0.5)
can be pointed at a device, and the general libmpv engine gained the same call
in the same release. So the sentence stopped being true: the engines these apps
play through CAN route now, and the only thing still missing was each app
saying which engine and which setting are its own.

That is what ``OutputDeviceBinding`` is. These tests pin down the three things
that make it safe to hand one picker to every app:

* the engine is asked of the app, not guessed from the machine -- a computer
  with libmpv installed can still be playing on the classic control;
* a device the engine will not open is NOT saved, because a setting naming a
  device you cannot hear is the exact split this area exists to close;
* the redirect to Windows survives for the one case where it is still the
  truth -- an engine with no device API.
"""

from __future__ import annotations

import pytest

from quill.ui.audio.output_routing import (
    engine_routes_devices,
    set_engine_output_device,
)
from quill.ui.media.output_device import OutputDeviceBinding


class _RoutingEngine:
    """An engine that can be pointed at a device (mpv, or modern Windows Media)."""

    def __init__(self, *, refuses: str = "") -> None:
        self._device = ""
        self._refuses = refuses
        self.calls: list[str] = []

    def set_audio_device(self, name: str) -> None:
        self.calls.append(name)
        if name and name == self._refuses:
            return  # refused: the previous device keeps playing
        self._device = name.strip()

    def audio_device(self) -> str:
        return self._device


class _ClassicEngine:
    """The classic wx.media control: no device API at all."""


class _RaisingEngine:
    def set_audio_device(self, name: str) -> None:
        raise RuntimeError("the engine went away mid-call")


# -- which engines can route -------------------------------------------------


def test_an_engine_that_takes_a_device_says_so() -> None:
    assert engine_routes_devices(_RoutingEngine()) is True


def test_the_classic_control_says_it_cannot() -> None:
    """The one case where the Windows-settings redirect is still the truth."""
    assert engine_routes_devices(_ClassicEngine()) is False


def test_no_engine_at_all_cannot_route() -> None:
    assert engine_routes_devices(None) is False


# -- setting the device ------------------------------------------------------


def test_a_device_the_engine_takes_reports_success() -> None:
    engine = _RoutingEngine()
    assert set_engine_output_device(engine, "wasapi/{aaa}") is True
    assert engine.audio_device() == "wasapi/{aaa}"


def test_a_device_the_engine_refuses_reports_failure() -> None:
    """A headset asleep, a card another program holds, an id Windows changed.

    The readback is what catches it: the engine keeps the previous device and
    says nothing, so only comparing what it reports against what was asked can
    tell the caller the choice did not take.
    """
    engine = _RoutingEngine(refuses="wasapi/{gone}")
    assert set_engine_output_device(engine, "wasapi/{gone}") is False
    assert engine.audio_device() == ""


def test_an_engine_with_no_device_api_reports_failure() -> None:
    assert set_engine_output_device(_ClassicEngine(), "wasapi/{aaa}") is False


def test_an_engine_that_raises_never_reaches_the_caller() -> None:
    # An engine mid-teardown must cost the command, not the app.
    assert set_engine_output_device(_RaisingEngine(), "wasapi/{aaa}") is False


def test_the_system_default_is_a_device_like_any_other() -> None:
    engine = _RoutingEngine()
    engine.set_audio_device("wasapi/{aaa}")
    assert set_engine_output_device(engine, "") is True
    assert engine.audio_device() == ""


# -- the binding an app hands over -------------------------------------------


def test_a_binding_carries_the_four_things_the_picker_needs() -> None:
    saved: list[str] = []
    engine = _RoutingEngine()
    binding = OutputDeviceBinding(
        app_name="QUILL Cast",
        engine=engine,
        current="wasapi/{aaa}",
        save=saved.append,
    )
    assert binding.app_name == "QUILL Cast"
    assert binding.engine is engine
    assert binding.current == "wasapi/{aaa}"
    binding.save("wasapi/{bbb}")
    assert saved == ["wasapi/{bbb}"]


# -- how choose_output_device routes an app ----------------------------------


class _Host:
    """An app host: the shape ``choose_output_device`` actually asks about."""

    def __init__(self, binding: object | None) -> None:
        self._binding = binding
        self.announced: list[str] = []
        self.frame = object()

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def audio_output_binding(self) -> object | None:
        return self._binding


def _route(host: object, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Run ``choose_output_device`` with the picker stubbed out.

    The Windows-settings fallback is stubbed too, and answers No: an app that
    has not opted in still reaches that branch, and it is the branch under test
    in the negative cases -- reaching it IS the correct behaviour there.
    """
    import wx

    import quill.ui.dialog_contract as dialog_contract
    import quill.ui.media.output_device as module

    seen: dict = {}

    def _pick(parent, **kwargs):
        seen.update(kwargs)
        seen["parent"] = parent

    monkeypatch.setattr(module, "pick_output_device", _pick)
    monkeypatch.setattr(dialog_contract, "show_message_box", lambda *a, **k: wx.NO)
    module.choose_output_device(host)
    return seen


def test_an_app_that_opted_in_gets_the_real_picker(monkeypatch) -> None:
    engine = _RoutingEngine()
    host = _Host(
        OutputDeviceBinding(
            app_name="QUILL Cast", engine=engine, current="wasapi/{aaa}", save=lambda _d: None
        )
    )
    seen = _route(host, monkeypatch)
    assert seen["app_name"] == "QUILL Cast"
    assert seen["engine"] is engine
    assert seen["current"] == "wasapi/{aaa}"
    assert seen["parent"] is host.frame


def test_an_app_whose_engine_is_not_up_yet_does_not_get_a_picker(monkeypatch) -> None:
    """Returning None is how an app says "not now" without costing the command."""
    seen = _route(_Host(None), monkeypatch)
    assert seen == {}


def test_a_binding_that_raises_is_not_a_picker(monkeypatch) -> None:
    class _Raising(_Host):
        def audio_output_binding(self) -> object | None:
            raise RuntimeError("controller is gone")

    seen = _route(_Raising(None), monkeypatch)
    assert seen == {}


def test_something_that_is_not_a_binding_is_ignored(monkeypatch) -> None:
    # A host that returns the wrong shape must not reach the picker with it.
    seen = _route(_Host({"app_name": "Wrong"}), monkeypatch)
    assert seen == {}


# -- the device list is cached, because asking is expensive ------------------


def test_the_device_list_is_not_enumerated_twice_in_a_row(monkeypatch) -> None:
    """Opening Preferences twice must not pay for two enumerations.

    Through libmpv an enumeration builds and tears down a handle on a 115 MB
    DLL -- about 2.5 seconds cold -- and every picker and Preferences window
    paid it again.
    """
    import quill.ui.audio.output_routing as routing

    calls = []
    monkeypatch.setattr(routing, "_cached", None)
    monkeypatch.setattr(
        routing,
        "_enumerate_output_devices",
        lambda: (calls.append(1), [("wasapi/{aaa}", "Speakers")])[1],
    )
    assert routing.list_output_devices() == [("wasapi/{aaa}", "Speakers")]
    assert routing.list_output_devices() == [("wasapi/{aaa}", "Speakers")]
    assert len(calls) == 1


def test_an_empty_answer_is_never_cached(monkeypatch) -> None:
    """[] is the shape a failed or timed-out query takes.

    Caching it would turn one bad moment into twenty seconds of "no devices" --
    which is exactly the symptom the WinRT timeout used to produce.
    """
    import quill.ui.audio.output_routing as routing

    calls = []
    monkeypatch.setattr(routing, "_cached", None)
    monkeypatch.setattr(routing, "_enumerate_output_devices", lambda: (calls.append(1), [])[1])
    assert routing.list_output_devices() == []
    assert routing.list_output_devices() == []
    assert len(calls) == 2, "an empty list must be retried, not remembered"


def test_forgetting_makes_the_next_ask_real(monkeypatch) -> None:
    """For when the hardware really may have changed: a headset just plugged in."""
    import quill.ui.audio.output_routing as routing

    calls = []
    monkeypatch.setattr(routing, "_cached", None)
    monkeypatch.setattr(
        routing,
        "_enumerate_output_devices",
        lambda: (calls.append(1), [("wasapi/{aaa}", "Speakers")])[1],
    )
    routing.list_output_devices()
    routing.forget_output_devices()
    routing.list_output_devices()
    assert len(calls) == 2


def test_the_caller_cannot_mutate_the_cache(monkeypatch) -> None:
    """A caller that sorts or filters the list in place must not poison it."""
    import quill.ui.audio.output_routing as routing

    monkeypatch.setattr(routing, "_cached", None)
    monkeypatch.setattr(
        routing, "_enumerate_output_devices", lambda: [("wasapi/{aaa}", "Speakers")]
    )
    first = routing.list_output_devices()
    first.clear()
    assert routing.list_output_devices() == [("wasapi/{aaa}", "Speakers")]


# -- what an engine can do, and why unknown means yes ------------------------


def test_an_engine_that_cannot_answer_keeps_its_controls() -> None:
    """The direction that matters.

    libmpv and the classic control cannot be asked whether a source can be
    seeked or paused. Defaulting to "no" would disable working controls and
    tell a listener the capability does not exist -- worse than leaving a
    rarely-unavailable one enabled. Only a real refusal ever takes one away.
    """
    from quill.ui.audio.audio_engine import engine_can_pause, engine_can_seek

    class _CannotSay:
        pass

    assert engine_can_seek(_CannotSay()) is True
    assert engine_can_pause(_CannotSay()) is True


def test_an_engine_that_says_no_is_believed() -> None:
    from quill.ui.audio.audio_engine import engine_can_pause, engine_can_seek

    class _LiveStream:
        def can_seek(self) -> bool:
            return False

        def can_pause(self) -> bool:
            return False

    assert engine_can_seek(_LiveStream()) is False
    assert engine_can_pause(_LiveStream()) is False


def test_an_engine_that_raises_keeps_its_controls() -> None:
    from quill.ui.audio.audio_engine import engine_can_seek

    class _Dying:
        def can_seek(self) -> bool:
            raise RuntimeError("engine is gone")

    assert engine_can_seek(_Dying()) is True


def test_buffering_progress_reads_as_ready_when_unknown() -> None:
    from quill.ui.audio.audio_engine import engine_buffering_progress

    class _CannotSay:
        pass

    class _HalfFull:
        def buffering_progress(self) -> float:
            return 0.5

    assert engine_buffering_progress(_CannotSay()) == 1.0
    assert engine_buffering_progress(_HalfFull()) == 0.5


def test_buffering_progress_is_clamped() -> None:
    from quill.ui.audio.audio_engine import engine_buffering_progress

    class _Nonsense:
        def buffering_progress(self) -> float:
            return 7.5

    assert engine_buffering_progress(_Nonsense()) == 1.0
