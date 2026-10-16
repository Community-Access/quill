"""D-24: the programs dictation never types into, and "Speech goes to OpenAI"."""

from __future__ import annotations

import pytest

from quill.core.expansion.targets import DENIED_PROCESSES
from quill.core.windows_dictation.engines import OPENAI_ENGINE, cloud_line, cloud_provider
from quill.core.windows_dictation.never_type import (
    DEFAULT_NEVER_TYPE,
    coerce_never_type,
    friendly_name,
    is_listed,
    normalise_image_name,
    refusal,
)
from quill.core.windows_dictation.settings_fields import DictationSettings, load_fields


@pytest.mark.parametrize(
    ("typed", "kept"),
    [
        ("keepass.exe", "keepass.exe"),
        ("KeePass", "keepass.exe"),
        ('  "C:\\Program Files\\KeePass\\KeePass.EXE"  ', "keepass.exe"),
        ("tool.com", "tool.com"),
        ("", ""),
        ("   ", ""),
        (None, ""),
        ("..", ""),
    ],
)
def test_a_name_is_kept_as_its_lower_case_file_name(typed: object, kept: str) -> None:
    assert normalise_image_name(typed) == kept


def test_the_list_starts_as_the_programs_expansion_already_refuses() -> None:
    assert set(DEFAULT_NEVER_TYPE) == set(DENIED_PROCESSES)
    assert DictationSettings().windows_dictation_never_type == list(DEFAULT_NEVER_TYPE)


def test_a_missing_or_hand_edited_value_is_the_default_but_an_emptied_list_stays_empty() -> None:
    assert coerce_never_type(None) == list(DEFAULT_NEVER_TYPE)
    assert coerce_never_type("keepass.exe") == list(DEFAULT_NEVER_TYPE)
    assert coerce_never_type([]) == []


def test_the_saved_list_is_cleaned_once_each_in_order() -> None:
    assert coerce_never_type(["Notepad", "notepad.exe", "", 7, "KeePass"]) == [
        "notepad.exe",
        "7.exe",
        "keepass.exe",
    ]


def test_load_fields_reads_the_list() -> None:
    assert load_fields({"windows_dictation_never_type": ["Word"]})[
        "windows_dictation_never_type"
    ] == ["word.exe"]
    assert load_fields({})["windows_dictation_never_type"] == list(DEFAULT_NEVER_TYPE)


def test_a_program_is_matched_by_file_name_and_never_by_anything_else() -> None:
    assert is_listed("KEEPASS.EXE", ["keepass.exe"])
    assert is_listed("keepass.exe", ["KeePass"])
    assert not is_listed("notepad.exe", ["keepass.exe"])
    assert not is_listed("", ["keepass.exe"])


def test_the_refusal_names_the_program_and_is_empty_when_not_listed() -> None:
    assert refusal("keepass.exe", ["keepass.exe"]) == (
        "Dictation does not type into KeePass. Move to another program."
    )
    assert refusal("logonui.exe", DEFAULT_NEVER_TYPE).startswith(
        "Dictation does not type into the Windows sign-in screen."
    )
    assert refusal("notepad.exe", ["keepass.exe"]) == ""


def test_an_unknown_program_is_said_as_its_file_name() -> None:
    assert friendly_name("Example") == "example.exe"


def test_only_a_cloud_engine_says_where_the_speech_goes() -> None:
    assert cloud_provider(OPENAI_ENGINE.id) == "OpenAI"
    assert cloud_line(OPENAI_ENGINE.id) == "Speech goes to OpenAI."
    assert cloud_line("sapi") == ""
