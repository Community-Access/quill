"""Unit tests for the wx-free model upgrade advisor (Phase 3)."""

from __future__ import annotations

from quill.core.model_upgrade import UpgradeSuggestion, suggest_llm_upgrade


def test_low_ram_machine_on_small_model_gets_no_suggestion() -> None:
    # 4 GB machine is correctly on llama-3.2-1b; there is nothing to upgrade to.
    assert suggest_llm_upgrade("llama-3.2-1b", total_ram_gb=4.0) is None


def test_capable_machine_on_small_model_is_offered_the_upgrade() -> None:
    suggestion = suggest_llm_upgrade("llama-3.2-1b", total_ram_gb=16.0)
    assert suggestion is not None
    assert suggestion.from_id == "llama-3.2-1b"
    assert suggestion.to_id == "phi-4-mini"
    assert suggestion.extra_download_gb > 0
    # The prompt is complete, speakable, and reassures the current model still works.
    msg = suggestion.message()
    assert "Phi-4-mini" in msg
    assert "keeps working" in msg


def test_already_on_best_model_gets_no_suggestion() -> None:
    assert suggest_llm_upgrade("phi-4-mini", total_ram_gb=32.0) is None


def test_unknown_model_gets_no_suggestion() -> None:
    assert suggest_llm_upgrade("not-a-model", total_ram_gb=32.0) is None


def test_unknown_ram_gets_no_suggestion() -> None:
    assert suggest_llm_upgrade("llama-3.2-1b", total_ram_gb=0.0) is None
    assert suggest_llm_upgrade("llama-3.2-1b", total_ram_gb=-1.0) is None


def test_low_resource_mode_suppresses_nagging_upward() -> None:
    # Even on a big machine, if the user chose low-resource mode we never nag upward.
    assert suggest_llm_upgrade("llama-3.2-1b", total_ram_gb=32.0, low_resource_mode=True) is None


def test_suggestion_is_frozen_value() -> None:
    s = UpgradeSuggestion("a", "b", "B", 1.7, "because")
    assert "1.7 GB" in s.message()
