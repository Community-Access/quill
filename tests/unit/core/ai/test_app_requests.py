"""The small apps' request words and their own AI settings file (codex.md Phase 3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.ai.app_ai_settings import (
    AppAiSettings,
    load_app_ai_settings,
    save_app_ai_settings,
    seed_from_quill,
    settings_file,
)
from quill.core.ai.app_requests import (
    INKWELL_DOCUMENT_CHARS,
    TEXT_ONLY,
    alerts_preface,
    beacon_picture_question,
    go_out_prompt,
    inkwell_suggest_prompt,
    parse_suggestions,
    will_play_prompt,
)


def test_go_out_forbids_rewording_alerts_and_is_text_only() -> None:
    prompt = go_out_prompt("Place: Tucson\n")
    assert "Do not reword" in prompt and TEXT_ONLY in prompt
    assert prompt.endswith("Place: Tucson")


def test_alerts_preface_keeps_the_services_words() -> None:
    assert alerts_preface([]) == ""
    assert alerts_preface([("Heat Advisory", "until 8 PM")]) == (
        "Active alert, as the Weather Service wrote it: Heat Advisory: until 8 PM."
    )
    two = alerts_preface([("Flood Watch", ""), ("Wind Advisory", "")])
    assert two.startswith("Active alerts,") and "Flood Watch; Wind Advisory" in two


def test_will_play_names_the_device_or_the_usual_ones() -> None:
    assert "on this device: iPhone" in will_play_prompt("File: a.flac", "iPhone")
    assert "car stereo" in will_play_prompt("File: a.flac")


def test_inkwell_prompt_caps_the_document_and_lists_existing() -> None:
    prompt = inkwell_suggest_prompt("x" * (INKWELL_DOCUMENT_CHARS + 500), ["brb", "Addr"])
    assert prompt.split("Document:\n", 1)[1] == "x" * INKWELL_DOCUMENT_CHARS
    assert "Addr, brb" in prompt


def test_parse_suggestions_keeps_only_well_formed_new_pairs() -> None:
    answer = (
        "Here you go:\n"
        "- qa -> quality assurance\n"
        "2. `ty` => thank you\n"
        "brb -> be right back\n"
        "qa -> again\n"
        "x -> too short\n"
        "same -> same\n"
    )
    assert parse_suggestions(answer, existing=["BRB"]) == [
        ("qa", "quality assurance"),
        ("ty", "thank you"),
    ]


def test_beacon_question_carries_the_ocr_words() -> None:
    assert "already read" not in beacon_picture_question("")
    assert "Invoice 42" in beacon_picture_question("Invoice 42")


def test_settings_round_trip_in_the_apps_own_file(tmp_path: Path) -> None:
    settings = AppAiSettings(ai_connection="chatgpt", ai_picture_consent=["chatgpt"])
    save_app_ai_settings(tmp_path, "weather", settings)
    assert (tmp_path / "weather-ai.json").is_file()
    loaded = load_app_ai_settings(tmp_path, "weather")
    assert loaded.ai_connection == "chatgpt" and loaded.ai_picture_consent == ["chatgpt"]
    assert load_app_ai_settings(tmp_path, "converter").ai_connection == ""
    with pytest.raises(ValueError):
        settings_file("quill")


def test_seed_copies_names_once_never_a_key(tmp_path: Path) -> None:
    quill = tmp_path / "settings.json"
    quill.write_text(
        json.dumps({"ai_own_key_provider": "gemini", "ai_own_key_model": "gemini-x"}),
        encoding="utf-8",
    )
    settings = AppAiSettings()
    assert seed_from_quill(settings, quill) is True
    assert (settings.ai_own_key_provider, settings.ai_own_key_model) == ("gemini", "gemini-x")
    assert seed_from_quill(settings, quill) is False  # once
