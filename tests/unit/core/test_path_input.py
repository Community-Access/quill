"""Shared path-field normalization (hardening pass)."""

from __future__ import annotations

import os

import pytest

from quill.core.path_input import clean_typed_path


def test_blank_input_returns_empty() -> None:
    assert clean_typed_path("") == ""
    assert clean_typed_path("   ") == ""


def test_strips_explorer_copy_as_path_quotes() -> None:
    assert clean_typed_path('"C:\\Users\\jeff\\notes.txt"') == "C:\\Users\\jeff\\notes.txt"
    assert clean_typed_path("'C:\\data'") == "C:\\data"


def test_strips_smart_quotes_from_web_paste() -> None:
    assert clean_typed_path("\u201cC:\\data\u201d") == "C:\\data"


def test_strips_nonbreaking_spaces() -> None:
    assert clean_typed_path("\u00a0C:\\data\u00a0") == "C:\\data"


def test_expands_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_TEST_DIR", "C:\\quilltest")
    expanded = clean_typed_path(
        "%QUILL_TEST_DIR%\\docs" if os.name == "nt" else "$QUILL_TEST_DIR/docs"
    )
    assert "QUILL_TEST_DIR" not in expanded
    assert "quilltest" in expanded


def test_expands_home_tilde() -> None:
    expanded = clean_typed_path("~")
    assert expanded == os.path.expanduser("~")


def test_converts_file_url_to_local_path() -> None:
    cleaned = clean_typed_path("file:///C:/Users/jeff/My%20Notes/a.txt")
    assert cleaned == os.sep.join(["C:", "Users", "jeff", "My Notes", "a.txt"])


def test_plain_paths_pass_through() -> None:
    assert clean_typed_path("C:\\plain\\path.txt") == "C:\\plain\\path.txt"
    assert clean_typed_path("relative/dir") == "relative/dir"


def test_never_raises_on_garbage() -> None:
    assert clean_typed_path("file:") != ""  # degenerate URL stays a string
    assert clean_typed_path('"') == '"'  # a lone quote is not a pair
