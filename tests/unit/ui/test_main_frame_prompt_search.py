"""Source-contract test for the _prompt_search dialog migration to show_web_form (DLG-1).

The live ``wx.Dialog`` is not runtime-instantiated in tests; the repo validates
dialog wiring through source contracts. This asserts that _prompt_search uses
show_web_form with the correct fields: query, optional replacement, mode choice,
and case-sensitive checkbox.
"""

from __future__ import annotations

from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_prompt_search_imports_show_web_form() -> None:
    assert "from quill.ui.web_form import show_web_form" in SOURCE


def test_prompt_search_uses_show_web_form() -> None:
    # Verify the function signature and show_web_form call exist
    assert "def _prompt_search(" in SOURCE
    # Check that show_web_form is called within _prompt_search
    prompt_search_start = SOURCE.index("def _prompt_search(")
    # Find the next function definition to bound the search
    next_def = SOURCE.index("\n    def ", prompt_search_start + 1)
    prompt_search_body = SOURCE[prompt_search_start:next_def]
    assert "show_web_form(" in prompt_search_body
    assert "values = show_web_form(" in prompt_search_body


def test_prompt_search_defines_required_fields() -> None:
    # Verify the field definitions exist in _prompt_search
    prompt_search_start = SOURCE.index("def _prompt_search(")
    next_def = SOURCE.index("\n    def ", prompt_search_start + 1)
    prompt_search_body = SOURCE[prompt_search_start:next_def]

    # Check for query field
    assert '"name": "query"' in prompt_search_body
    assert '"label": "Find text"' in prompt_search_body
    assert '"type": "text"' in prompt_search_body

    # Check for replacement field (conditional)
    assert '"name": "replacement"' in prompt_search_body
    assert '"label": "Replace with"' in prompt_search_body

    # Check for mode field
    assert '"name": "mode"' in prompt_search_body
    assert '"label": "Search mode"' in prompt_search_body
    assert '"type": "select"' in prompt_search_body

    # Check for case_sensitive field
    assert '"name": "case_sensitive"' in prompt_search_body
    assert '"label": "Case sensitive"' in prompt_search_body
    assert '"type": "checkbox"' in prompt_search_body


def test_prompt_search_handles_cancel_and_empty_query() -> None:
    # Verify cancel and empty query handling
    prompt_search_start = SOURCE.index("def _prompt_search(")
    next_def = SOURCE.index("\n    def ", prompt_search_start + 1)
    prompt_search_body = SOURCE[prompt_search_start:next_def]

    assert "if values is None:" in prompt_search_body
    assert "return None" in prompt_search_body
    assert "if not query:" in prompt_search_body


def test_prompt_search_builds_search_options() -> None:
    # Verify SearchOptions construction with correct mode mapping
    prompt_search_start = SOURCE.index("def _prompt_search(")
    next_def = SOURCE.index("\n    def ", prompt_search_start + 1)
    prompt_search_body = SOURCE[prompt_search_start:next_def]

    assert "SearchOptions(" in prompt_search_body
    assert 'whole_word=mode == "Whole word"' in prompt_search_body
    assert 'use_regex=mode == "Regular expression"' in prompt_search_body
    assert 'wildcard=mode == "Wildcard"' in prompt_search_body


def test_prompt_search_no_longer_uses_hand_rolled_dialog() -> None:
    # Verify the old wx.Dialog construction is removed
    prompt_search_start = SOURCE.index("def _prompt_search(")
    next_def = SOURCE.index("\n    def ", prompt_search_start + 1)
    prompt_search_body = SOURCE[prompt_search_start:next_def]

    # These patterns should NOT appear in the migrated version
    assert "wx.Dialog(self.frame" not in prompt_search_body
    assert "wx.Panel(dialog)" not in prompt_search_body
    assert "wx.TextCtrl(panel" not in prompt_search_body
    assert "dialog.CreateButtonSizer" not in prompt_search_body
    assert "dialog.Destroy()" not in prompt_search_body
