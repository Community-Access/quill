"""QUILL Cast's automatic feed check reads the store Cast Preferences writes.

A listener chose "every 15 minutes" in Cast and was told feeds are only
checked when asked. Cast Preferences write ``podcast_check_*`` onto
``PodcastHistory``; the monitor asked "settings, else history", and Cast's
frame *has* a ``settings`` (``AppShellFrame`` loads the editor's), whose
switch is off by default -- so the check could never start in Cast.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from quill.apps.podcasts_routes import CastPlaceRoutesMixin
from quill.core.podcasts import check_state, refresh_schedule, schedule_policy
from quill.core.podcasts.history import PodcastHistory
from quill.core.podcasts.subscriptions import PodcastLibrary, PodcastShow
from quill.core.settings import Settings
from quill.ui.podcasts.new_feed_check import check_settings
from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.ui.podcasts.check_monitor import PodcastCheckMonitor  # noqa: E402

OFF_WORDS = "only checked when you ask"


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    return shared_wx_app()


@pytest.fixture
def frame():
    window = wx.Frame(None)
    yield window
    window.Destroy()


class _CastHost(CastPlaceRoutesMixin):
    """The shape of PodcastsAppFrame that matters here: both stores present."""

    def __init__(self, library: PodcastLibrary) -> None:
        self.settings = Settings()  # the editor's: podcast_check_enabled False
        self._podcast_history = PodcastHistory()
        self._podcast_history.podcast_check_enabled = True
        self._podcast_history.podcast_check_interval_minutes = 15
        self._podcast_library = library


def _monitor(frame: Any, host: Any, library: PodcastLibrary) -> PodcastCheckMonitor:
    # The same provider _init_podcasts hands the monitor.
    return PodcastCheckMonitor(
        frame,
        settings_provider=lambda: check_settings(host),
        library_provider=lambda: library,
        refresh_show=lambda _show_id: None,
        library_changed=lambda: None,
    )


def test_cast_checks_on_the_cadence_its_preferences_chose(frame) -> None:
    library = PodcastLibrary()
    host = _CastHost(library)
    assert host.settings.podcast_check_enabled is False
    monitor = _monitor(frame, host, library)
    try:
        assert OFF_WORDS not in monitor.describe()
        assert monitor.apply() is True
        assert monitor.interval_minutes() == 15
    finally:
        monitor.shutdown()


def test_quill_still_reads_its_own_settings(frame) -> None:
    library = PodcastLibrary()
    settings = Settings()
    settings.podcast_check_enabled = True
    settings.podcast_check_interval_minutes = 30
    history = PodcastHistory()  # Cast's switch, off: must not be what QUILL reads
    host = SimpleNamespace(settings=settings, _podcast_history=history)
    monitor = _monitor(frame, host, library)
    try:
        assert monitor.apply() is True
        assert monitor.interval_minutes() == 30
    finally:
        monitor.shutdown()


# -- each podcast's own schedule ------------------------------------------------


def _show(library: PodcastLibrary, show_id: str) -> PodcastShow:
    show = PodcastShow(id=show_id, title=show_id, feed_url=f"https://x/{show_id}.xml")
    library.shows.append(show)
    return show


def test_a_saved_schedule_decides_whether_a_podcast_is_due(frame) -> None:
    library = PodcastLibrary()
    host = _CastHost(library)
    monitor = _monitor(frame, host, library)
    now = datetime.now(UTC)
    riding = _show(library, "riding")
    manual = _show(library, "manual")
    daily = _show(library, "daily")
    stale = _show(library, "stale")
    schedule_policy.set_schedule(
        library, manual, refresh_schedule.Schedule(refresh_schedule.MANUAL)
    )
    for show in (daily, stale):
        schedule_policy.set_schedule(
            library, show, refresh_schedule.Schedule(refresh_schedule.INTERVAL, 1440)
        )
    check_state.record_success(library, daily, now=now - timedelta(hours=1))
    check_state.record_success(library, stale, now=now - timedelta(days=2))
    try:
        # No schedule anywhere: rides along on the heartbeat, as before.
        assert monitor._show_is_due(library, riding) is True
        assert monitor._show_is_due(library, manual) is False
        assert monitor._show_is_due(library, daily) is False
        assert monitor._show_is_due(library, stale) is True
    finally:
        monitor.shutdown()


# -- Change Schedule ------------------------------------------------------------


def _schedule_host(enabled: bool) -> SimpleNamespace:
    history = PodcastHistory()
    history.podcast_check_enabled = enabled
    applied: list[bool] = []
    monitor = SimpleNamespace(apply=lambda: applied.append(enabled) or enabled)
    return SimpleNamespace(
        _podcast_check_reads_history=True,
        _podcast_history=history,
        _podcast_check_monitor=monitor,
        applied=applied,
    )


def test_change_schedule_restarts_the_check() -> None:
    from quill.ui.podcasts.schedule_dialog import _switch_words

    host = _schedule_host(True)
    words = _switch_words(host, refresh_schedule.Schedule(refresh_schedule.INTERVAL, 15))
    assert words == ""
    assert host.applied == [True]


def test_change_schedule_says_when_the_switch_is_off() -> None:
    from quill.ui.podcasts.schedule_dialog import _switch_words

    host = _schedule_host(False)
    words = _switch_words(host, refresh_schedule.Schedule(refresh_schedule.INTERVAL, 15))
    assert "Automatic checking is off" in words
    assert host._podcast_history.podcast_check_enabled is False  # never turned on for you
    assert _switch_words(host, refresh_schedule.Schedule(refresh_schedule.MANUAL)) == ""


# -- Preferences ----------------------------------------------------------------


def test_changing_only_the_interval_reapplies_the_check(monkeypatch, tmp_path) -> None:
    import quill.ui.podcasts.preferences_window as window_module
    from quill.apps.podcasts_preferences import CastPreferencesMixin

    class _Window:
        def __init__(self, _parent: Any, **_kwargs: Any) -> None:
            pass

        def show(self) -> Any:
            return ({"podcast_check_interval_minutes": 15}, {})

    monkeypatch.setattr(window_module, "CastPreferencesWindow", _Window)
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "quill.ui.podcasts.record_tasks.submit",
        lambda *_a, **_k: SimpleNamespace(),
    )
    applied: list[int] = []
    spoken: list[str] = []
    history = PodcastHistory()
    history.podcast_check_enabled = True
    host = SimpleNamespace(
        frame=SimpleNamespace(GetMenuBar=lambda: None),
        _podcast_history=history,
        _podcast_library=PodcastLibrary(),
        _announce=spoken.append,
        _save_podcast_library=lambda: None,
        _podcast_check_monitor=SimpleNamespace(
            apply=lambda: applied.append(history.podcast_check_interval_minutes) or True,
            describe=lambda: "Checking every 15 minutes.",
        ),
    )
    CastPreferencesMixin._open_preferences(host)
    assert applied == [15]
    assert spoken[-1].count("Checking every 15 minutes.") == 1
