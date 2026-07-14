"""Tests for verbosity profiles and the announcement-verbosity bridge (§5-§6)."""

from __future__ import annotations

from quill.core.verbosity.channels import Channel
from quill.core.verbosity.profiles import (
    BEGINNER,
    BUILTIN_PROFILES,
    DEFAULT_PROFILE,
    EXPERT,
    NORMAL,
    QUIET,
    CustomProfile,
    SoundPolicy,
    active_profile,
    profile_for_announcement_verbosity,
)


def test_four_builtin_profiles_exposed() -> None:
    assert set(BUILTIN_PROFILES) == {"Beginner", "Normal", "Expert", "Quiet"}


def test_default_profile_is_normal() -> None:
    assert DEFAULT_PROFILE is NORMAL
    assert DEFAULT_PROFILE.name == "Normal"


def test_quiet_drops_speech_and_sound_but_keeps_floor() -> None:
    assert Channel.SPEECH not in QUIET.channels
    assert Channel.SOUND not in QUIET.channels
    assert Channel.BRAILLE in QUIET.channels
    assert Channel.VISUAL in QUIET.channels
    assert QUIET.sound_policy == SoundPolicy.OFF


def test_expert_suppresses_routine_and_is_errors_only_sound() -> None:
    assert EXPERT.suppress_routine
    assert EXPERT.sound_policy == SoundPolicy.ERRORS_ONLY


def test_beginner_is_full_context() -> None:
    assert not BEGINNER.suppress_routine
    assert BEGINNER.sound_policy == SoundPolicy.ALL


def test_announcement_verbosity_maps_to_ladder() -> None:
    # §1.1 read-side contract: the legacy knob has a real consumer.
    assert profile_for_announcement_verbosity("minimal") is EXPERT
    assert profile_for_announcement_verbosity("normal") is NORMAL
    assert profile_for_announcement_verbosity("verbose") is BEGINNER


def test_announcement_verbosity_unknown_falls_back_to_default() -> None:
    assert profile_for_announcement_verbosity("nonsense") is DEFAULT_PROFILE
    assert profile_for_announcement_verbosity("  VERBOSE  ") is BEGINNER


class _Settings:
    def __init__(self, value: str) -> None:
        self.announcement_verbosity = value


def test_active_profile_reads_settings() -> None:
    assert active_profile(_Settings("minimal")) is EXPERT
    assert active_profile(_Settings("verbose")) is BEGINNER


def test_custom_profile_round_trips_to_json() -> None:
    profile = CustomProfile(
        name="My Mix",
        base="Expert",
        channels=Channel.SPEECH | Channel.VISUAL,
        per_verb_overrides={"nav.next_line": "Quiet"},
        per_chord_overrides={"ctrl+s": "Normal"},
        templates={"Concise": "{line}"},
        data_order={"nav.next_line": ["line", "text"]},
    )
    restored = CustomProfile.from_dict(profile.to_dict())
    assert restored == profile


def test_custom_profile_defaults() -> None:
    profile = CustomProfile(name="Bare")
    data = profile.to_dict()
    assert data["base"] == "Normal"
    assert set(data["channels"]) == {"SPEECH", "BRAILLE", "SOUND", "VISUAL"}
    restored = CustomProfile.from_dict(data)
    assert restored == profile
