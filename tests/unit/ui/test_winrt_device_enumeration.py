"""Asking Windows for sound cards must ask for sound cards.

Reported 2026-09-29: "why is it taking two seconds or longer to bring up
preferences in quill radio?"

Because the device list behind that window swept every device on the machine.
The 3.x PyWinRT projection exposed the audio-render overload under the generated
name ``find_all_async_device_class``. PyWinRT 4.0 removes those aliases and
unifies the overloads as ``find_all_async(DeviceClass.AUDIO_RENDER)``. On the
reporter's machine the unfiltered sweep returned **4,048 devices in 2.4
seconds**, against **2 devices in 8 milliseconds** for the filtered query.
Preferences ran it on the UI thread every time it opened, and the family list
ran it twice and hit its own five-second timeout.

So the rule these tests hold: ask for the audio endpoints when the runtime can
be asked, and only sweep when it genuinely cannot. A projection without the
filtered overload should be slow, not broken.
"""

from __future__ import annotations

import gc
import weakref

import pytest

from quill.ui.audio import winrt_engine


class _Device:
    """Enough of ``DeviceInformation`` for the filter and the id parsing."""

    def __init__(self, ident: str, name: str, *, enabled: bool = True) -> None:
        self.id = ident
        self.name = name
        self.is_enabled = enabled


_RENDER = winrt_engine._RENDER_CLASS


def _endpoint(guid: str, name: str, *, enabled: bool = True) -> _Device:
    ident = rf"\\?\SWD#MMDEVAPI#{{0.0.0.00000000}}.{{{guid}}}#{_RENDER}"
    return _Device(ident, name, enabled=enabled)


@pytest.fixture
def statics(monkeypatch):
    """A stand-in ``DeviceInformation`` that records which route was taken."""

    class _Statics:
        def __init__(self) -> None:
            self.by_class_calls = 0
            self.sweep_calls = 0
            self.by_class_available = True
            self.audio_render = object()
            self.by_class_argument = None
            self.devices = [
                _endpoint("aaaaaaaa-0000-0000-0000-000000000001", "Speakers (Realtek)"),
                _endpoint("bbbbbbbb-0000-0000-0000-000000000002", "Speakers (Logi USB Headset)"),
            ]

        def find_all_async(self, *args):
            if args:
                self.by_class_calls += 1
                self.by_class_argument = args[0]
                if not self.by_class_available:
                    raise TypeError("Invalid parameter count")
                return ("by_class", self.devices)
            self.sweep_calls += 1
            # The sweep returns the whole machine; only two are sound cards.
            noise = [_Device(rf"\\?\USB#VID_046D#{i}", f"Some USB thing {i}") for i in range(50)]
            return ("sweep", noise + self.devices)

    fake = _Statics()

    class _DeviceClass:
        pass

    _DeviceClass.AUDIO_RENDER = fake.audio_render

    class _Module:
        DeviceInformation = fake
        DeviceClass = _DeviceClass

    import sys

    monkeypatch.setitem(sys.modules, "winrt.windows.devices.enumeration", _Module)
    monkeypatch.setattr(winrt_engine, "_wait", lambda op, timeout=5.0: op[1])
    monkeypatch.setattr(winrt_engine, "winrt_media_available", lambda: True)
    return fake


def test_the_audio_endpoints_are_asked_for_by_class(statics) -> None:
    """The whole fix: ask for sound cards, do not sweep the machine."""
    devices = winrt_engine.list_audio_devices()
    assert statics.by_class_calls == 1
    assert statics.by_class_argument is statics.audio_render
    assert statics.sweep_calls == 0, "the machine-wide sweep is what took two seconds"
    assert len(devices) == 2


def test_the_names_come_back_in_the_shared_mpv_spelling(statics) -> None:
    """One naming for every engine, so a device saved under one is honoured by
    the others (quill/ui/audio/output_routing)."""
    names = [name for name, _desc in winrt_engine.list_audio_devices()]
    assert names == [
        "wasapi/{aaaaaaaa-0000-0000-0000-000000000001}",
        "wasapi/{bbbbbbbb-0000-0000-0000-000000000002}",
    ]


def test_a_runtime_without_the_named_overload_still_answers(statics) -> None:
    """Slow, not broken: the sweep is the floor, not the plan."""
    statics.by_class_available = False
    devices = winrt_engine.list_audio_devices()
    assert statics.sweep_calls == 1
    assert len(devices) == 2, "the sweep must still find the sound cards among the noise"


def test_a_disabled_endpoint_is_not_offered(statics) -> None:
    statics.devices.append(
        _endpoint("cccccccc-0000-0000-0000-000000000003", "Unplugged thing", enabled=False)
    )
    assert len(winrt_engine.list_audio_devices()) == 2


def test_a_query_that_times_out_is_an_empty_list_not_a_crash(statics, monkeypatch) -> None:
    """Preferences must open even when Windows will not answer."""

    def _timeout(_op, timeout=5.0):
        raise TimeoutError("the Windows device query did not complete")

    monkeypatch.setattr(winrt_engine, "_wait", _timeout)
    assert winrt_engine.list_audio_devices() == []


def test_no_engine_means_no_query_at_all(monkeypatch) -> None:
    monkeypatch.setattr(winrt_engine, "winrt_media_available", lambda: False)
    assert winrt_engine.list_audio_devices() == []


def test_listing_does_not_keep_native_device_proxies_alive(monkeypatch) -> None:
    """DeviceInformation COM proxies must not survive until interpreter exit.

    Holding them in a module cache caused Windows to exit with 0xC0000005
    while Python was tearing down the WinRT projections.
    """
    device = _endpoint("aaaaaaaa-0000-0000-0000-000000000001", "Speakers")
    device_ref = weakref.ref(device)
    pending = [device]
    monkeypatch.setattr(winrt_engine, "_find_audio_endpoints", lambda: [pending.pop()])
    monkeypatch.setattr(winrt_engine, "winrt_media_available", lambda: True)

    assert winrt_engine.list_audio_devices() == [
        ("wasapi/{aaaaaaaa-0000-0000-0000-000000000001}", "Speakers")
    ]
    del device
    gc.collect()
    assert device_ref() is None
