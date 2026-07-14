"""Tests for the shared Markdown fence helpers (#307)."""

from __future__ import annotations

from quill.core.markdown_fences import fence_open_char, is_fence_line


def test_three_backticks_is_a_fence() -> None:
    assert is_fence_line("```") is True
    assert fence_open_char("```") == "`"


def test_four_backticks_is_a_fence() -> None:
    assert is_fence_line("````python") is True
    assert fence_open_char("````python") == "`"


def test_tilde_fence_is_a_fence() -> None:
    assert is_fence_line("~~~") is True
    assert fence_open_char("~~~") == "~"


def test_indented_fence_recognised_up_to_three_spaces() -> None:
    assert is_fence_line("   ```") is True
    assert is_fence_line("    ```") is False  # four-space indent: code, not fence


def test_two_backticks_is_not_a_fence() -> None:
    assert is_fence_line("``") is False
    assert fence_open_char("``") is None


def test_plain_text_is_not_a_fence() -> None:
    assert is_fence_line("hello") is False
    assert fence_open_char("hello") is None


def test_fence_line_strips_trailing_newline() -> None:
    assert is_fence_line("```\n") is True
    assert fence_open_char("```\r\n") == "`"
