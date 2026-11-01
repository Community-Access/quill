"""Each QuillVille app's own AI choice survives a save (codex.md 10A.6)."""

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


def test_studio_keeps_its_own_ai_choice_and_picture_consent(tmp_path: Path) -> None:
    from quill.core.audio_studio.ai_settings import (
        StudioAiSettings,
        load_ai_settings,
        save_ai_settings,
    )

    settings = StudioAiSettings()
    settings.ai_connection = "own_key"
    settings.ai_own_key_provider = "gemini"
    settings.ai_picture_consent = ["own_key:gemini"]
    settings.ai_privacy_accepted_version = 2
    save_ai_settings(tmp_path, settings)
    loaded = load_ai_settings(tmp_path)
    assert (loaded.ai_connection, loaded.ai_own_key_provider) == ("own_key", "gemini")
    assert loaded.ai_picture_consent == ["own_key:gemini"]
    assert loaded.ai_privacy_accepted_version == 2


def test_an_unknown_studio_choice_reads_as_not_yet_decided(tmp_path: Path) -> None:
    import json

    from quill.core.audio_studio.ai_settings import SETTINGS_FILE, load_ai_settings

    (tmp_path / SETTINGS_FILE).write_text(json.dumps({"ai_connection": "hal"}))
    assert load_ai_settings(tmp_path).ai_connection == ""


def test_transcribe_keeps_its_own_ai_choice(tmp_path: Path) -> None:
    from quill.core.transcribe.settings import TranscribeSettings, load_settings, save_settings

    settings = TranscribeSettings()
    settings.ai_connection = "chatgpt"
    settings.ai_seeded = True
    settings.ai_sign_in_noticed = True
    save_settings(tmp_path, settings)
    loaded = load_settings(tmp_path)
    assert loaded.ai_connection == "chatgpt"
    assert loaded.ai_seeded and loaded.ai_sign_in_noticed


def test_the_picture_consent_is_per_connection_and_per_company() -> None:
    from quill.core.ai.picture_consent import consent_key, consent_sentence, given, needs_consent

    assert consent_sentence("QUILL Studio", "chatgpt") == (
        "Pictures you ask about in QUILL Studio go to OpenAI on your ChatGPT plan. "
        "Nothing is sent until you ask."
    )
    consented = given([], consent_key("own_key", "openai"))
    assert not needs_consent(consented, consent_key("own_key", "openai"))
    assert needs_consent(consented, consent_key("own_key", "gemini"))
    assert needs_consent(consented, consent_key("copilot"))
    assert given(consented, consent_key("own_key", "openai")) == consented
