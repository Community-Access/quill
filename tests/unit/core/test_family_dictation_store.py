"""One dictation settings store for the family, both directions (dict.md D-13).

``quill/core/windows_dictation/family_store.py``: written when Dictation
Settings is saved in any of QUILL, QUILL Lite, QUILL Transcribe and Quill
Inkwell; taken when another of them comes to the front. The conftest fixture
``_family_dictation_of_its_own`` gives each test its own family folder.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation import family_store
from quill.core.windows_dictation.family_store import (
    FILE_NAME,
    SHARED_FIELDS,
    FamilyDictationError,
    adopt,
    adopt_fields,
    family_dictation_dir,
    publish,
    publish_fields,
    read_shared,
    stamp,
)
from quill.core.windows_dictation.settings_fields import (
    FAMILY_LOCAL_FIELDS,
    SHARE_FIELD,
    DictationSettings,
    load_fields,
    settle_share,
    share_on,
    shares_by_default,
)


def _editor(**changes: Any) -> DictationSettings:
    """An editor's settings object (QUILL's and QUILL Lite's carry these fields)."""
    settings = DictationSettings()
    for name, value in changes.items():
        setattr(settings, name, value)
    return settings


def test_a_choice_saved_in_an_editor_reaches_transcribe() -> None:
    """QUILL to QUILL Transcribe: the direction the old hand-off never covered
    without Dictate in Other Programs."""
    quill = _editor(windows_dictation_auto_punctuation=False, **{SHARE_FIELD: "on"})
    assert publish(quill, app="quill") is True

    transcribe = {SHARE_FIELD: "on", "windows_dictation_working_tick": True}
    updated = adopt_fields(transcribe, app="transcribe")
    assert updated is not None
    assert updated["windows_dictation_auto_punctuation"] is False
    assert updated["windows_dictation_working_tick"] is True  # its own, untouched


def test_a_choice_saved_in_transcribe_reaches_an_editor() -> None:
    """QUILL Transcribe to QUILL: the direction that did not exist at all."""
    transcribe = {SHARE_FIELD: "on", "windows_dictation_speech_language": "es"}
    assert publish_fields(transcribe, app="transcribe") is True

    quill = _editor(**{SHARE_FIELD: "on"})
    assert adopt(quill, app="quill") is True
    assert quill.windows_dictation_speech_language == "es"
    assert adopt(quill, app="quill") is False  # nothing new the second time


def test_what_each_program_keeps_to_itself_is_never_written_or_taken() -> None:
    assert not FAMILY_LOCAL_FIELDS & SHARED_FIELDS
    quill = _editor(
        windows_dictation_working_tick=True,
        windows_dictation_openai_consent=True,
        **{SHARE_FIELD: "on"},
    )
    publish(quill, app="quill")
    raw = json.loads((family_dictation_dir() / FILE_NAME).read_text(encoding="utf-8"))
    assert not set(raw["dictation"]) & FAMILY_LOCAL_FIELDS
    assert raw["written_by"] == "quill" and raw["schema"] == family_store.SCHEMA

    lite = _editor(**{SHARE_FIELD: "on"})
    adopt(lite, app="lite")
    assert lite.windows_dictation_working_tick is False
    assert lite.windows_dictation_openai_consent is False  # consent is never shared


def test_sharing_off_neither_writes_nor_takes() -> None:
    publish_fields({SHARE_FIELD: "on", "windows_dictation_speech_language": "es"}, app="lite")
    before = (family_dictation_dir() / FILE_NAME).read_bytes()

    assert (
        publish_fields({SHARE_FIELD: "off", "windows_dictation_speech_language": "en"}, app="quill")
        is False
    )
    assert (family_dictation_dir() / FILE_NAME).read_bytes() == before
    assert adopt_fields({SHARE_FIELD: "off"}, app="quill") is None


def test_sharing_is_on_for_defaults_and_off_for_somebody_who_chose() -> None:
    """An upgrade never swaps somebody's choices for another program's."""
    assert shares_by_default({}) is True
    assert share_on(load_fields({})) is True
    chosen = {"windows_dictation_speech_language": "es"}
    assert shares_by_default(chosen) is False
    assert load_fields(chosen)[SHARE_FIELD] == "off"
    # A program-local difference (the working tick) is not a choice to protect.
    assert shares_by_default({"windows_dictation_working_tick": True}) is True


def test_settle_share_decides_before_the_first_change() -> None:
    """Changing a setting must not itself turn an undecided "on" into "off"."""
    stored: dict[str, Any] = {}
    settle_share(stored)
    assert stored[SHARE_FIELD] == "on"
    settings = _editor()
    settle_share(settings)
    settings.windows_dictation_speech_language = "es"
    assert share_on({SHARE_FIELD: settings.windows_dictation_share_family}) is True


def test_the_first_adopt_keeps_a_copy_of_the_programs_own_values() -> None:
    publish_fields({SHARE_FIELD: "on", "windows_dictation_speech_language": "es"}, app="quill")
    mine = {SHARE_FIELD: "on", "windows_dictation_auto_punctuation": False}
    assert adopt_fields(mine, app="transcribe") is not None
    backup = family_dictation_dir() / "before-sharing-transcribe.json"
    saved = json.loads(backup.read_text(encoding="utf-8"))
    assert saved["dictation"]["windows_dictation_auto_punctuation"] is False
    first = backup.read_bytes()

    publish_fields({SHARE_FIELD: "on", "windows_dictation_speech_language": "en"}, app="quill")
    adopt_fields({SHARE_FIELD: "on", "windows_dictation_speech_language": "es"}, app="transcribe")
    assert backup.read_bytes() == first  # once, never overwritten


def test_nothing_is_taken_when_the_copy_cannot_be_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    publish_fields({SHARE_FIELD: "on", "windows_dictation_speech_language": "es"}, app="quill")
    from quill.core import storage

    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(storage, "write_json_atomic", refuse)
    assert adopt_fields({SHARE_FIELD: "on"}, app="lite") is None


def test_a_write_that_fails_is_reported_not_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import storage

    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(storage, "write_json_atomic", refuse)
    with pytest.raises(FamilyDictationError) as caught:
        publish_fields({SHARE_FIELD: "on"}, app="quill")
    assert caught.value.code == "QUILL-DICTATION-FAMILY-WRITE"
    message = caught.value.sentence
    assert message.startswith("Saved here, but the other QuillVille programs will not see")
    assert "Access is denied" in message


def test_fields_a_newer_build_wrote_are_kept() -> None:
    folder = family_dictation_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / FILE_NAME).write_text(
        json.dumps({"schema": 1, "dictation": {"windows_dictation_future_thing": 7}}),
        encoding="utf-8",
    )
    publish_fields({SHARE_FIELD: "on", "windows_dictation_speech_language": "es"}, app="quill")
    raw = json.loads((folder / FILE_NAME).read_text(encoding="utf-8"))
    assert raw["dictation"]["windows_dictation_future_thing"] == 7
    assert read_shared()["windows_dictation_speech_language"] == "es"
    assert "windows_dictation_future_thing" not in read_shared()


def test_an_unreadable_family_file_changes_nothing() -> None:
    folder = family_dictation_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / FILE_NAME).write_text("{not json", encoding="utf-8")
    assert adopt_fields({SHARE_FIELD: "on"}, app="quill") is None


def test_stamp_changes_only_when_the_file_does(tmp_path: Path) -> None:
    del tmp_path
    assert stamp() is None
    publish_fields({SHARE_FIELD: "on"}, app="quill")
    first = stamp()
    assert first is not None and stamp() == first
