from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.ai.copilot_preferences import (
    CopilotPreferences,
    load_copilot_preferences,
    save_copilot_preferences,
)


def test_missing_preferences_use_privacy_preserving_defaults(tmp_path: Path) -> None:
    assert load_copilot_preferences(tmp_path) == CopilotPreferences()


def test_preferences_round_trip_per_app_data_directory(tmp_path: Path) -> None:
    preferences = CopilotPreferences(
        auto_tier="intelligence",
        keep_sessions=True,
        long_context=True,
        share_enabled_skills=True,
        resume_session_id="saved-session",
    )
    save_copilot_preferences(preferences, tmp_path)

    assert load_copilot_preferences(tmp_path) == preferences
    assert (tmp_path / "ai" / "copilot-preferences.json").is_file()


def test_invalid_saved_values_fall_back_without_enabling_optional_features(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ai" / "copilot-preferences.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"auto_tier":"unknown","keep_sessions":"yes","long_context":"yes",'
        '"share_enabled_skills":1}',
        encoding="utf-8",
    )

    assert load_copilot_preferences(tmp_path) == CopilotPreferences()


def test_resume_session_id_is_trimmed_and_malformed_values_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "ai" / "copilot-preferences.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"resume_session_id":"  saved-session  "}', encoding="utf-8")

    assert load_copilot_preferences(tmp_path).resume_session_id == "saved-session"

    path.write_text('{"resume_session_id": ["not", "an", "id"]}', encoding="utf-8")
    assert load_copilot_preferences(tmp_path).resume_session_id == ""


def test_saving_an_unknown_auto_tier_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown Copilot Auto tier"):
        save_copilot_preferences(CopilotPreferences(auto_tier="unbounded"), tmp_path)
