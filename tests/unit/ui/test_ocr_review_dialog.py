"""Source-contract test for the OCR review dialog (OCR-4).

The live ``wx.Dialog`` is not runtime-instantiated in tests; the repo validates
dialog wiring through source contracts. This asserts the dialog surfaces a
read-only text control for reviewing OCR results with Insert/Copy/Discard
actions and proper keyboard navigation.
"""

from __future__ import annotations

from pathlib import Path

DIALOG_SOURCE = (
    Path(__file__).resolve().parents[3] / "quill" / "ui" / "ocr_review_dialog.py"
).read_text(encoding="utf-8")

MAIN_FRAME_SOURCE = (
    Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py"
).read_text(encoding="utf-8")


def test_dialog_uses_readonly_multiline_textctrl() -> None:
    """The dialog must use wx.TextCtrl with TE_MULTILINE | TE_READONLY per instructions."""
    assert "wx.TextCtrl" in DIALOG_SOURCE
    assert "wx.TE_MULTILINE | wx.TE_READONLY" in DIALOG_SOURCE


def test_dialog_has_insert_copy_discard_buttons() -> None:
    """The dialog provides Insert, Copy, and Discard action buttons."""
    assert "wx.ID_OK" in DIALOG_SOURCE  # Insert button
    assert "wx.ID_COPY" in DIALOG_SOURCE  # Copy button
    assert "wx.ID_CANCEL" in DIALOG_SOURCE  # Discard button
    assert '"&Insert"' in DIALOG_SOURCE
    assert '"&Copy"' in DIALOG_SOURCE
    assert '"&Discard"' in DIALOG_SOURCE


def test_dialog_uses_dialog_contract() -> None:
    """The dialog follows the A11Y-4 dialog contract."""
    assert "apply_modal_ids" in DIALOG_SOURCE
    assert "show_modal_dialog" in DIALOG_SOURCE


def test_dialog_sets_default_button() -> None:
    """Insert button is the default (affirmative action)."""
    assert "SetDefault()" in DIALOG_SOURCE
    assert "affirmative_id=self._wx.ID_OK" in DIALOG_SOURCE


def test_dialog_binds_escape_key() -> None:
    """Escape key cancels the dialog."""
    assert "wx.EVT_CHAR_HOOK" in DIALOG_SOURCE
    assert "wx.WXK_ESCAPE" in DIALOG_SOURCE
    assert "escape_id=self._wx.ID_CANCEL" in DIALOG_SOURCE


def test_dialog_is_resizable() -> None:
    """Dialog supports resize for screen-reader users."""
    assert "wx.RESIZE_BORDER" in DIALOG_SOURCE


def test_main_frame_wires_ocr_review_dialog() -> None:
    """Main frame imports and uses the OCR review dialog."""
    assert "from quill.ui.ocr_review_dialog import OcrReviewDialog" in MAIN_FRAME_SOURCE
    assert "from quill.io.ocr import" in MAIN_FRAME_SOURCE
    assert "render_ocr_review" in MAIN_FRAME_SOURCE


def test_main_frame_shows_review_dialog_after_ocr() -> None:
    """Main frame displays the review dialog and handles Insert/Copy/Discard."""
    # Check that review text is rendered
    assert "render_ocr_review(ocr_result)" in MAIN_FRAME_SOURCE

    # Check that dialog is created and shown
    assert "OcrReviewDialog(self.frame, review_text)" in MAIN_FRAME_SOURCE
    assert ".show_modal()" in MAIN_FRAME_SOURCE

    # Check that all three actions are handled
    assert "if dialog_result == wx.ID_OK:" in MAIN_FRAME_SOURCE  # Insert
    assert "elif dialog_result == wx.ID_COPY:" in MAIN_FRAME_SOURCE  # Copy
    assert "else:" in MAIN_FRAME_SOURCE  # Discard


def test_main_frame_handles_insert_action() -> None:
    """Insert action creates new file and inserts OCR text."""
    assert "self.new_file()" in MAIN_FRAME_SOURCE
    assert "self._replace_document_text(ocr_result.text)" in MAIN_FRAME_SOURCE
    assert "OCR text inserted" in MAIN_FRAME_SOURCE


def test_main_frame_handles_copy_action() -> None:
    """Copy action copies OCR text to clipboard."""
    assert "wx.TheClipboard.Open()" in MAIN_FRAME_SOURCE
    assert "wx.TextDataObject(ocr_result.text)" in MAIN_FRAME_SOURCE
    assert "OCR text copied to clipboard" in MAIN_FRAME_SOURCE


def test_main_frame_handles_discard_action() -> None:
    """Discard action announces discard and does not insert text."""
    assert "OCR text discarded" in MAIN_FRAME_SOURCE
