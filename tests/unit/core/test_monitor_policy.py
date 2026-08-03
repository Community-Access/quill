"""The ambient-monitor policy triple: defaults, clamping, prose, resolution."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from quill.core.announce.message import Severity
from quill.core.monitor_policy import (
    MONITOR_GITHUB,
    MONITOR_PODCASTS,
    MONITOR_SPECS,
    MONITOR_WATCH_FOLDER,
    MONITOR_WEATHER,
    MonitorPolicy,
    clamp_interval_minutes,
    clamp_interval_seconds,
    interval_phrase,
    monitor_spec,
    resolve_monitor_policy,
)
from quill.core.settings import Settings
from quill.core.sound_events import SoundEvent

ALL_MONITORS = (MONITOR_WATCH_FOLDER, MONITOR_WEATHER, MONITOR_PODCASTS, MONITOR_GITHUB)


# -- defaults ---------------------------------------------------------------


def test_default_policy_is_silent_and_polite() -> None:
    policy = MonitorPolicy()
    assert policy.audible_tick is False
    assert policy.interrupt_speech is False
    assert policy.tick_sound_event == ""
    assert policy.severity is Severity.ROUTINE


@pytest.mark.parametrize("monitor", ALL_MONITORS)
def test_every_monitor_defaults_to_quiet_and_non_interrupting(monitor: str) -> None:
    # Nothing may start ticking or interrupting on a fresh install.
    policy = resolve_monitor_policy(Settings(), monitor)
    assert policy.audible_tick is False
    assert policy.interrupt_speech is False
    assert policy.monitor == monitor


@pytest.mark.parametrize("monitor", ALL_MONITORS)
def test_every_monitor_declares_a_nonzero_floor(monitor: str) -> None:
    spec = MONITOR_SPECS[monitor]
    assert spec.minimum_seconds > 0
    assert spec.minimum_seconds <= spec.default_seconds <= spec.maximum_seconds


def test_unknown_monitor_falls_back_instead_of_raising() -> None:
    spec = monitor_spec("some_future_watcher")
    assert spec.minimum_seconds > 0
    policy = resolve_monitor_policy(Settings(), "some_future_watcher")
    assert policy.poll_interval_seconds == spec.default_seconds


# -- clamping ---------------------------------------------------------------


@pytest.mark.parametrize("monitor", ALL_MONITORS)
@pytest.mark.parametrize("bad", [0, -1, -3600])
def test_zero_and_negative_intervals_are_rejected(monitor: str, bad: int) -> None:
    seconds = clamp_interval_seconds(monitor, bad)
    assert seconds == MONITOR_SPECS[monitor].minimum_seconds
    assert seconds > 0


@pytest.mark.parametrize("monitor", ALL_MONITORS)
def test_absurdly_large_intervals_clamp_to_the_ceiling(monitor: str) -> None:
    assert clamp_interval_seconds(monitor, 10**9) == MONITOR_SPECS[monitor].maximum_seconds


def test_garbage_interval_falls_back_to_the_default() -> None:
    assert clamp_interval_seconds(MONITOR_PODCASTS, "soon") == (
        MONITOR_SPECS[MONITOR_PODCASTS].default_seconds
    )
    assert clamp_interval_seconds(MONITOR_PODCASTS, None) == (
        MONITOR_SPECS[MONITOR_PODCASTS].default_seconds
    )


def test_in_range_interval_is_kept_exactly() -> None:
    assert clamp_interval_seconds(MONITOR_WATCH_FOLDER, 42) == 42


def test_clamp_interval_minutes_never_returns_zero() -> None:
    assert clamp_interval_minutes(MONITOR_PODCASTS, 0) == 5
    assert clamp_interval_minutes(MONITOR_GITHUB, -10) == 5
    assert clamp_interval_minutes(MONITOR_GITHUB, 30) == 30
    assert clamp_interval_minutes(MONITOR_GITHUB, 10**6) == 1440


# -- describe() prose -------------------------------------------------------


def test_describe_reads_as_one_english_sentence() -> None:
    policy = MonitorPolicy(poll_interval_seconds=900, audible_tick=True, interrupt_speech=False)
    assert policy.describe() == (
        "Checks every 15 minutes, ticks audibly, does not interrupt speech."
    )


@pytest.mark.parametrize(
    ("seconds", "tick", "interrupt", "expected"),
    [
        (5, False, False, "Checks every 5 seconds, checks silently, does not interrupt speech."),
        (1, False, False, "Checks every second, checks silently, does not interrupt speech."),
        (60, True, True, "Checks every minute, ticks audibly, interrupts speech."),
        (600, False, True, "Checks every 10 minutes, checks silently, interrupts speech."),
        (3600, True, False, "Checks every hour, ticks audibly, does not interrupt speech."),
        (7200, True, True, "Checks every 2 hours, ticks audibly, interrupts speech."),
        (
            90,
            False,
            False,
            "Checks every 1 minute and 30 seconds, checks silently, does not interrupt speech.",
        ),
    ],
)
def test_describe_covers_the_combinations(
    seconds: int, tick: bool, interrupt: bool, expected: str
) -> None:
    policy = MonitorPolicy(
        poll_interval_seconds=seconds, audible_tick=tick, interrupt_speech=interrupt
    )
    assert policy.describe() == expected


def test_interval_phrase_avoids_absurd_units() -> None:
    assert interval_phrase(5400) == "every 90 minutes"
    assert interval_phrase(86400) == "every 24 hours"
    assert "seconds" not in interval_phrase(1800)


# -- the three controls -----------------------------------------------------


def test_audible_tick_selects_the_progress_tick_earcon() -> None:
    assert MonitorPolicy(audible_tick=True).tick_sound_event == SoundEvent.PROGRESS_TICK
    assert MonitorPolicy(audible_tick=False).tick_sound_event == ""


def test_interrupt_speech_raises_the_announcement_severity() -> None:
    assert MonitorPolicy(interrupt_speech=True).severity is Severity.WARNING
    assert MonitorPolicy(interrupt_speech=True).severity.interrupts is True
    assert MonitorPolicy(interrupt_speech=False).severity is Severity.ROUTINE
    assert MonitorPolicy(interrupt_speech=False).severity.interrupts is False


def test_force_speech_mirrors_interrupt_speech() -> None:
    assert MonitorPolicy(interrupt_speech=True).force_speech is True
    assert MonitorPolicy(interrupt_speech=False).force_speech is False


def test_poll_interval_ms_and_minutes() -> None:
    policy = MonitorPolicy(poll_interval_seconds=900)
    assert policy.poll_interval_ms == 900_000
    assert policy.poll_interval_minutes == 15
    assert MonitorPolicy(poll_interval_seconds=5).poll_interval_minutes == 1


def test_is_due_respects_the_interval_and_survives_clock_jumps() -> None:
    policy = MonitorPolicy(poll_interval_seconds=600)
    assert policy.is_due(0.0, 100.0) is True  # never checked
    assert policy.is_due(100.0, 200.0) is False
    assert policy.is_due(100.0, 700.0) is True
    assert policy.is_due(500.0, 100.0) is True  # clock went backwards


# -- per-monitor resolution -------------------------------------------------


def test_watch_folder_reads_its_seconds_setting() -> None:
    settings = Settings(
        watch_folder_poll_interval_seconds=30,
        watch_folder_audible_tick=True,
        watch_folder_interrupt_speech=True,
    )
    policy = resolve_monitor_policy(settings, MONITOR_WATCH_FOLDER)
    assert policy.poll_interval_seconds == 30
    assert policy.audible_tick is True
    assert policy.interrupt_speech is True


def test_podcast_and_github_read_their_minutes_settings() -> None:
    settings = Settings(
        podcast_check_interval_minutes=30,
        podcast_check_audible_tick=True,
        github_poll_interval_minutes=45,
        github_poll_interrupt_speech=True,
    )
    podcasts = resolve_monitor_policy(settings, MONITOR_PODCASTS)
    assert podcasts.poll_interval_seconds == 1800
    assert podcasts.audible_tick is True
    assert podcasts.interrupt_speech is False
    github = resolve_monitor_policy(settings, MONITOR_GITHUB)
    assert github.poll_interval_seconds == 2700
    assert github.interrupt_speech is True
    assert github.audible_tick is False


def test_weather_takes_its_interval_from_its_own_config() -> None:
    # The weather watch keeps its cadence in weather_monitor.json, not Settings,
    # so the caller supplies it; the two flags still come from Settings.
    settings = Settings(weather_monitor_audible_tick=True)
    policy = resolve_monitor_policy(settings, MONITOR_WEATHER, interval_seconds=15 * 60)
    assert policy.poll_interval_seconds == 900
    assert policy.audible_tick is True
    assert policy.describe().startswith("Checks every 15 minutes, ticks audibly")


def test_resolution_clamps_a_hand_edited_zero() -> None:
    settings = Settings(watch_folder_poll_interval_seconds=0, podcast_check_interval_minutes=0)
    assert resolve_monitor_policy(settings, MONITOR_WATCH_FOLDER).poll_interval_seconds == 2
    assert resolve_monitor_policy(settings, MONITOR_PODCASTS).poll_interval_seconds == 300


def test_resolution_without_settings_uses_defaults() -> None:
    policy = resolve_monitor_policy(None, MONITOR_GITHUB)
    assert policy.poll_interval_seconds == MONITOR_SPECS[MONITOR_GITHUB].default_seconds
    assert policy.audible_tick is False
    assert policy.interrupt_speech is False


def test_resolution_tolerates_an_unrelated_settings_object() -> None:
    class Foreign:
        pass

    policy = resolve_monitor_policy(Foreign(), MONITOR_PODCASTS)
    assert policy.poll_interval_seconds == MONITOR_SPECS[MONITOR_PODCASTS].default_seconds


# -- settings round-trip ----------------------------------------------------


def test_new_monitor_settings_round_trip_through_from_dict() -> None:
    original = Settings(
        watch_folder_poll_interval_seconds=12,
        watch_folder_audible_tick=True,
        watch_folder_interrupt_speech=True,
        weather_monitor_audible_tick=True,
        weather_monitor_interrupt_speech=True,
        podcast_check_enabled=True,
        podcast_check_interval_minutes=30,
        podcast_check_audible_tick=True,
        podcast_check_interrupt_speech=True,
        github_poll_interval_minutes=45,
        github_poll_audible_tick=True,
        github_poll_interrupt_speech=True,
    )
    restored = Settings.from_dict(asdict(original))
    for name in (
        "watch_folder_poll_interval_seconds",
        "watch_folder_audible_tick",
        "watch_folder_interrupt_speech",
        "weather_monitor_audible_tick",
        "weather_monitor_interrupt_speech",
        "podcast_check_enabled",
        "podcast_check_interval_minutes",
        "podcast_check_audible_tick",
        "podcast_check_interrupt_speech",
        "github_poll_interval_minutes",
        "github_poll_audible_tick",
        "github_poll_interrupt_speech",
    ):
        assert getattr(restored, name) == getattr(original, name), name


def test_monitor_defaults_are_all_off_in_a_fresh_settings_object() -> None:
    settings = Settings()
    assert settings.podcast_check_enabled is False
    for name in (
        "watch_folder_audible_tick",
        "watch_folder_interrupt_speech",
        "weather_monitor_audible_tick",
        "weather_monitor_interrupt_speech",
        "podcast_check_audible_tick",
        "podcast_check_interrupt_speech",
        "github_poll_audible_tick",
        "github_poll_interrupt_speech",
    ):
        assert getattr(settings, name) is False, name


def test_from_dict_clamps_a_hand_edited_zero_interval() -> None:
    loaded = Settings.from_dict({
        "watch_folder_poll_interval_seconds": 0,
        "podcast_check_interval_minutes": 0,
        "github_poll_interval_minutes": -5,
    })
    assert loaded.watch_folder_poll_interval_seconds == 2
    assert loaded.podcast_check_interval_minutes == 5
    assert loaded.github_poll_interval_minutes == 5
