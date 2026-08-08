"""Shared fixtures for the UI unit tests.

The window-handle exhaustion that used to make a single-process run of this
directory collapse three quarters of the way through is FIXED -- see
``_reclaim_leaked_wx_windows`` in ``tests/conftest.py``. A bare
``pytest tests/unit/ui`` passes again (2609 tests, handles peaking at 523
against the 10,000 ceiling).

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
