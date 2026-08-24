"""The automatic check's settings, in the store standalone QUILL Cast has.

``PodcastCheckMonitor`` reads its settings object duck-typed, and inside QUILL
that object is :class:`~quill.core.settings.Settings`. Standalone QUILL Cast has
no ``Settings`` at all -- so ``getattr(self, "settings", None)`` answered
``None``, ``podcast_check_enabled`` read as ``False`` every time, and the
background check could not be turned on by any route in that app. The feature
existed, was tested, and was unreachable.

``PodcastHistory`` now answers for it, under **the same field names**, because
the alternative -- a second name for the same setting -- is exactly how the two
apps came to clamp one interval to two different ranges in the first place.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.podcasts import refresh_policy
from quill.core.podcasts.history import PodcastHistory, load_history, save_history


def test_the_check_is_off_until_asked_for() -> None:
    """An app that reaches the network on a schedule nobody chose is spending
    somebody else's data allowance."""
    history = PodcastHistory()
    assert history.podcast_check_enabled is False
    assert history.podcast_check_audible_tick is False
    assert history.podcast_check_interrupt_speech is False


def test_the_settings_survive_a_restart(tmp_path: Path) -> None:
    history = PodcastHistory()
    history.podcast_check_enabled = True
    history.podcast_check_interval_minutes = 180
    history.podcast_check_audible_tick = True
    history.podcast_check_interrupt_speech = True
    save_history(tmp_path, history)

    back = load_history(tmp_path)
    assert back.podcast_check_enabled is True
    assert back.podcast_check_interval_minutes == 180
    assert back.podcast_check_audible_tick is True
    assert back.podcast_check_interrupt_speech is True


def test_an_older_file_reads_as_never_asked_for(tmp_path: Path) -> None:
    (tmp_path / "podcast_history.json").write_text(
        json.dumps({"resume_on_launch": True}), encoding="utf-8"
    )
    history = load_history(tmp_path)
    assert history.podcast_check_enabled is False
    # Absent is *not* "manually only": an older file predates the setting, and
    # reading it as a choice would be inventing one nobody made.
    assert history.podcast_check_interval_minutes == 60


def test_manually_only_is_a_choice_and_survives(tmp_path: Path) -> None:
    (tmp_path / "podcast_history.json").write_text(
        json.dumps({"podcast_check_interval_minutes": 0}), encoding="utf-8"
    )
    assert load_history(tmp_path).podcast_check_interval_minutes == 0


def test_a_hand_edited_interval_goes_through_the_shared_normalisation(tmp_path: Path) -> None:
    """One list, one clamping, one meaning -- the same Quill Radio uses."""
    (tmp_path / "podcast_history.json").write_text(
        json.dumps({"podcast_check_interval_minutes": 1}), encoding="utf-8"
    )
    assert load_history(tmp_path).podcast_check_interval_minutes == (
        refresh_policy.MIN_INTERVAL_MINUTES
    )


def test_junk_in_the_file_reads_as_manual_rather_than_crashing(tmp_path: Path) -> None:
    (tmp_path / "podcast_history.json").write_text(
        json.dumps({"podcast_check_interval_minutes": "every hour"}), encoding="utf-8"
    )
    assert load_history(tmp_path).podcast_check_interval_minutes == 0


def test_the_names_match_the_ones_the_monitor_reads() -> None:
    """The whole point: the monitor does not know which store answered it."""
    from quill.core.monitor_policy import MONITOR_PODCASTS, monitor_spec

    spec = monitor_spec(MONITOR_PODCASTS)
    history = PodcastHistory()
    for name in (spec.interval_setting, spec.tick_setting, spec.interrupt_setting):
        assert name and hasattr(history, name), name
    assert hasattr(history, "podcast_check_enabled")


def test_the_names_match_quills_own_settings() -> None:
    """Two stores, one vocabulary -- so neither app can drift from the other."""
    from quill.core.settings import Settings

    settings = Settings()
    history = PodcastHistory()
    for name in (
        "podcast_check_enabled",
        "podcast_check_interval_minutes",
        "podcast_check_audible_tick",
        "podcast_check_interrupt_speech",
    ):
        assert hasattr(settings, name) and hasattr(history, name), name
