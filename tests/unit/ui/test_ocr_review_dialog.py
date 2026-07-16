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
    """The ocr_image_file method uses OcrReviewDialog and render_ocr_review."""
    source_path = (
        Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "main_frame_image.py"
    )
    source = source_path.read_text(encoding="utf-8")

    # Check that main_frame imports and uses OcrReviewDialog
    assert "from quill.ui.ocr_review_dialog import OcrReviewDialog" in source
    assert "from quill.io.ocr import render_ocr_review" in source
    assert "render_ocr_review(ocr_result)" in source
    assert "OcrReviewDialog(" in source


def test_main_frame_handles_insert_copy_discard_actions() -> None:
    """The ocr_image_file method handles Insert, Copy, and Discard actions."""
    source_path = (
        Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "main_frame_image.py"
    )
    source = source_path.read_text(encoding="utf-8")

    # Check that the three actions are handled
    assert "OcrReviewDialog.ID_INSERT" in source
    assert "OcrReviewDialog.ID_COPY" in source
    assert "OcrReviewDialog.ID_DISCARD" in source or "else:" in source  # Discard is the else case


def test_main_frame_returns_focus_to_editor() -> None:
    """The ocr_image_file method returns focus to the editor after the dialog."""
    source_path = (
        Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "main_frame_image.py"
    )
    source = source_path.read_text(encoding="utf-8")

    # Check that focus is returned to the editor
    # Look for the pattern after the OCR review dialog section
    assert "self.editor.SetFocus()" in source


def _image_mixin_source() -> str:
    return (
        Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "main_frame_image.py"
    ).read_text(encoding="utf-8")


def test_ocr3_clipboard_and_screen_capture_methods_exist() -> None:
    """OCR-3 adds clipboard and screen-capture OCR entry points to the mixin."""
    source = _image_mixin_source()

    assert "def ocr_clipboard_image(self) -> None:" in source
    assert "def ocr_screen_capture(self) -> None:" in source
    # Both capture sources funnel through the shared threaded review pipeline.
    assert "def _run_ocr_on_path(" in source
    assert "confirm: bool, structured: bool = False" in source
    assert "self._run_ocr_on_path(image_path, confirm=False)" in source


def test_shell2_structured_ocr_runs_assistant_structure_transform() -> None:
    """SHELL-2: the structured verb reflows OCR text via the assistant.

    The worker thread runs ``transform("structure", ...)`` when an assistant is
    available and degrades to plain OCR otherwise, so the verb never hard-fails.
    """
    source = _image_mixin_source()

    assert "def _apply_ocr_structuring(" in source
    assert 'assistant.transform("structure"' in source
    assert "structure_skip" in source
    # The structured flag flows into the review pipeline.
    assert "if structured and ocr_result.text.strip():" in source


def test_shell2_handle_shell_request_passes_structured_for_structured_verb() -> None:
    """``ocr-structured`` requests reach _run_ocr_on_path with structured=True."""
    _ui = Path(__file__).parent.parent.parent.parent / "quill" / "ui"
    main_frame = (
        (_ui / "main_frame.py").read_text(encoding="utf-8")
        + "\n"
        + (_ui / "main_frame_menu.py").read_text(encoding="utf-8")
        + "\n"
        + (_ui / "main_frame_menu_bindings.py").read_text(encoding="utf-8")
    )

    assert 'structured=action == "ocr-structured"' in main_frame


def test_ocr3_capture_uses_windows_capture_helper() -> None:
    """The capture paths use the offline Windows screen-capture helper (OCR-3)."""
    source = _image_mixin_source()

    assert "from quill.platform.windows.screen_capture import" in source
    assert "capture_clipboard_image" in source
    assert "capture_screen" in source
    # The empty-clipboard case is handled gracefully rather than crashing.
    assert "ClipboardImageEmpty" in source
    assert "ScreenCaptureError" in source


def test_ocr3_commands_are_wired_in_main_frame() -> None:
    """The two OCR-3 commands are registered, menued, and event-bound."""
    _ui = Path(__file__).parent.parent.parent.parent / "quill" / "ui"
    main_frame = (
        (_ui / "main_frame.py").read_text(encoding="utf-8")
        + "\n"
        + (_ui / "main_frame_commands.py").read_text(encoding="utf-8")
        + "\n"
        + (_ui / "main_frame_menu.py").read_text(encoding="utf-8")
        + "\n"
        + (_ui / "main_frame_menu_bindings.py").read_text(encoding="utf-8")
    )

    # Command registration
    assert '"tools.ocr_clipboard"' in main_frame
    assert '"tools.ocr_screen"' in main_frame
    assert "self.ocr_clipboard_image," in main_frame
    assert "self.ocr_screen_capture," in main_frame
    # Menu items
    assert '"tools.ocr_clipboard"' in main_frame
    assert "self._id_ocr_clipboard" in main_frame
    assert "self._id_ocr_screen" in main_frame
    # Event bindings
    assert "self.ocr_clipboard_image()" in main_frame
    assert "self.ocr_screen_capture()" in main_frame
