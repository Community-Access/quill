"""A saved podcast setting reaches the episode already playing (Chris, 2026-11-19).

Quill Cast's Settings for This Podcast set to 1.5x saved and said so, and the
episode went on at its old speed; only Speed Up or Speed Down changed it. The
player is told a podcast's speed and sound when an episode starts, and nothing
told it again. Now every save of the library pushes what changed, and only that.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.settings_catalog import definition
from quill.core.podcasts.settings_resolver import set_value
from quill.core.podcasts.settings_types import LEVEL_GLOBAL, LEVEL_SHOW
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.live_settings import reapply_saved_settings, remember_applied


class _State:
    def __init__(self) -> None:
        self.show_id: str | None = None
        self.episode_guid: str | None = None


class _Controller:
    def __init__(self) -> None:
        self.state = _State()
        self.rates: list[float] = []
        self.enhancements: list[dict[str, Any]] = []
        self.boosts: list[float] = []
        self.played: list[dict[str, Any]] = []

    def play_episode(self, **kwargs: Any) -> None:
        self.played.append(kwargs)
        self.state.show_id = kwargs["show_id"]
        self.state.episode_guid = kwargs["episode_guid"]

    def set_rate(self, rate: float) -> None:
        self.rates.append(rate)

    def set_enhancement(self, **kwargs: Any) -> None:
        self.enhancements.append(kwargs)

    def set_volume_boost(self, multiplier: float) -> None:
        self.boosts.append(multiplier)


class _Host:
    def __init__(self, library: PodcastLibrary, controller: _Controller) -> None:
        self._podcast_library = library
        self._podcast_controller = controller


def _playing(*, local: bool = False) -> tuple[_Host, PodcastLibrary, PodcastShow, _Controller]:
    from quill.ui.podcasts.show_actions import start_episode_playback

    library = PodcastLibrary()
    show = PodcastShow(id="s1", title="Hard Fork", feed_url="https://example.invalid/hf")
    if local:
        show.is_local = True
    episode = PodcastEpisode(guid="e1", title="One", audio_url="https://example.invalid/1.mp3")
    show.episodes.append(episode)
    library.add_show(show)
    controller = _Controller()
    assert start_episode_playback(controller, library, show, episode)
    return _Host(library, controller), library, show, controller


def test_chris_a_podcast_set_to_one_and_a_half_plays_at_one_and_a_half() -> None:
    host, library, show, controller = _playing()
    assert controller.played[0]["rate"] == 1.0
    # Settings for This Podcast: Playback speed 1.5, OK.
    assert set_value(library, definition("speed"), 1.5, level=LEVEL_SHOW, scope_id=show.id)
    assert reapply_saved_settings(host) == ["speed"]
    assert controller.rates == [1.5]


def test_a_shared_default_reaches_a_podcast_that_follows_it() -> None:
    host, library, _show, controller = _playing()
    set_value(library, definition("speed"), 1.25, level=LEVEL_GLOBAL)
    assert reapply_saved_settings(host) == ["speed"]
    assert controller.rates == [1.25]


def test_a_save_that_changed_nothing_touches_nothing() -> None:
    host, _library, _show, controller = _playing()
    boosts = list(controller.boosts)  # the start of the episode sets its boost once
    assert reapply_saved_settings(host) == []
    assert reapply_saved_settings(host) == []
    assert (controller.rates, controller.enhancements, controller.boosts) == ([], [], boosts)


def test_a_new_speed_is_pushed_once_not_on_every_later_save() -> None:
    host, library, show, controller = _playing()
    set_value(library, definition("speed"), 2.0, level=LEVEL_SHOW, scope_id=show.id)
    reapply_saved_settings(host)
    reapply_saved_settings(host)  # a feed refresh saves too
    assert controller.rates == [2.0]


def test_sound_changes_reload_through_the_relay_and_boost_is_set() -> None:
    host, library, show, controller = _playing()
    library.apply_show_override(show, eq_bass_db=4.0, volume_boost="high")
    pushed = reapply_saved_settings(host)
    assert "eq_bass_db" in pushed and "volume_boost" in pushed
    assert controller.enhancements[-1]["bass_db"] == 4.0
    assert controller.boosts


def test_another_podcast_s_setting_does_not_touch_this_episode() -> None:
    host, library, _show, controller = _playing()
    other = PodcastShow(id="s2", title="Other", feed_url="https://example.invalid/o")
    library.add_show(other)
    set_value(library, definition("speed"), 3.0, level=LEVEL_SHOW, scope_id=other.id)
    assert reapply_saved_settings(host) == []
    assert controller.rates == []


def test_a_file_with_its_own_speed_keeps_it() -> None:
    host, library, show, controller = _playing(local=True)
    show.episodes[0].speed_override = 0.8
    set_value(library, definition("speed"), 1.5, level=LEVEL_SHOW, scope_id=show.id)
    assert reapply_saved_settings(host) == []
    assert controller.rates == []


def test_a_scan_in_progress_is_left_alone_and_the_speed_follows_later() -> None:
    host, library, show, controller = _playing()

    class Scan:
        is_scanning = True

    host._scan_hold = Scan()  # type: ignore[attr-defined]
    set_value(library, definition("speed"), 1.5, level=LEVEL_SHOW, scope_id=show.id)
    assert reapply_saved_settings(host) == []
    host._scan_hold.is_scanning = False  # type: ignore[attr-defined]
    assert reapply_saved_settings(host) == ["speed"]
    assert controller.rates == [1.5]


def test_something_this_module_never_started_is_never_handed_settings() -> None:
    host, library, show, controller = _playing()
    controller.play_episode(show_id="spotify", episode_guid="spotify:episode:x", title="x")
    set_value(library, definition("speed"), 1.5, level=LEVEL_GLOBAL)
    assert reapply_saved_settings(host) == []
    remember_applied(controller, library.settings)
    assert controller.rates == []


def test_every_save_carries_it(monkeypatch) -> None:
    """The hook is in the one save path QUILL and Quill Cast share."""
    from quill.ui import main_frame_podcast_save as save

    host, library, show, controller = _playing()

    class Saver(save.PodcastLibrarySaveMixin):
        _podcast_library_loading = False
        _check_run = None

        class _podcast_download_queue:  # noqa: N801 - the attribute it stands in for
            @staticmethod
            def set_reconnect_settings(*_a: Any, **_k: Any) -> None:
                pass

        def __init__(self) -> None:
            self._podcast_library = library
            self._podcast_controller = controller

        def _podcast_library_is_large(self) -> bool:
            return False

        def _flush_podcast_library(self) -> None:
            pass

    saver = Saver()
    set_value(library, definition("speed"), 1.5, level=LEVEL_SHOW, scope_id=show.id)
    saver._save_podcast_library()
    assert controller.rates == [1.5]


def test_the_podcast_speed_box_steps_like_speed_up() -> None:
    speed = definition("speed")
    assert (speed.step, speed.digits) == (0.05, 2)
