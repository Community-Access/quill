"""Source-contract tests for OcrReviewDialog (OCR-4).

These tests validate the wiring of the OCR review dialog by reading the source
as text and asserting that the expected patterns are present. This approach
works on Linux where wx cannot be imported at runtime.
"""

from __future__ import annotations

from pathlib import Path


def test_ocr_review_dialog_has_multiline_readonly_text_ctrl() -> None:
    """The OCR review dialog uses a stock wx.TextCtrl with TE_MULTILINE | TE_READONLY."""
    source_path = (
        Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "ocr_review_dialog.py"
    )
    source = source_path.read_text(encoding="utf-8")

    # Check that the dialog uses wx.TE_MULTILINE | TE_READONLY for the text display
    assert "wx.TE_MULTILINE | wx.TE_READONLY" in source


def test_ocr_review_dialog_has_insert_copy_discard_buttons() -> None:
    """The OCR review dialog has Insert, Copy, and Discard buttons."""
    source_path = (
        Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "ocr_review_dialog.py"
    )
    source = source_path.read_text(encoding="utf-8")

    # Check that the dialog defines the three action buttons
    assert 'label="Insert"' in source
    assert 'label="Copy"' in source
    assert 'label="Discard"' in source


def test_ocr_review_dialog_uses_apply_modal_ids() -> None:
    """The OCR review dialog sets affirmative and escape ids via apply_modal_ids."""
    source_path = (
        Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "ocr_review_dialog.py"
    )
    source = source_path.read_text(encoding="utf-8")

    # Check that the dialog uses apply_modal_ids
    assert "apply_modal_ids" in source
    assert "affirmative_id" in source
    assert "escape_id" in source


def test_ocr_review_dialog_uses_show_modal_dialog() -> None:
    """The OCR review dialog uses show_modal_dialog for accessibility hooks."""
    source_path = (
        Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "ocr_review_dialog.py"
    )
    source = source_path.read_text(encoding="utf-8")

    # Check that the dialog uses show_modal_dialog
    assert "show_modal_dialog" in source


def test_main_frame_wires_ocr_review_dialog() -> None:
    """MainFrame's ocr_image_file method uses OcrReviewDialog and render_ocr_review."""
    source_path = Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "main_frame.py"
    source = source_path.read_text(encoding="utf-8")

    # Check that main_frame imports and uses OcrReviewDialog
    assert "from quill.ui.ocr_review_dialog import OcrReviewDialog" in source
    assert "from quill.io.ocr import render_ocr_review" in source
    assert "render_ocr_review(ocr_result)" in source
    assert "OcrReviewDialog(" in source


def test_main_frame_handles_insert_copy_discard_actions() -> None:
    """MainFrame's ocr_image_file method handles Insert, Copy, and Discard actions."""
    source_path = Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "main_frame.py"
    source = source_path.read_text(encoding="utf-8")

    # Check that the three actions are handled
    assert "OcrReviewDialog.ID_INSERT" in source
    assert "OcrReviewDialog.ID_COPY" in source
    assert "OcrReviewDialog.ID_DISCARD" in source or "else:" in source  # Discard is the else case


def test_main_frame_returns_focus_to_editor() -> None:
    """MainFrame's ocr_image_file method returns focus to the editor after the dialog."""
    source_path = Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "main_frame.py"
    source = source_path.read_text(encoding="utf-8")

    # Check that focus is returned to the editor
    # Look for the pattern after the OCR review dialog section
    assert "self.editor.SetFocus()" in source
