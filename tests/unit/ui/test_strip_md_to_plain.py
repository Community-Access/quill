"""Tests for the lightweight markdown flattener used by the
Check-for-Updates dialog body (issue #605).

The flattener lives in :mod:`quill.core.text_utils` as
``strip_md_to_plain``, called from ``MainFrame._html_info`` (the
Check-for-Updates dialog body). The old symbol ``_md_to_plain``
imported from :mod:`quill.ui.info_pages` was removed in the
About-dialog rewrite for #260, which broke the Check-for-Updates
path; the new helper is the fix. The tests below exercise the
helper directly so they run without wxPython.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from quill.core.text_utils import strip_md_to_plain

MAIN_FRAME = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)
INFO_PAGES = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "info_pages.py").read_text(
    encoding="utf-8"
)


# ---------------------------------------------------------------------------
# Behavioural tests
# ---------------------------------------------------------------------------


def test_strips_simple_heading_and_preserves_underline() -> None:
    text = "# Update check failed\n\nCould not check for updates."
    out = strip_md_to_plain(text)
    assert "Update check failed" in out
    # H1 underline is '=' characters, length = min(len, 60)
    assert "=" in out.splitlines()[1]
    assert "Could not check for updates." in out


def test_h2_uses_dash_underline() -> None:
    text = "## Release notes\n\nNotes body."
    out = strip_md_to_plain(text)
    lines = out.splitlines()
    assert lines[0] == "Release notes"
    assert set(lines[1]) == {"-"}
    # and the length matches min(len("Release notes"), 60) = 13
    assert len(lines[1]) == len("Release notes")


def test_strips_double_asterisk_bold() -> None:
    text = "You're on the **beta** channel."
    assert strip_md_to_plain(text) == "You're on the beta channel."


def test_strips_inline_code_spans() -> None:
    text = "Could not check: `URLError: timeout`"
    assert strip_md_to_plain(text) == "Could not check: URLError: timeout"


def test_strips_markdown_link_and_keeps_label() -> None:
    text = "See [docs](https://example.com) for details."
    assert strip_md_to_plain(text) == "See docs (https://example.com) for details."


def test_preserves_bullet_lists_unchanged() -> None:
    text = "- one\n- two\n- three"
    assert strip_md_to_plain(text) == "- one\n- two\n- three"


def test_preserves_user_paragraphs_unchanged() -> None:
    text = "First paragraph.\n\nSecond paragraph."
    assert strip_md_to_plain(text) == text


def test_strips_trailing_two_space_line_break_marker() -> None:
    # The update dialog uses "  \n" for explicit line breaks. After splitting
    # on newlines the spaces are part of the previous line and the result
    # should still read cleanly.
    text = "**Channel:** Stable  \n**Version:** 0.7.0"
    out = strip_md_to_plain(text)
    assert "Channel: Stable" in out
    assert "Version: 0.7.0" in out


def test_empty_input_returns_empty_string() -> None:
    assert strip_md_to_plain("") == ""


def test_strips_inline_backticks_inside_code_fence_too() -> None:
    # The flattener applies its inline-backtick rule line-by-line after
    # splitting on newlines, so a fenced code block becomes a run of lines
    # each with the wrapping backticks stripped. This is acceptable because
    # the GLOW update notes and the Check-for-Updates dialog never use
    # fenced code, and a MessageDialog would render a fence poorly anyway.
    text = '```\n{\n  "key": "value"\n}\n```'
    out = strip_md_to_plain(text)
    assert "```" not in out
    assert '"key": "value"' in out


# ---------------------------------------------------------------------------
# Structural / source-pin tests
# ---------------------------------------------------------------------------


def test_html_info_calls_strip_md_to_plain() -> None:
    # #605 regression pin: the Check-for-Updates dialog body
    # (MainFrame._html_info) must go through strip_md_to_plain, not
    # through the dead _md_to_plain import from quill.ui.info_pages.
    body = re.search(
        r"def _html_info\(self, title: str, markdown_text: str\) -> None:.*?(?=^    def |\Z)",
        MAIN_FRAME,
        re.MULTILINE | re.DOTALL,
    )
    assert body is not None, "_html_info not found"
    assert "from quill.ui.info_pages import _md_to_plain" not in body.group(0)
    assert "strip_md_to_plain(markdown_text)" in body.group(0)


def test_strip_md_to_plain_lives_in_core_text_utils() -> None:
    # The helper has to live in quill.core (no wx import) so the test
    # can import it without instantiating MainFrame, and so other
    # dialogs in the future can call it without pulling in wx.
    text_utils = Path(__file__).resolve().parents[3] / "quill" / "core" / "text_utils.py"
    assert text_utils.exists()
    src = text_utils.read_text(encoding="utf-8")
    assert "def strip_md_to_plain" in src
    # And it is not nested inside a class.
    assert "class " not in src


def test_info_pages_does_not_re_expose_md_to_plain() -> None:
    # #260 pin: the About dialog rewrite removed _md_to_plain from
    # info_pages because it was flattening Markdown for JAWS Forms
    # mode. That pin must still hold, so we don't reintroduce the
    # symbol there and break the About dialog again.
    assert "def _md_to_plain" not in INFO_PAGES
    assert "_md_to_plain" not in INFO_PAGES


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
