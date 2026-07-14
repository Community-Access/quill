"""Round-trip tests for the verbosity settings fields (§35, sub-PR 1.5)."""

from __future__ import annotations

from dataclasses import asdict

from quill.core.settings import Settings


def test_defaults() -> None:
    s = Settings()
    assert s.verbosity_mastery_enabled is True
    assert s.verbosity_mastery_threshold == 25
    assert s.verbosity_validation_mode == "on_button"
    assert s.verbosity_history_enabled is True
    assert s.verbosity_history_limit == 100
    assert s.verbosity_history_clear_on_exit is False
    assert s.verbosity_task_profile_suggestions is False
    assert s.verbosity_safe_mode_enabled is False


def test_round_trip_through_from_dict() -> None:
    s = Settings(
        verbosity_mastery_enabled=False,
        verbosity_mastery_threshold=40,
        verbosity_validation_mode="live",
        verbosity_history_enabled=False,
        verbosity_history_limit=250,
        verbosity_history_clear_on_exit=True,
        verbosity_task_profile_suggestions=True,
        verbosity_safe_mode_enabled=True,
    )
    restored = Settings.from_dict(asdict(s))
    assert restored.verbosity_mastery_enabled is False
    assert restored.verbosity_mastery_threshold == 40
    assert restored.verbosity_validation_mode == "live"
    assert restored.verbosity_history_limit == 250
    assert restored.verbosity_task_profile_suggestions is True
    assert restored.verbosity_safe_mode_enabled is True


def test_validation_mode_falls_back_on_garbage() -> None:
    restored = Settings.from_dict({"verbosity_validation_mode": "nonsense"})
    assert restored.verbosity_validation_mode == "on_button"


def test_threshold_clamped() -> None:
    assert (
        Settings.from_dict({"verbosity_mastery_threshold": 99999}).verbosity_mastery_threshold
        == 1000
    )
    assert Settings.from_dict({"verbosity_mastery_threshold": 0}).verbosity_mastery_threshold == 1


def test_history_limit_clamped() -> None:
    assert Settings.from_dict({"verbosity_history_limit": 0}).verbosity_history_limit == 1
