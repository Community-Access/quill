"""Tests for WindowManager's navigation logic (wx calls faked)."""

from __future__ import annotations

from quill.ui.window_menu import WindowManager


class _FakeWx:
    """Just enough wx for WindowManager.__init__ (only NewIdRef is used here)."""

    def __init__(self) -> None:
        self._n = 1000

    def NewIdRef(self):  # noqa: N802 - wx shape
        self._n += 1
        return self._n


class _FakeFrame:
    def __init__(self, frame_id: int) -> None:
        self._id = frame_id
        self.calls: list[str] = []

    def GetId(self) -> int:  # noqa: N802 - wx shape
        return self._id

    def Show(self) -> None:  # noqa: N802
        self.calls.append("Show")

    def Raise(self) -> None:  # noqa: N802
        self.calls.append("Raise")

    def SetFocus(self) -> None:  # noqa: N802
        self.calls.append("SetFocus")


def _wm_with(*frames: _FakeFrame) -> WindowManager:
    wm = WindowManager(_FakeWx())
    titles = ["Main", "Browse", "Weather", "Manager"]
    for frame, title in zip(frames, titles, strict=False):
        wm.register(frame, title)
    return wm


def test_register_tracks_and_activates() -> None:
    a, b, c = _FakeFrame(1), _FakeFrame(2), _FakeFrame(3)
    wm = _wm_with(a, b, c)
    assert len(wm) == 3
    assert wm.activate("2") is b
    assert b.calls == ["Show", "Raise", "SetFocus"]  # raised, shown, focused


def test_next_previous_cycle() -> None:
    a, b, c = _FakeFrame(1), _FakeFrame(2), _FakeFrame(3)
    wm = _wm_with(a, b, c)
    assert wm.activate_next(a) is b
    assert wm.activate_next(c) is a  # wraps to the first
    assert wm.activate_previous(a) is c  # wraps to the last
    assert wm.activate_previous(b) is a


def test_activate_number_is_one_based_and_bounded() -> None:
    a, b, c = _FakeFrame(1), _FakeFrame(2), _FakeFrame(3)
    wm = _wm_with(a, b, c)
    assert wm.activate_number(1) is a
    assert wm.activate_number(3) is c
    assert wm.activate_number(0) is None
    assert wm.activate_number(4) is None


def test_unregister_renumbers_and_previous_key_for_close() -> None:
    a, b, c = _FakeFrame(1), _FakeFrame(2), _FakeFrame(3)
    wm = _wm_with(a, b, c)
    # Closing b: the window to fall back to is the one before it (a).
    assert wm.previous_key(b) == "1"
    wm.unregister(b)
    assert len(wm) == 2
    assert wm.activate_number(2) is c  # c renumbered from position 3 to 2
    assert wm.activate("3") is c  # its stable key is unchanged
    assert wm.activate("2") is None  # b's key is gone


def test_activate_unknown_key_is_safe() -> None:
    wm = _wm_with(_FakeFrame(1))
    assert wm.activate("999") is None
