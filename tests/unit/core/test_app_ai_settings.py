"""Quill Radio's and QUILL Cast's own AI choice survives a save (codex.md 10A.6)."""

from __future__ import annotations

from pathlib import Path


def test_radio_keeps_its_own_ai_fields(tmp_path: Path) -> None:
    from quill.core.radio.history import RadioHistory
    from quill.core.radio.history_store import load_history, save_history

    history = RadioHistory()
    history.ai_connection = "own_key"
    history.ai_own_key_provider = "gemini"
    history.ai_own_key_model = "gemini-pro"
    history.ai_copilot_model = "auto"
    history.ai_privacy_accepted_version = 3
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert (loaded.ai_connection, loaded.ai_own_key_provider, loaded.ai_own_key_model) == (
        "own_key",
        "gemini",
        "gemini-pro",
    )
    assert loaded.ai_copilot_model == "auto"
    assert loaded.ai_privacy_accepted_version == 3


def test_an_unknown_radio_choice_reads_as_not_yet_decided(tmp_path: Path) -> None:
    import json

    from quill.core.radio.history_store import load_history

    (tmp_path / "radio_history.json").write_text(json.dumps({"ai_connection": "hal"}))
    assert load_history(tmp_path).ai_connection == ""


def test_cast_keeps_its_own_ai_choice(tmp_path: Path) -> None:
    from quill.core.podcasts.history import PodcastHistory, load_history, save_history

    history = PodcastHistory()
    history.ai_connection = "chatgpt"
    history.ai_codex_model = "gpt-5"
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert loaded.ai_connection == "chatgpt"
    assert loaded.ai_codex_model == "gpt-5"
