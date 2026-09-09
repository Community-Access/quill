"""The rule that decides where a live spell checker keeps quiet.

Shared by QUILL and QuillLite, so it is tested once, here, rather than twice
against two products that could then disagree.

This is not a cosmetic preference. Spell-check-as-you-type in a source or
configuration file flags every identifier, key, tag and flag, and none of those
alerts are right. A sighted user learns to ignore an underline; a screen-reader
user pays an interruption for each one, which is why QUILL's live alert and
QuillLite's both consult this before saying anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.spellcheck_filetypes import (
    CODE_SUFFIXES,
    is_code_filename,
    live_check_default_for,
)


@pytest.mark.parametrize(
    "name",
    [
        "main.py",
        "settings.json",
        "tsconfig.json",
        "app.tsx",
        "index.html",
        "theme.css",
        "build.ps1",
        "Makefile.mk",
        "schema.sql",
        "output.log",
        "data.csv",
        "docker-compose.yml",
    ],
)
def test_code_and_configuration_are_skipped(name: str) -> None:
    assert is_code_filename(name) is True
    assert live_check_default_for(name) is False


@pytest.mark.parametrize(
    "name",
    ["letter.txt", "chapter.rtf", "notes.md", "README", "minutes.text", "essay.doc"],
)
def test_prose_is_checked(name: str) -> None:
    assert is_code_filename(name) is False
    assert live_check_default_for(name) is True


def test_the_two_functions_are_exact_opposites() -> None:
    """``live_check_default_for`` exists only so no caller writes the negation."""
    for name in ("a.py", "a.txt", "a", None):
        assert live_check_default_for(name) is not is_code_filename(name)


def test_none_is_prose() -> None:
    """A never-saved document has no name to judge, and prose is the safer guess."""
    assert live_check_default_for(None) is True


def test_markdown_is_deliberately_absent_from_the_code_list() -> None:
    """Regression guard on the one judgement call in the table.

    Markdown is where people write; its code *regions* are suppressed by
    quill.core.spellcheck_live instead. Adding ".md" here would silence the
    prose as well as the code, which is the wrong half.
    """
    assert ".md" not in CODE_SUFFIXES
    assert ".markdown" not in CODE_SUFFIXES
    assert ".txt" not in CODE_SUFFIXES
    assert ".rtf" not in CODE_SUFFIXES


def test_every_entry_is_a_lowercase_dotted_suffix() -> None:
    """A stray ``py`` or ``.PY`` in the table would never match anything.

    ``Path.suffix`` yields a leading dot and the lookup lowercases, so an entry
    in any other shape is dead weight that reads as coverage.
    """
    for suffix in CODE_SUFFIXES:
        assert suffix.startswith("."), suffix
        assert suffix == suffix.lower(), suffix
        assert " " not in suffix, suffix


def test_a_path_object_and_a_string_agree() -> None:
    assert is_code_filename(Path("a/b/c.py")) is is_code_filename("a/b/c.py") is True


def test_quill_settings_carries_the_switch_and_defaults_to_skipping() -> None:
    """QUILL reaches the rule through a setting, so it can be turned off."""
    from quill.core.settings import Settings

    assert Settings().spellcheck_skip_code_files is True
