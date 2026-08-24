"""When a video will not play, the app offers the one thing that fixes it.

"If a video doesn't play, can't we prompt the user to update the component
automagically please?" (2026-08-23). It is the right question because this
failure has exactly one cause: YouTube issues stream addresses per player
client and stops honouring them for the others, so a yt-dlp that has fallen
behind resolves everything correctly -- title, length, chapters -- and hands
back an address that is refused. Nothing the listener can do in the player
helps, and the repair is one menu item they have no reason to know about.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.ui.radio import youtube_ui
from quill.ui.radio.youtube_playback import STALE_COMPONENT_MESSAGE


class _Wx:
    YES = 5103
    NO = 5104
    OK = 4
    YES_NO = 10
    ICON_QUESTION = 40
    ICON_INFORMATION = 50
    ICON_ERROR = 60

    def CallAfter(self, fn: Any, *args: Any) -> None:  # noqa: N802 - wx's own casing
        fn(*args)


class _State:
    def __init__(self, name: str, message: str, station: Any = None) -> None:
        self.state = type("S", (), {"name": name})()
        self.message = message
        self.station = station


class _Tasks:
    def submit(self, _name: str, work: Any, *, on_success: Any = None, on_failure: Any = None):
        try:
            result = work()
        except Exception as exc:  # noqa: BLE001
            if on_failure is not None:
                on_failure("op", exc)
            return
        if on_success is not None:
            on_success("op", result)


class _Controller:
    def __init__(self) -> None:
        self.played: list[Any] = []

    def play_station(self, station: Any) -> None:
        self.played.append(station)


class _Host:
    def __init__(self, answer: int = _Wx.YES) -> None:
        self._wx = _Wx()
        self._safe_mode = False
        self._task_manager = _Tasks()
        self._radio_controller = _Controller()
        self.answer = answer
        self.boxes: list[str] = []
        self.said: list[str] = []

    def _show_message_box(self, message: str, _title: str, _flags: int) -> int:
        self.boxes.append(message)
        return self.answer

    def _announce(self, message: str) -> None:
        self.said.append(message)


def _install(monkeypatch: pytest.MonkeyPatch, *, version: str = "2026.08.19") -> list[int]:
    """Stand in for the pip install, and report how often it ran."""
    from quill.core.radio import youtube as youtube_module
    from quill.core.speech import engine_install

    runs: list[int] = []
    monkeypatch.setattr(engine_install, "install_yt_dlp", lambda *_a, **_k: runs.append(1))
    monkeypatch.setattr(youtube_module, "youtube_version", lambda: version)
    return runs


def test_a_stale_component_failure_offers_the_repair(monkeypatch: pytest.MonkeyPatch) -> None:
    runs = _install(monkeypatch)
    station = object()
    host = _Host(answer=_Wx.YES)

    assert youtube_ui.offer_stale_component_update(
        host, _State("ERROR", STALE_COMPONENT_MESSAGE, station)
    )

    assert runs == [1]
    # And it finishes what the listener was actually trying to do.
    assert host._radio_controller.played == [station]
    assert any("2026.08.19" in box for box in host.boxes)


def test_declining_leaves_everything_alone_and_says_where_the_door_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs = _install(monkeypatch)
    host = _Host(answer=_Wx.NO)

    assert not youtube_ui.offer_stale_component_update(
        host, _State("ERROR", STALE_COMPONENT_MESSAGE)
    )

    assert runs == []
    assert any("Update YouTube Support" in m for m in host.said)


def test_it_is_asked_once_per_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """An app that asks after every failure is an app arguing with somebody."""
    _install(monkeypatch)
    host = _Host(answer=_Wx.NO)
    state = _State("ERROR", STALE_COMPONENT_MESSAGE)

    youtube_ui.offer_stale_component_update(host, state)
    youtube_ui.offer_stale_component_update(host, state)

    assert len(host.boxes) == 1


def test_an_ordinary_failure_is_not_blamed_on_the_component() -> None:
    host = _Host()
    assert not youtube_ui.offer_stale_component_update(
        host, _State("ERROR", "That stream could not be opened.")
    )
    assert host.boxes == []


def test_a_successful_play_is_never_interrupted() -> None:
    host = _Host()
    assert not youtube_ui.offer_stale_component_update(host, _State("PLAYING", ""))
    assert host.boxes == []


def test_safe_mode_never_offers_a_download(monkeypatch: pytest.MonkeyPatch) -> None:
    runs = _install(monkeypatch)
    host = _Host()
    host._safe_mode = True

    assert not youtube_ui.offer_stale_component_update(
        host, _State("ERROR", STALE_COMPONENT_MESSAGE)
    )
    assert runs == []
    assert host.boxes == []


def test_a_failed_install_says_so_in_a_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.speech import engine_install

    def _boom(*_a: Any, **_k: Any) -> None:
        raise RuntimeError("no network")

    monkeypatch.setattr(engine_install, "install_yt_dlp", _boom)
    host = _Host(answer=_Wx.YES)

    youtube_ui.offer_stale_component_update(host, _State("ERROR", STALE_COMPONENT_MESSAGE))

    assert any("could not be updated" in box for box in host.boxes)
    assert host._radio_controller.played == []


def test_the_menu_command_shares_the_same_install(monkeypatch: pytest.MonkeyPatch) -> None:
    """One repair, one implementation -- and it reports in a dialog either way."""
    runs = _install(monkeypatch)
    host = _Host(answer=_Wx.YES)

    youtube_ui.update_youtube_support(host)

    assert runs == [1]
    assert any("2026.08.19" in box for box in host.boxes)
