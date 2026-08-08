"""Shared fixtures for the UI unit tests.

KNOWN ISSUE -- window-handle leak (not yet fixed at the source). Windows caps
a process at 10,000 User (Window Manager) handles. Widget tests that create a
wx.Frame or wx.Dialog and let it fall out of scope leak the native HWND for
the life of the process: Python's garbage collector does not destroy a wx
window, only an explicit Destroy() does. A single-process run of this
directory exhausts the ceiling about three quarters of the way through and
collapses into a cascade of failures that look unrelated to their tests
("Failed to create dialog. Incorrect DLGTEMPLATE?", "can't append invalid
menu to menubar", "'NoneType' object has no attribute 'Enable'").

CI works around it by running this directory in its own xdist pool with more
workers than cores, so no single process gets close (see pr-ci.yml). An
autouse teardown that destroyed each test's leaked top-level windows was
tried on 2026-08-07 and made no measurable difference to the failure count,
so the leak is not (only) un-destroyed top-level windows -- diagnosing it
properly means instrumenting GetGuiResources per test. Until then, run this
directory with -n to reproduce CI locally; a bare single-process
`pytest tests/unit/ui` is expected to fail late.

The one fixture here exists because of a wxPython 4.3 (wxWidgets 3.3)
interaction: constructing a REAL ``wx.media.MediaCtrl`` with the WMP10
ActiveX backend deep into a long single-process test run access-violates on
COM state some earlier test leaves behind (it works in isolation and in the
real app, which creates it once at startup — verified by launch check). No
unit test actually plays audio: every radio/player test either injects its
own fake engine or only exercises controller logic, so the real ActiveX
control is never load-bearing here.
"""

from __future__ import annotations

import pytest


class _StubWxMediaEngine:
    """Protocol-complete stand-in for quill.ui.audio.audio_engine.WxMediaEngine."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.loads: list[str] = []
        self.closed = False

    def load(self, source: str) -> bool:
        self.loads.append(source)
        return True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    def seek_ms(self, position: int) -> None:
        pass

    def position_ms(self) -> int:
        return 0

    def length_ms(self) -> int:
        return 0

    def is_playing(self) -> bool:
        return False

    def set_volume(self, percent: int) -> None:
        pass

    def set_rate(self, rate: float) -> None:
        pass

    def set_audio_device(self, name: str) -> None:
        pass


@pytest.fixture(autouse=True)
def _no_real_wmp10_media_ctrl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace WxMediaEngine with a stub wherever controllers construct one."""
    for module_name in (
        "quill.ui.radio.player_controller",
        "quill.ui.audio.audio_engine",
    ):
        try:
            module = __import__(module_name, fromlist=["WxMediaEngine"])
        except Exception:  # noqa: BLE001 - optional module missing is fine
            continue
        if hasattr(module, "WxMediaEngine"):
            monkeypatch.setattr(module, "WxMediaEngine", _StubWxMediaEngine)
