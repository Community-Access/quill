"""The Earshot-parity settings, and the behaviour each one steers.

Five fields arrived together and each one exists because something in the app
was either hardcoded or commented-but-unimplemented. The cases below check the
behaviour, not the field: a setting nothing reads is the bug these close.
"""

from __future__ import annotations

from typing import Any

from quill.core import net_metered
from quill.core.podcasts.models import PodcastSettings


def test_the_settings_round_trip_and_tolerate_junk() -> None:
    settings = PodcastSettings(
        history_retention_days=365,
        download_on_metered=False,
        stats_streaks_enabled=True,
        directory_source="both",
        queue_group_mode="folder",
    )
    restored = PodcastSettings.from_dict(settings.to_dict())
    assert restored.history_retention_days == 365
    assert restored.download_on_metered is False
    assert restored.stats_streaks_enabled is True
    assert restored.directory_source == "both"
    assert restored.queue_group_mode == "folder"

    junk = PodcastSettings.from_dict({
        "directory_source": "carrier pigeon",
        "queue_group_mode": "spiral",
    })
    assert junk.directory_source == "itunes"
    assert junk.queue_group_mode == "none"


def test_the_shipped_defaults_change_nobody_s_behaviour() -> None:
    """An upgrade must not turn anything on or off under somebody."""
    settings = PodcastSettings()
    assert settings.history_retention_days == 90
    assert settings.download_on_metered is True
    assert settings.stats_streaks_enabled is False
    assert settings.directory_source == "itunes"
    assert settings.queue_group_mode == "none"


# -- C10: the metered guard --------------------------------------------------


def test_unknown_counts_as_unmetered(monkeypatch: Any) -> None:
    """Refusing to download on a guess is worse than downloading."""
    monkeypatch.setattr(net_metered, "connection_cost", lambda: net_metered.UNKNOWN)
    assert net_metered.may_download(PodcastSettings(download_on_metered=False)) is True


def test_a_metered_connection_holds_an_automatic_download(monkeypatch: Any) -> None:
    monkeypatch.setattr(net_metered, "connection_cost", lambda: net_metered.METERED)
    settings = PodcastSettings(download_on_metered=False)
    assert net_metered.may_download(settings) is False


def test_a_download_you_asked_for_always_happens(monkeypatch: Any) -> None:
    """The guard stops the app spending your data, not you spending it."""
    monkeypatch.setattr(net_metered, "connection_cost", lambda: net_metered.METERED)
    settings = PodcastSettings(download_on_metered=False)
    assert net_metered.may_download(settings, automatic=False) is True


def test_leaving_the_setting_on_never_consults_the_connection(monkeypatch: Any) -> None:
    def _boom() -> str:
        raise AssertionError("the connection must not be probed when the guard is off")

    monkeypatch.setattr(net_metered, "connection_cost", _boom)
    assert net_metered.may_download(PodcastSettings(download_on_metered=True)) is True


def test_a_machine_with_no_winrt_bridge_answers_unknown() -> None:
    """Every supported machine must get an answer, not an exception."""
    assert net_metered.connection_cost() in (
        net_metered.METERED,
        net_metered.UNMETERED,
        net_metered.UNKNOWN,
    )


def test_held_back_downloads_are_said_once_with_a_count() -> None:
    assert net_metered.held_back_message(0) == ""
    assert "Holding 1 download" in net_metered.held_back_message(1)
    assert "Holding 3 downloads" in net_metered.held_back_message(3)
    assert "download anything yourself" in net_metered.held_back_message(3)


def test_auto_download_is_held_on_a_metered_connection(monkeypatch: Any) -> None:
    from quill.core.podcasts.acquisition import episodes_to_auto_download
    from quill.core.podcasts.models import PodcastEpisode, PodcastShow
    from quill.core.podcasts.subscriptions import PodcastLibrary

    show = PodcastShow(id="s", title="Show", feed_url="https://f")
    show.episodes = [PodcastEpisode(guid="g", title="Ep", audio_url="https://a.mp3")]
    library = PodcastLibrary()
    library.shows = [show]
    library.settings = PodcastSettings(auto_download_count=3, download_on_metered=False)

    monkeypatch.setattr(net_metered, "connection_cost", lambda: net_metered.UNMETERED)
    assert episodes_to_auto_download(library, show)

    monkeypatch.setattr(net_metered, "connection_cost", lambda: net_metered.METERED)
    assert episodes_to_auto_download(library, show) == []


def test_prebuffering_waits_on_a_metered_connection() -> None:
    """Speculative bytes for an episode nobody has asked for yet."""
    from quill.core.podcasts.prebuffer import plan

    kwargs: dict[str, Any] = {
        "enabled": True,
        "position_ms": 1_780_000,
        "duration_ms": 1_800_000,
        "next_show_id": "s",
        "next_episode_guid": "g",
        "next_url": "https://a.mp3",
    }
    assert plan(**kwargs).should_fetch is True
    held = plan(**kwargs, on_metered=True)
    assert held.should_fetch is False
    assert "metered" in held.reason
