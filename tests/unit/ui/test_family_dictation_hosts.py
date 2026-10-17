"""The four programs' side of the family's dictation settings (dict.md D-13).

QUILL and QUILL Lite through ``DictationExtrasMixin`` (one implementation for
both editors), QUILL Transcribe through ``TranscribeCommandsMixin`` and Quill
Inkwell through ``InkwellDictationMixin``: what is saved in one is taken by
another, quietly; a family file that cannot be written is said aloud.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.apps.inkwell_dictation import InkwellDictationMixin
from quill.apps.transcribe_commands import TranscribeCommandsMixin
from quill.core.windows_dictation.settings_fields import SHARE_FIELD, DictationSettings
from quill.ui.windows_dictation_extras import DictationExtrasMixin


class _Editor(DictationExtrasMixin):
    def __init__(self, app: str) -> None:
        self.settings = DictationSettings()
        self.app = app
        self.said: list[str] = []
        self.status: list[str] = []
        self.saves = 0

    def _dictation_settings(self) -> Any:
        return self.settings

    def _dictation_app(self) -> str:
        return self.app

    def _dictation_say(self, text: str) -> None:
        self.said.append(text)

    def _dictation_status(self, text: str) -> None:
        self.status.append(text)

    def _dictation_save_settings(self) -> None:
        self.saves += 1


class _Transcribe(TranscribeCommandsMixin):
    def __init__(self) -> None:
        self._settings = SimpleNamespace(dictation={})
        self.said: list[str] = []
        self.saves = 0

    def _save(self) -> None:
        self.saves += 1

    def _announce(self, text: str, **_kw: Any) -> None:
        self.said.append(text)


def _refuse_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import storage

    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(storage, "write_json_atomic", refuse)


def test_saved_in_quill_taken_by_quill_lite_quietly() -> None:
    quill, lite = _Editor("quill"), _Editor("lite")
    quill.settings.windows_dictation_speech_language = "es"
    setattr(quill.settings, SHARE_FIELD, "on")
    quill._dictation_share_settings()
    assert quill.said == []

    assert lite._dictation_take_family() is True
    assert lite.settings.windows_dictation_speech_language == "es"
    assert lite.saves == 1
    assert lite.status == ["Dictation settings updated from the family."]
    assert lite.said == []  # the status bar, not speech: the change is the person's own
    assert lite._dictation_take_family() is False


def test_transcribe_and_an_editor_both_directions() -> None:
    transcribe = _Transcribe()
    transcribe._set_dictation_field("windows_dictation_auto_punctuation", False)
    quill = _Editor("quill")
    assert quill._dictation_take_family() is True
    assert quill.settings.windows_dictation_auto_punctuation is False

    quill.settings.windows_dictation_speech_language = "es"
    quill._dictation_share_settings()
    assert transcribe.take_family_dictation() is True
    assert transcribe._settings.dictation["windows_dictation_speech_language"] == "es"
    assert transcribe.take_family_dictation() is False  # one stat a tick, nothing new


def test_transcribes_own_write_is_not_news_to_itself() -> None:
    transcribe = _Transcribe()
    transcribe._set_dictation_field("windows_dictation_speech_language", "es")
    saves = transcribe.saves
    assert transcribe.take_family_dictation() is False
    assert transcribe.saves == saves


def test_an_editor_says_when_the_family_file_cannot_be_written(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    quill = _Editor("quill")
    setattr(quill.settings, SHARE_FIELD, "on")
    _refuse_writes(monkeypatch)
    quill._dictation_share_settings()
    assert len(quill.said) == 1
    assert quill.said[0].startswith("Saved here, but the other QuillVille programs")
    assert "Access is denied" in quill.said[0]


def test_transcribe_says_when_the_family_file_cannot_be_written(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transcribe = _Transcribe()
    _refuse_writes(monkeypatch)
    transcribe._set_dictation_field("windows_dictation_speech_language", "es")
    assert transcribe.saves == 1  # its own copy is saved either way
    assert len(transcribe.said) == 1 and "Access is denied" in transcribe.said[0]


def test_inkwell_says_when_the_family_file_cannot_be_written(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = SimpleNamespace(_settings=SimpleNamespace(dictation={SHARE_FIELD: "on"}), said=[])
    host._announce = lambda text, **_kw: host.said.append(text)
    _refuse_writes(monkeypatch)
    InkwellDictationMixin._share_dictation(host)  # type: ignore[arg-type]
    assert len(host.said) == 1 and "Access is denied" in host.said[0]


def test_a_program_that_does_not_share_is_left_alone() -> None:
    quill = _Editor("quill")
    quill.settings.windows_dictation_speech_language = "es"
    setattr(quill.settings, SHARE_FIELD, "on")
    quill._dictation_share_settings()

    lite = _Editor("lite")
    setattr(lite.settings, SHARE_FIELD, "off")
    assert lite._dictation_take_family() is False
    assert lite.settings.windows_dictation_speech_language == "en"
