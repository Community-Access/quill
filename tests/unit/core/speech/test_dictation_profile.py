"""Tests for the user dictation profile (quill.core.speech.dictation_profile)."""

from __future__ import annotations

from quill.core.speech.dictation_profile import (
    TEMPLATE,
    DictationProfile,
    ensure_profile_file,
    load_profile,
    parse_profile,
)

SAMPLE = """\
# My profile

## Vocabulary
- GitHub
- wxPython
QUILL
github

## Replacements
new line => \\n
get hub => GitHub
smiley => :)

## Commands
save everything => file.save_all
bold that => format.bold
"""


def test_parse_vocabulary_dedupes_case_insensitively() -> None:
    profile = parse_profile(SAMPLE)
    # "github" duplicate of "GitHub" is dropped; order preserved.
    assert profile.vocabulary == ("GitHub", "wxPython", "QUILL")


def test_initial_prompt() -> None:
    profile = parse_profile(SAMPLE)
    assert profile.initial_prompt() == "Vocabulary: GitHub, wxPython, QUILL."


def test_initial_prompt_empty_without_vocabulary() -> None:
    assert DictationProfile().initial_prompt() == ""


def test_replacements_applied_in_order_case_insensitive() -> None:
    profile = parse_profile(SAMPLE)
    out = profile.apply_replacements("please open get hub and add a Smiley")
    assert "GitHub" in out
    assert ":)" in out


def test_replacement_newline_escape() -> None:
    profile = parse_profile(SAMPLE)
    out = profile.apply_replacements("first new line second")
    assert out == "first \n second"


def test_replacement_is_whole_word() -> None:
    profile = parse_profile("## Replacements\ncat => dog\n")
    # "category" must not become "dogegory".
    assert profile.apply_replacements("category cat") == "category dog"


def test_command_aliases_grouped_by_id() -> None:
    profile = parse_profile(SAMPLE)
    aliases = profile.command_aliases()
    assert aliases == {
        "file.save_all": ("save everything",),
        "format.bold": ("bold that",),
    }


def test_empty_document_is_empty_profile() -> None:
    profile = parse_profile("just some text\nno headings here")
    assert profile.is_empty


def test_load_missing_file_is_empty(tmp_path) -> None:
    assert load_profile(tmp_path / "nope.md").is_empty


def test_load_roundtrip(tmp_path) -> None:
    path = tmp_path / "dictation.md"
    path.write_text(SAMPLE, encoding="utf-8")
    profile = load_profile(path)
    assert profile.vocabulary == ("GitHub", "wxPython", "QUILL")
    assert not profile.is_empty


def test_ensure_profile_file_writes_template_once(tmp_path) -> None:
    path = tmp_path / "sub" / "dictation.md"
    created = ensure_profile_file(path)
    assert created == path
    assert path.is_file()
    # Editing then re-ensuring must not clobber the user's content.
    path.write_text("## Vocabulary\n- Mine\n", encoding="utf-8")
    ensure_profile_file(path)
    assert "Mine" in path.read_text(encoding="utf-8")


def test_template_parses_and_is_nonempty() -> None:
    profile = parse_profile(TEMPLATE)
    assert not profile.is_empty
    assert "QUILL" in profile.vocabulary
    assert profile.command_aliases().get("file.save_all") == ("save everything",)
