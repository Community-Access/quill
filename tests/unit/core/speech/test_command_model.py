"""Tests for the small-command-model preference (service.preferred_command_model)."""

from __future__ import annotations

from quill.core.speech.service import preferred_command_model


def test_prefers_base_then_tiny_then_small() -> None:
    assert preferred_command_model(["small", "base", "tiny", "medium"]) == "base"
    assert preferred_command_model(["small", "tiny", "medium"]) == "tiny"
    assert preferred_command_model(["small", "medium", "large-v3"]) == "small"


def test_falls_back_to_first_when_no_small_tier() -> None:
    assert preferred_command_model(["medium", "large-v3"]) == "medium"


def test_empty_is_empty() -> None:
    assert preferred_command_model([]) == ""


def test_returns_a_member_of_the_input() -> None:
    ids = ["large-v3", "medium"]
    assert preferred_command_model(ids) in ids
