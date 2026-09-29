"""Windows' own now-playing card, and the keys it must not take.

The modern Windows Media engine owns a ``SystemMediaTransportControls`` -- the
panel on the volume flyout and the lock screen -- and nothing filled it in, so
Quill's card was blank while every other media app on the machine had a title
in it. It is an accessibility surface: the screen reader reads the flyout when
it opens, and Windows' own "what is playing?" answers come from this card.

Two rules hold the whole design up, and both are tested here rather than
described in a comment.

**It claims no buttons.** SMTC has two halves -- the card, and the routing of
the keyboard's media keys. The QuillVille apps already claim those keys
themselves with ``RegisterHotKey`` (``AppShellFrame._register_media_keys``),
which works from the tray and without focus, and ``winrt_engine`` disables the
command manager for exactly that reason. A second claimant turns "which one
answers" into a matter of timing, so every button flag is set False on purpose.

**It says nothing out loud.** Announcing what was just put on the card would be
the over-announcing GATE-13 exists to stop: the reader already reads the flyout.
Nothing in this path speaks.
"""

from __future__ import annotations

import pytest

from quill.ui.audio import now_playing


class _Updater:
    def __init__(self) -> None:
        self.type = None
        self.app_media_id = ""
        self.updated = 0
        self.cleared = 0
        self.music_properties = type("_Music", (), {})()
        self.video_properties = type("_Video", (), {})()

    def update(self) -> None:
        self.updated += 1

    def clear_all(self) -> None:
        self.cleared += 1


class _Controls:
    """A stand-in SystemMediaTransportControls that records what was claimed."""

    def __init__(self) -> None:
        self.is_enabled = False
        self.playback_status = None
        self.display_updater = _Updater()
        for flag in now_playing._BUTTON_FLAGS:
            setattr(self, flag, True)  # start claimed, so clearing them is visible


class _Engine:
    def __init__(self, controls: object | None) -> None:
        self._controls = controls

    def media_transport_controls(self) -> object | None:
        return self._controls


class _ClassicEngine:
    """The classic wx.media control: no card, no transport controls."""


@pytest.fixture
def winrt(monkeypatch):
    """Stand in for the ``winrt.windows.media`` enums the card uses."""
    import sys

    class _Module:
        class MediaPlaybackType:
            MUSIC = "music-type"
            VIDEO = "video-type"

        class MediaPlaybackStatus:
            CLOSED = "closed"
            CHANGING = "changing"
            STOPPED = "stopped"
            PLAYING = "playing"
            PAUSED = "paused"

    monkeypatch.setitem(sys.modules, "winrt.windows.media", _Module)
    return _Module


# -- the card itself ---------------------------------------------------------


def test_the_title_and_artist_reach_the_card(winrt) -> None:
    controls = _Controls()
    assert now_playing.update_now_playing(
        _Engine(controls), app_name="Quill Radio", title="BBC Radio 4", artist="The Archers"
    )
    music = controls.display_updater.music_properties
    assert music.title == "BBC Radio 4"
    assert music.artist == "The Archers"
    assert controls.display_updater.app_media_id == "Quill Radio"
    assert controls.display_updater.updated == 1


def test_no_buttons_are_ever_claimed(winrt) -> None:
    """The rule the apps' own media keys depend on.

    Every flag starts True here so that leaving even one alone would fail.
    """
    controls = _Controls()
    now_playing.update_now_playing(_Engine(controls), app_name="Quill Radio", title="A station")
    still_claimed = [f for f in now_playing._BUTTON_FLAGS if getattr(controls, f)]
    assert still_claimed == [], f"SMTC claimed media keys the app owns: {still_claimed}"


def test_the_card_is_enabled_so_windows_shows_it(winrt) -> None:
    controls = _Controls()
    now_playing.update_now_playing(_Engine(controls), app_name="Quill Radio", title="A station")
    assert controls.is_enabled is True


def test_an_empty_title_takes_the_card_down(winrt) -> None:
    """A card that says nothing is worse than no card."""
    controls = _Controls()
    assert now_playing.update_now_playing(_Engine(controls), app_name="Quill Radio", title="  ")
    assert controls.display_updater.cleared == 1


def test_the_app_name_stands_in_for_a_missing_artist(winrt) -> None:
    # A station that sends no track title still names the app, not a blank row.
    controls = _Controls()
    now_playing.update_now_playing(_Engine(controls), app_name="Quill Radio", title="A station")
    assert controls.display_updater.music_properties.artist == "Quill Radio"


def test_a_video_uses_the_video_half_of_the_card(winrt) -> None:
    controls = _Controls()
    now_playing.update_now_playing(
        _Engine(controls),
        app_name="Quill Media Player",
        title="A film",
        artist="Chapter 2",
        kind=now_playing.MEDIA_KIND_VIDEO,
    )
    assert controls.display_updater.video_properties.title == "A film"
    assert controls.display_updater.video_properties.subtitle == "Chapter 2"


# -- status, so the card does not lie ----------------------------------------


def test_paused_is_reported_as_paused(winrt) -> None:
    controls = _Controls()
    assert now_playing.set_playback_status(_Engine(controls), "paused")
    assert controls.playback_status == "paused"


def test_an_unknown_status_is_ignored_rather_than_guessed(winrt) -> None:
    controls = _Controls()
    assert now_playing.set_playback_status(_Engine(controls), "dithering") is False
    assert controls.playback_status is None


def test_clearing_closes_the_card(winrt) -> None:
    controls = _Controls()
    assert now_playing.clear_now_playing(_Engine(controls))
    assert controls.display_updater.cleared == 1
    assert controls.playback_status == "closed"


# -- engines that have no card ----------------------------------------------


def test_an_engine_without_a_card_is_not_an_error(winrt) -> None:
    """libmpv and the classic control have no card; that costs nothing."""
    assert now_playing.supports_now_playing(_ClassicEngine()) is False
    assert (
        now_playing.update_now_playing(_ClassicEngine(), app_name="Quill Radio", title="x") is False
    )
    assert now_playing.clear_now_playing(_ClassicEngine()) is False


def test_an_engine_mid_teardown_is_not_an_error(winrt) -> None:
    class _Dying:
        def media_transport_controls(self):
            raise RuntimeError("wrapped C/C++ object has been deleted")

    assert now_playing.update_now_playing(_Dying(), app_name="Quill Radio", title="x") is False


def test_a_windows_build_that_refuses_costs_the_card_not_the_playback(winrt) -> None:
    """A real refusal seen while building this: "The media type has not been
    initialized." The card is never worth the playback."""

    class _Refusing:
        is_enabled = False

        @property
        def display_updater(self):
            raise OSError("The media type has not been initialized.")

    assert (
        now_playing.update_now_playing(_Engine(_Refusing()), app_name="Quill Radio", title="x")
        is False
    )
