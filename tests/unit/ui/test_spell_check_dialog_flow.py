"""Source-contract tests for the F7 spelling review dialog (issue #129 successor).

wxPython cannot be imported headlessly, so these tests pin observable source
contracts rather than running the dialog. They replaced the old single-dialog
chooser checks when the guided SpellingReviewDialog was introduced.
"""

from __future__ import annotations

from pathlib import Path


def _main_frame_source() -> str:
    return Path("quill/ui/main_frame.py").read_text(encoding="utf-8")


def _spell_dialog_body() -> str:
    source = _main_frame_source()
    start = source.index("def open_spell_check_dialog")
    end = source.index("def _choose_misspelling_with_context")
    return source[start:end]


def test_f7_uses_guided_review_dialog() -> None:
    body = _spell_dialog_body()
    assert "SpellingReviewDialog" in body


def test_f7_builds_review_session() -> None:
    body = _spell_dialog_body()
    assert "ReviewSession" in body


def test_f7_handles_selection_scope() -> None:
    body = _spell_dialog_body()
    assert "GetSelection" in body
    assert "selected text" in body


def test_f7_reports_no_issues_when_clean() -> None:
    body = _spell_dialog_body()
    assert "is_complete" in body
    assert "No misspellings found" in body


def test_no_misspellings_announced_once() -> None:
    # #728: "No misspellings found" was spoken twice -- _set_status already
    # announces the message, and a redundant explicit _announce spoke it again.
    # The clean path must announce exactly once, via _set_status only.
    body = _spell_dialog_body()
    assert 'self._set_status("No misspellings found.")' in body
    assert 'self._announce("No misspellings found.")' not in body


def test_f7_invalidates_dictionary_cache_on_close() -> None:
    body = _spell_dialog_body()
    assert "_invalidate_spell_dictionary_cache" in body


def test_multi_word_chooser_button_names_the_corrections_action() -> None:
    """The original multi-word chooser still uses 'Show Corrections...' (unchanged)."""
    source = _main_frame_source()
    assert 'label="Show Corrections..."' in source
    assert 'label="Review Word"' not in source
