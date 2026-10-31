"""quill.ui.dpi and quill.platform.windows.dpi_awareness (#1702)."""

from __future__ import annotations

import ctypes
import sys

import pytest

from quill.platform.windows import dpi_awareness
from quill.ui import dpi


class _Window:
    def __init__(self, factor: float) -> None:
        self._factor = factor

    def GetDPIScaleFactor(self) -> float:  # noqa: N802 - wx's name
        return self._factor


class _DeadWindow:
    def GetDPIScaleFactor(self) -> float:  # noqa: N802 - wx's name
        raise RuntimeError("wrapped C/C++ object has been deleted")


def test_dip_scales_by_the_windows_factor() -> None:
    assert dpi.dip(_Window(1.5), 100) == 150
    assert dpi.dip(_Window(2.0), 333) == 666


def test_dip_is_identical_at_100_percent() -> None:
    for value in (1, 7, 120, 720):
        assert dpi.dip(_Window(1.0), value) == value


def test_dip_size_preserves_default_coord() -> None:
    size = dpi.dip_size(_Window(2.0), -1, 200)
    assert (size.width, size.height) == (-1, 400)


def test_dip_size_returns_a_wx_size() -> None:
    import wx

    size = dpi.dip_size(_Window(1.25), 720, 580)
    assert isinstance(size, wx.Size)
    assert (size.width, size.height) == (900, 725)


def test_no_app_and_no_window_means_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    import wx

    monkeypatch.setattr(wx, "GetApp", lambda: None)
    assert dpi.scale_factor(None) == 1.0
    assert dpi.dip(None, 640) == 640


def test_a_dead_or_foreign_window_falls_back_to_the_display(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wx

    monkeypatch.setattr(wx, "GetApp", lambda: None)
    assert dpi.dip(_DeadWindow(), 50) == 50
    assert dpi.dip(object(), 50) == 50
    assert dpi.dip("not a window", 50) == 50


def test_display_factor_is_used_with_an_app(wx_session_app: object) -> None:
    import wx

    expected = wx.Display(0).GetScaleFactor()
    assert dpi.scale_factor(None) == pytest.approx(expected)


class _Fn:
    def __init__(self, result: object = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[object, ...]] = []

    def __call__(self, *args: object) -> object:
        self.calls.append(args)
        if self.error is not None:
            raise self.error
        return self.result


class _Lib:
    def __init__(self, **functions: _Fn) -> None:
        for name, fn in functions.items():
            setattr(self, name, fn)


class _WinDLL:
    def __init__(self, user32: _Lib, shcore: _Lib) -> None:
        self.user32 = user32
        self.shcore = shcore


@pytest.fixture
def fresh(monkeypatch: pytest.MonkeyPatch):
    dpi_awareness._reset_for_tests()
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("QUILL_DPI_UNAWARE", raising=False)
    yield monkeypatch
    dpi_awareness._reset_for_tests()


def _install(monkeypatch: pytest.MonkeyPatch, windll: _WinDLL) -> None:
    monkeypatch.setattr(ctypes, "windll", windll, raising=False)


def test_per_monitor_v2_is_tried_first(fresh: pytest.MonkeyPatch) -> None:
    context = _Fn(result=1)
    legacy = _Fn(result=0)
    _install(
        fresh,
        _WinDLL(_Lib(SetProcessDpiAwarenessContext=context), _Lib(SetProcessDpiAwareness=legacy)),
    )
    assert dpi_awareness.enable_dpi_awareness() == "per-monitor-v2"
    assert len(context.calls) == 1
    assert context.calls[0][0].value == ctypes.c_void_p(-4).value  # PER_MONITOR_AWARE_V2
    assert legacy.calls == []


def test_falls_back_to_shcore_per_monitor(fresh: pytest.MonkeyPatch) -> None:
    legacy = _Fn(result=0)
    _install(
        fresh,
        _WinDLL(
            _Lib(SetProcessDpiAwarenessContext=_Fn(result=0)), _Lib(SetProcessDpiAwareness=legacy)
        ),
    )
    assert dpi_awareness.enable_dpi_awareness() == "per-monitor"
    assert legacy.calls == [(2,)]


def test_falls_back_to_system_aware_on_old_windows(fresh: pytest.MonkeyPatch) -> None:
    aware = _Fn(result=1)
    _install(fresh, _WinDLL(_Lib(SetProcessDPIAware=aware), _Lib()))
    assert dpi_awareness.enable_dpi_awareness() == "system"
    assert aware.calls == [()]


def test_every_failure_is_tolerated(fresh: pytest.MonkeyPatch) -> None:
    boom = _Fn(error=OSError("no"))
    _install(
        fresh,
        _WinDLL(
            _Lib(SetProcessDpiAwarenessContext=boom, SetProcessDPIAware=boom),
            _Lib(SetProcessDpiAwareness=_Fn(result=0x80070005)),
        ),
    )
    assert dpi_awareness.enable_dpi_awareness() == "unavailable"


def test_the_declaration_runs_once(fresh: pytest.MonkeyPatch) -> None:
    context = _Fn(result=1)
    _install(fresh, _WinDLL(_Lib(SetProcessDpiAwarenessContext=context), _Lib()))
    dpi_awareness.enable_dpi_awareness()
    dpi_awareness.enable_dpi_awareness()
    assert len(context.calls) == 1


def test_not_windows_is_a_no_op(fresh: pytest.MonkeyPatch) -> None:
    fresh.setattr(sys, "platform", "darwin")
    assert dpi_awareness.enable_dpi_awareness() == "unsupported"


def test_environment_opt_out(fresh: pytest.MonkeyPatch) -> None:
    context = _Fn(result=1)
    _install(fresh, _WinDLL(_Lib(SetProcessDpiAwarenessContext=context), _Lib()))
    fresh.setenv("QUILL_DPI_UNAWARE", "1")
    assert dpi_awareness.enable_dpi_awareness() == "disabled"
    assert context.calls == []
