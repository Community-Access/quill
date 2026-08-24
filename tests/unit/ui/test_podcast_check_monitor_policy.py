"""QUILL Cast's background check, once its cadence became the shared one.

The monitor used to clamp ``podcast_check_interval_minutes`` to its own range
and offer its own list, so "every 12 hours" was a choice in one app and not the
other, and a value one app accepted the other quietly rewrote. It now asks
:mod:`quill.core.podcasts.refresh_policy`, which is the module Quill Radio asks
too -- one list, one normalisation, one meaning for zero.

Two behaviours here are the point of section 1 rather than housekeeping:

* **A forced check passes the automatic switch.** The switch answers "check
  without being asked", which is off by default; Check All Feeds Now answers
  "check now, because I asked". Reading one as the other would have shipped a
  menu item that did nothing for everybody on the default settings.
* **Safe Mode still says no**, forced or not.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts import refresh_policy
from quill.core.podcasts.subscriptions import PodcastLibrary, PodcastShow

wx = pytest.importorskip("wx")

from quill.ui.podcasts.check_monitor import PodcastCheckMonitor  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture
def frame():
    window = wx.Frame(None)
    yield window
    window.Destroy()


class _Settings:
    def __init__(self, *, enabled: bool = True, minutes: int = 60) -> None:
        self.podcast_check_enabled = enabled
        self.podcast_check_interval_minutes = minutes
        self.podcast_check_tick_sound = False
        self.podcast_check_interrupt = False


def _Show(show_id: str, *, paused: bool = False, feed: str = "https://x/f.xml") -> PodcastShow:
    """A real model, so the claim can actually save the library it stamps."""
    show = PodcastShow(id=show_id, title=show_id, feed_url=feed)
    show.paused = paused
    return show


def _Library(shows: list[PodcastShow], stamp: str = "") -> PodcastLibrary:
    """Also a real model: claiming the round saves the library it stamps."""
    library = PodcastLibrary(shows=shows)
    library.last_auto_check = stamp
    return library


def _monitor(frame, settings: _Settings, library: PodcastLibrary, *, safe_mode: bool = False):
    refreshed: list[str] = []
    monitor = PodcastCheckMonitor(
        frame,
        settings_provider=lambda: settings,
        library_provider=lambda: library,
        refresh_show=refreshed.append,
        safe_mode=safe_mode,
    )
    return monitor, refreshed


@pytest.fixture(autouse=True)
def _no_real_library(monkeypatch, tmp_path):
    """The claim writes the shared stamp to disk; keep it in a temp folder."""
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)


# -- the cadence is the shared one ----------------------------------------------


def test_the_interval_is_normalised_by_the_shared_policy(frame) -> None:
    library = _Library([])
    for stored, expected in ((0, 0), (1, refresh_policy.MIN_INTERVAL_MINUTES), (720, 720)):
        monitor, _ = _monitor(frame, _Settings(minutes=stored), library)
        assert monitor.interval_minutes() == expected


def test_manually_only_starts_no_timer(frame) -> None:
    monitor, _ = _monitor(frame, _Settings(minutes=0), _Library([]))
    assert monitor.apply() is False
    monitor.stop()


# -- force ----------------------------------------------------------------------


def test_a_forced_check_runs_even_with_the_automatic_switch_off(frame) -> None:
    """The default is off. A menu item that did nothing on the default is a bug."""
    library = _Library([_Show("live")])
    monitor, refreshed = _monitor(frame, _Settings(enabled=False), library)

    assert monitor.check_now(force=True) == 1
    assert refreshed == ["live"]


def test_an_automatic_check_still_respects_the_switch(frame) -> None:
    library = _Library([_Show("live")])
    monitor, refreshed = _monitor(frame, _Settings(enabled=False), library)

    assert monitor.check_now() == 0
    assert refreshed == []


def test_a_forced_check_asks_the_paused_show_too(frame) -> None:
    library = _Library([_Show("live"), _Show("resting", paused=True)])
    monitor, refreshed = _monitor(frame, _Settings(), library)

    monitor.check_now(force=True)

    assert refreshed == ["live", "resting"]


def test_an_automatic_check_leaves_the_paused_show_alone(frame) -> None:
    library = _Library([_Show("live"), _Show("resting", paused=True)])
    monitor, refreshed = _monitor(frame, _Settings(), library)

    monitor.check_now()

    assert refreshed == ["live"]


def test_a_show_with_no_feed_is_never_asked(frame) -> None:
    library = _Library([_Show("local", feed="")])
    monitor, refreshed = _monitor(frame, _Settings(), library)

    assert monitor.check_now(force=True) == 0
    assert refreshed == []


def test_safe_mode_refuses_a_forced_check_too(frame) -> None:
    library = _Library([_Show("live")])
    monitor, refreshed = _monitor(frame, _Settings(), library, safe_mode=True)

    assert monitor.check_now(force=True) == 0
    assert refreshed == []


# -- the shared stamp -----------------------------------------------------------


def test_a_check_quill_radio_just_ran_is_skipped(frame) -> None:
    import time

    library = _Library([_Show("live")], stamp=refresh_policy.stamp_now(time.time()))
    monitor, refreshed = _monitor(frame, _Settings(minutes=60), library)

    assert monitor.check_now() == 0
    assert refreshed == []


def test_the_round_is_claimed_before_the_work(frame) -> None:
    """Claimed after the fetch, the other app would still see a stale stamp."""
    library = _Library([_Show("live")])
    stamp_when_asked: list[str] = []
    monitor = PodcastCheckMonitor(
        frame,
        settings_provider=lambda: _Settings(minutes=60),
        library_provider=lambda: library,
        refresh_show=lambda _id: stamp_when_asked.append(str(library.last_auto_check)),
        safe_mode=False,
    )

    monitor.check_now()

    assert stamp_when_asked and all(stamp_when_asked)


def test_a_forced_check_never_defers_to_the_stamp(frame) -> None:
    import time

    library = _Library([_Show("live")], stamp=refresh_policy.stamp_now(time.time()))
    monitor, refreshed = _monitor(frame, _Settings(minutes=60), library)

    assert monitor.check_now(force=True) == 1
    assert refreshed == ["live"]


def test_one_bad_feed_never_stops_the_rest(frame) -> None:
    library = _Library([_Show("bad"), _Show("good")])
    refreshed: list[str] = []

    def _refresh(show_id: str) -> None:
        if show_id == "bad":
            raise RuntimeError("that host is down")
        refreshed.append(show_id)

    monitor = PodcastCheckMonitor(
        frame,
        settings_provider=lambda: _Settings(),
        library_provider=lambda: library,
        refresh_show=_refresh,
        safe_mode=False,
    )

    assert monitor.check_now(force=True) == 1
    assert refreshed == ["good"]


# -- the feature gate -----------------------------------------------------------


def test_a_build_with_podcasts_off_never_polls_however_it_is_asked(frame) -> None:
    library = _Library([_Show("live")])
    refreshed: list[str] = []
    monitor = PodcastCheckMonitor(
        frame,
        settings_provider=lambda: _Settings(),
        library_provider=lambda: library,
        refresh_show=refreshed.append,
        feature_enabled=lambda: False,
    )

    assert monitor.check_now() == 0
    assert monitor.check_now(force=True) == 0
    assert refreshed == []


def test_the_policy_reads_back_as_one_sentence(frame) -> None:
    monitor, _ = _monitor(frame, _Settings(enabled=False), _Library([]))
    assert monitor.describe() == "Podcast feeds are only checked when you ask."
