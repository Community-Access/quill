"""Per-book volume + Mute wiring in PlayerPanel (Phase 2 port-in, Task 2.9)."""

from __future__ import annotations

import pytest

from quill.core.audio_studio.book_prefs import BookPrefs
from quill.ui.audio_studio.player_panel import PlayerPanel


@pytest.fixture
def app():
    import wx

    a = wx.App(False)
    yield a
    a.Destroy()


class _FakeEngine:
    """Records volume calls; ``load`` succeeds without touching wx.media."""

    def __init__(self) -> None:
        self.volume_calls: list[int] = []
        self.loaded: list[str] = []

    def load(self, path: str) -> bool:
        self.loaded.append(path)
        return True

    def set_volume(self, percent: int) -> None:
        self.volume_calls.append(int(percent))

    def play(self) -> None: ...

    def pause(self) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...

    def seek(self, ms: int, *, resume: bool | None = None) -> None: ...

    def position_ms(self) -> int:
        return 0

    def is_playing(self) -> bool:
        return False

    def set_rate(self, rate: float) -> None: ...


def _panel(app) -> PlayerPanel:
    import wx

    parent = wx.Frame(None)
    p = PlayerPanel(parent)
    p._engine = _FakeEngine()  # type: ignore[assignment]
    return p


def test_load_applies_book_volume(app) -> None:
    p = _panel(app)
    p.load("dummy.mp3", chapters=[], book_prefs=BookPrefs(volume_percent=42, muted=False))
    assert p._engine.volume_calls[-1] == 42  # type: ignore[attr-defined]


def test_load_defaults_to_full_volume(app) -> None:
    p = _panel(app)
    p.load("dummy.mp3", chapters=[], book_prefs=None)
    assert p._engine.volume_calls[-1] == 100  # type: ignore[attr-defined]


def test_load_muted_zeroes_engine_volume(app) -> None:
    p = _panel(app)
    p.load(
        "dummy.mp3",
        chapters=[],
        book_prefs=BookPrefs(volume_percent=42, muted=True),
    )
    assert p._engine.volume_calls[-1] == 0  # type: ignore[attr-defined]


def test_toggle_mute_restores_volume(app) -> None:
    p = _panel(app)
    p.load(
        "dummy.mp3",
        chapters=[],
        book_prefs=BookPrefs(volume_percent=42, muted=True),
    )
    p.toggle_mute()  # unmute -> engine volume returns to 42
    assert p._engine.volume_calls[-1] == 42  # type: ignore[attr-defined]
    p.toggle_mute()  # mute again -> 0
    assert p._engine.volume_calls[-1] == 0  # type: ignore[attr-defined]


def test_callbacks_fire_on_volume_mute_finished(app) -> None:
    import wx

    parent = wx.Frame(None)
    volumes: list[int] = []
    mutes: list[bool] = []
    finished: list[bool] = []
    p = PlayerPanel(
        parent,
        on_volume=volumes.append,
        on_mute=mutes.append,
        on_finished=lambda: finished.append(True),
    )
    p._engine = _FakeEngine()  # type: ignore[assignment]
    p.load("dummy.mp3", chapters=[], book_prefs=None)
    # Simulate a volume-slider drag.
    p._volume.SetValue(55)
    p._on_volume(wx.CommandEvent())
    assert volumes[-1] == 55
    # Mute + unmute fire the mute callback.
    p.toggle_mute()
    assert mutes[-1] is True
    p.toggle_mute()
    assert mutes[-1] is False
    # Engine finish fires the finished callback.
    p._on_engine_finished()
    assert finished == [True]
    parent.Destroy()
