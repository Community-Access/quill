"""A global route owns its wx identifier until the host releases the route."""

from __future__ import annotations

import weakref
from types import SimpleNamespace

import pytest

from quill.ui.main_frame_hotkeys import GlobalHotkeysMixin


class IdPool:
    def __init__(self):
        self.used = set()

    def allocate(self):
        value = 1
        while value in self.used:
            value += 1
        self.used.add(value)
        return IdRef(self, value)


class IdRef:
    def __init__(self, pool, value):
        self.pool = pool
        self.value = value

    def __int__(self):
        return self.value

    def __del__(self):
        self.pool.used.remove(self.value)


def test_routes_cannot_share_an_id_recycled_after_a_temporary_ref() -> None:
    pool = IdPool()
    host = GlobalHotkeysMixin()
    host._wx = SimpleNamespace(NewIdRef=pool.allocate)

    play = host._global_hotkey_wx_id("podcasts.play_pause")
    stop = host._global_hotkey_wx_id("podcasts.stop")

    assert play != stop
    assert pool.used == {play, stop}
    assert host._global_hotkey_wx_id("podcasts.play_pause") == play
    assert len(host._global_hotkey_ids) == 2


def test_unregister_uses_integer_ids_and_keeps_refs_for_reload() -> None:
    pool = IdPool()
    host = GlobalHotkeysMixin()
    host._wx = SimpleNamespace(NewIdRef=pool.allocate)
    ids = [
        host._global_hotkey_wx_id("podcasts.play_pause"),
        host._global_hotkey_wx_id("podcasts.stop"),
    ]
    unregistered = []
    host.frame = SimpleNamespace(UnregisterHotKey=unregistered.append)

    host._unregister_global_hotkeys()

    assert unregistered == ids
    assert all(type(value) is int for value in unregistered)
    assert pool.used == set(ids)
    assert host._global_hotkey_wx_id("podcasts.play_pause") == ids[0]


def test_native_wx_ref_is_kept_alive_with_the_global_route() -> None:
    wx = pytest.importorskip("wx")
    app = wx.GetApp() or wx.App()
    host = GlobalHotkeysMixin()
    host._wx = wx
    value = host._global_hotkey_wx_id("podcasts.play_pause")
    reference = weakref.ref(host._global_hotkey_ids["podcasts.play_pause"])

    assert reference() is not None
    assert int(reference()) == value
    assert app is wx.GetApp()
