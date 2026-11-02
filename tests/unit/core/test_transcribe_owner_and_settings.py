"""QUILL Transcribe's wx-free half: the one-owner rule, its settings, its models.

The owner lock is a real operating-system file lock in a temporary folder: two
locks in one process collide exactly as two programs do, which is what lets
this test say "Transcribe and Inkwell never both own Dictate Anywhere".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core import dictation_owner
from quill.core.dictation_owner import OwnerLock, current_owner, send_request, take_requests
from quill.core.expansion.settings import InkwellSettings
from quill.core.expansion.settings import save_settings as save_inkwell
from quill.core.transcribe import models
from quill.core.transcribe.settings import (
    TranscribeSettings,
    load_settings,
    save_settings,
    take_from_inkwell,
)

# -- one owner ----------------------------------------------------------------- #


def test_only_one_app_owns_dictate_anywhere_at_a_time(tmp_path: Path) -> None:
    transcribe = OwnerLock("transcribe", folder=tmp_path)
    inkwell = OwnerLock("inkwell", folder=tmp_path)
    assert transcribe.claim()
    assert not inkwell.claim()
    assert current_owner(folder=tmp_path) == "transcribe"
    transcribe.release()
    assert current_owner(folder=tmp_path) == ""
    assert inkwell.claim()
    assert not transcribe.claim()
    assert current_owner(folder=tmp_path) == "inkwell"
    inkwell.release()


def test_claiming_twice_is_idempotent_and_release_is_safe_twice(tmp_path: Path) -> None:
    lock = OwnerLock("transcribe", folder=tmp_path)
    assert lock.claim() and lock.claim() and lock.held
    lock.release()
    lock.release()
    assert not lock.held


def test_a_note_left_behind_by_a_crash_names_nobody(tmp_path: Path) -> None:
    (tmp_path / "dictate-anywhere-owner.json").write_text(
        json.dumps({"app": "inkwell", "pid": 1}), encoding="utf-8"
    )
    assert current_owner(folder=tmp_path) == ""


def test_asking_who_owns_it_does_not_take_it(tmp_path: Path) -> None:
    assert current_owner(folder=tmp_path) == ""
    assert OwnerLock("inkwell", folder=tmp_path).claim()


def test_an_unknown_app_cannot_own_it(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        OwnerLock("radio", folder=tmp_path)


def test_requests_carry_one_known_word_and_nothing_else(tmp_path: Path) -> None:
    assert send_request("toggle", sender="inkwell", folder=tmp_path)
    assert not send_request("type hello", sender="inkwell", folder=tmp_path)
    # Quill Radio and Quill Cast may ask since Dictate Here (D-16); others may not.
    assert not send_request("toggle", sender="weather", folder=tmp_path)
    with (tmp_path / "dictate-anywhere-requests.jsonl").open("a", encoding="utf-8") as handle:
        handle.write('{"command": "toggle", "sender": "inkwell", "text": "secret"}\n')
        handle.write("not json\n")
        handle.write('{"command": "delete everything", "sender": "inkwell"}\n')
    requests = take_requests(folder=tmp_path)
    assert [(r.command, r.sender) for r in requests] == [
        ("toggle", "inkwell"),
        ("toggle", "inkwell"),
    ]
    assert take_requests(folder=tmp_path) == []


def test_an_oversized_request_file_is_thrown_away(tmp_path: Path) -> None:
    (tmp_path / "dictate-anywhere-requests.jsonl").write_text("x" * 20_000, encoding="utf-8")
    assert take_requests(folder=tmp_path) == []
    assert not (tmp_path / "dictate-anywhere-requests.jsonl").exists()


def test_the_command_list_has_no_way_to_carry_words() -> None:
    assert dictation_owner.COMMANDS == {"toggle", "start", "stop", "show"}


# -- settings ------------------------------------------------------------------ #


def test_settings_start_with_alt_shift_backslash_and_round_trip(tmp_path: Path) -> None:
    fresh = load_settings(tmp_path)
    assert fresh.dictation_hotkey == "Alt+Shift+\\" and not fresh.setup_done
    fresh.setup_done = True
    fresh.dictation_hotkey = "Ctrl+Alt+Shift+F9"
    fresh.dictation = {"windows_dictation_engine": "whisper", "stray": 1}
    save_settings(tmp_path, fresh)
    loaded = load_settings(tmp_path)
    assert loaded.setup_done and loaded.dictation_hotkey == "Ctrl+Alt+Shift+F9"
    assert loaded.dictation == {"windows_dictation_engine": "whisper"}


def test_an_emptied_key_stays_empty(tmp_path: Path) -> None:
    """No key is a choice the listener can make, and it is kept."""
    settings = load_settings(tmp_path)
    settings.dictation_hotkey = ""
    save_settings(tmp_path, settings)
    assert load_settings(tmp_path).dictation_hotkey == ""


def test_a_newer_file_is_read_and_never_written_over(tmp_path: Path) -> None:
    path = tmp_path / "transcribe.json"
    path.write_text(json.dumps({"schema_version": 99, "setup_done": True}), encoding="utf-8")
    settings = load_settings(tmp_path)
    assert settings.read_only and settings.setup_done
    settings.setup_done = False
    save_settings(tmp_path, settings)
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 99


def test_settings_never_hold_transcript_text_or_keys(tmp_path: Path) -> None:
    save_settings(tmp_path, TranscribeSettings())
    saved = json.loads((tmp_path / "transcribe.json").read_text(encoding="utf-8"))
    assert set(saved) == {
        "schema_version",
        "setup_done",
        "dictation_hotkey",
        "command_hotkey",  # D-1: the key's name, empty until chosen
        "status_hotkey",  # D-6: Dictation Status, Resume and Discard, empty until chosen
        "resume_hotkey",
        "discard_hotkey",
        "start_in_tray",
        "close_to_tray",
        "inkwell_checked",
        "dictation",
        # Its own AI choice (decision 2): names and flags, never a key or a token.
        "ai_connection",
        "ai_own_key_provider",
        "ai_own_key_model",
        "ai_copilot_model",
        "ai_codex_model",
        "ai_privacy_accepted_version",
        "ai_seeded",
        "ai_sign_in_noticed",
    }


# -- from Inkwell -------------------------------------------------------------- #


def _inkwell(tmp_path: Path, *, key: str = "Ctrl+Alt+Shift+F2") -> None:
    settings = InkwellSettings()
    settings.dictate_anywhere_hotkey = key
    settings.dictation = {"windows_dictation_engine": "whisper"}
    save_inkwell(tmp_path, settings)


def test_inkwells_dictate_anywhere_settings_come_over_once(tmp_path: Path) -> None:
    _inkwell(tmp_path)
    before = (tmp_path / "inkwell.json").read_bytes()
    settings = TranscribeSettings()
    notice = take_from_inkwell(settings, tmp_path)
    assert settings.dictation == {"windows_dictation_engine": "whisper"}
    assert settings.dictation_hotkey == "Ctrl+Alt+Shift+F2"
    assert "Quill Inkwell" in notice and "Ctrl+Alt+Shift+F2" in notice
    assert (tmp_path / "inkwell.json").read_bytes() == before  # never changed
    settings.dictation_hotkey = ""
    assert take_from_inkwell(settings, tmp_path) == ""  # idempotent
    assert settings.dictation_hotkey == ""


def test_transcribes_own_choices_win_over_inkwells(tmp_path: Path) -> None:
    _inkwell(tmp_path)
    settings = TranscribeSettings(
        dictation_hotkey="Ctrl+Alt+Shift+F9",
        dictation={"windows_dictation_engine": "moonshine"},
    )
    assert take_from_inkwell(settings, tmp_path) == ""
    assert settings.dictation_hotkey == "Ctrl+Alt+Shift+F9"
    assert settings.dictation == {"windows_dictation_engine": "moonshine"}


def test_no_inkwell_means_nothing_to_bring(tmp_path: Path) -> None:
    settings = TranscribeSettings()
    assert take_from_inkwell(settings, tmp_path) == ""
    assert settings.inkwell_checked


# -- models -------------------------------------------------------------------- #


def test_the_list_marks_every_model_local_or_not_and_ready_or_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(models, "_openai_ready", lambda: False)
    rows = models.model_rows()
    ids = [row.id for row in rows]
    assert ids[:3] == ["moonshine", "whisper", "windows"]
    assert "voice_typing" not in ids and "openai" not in ids
    assert all(row.local for row in rows)
    for row in rows:
        assert ("not downloaded" in row.label) == (not row.ready)
        assert "on this computer" in row.label
        # D-22: every model names its tier; Windows speech recognition is not a model.
        assert (row.tier in row.label) and bool(row.tier) == (row.id != "windows")
    assert rows[0].label.startswith("Moonshine (on this computer; Lightweight; ")


def test_openai_is_listed_only_with_a_key_and_says_where_speech_goes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(models, "_openai_ready", lambda: True)
    row = models.model_rows()[-1]
    assert row.id == "openai" and not row.local
    assert "sends your speech over the internet" in row.label


def test_a_chosen_model_that_is_not_here_is_refused_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.windows_dictation import model_store

    monkeypatch.setattr(model_store, "installed", lambda _model: False)
    problem = models.start_problem("whisper_small", "en", openai_consent=False)
    assert problem.startswith("Whisper small is not on this computer yet.")
    assert "use the built-in model this time" in problem


def test_openai_needs_consent_before_any_speech_is_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.windows_dictation import openai_models

    monkeypatch.setattr(openai_models, "load_key", lambda: "sk-test")
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    assert "not switched on" in models.start_problem("openai", "en", openai_consent=False)
    assert models.start_problem("openai", "en", openai_consent=True) == ""


def test_windows_voice_typing_is_not_transcribes_to_run() -> None:
    assert "Windows+H" in models.start_problem("voice_typing", "en", openai_consent=False)


def test_model_names_are_plain() -> None:
    assert models.model_name("moonshine") == "Moonshine"
    assert models.model_name("openai") == "OpenAI"
    assert models.model_name("whisper_small") == "Whisper small"
    assert models.FALLBACK_ENGINE == "moonshine"
