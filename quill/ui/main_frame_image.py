"""Image capture, OCR, and AI image description mixin for MainFrame.

Extracted from ``main_frame.py`` to keep that module under its GATE-11
module-size budget (the OCR-3 clipboard/screen capture work and the on-demand
image-description feature live here). The methods reference ``self`` attributes
and helpers that live on :class:`MainFrame` (``self._wx``, ``self.frame``,
``self.editor``, ``self.settings``, ``self._set_status``, ``self._announce``,
``self._region_tracker``, ``self._show_modal_dialog``,
``self._show_message_box``), so every call resolves identically through the
method-resolution order. No behavior changed for the existing file-OCR and
describe-image paths; OCR-3 adds clipboard and screen-capture OCR entry points
that share the same threaded review pipeline.
"""

from __future__ import annotations

import threading
from pathlib import Path


class ImageCaptureMixin:
    """Image-source picking, OCR, and AI description, mixed into MainFrame."""

    def ocr_image_file(self) -> None:
        """OCR an image chosen from a file with the built-in Windows engine."""
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "OCR image",
            wildcard=(
                "Image files (*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.bmp)|"
                "*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.bmp|All files (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "OCR Image") != wx.ID_OK:
                self._set_status("OCR cancelled")
                return
            image_path = Path(dialog.GetPath())
        self._run_ocr_on_path(image_path, confirm=True)

    def ocr_clipboard_image(self) -> None:
        """OCR the image currently on the clipboard (OCR-3)."""
        wx = self._wx
        import tempfile

        from quill.platform.windows.screen_capture import (
            ClipboardImageEmpty,
            ScreenCaptureError,
            capture_clipboard_image,
        )

        try:
            image_path = capture_clipboard_image(Path(tempfile.gettempdir()))
        except ClipboardImageEmpty:
            self._show_message_box(
                "There is no image on the clipboard. Copy an image first, then try again.",
                "OCR Clipboard Image",
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("No clipboard image")
            return
        except ScreenCaptureError as exc:
            self._show_message_box(str(exc), "OCR Clipboard Image", wx.ICON_ERROR | wx.OK)
            self._set_status("Clipboard OCR failed")
            return
        self._set_status("Reading clipboard image...")
        self._run_ocr_on_path(image_path, confirm=False)

    def ocr_screen_capture(self) -> None:
        """Capture the screen or active window and OCR it (OCR-3)."""
        wx = self._wx
        import tempfile

        from quill.platform.windows.screen_capture import (
            ScreenCaptureError,
            capture_screen,
        )

        targets = ["The whole screen", "The active window"]
        with wx.SingleChoiceDialog(
            self.frame, "Capture which area for OCR?", "OCR Screen Capture", targets
        ) as dlg:
            dlg.SetSelection(1)
            if self._show_modal_dialog(dlg, "OCR Screen Capture") != wx.ID_OK:
                self._set_status("OCR cancelled")
                return
            target = "screen" if dlg.GetSelection() == 0 else "active_window"
        try:
            image_path = capture_screen(Path(tempfile.gettempdir()), target)
        except ScreenCaptureError as exc:
            self._show_message_box(str(exc), "OCR Screen Capture", wx.ICON_ERROR | wx.OK)
            self._set_status("Screen OCR failed")
            return
        self._set_status("Reading screen capture...")
        self._run_ocr_on_path(image_path, confirm=False)

    def _run_ocr_on_path(
        self, image_path: Path, *, confirm: bool, structured: bool = False
    ) -> None:
        """Run OCR on ``image_path`` off-thread and show the review dialog.

        Shared by the file, clipboard, and screen-capture OCR entry points
        (OCR-3). When ``confirm`` is true the user is asked to approve the local
        OCR run first (the file path keeps its original confirmation); capture
        sources skip the prompt because the user already chose to capture.

        When ``structured`` is true (the "OCR with Quill (structured Markdown)"
        shell verb, SHELL-2), the recognized text is reflowed into structured
        Markdown by the configured assistant in the same worker thread. If no
        assistant is available the plain OCR text is used and the status note
        says so, so the verb always degrades safely.
        """
        wx = self._wx
        from quill.io.ocr import (
            OcrCancelledError,
            OcrFailedError,
            OcrUnavailableError,
            ocr_image,
        )

        if confirm:
            result = self._show_message_box(
                "Run OCR on this image locally with the built-in Windows engine?",
                "OCR Image",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            )
            if result != wx.YES:
                self._set_status("OCR cancelled")
                return
        progress_state: dict[str, object] = {
            "message": "Starting OCR...",
            "done": False,
            "error": None,
            "result": None,
            "structured": False,
        }
        cancel_requested = threading.Event()

        def run_ocr() -> None:
            try:
                ocr_result = ocr_image(
                    image_path,
                    on_progress=lambda message: progress_state.__setitem__("message", message),
                    cancel_requested=cancel_requested.is_set,
                )
                if structured and ocr_result.text.strip():
                    self._apply_ocr_structuring(ocr_result, progress_state)
                progress_state["result"] = ocr_result
            except OcrCancelledError as exc:
                progress_state["error"] = exc
            except (OcrUnavailableError, OcrFailedError) as exc:
                progress_state["error"] = exc
            finally:
                progress_state["done"] = True

        worker = threading.Thread(  # GATE-40-OK: OCR image worker; posts via CallAfter.
            target=run_ocr, name="ocr-image", daemon=True
        )
        worker.start()
        progress = wx.ProgressDialog(
            "OCR Image",
            str(progress_state["message"]),
            maximum=100,
            parent=self.frame,
            style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_ELAPSED_TIME | wx.PD_CAN_ABORT,
        )
        try:
            step = 10
            while not progress_state["done"]:
                keep_going, _ = progress.Update(step, str(progress_state["message"]))
                if not keep_going:
                    cancel_requested.set()
                wx.MilliSleep(100)
                step = min(90, step + 4)
            worker.join()
            error = progress_state["error"]
            if isinstance(error, OcrCancelledError):
                self._set_status("OCR cancelled")
                return
            if isinstance(error, OcrUnavailableError):
                self._show_message_box(str(error), "OCR Image", wx.ICON_INFORMATION | wx.OK)
                self._set_status("OCR unavailable")
                return
            if isinstance(error, OcrFailedError):
                self._show_message_box(str(error), "OCR Image", wx.ICON_ERROR | wx.OK)
                self._set_status("OCR failed")
                return
            ocr_result = progress_state["result"]
            if ocr_result is None:
                self._set_status("OCR failed")
                return
            progress.Update(90, "Opening OCR result")
        finally:
            cancel_requested.set()
            worker.join(timeout=0.5)
            progress.Destroy()

        # Show the OCR review dialog with Insert/Copy/Discard actions
        from quill.io.ocr import render_ocr_review
        from quill.ui.ocr_review_dialog import OcrReviewDialog

        rendered_text = render_ocr_review(ocr_result)
        was_structured = bool(progress_state.get("structured"))
        structure_skip = progress_state.get("structure_skip")
        review_title = "OCR Review (structured Markdown)" if was_structured else "OCR Review"
        review_dialog = OcrReviewDialog(self.frame, review_title, rendered_text)
        choice = review_dialog.show_modal(
            announce=self._announce,
            enter_region=self._region_tracker.enter,
            exit_region=self._region_tracker.exit,
        )

        if choice == OcrReviewDialog.ID_INSERT:
            # Insert at current cursor position
            pos = self.editor.GetInsertionPoint()
            self.editor.WriteText(ocr_result.text)
            self.editor.SetInsertionPoint(pos + len(ocr_result.text))
            if was_structured:
                self._set_status(f"Structured OCR text inserted ({ocr_result.engine})")
            elif structure_skip:
                self._set_status(
                    f"OCR text inserted, structuring skipped: {structure_skip} "
                    f"({ocr_result.engine})"
                )
            else:
                self._set_status(f"OCR text inserted ({ocr_result.engine})")
        elif choice == OcrReviewDialog.ID_COPY:
            # Copy to clipboard
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(ocr_result.text))
                wx.TheClipboard.Close()
                self._set_status(f"OCR text copied to clipboard ({ocr_result.engine})")
            else:
                self._set_status("Failed to copy to clipboard")
        else:
            # Discard
            self._set_status("OCR discarded")

        # Return focus to the editor
        self.editor.SetFocus()

    def _apply_ocr_structuring(self, ocr_result: object, progress_state: dict[str, object]) -> None:
        """Reflow OCR text into structured Markdown via the assistant (SHELL-2).

        Runs inside the OCR worker thread, so the network/model call stays off
        the UI thread and shares the existing progress dialog. Best-effort: any
        missing or unavailable assistant, or any transform failure, leaves the
        plain OCR text in place and records why in ``progress_state`` so the
        status line can tell the user the structured pass was skipped.
        """
        assistant = getattr(self, "_assistant", None)
        if assistant is None:
            progress_state["structure_skip"] = "no assistant configured"
            return
        try:
            available, reason = assistant.is_available()
        except Exception as exc:  # noqa: BLE001 - degrade to plain OCR
            progress_state["structure_skip"] = str(exc)
            return
        if not available:
            progress_state["structure_skip"] = reason or "assistant unavailable"
            return
        progress_state["message"] = "Structuring recognized text..."
        try:
            structured_text = assistant.transform("structure", ocr_result.text)
        except Exception as exc:  # noqa: BLE001 - degrade to plain OCR
            progress_state["structure_skip"] = str(exc)
            return
        if structured_text and structured_text.strip():
            ocr_result.text = structured_text
            progress_state["structured"] = True

    def _pick_image_source(self, title: str) -> Path | None:
        """Ask where the image comes from and return a path, or ``None``.

        Offers the three QUILL image sources — an image file, the current
        clipboard image, or a screen/active-window capture — and returns a
        concrete image path ready for OCR or AI description. Screen and
        clipboard captures are written to a temporary PNG via the Windows
        capture helper. Returns ``None`` when the user cancels or no image is
        available.
        """
        wx = self._wx
        sources = [
            "Image file...",
            "Clipboard image",
            "Capture the screen",
            "Capture active window",
        ]
        with wx.SingleChoiceDialog(self.frame, "Choose the image to use:", title, sources) as dlg:
            dlg.SetSelection(0)
            if self._show_modal_dialog(dlg, title) != wx.ID_OK:
                self._set_status(f"{title} cancelled")
                return None
            selection = dlg.GetSelection()
        if selection == 0:
            with wx.FileDialog(
                self.frame,
                title,
                wildcard=(
                    "Image files (*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.bmp;*.gif;*.webp;"
                    "*.heic;*.heif)|"
                    "*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.bmp;*.gif;*.webp;*.heic;*.heif|"
                    "All files (*.*)|*.*"
                ),
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as dialog:
                if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                    self._set_status(f"{title} cancelled")
                    return None
                return Path(dialog.GetPath())
        import tempfile

        from quill.platform.windows.screen_capture import (
            ClipboardImageEmpty,
            ScreenCaptureError,
            capture_clipboard_image,
            capture_screen,
        )

        dest = Path(tempfile.gettempdir())
        try:
            if selection == 1:
                return capture_clipboard_image(dest)
            if selection == 2:
                return capture_screen(dest, "screen")
            return capture_screen(dest, "active_window")
        except ClipboardImageEmpty:
            self._show_message_box(
                "There is no image on the clipboard. Copy an image first, then try again.",
                title,
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("No clipboard image")
            return None
        except ScreenCaptureError as exc:
            self._show_message_box(str(exc), title, wx.ICON_ERROR | wx.OK)
            self._set_status(f"{title} failed")
            return None

    def describe_image_with_ai(self) -> None:
        """Describe an image on demand with the configured vision model (AI).

        Lets the user pick an image (file, clipboard, or screen capture), sends
        it to the connected AI provider's vision model, and offers the written
        description for insertion, copy, or discard through the shared review
        dialog. The request runs off the UI thread with a cancelable progress
        dialog so the editor stays responsive.
        """
        wx = self._wx
        _TITLE = "Describe Image"
        from quill.core.ai.model_manager import load_ai_enabled

        if not load_ai_enabled():
            self._show_message_box(
                "AI is turned off. Turn it on from Tools > AI Assistant, then connect a "
                "vision-capable model to describe images.",
                _TITLE,
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("AI is off")
            return

        from quill.core.assistant_ai import (
            load_assistant_api_key,
            load_assistant_connection_settings,
        )

        connection = load_assistant_connection_settings()
        if connection.provider.strip().lower() == "off":
            self._show_message_box(
                "No AI provider is connected. Open AI Model & Connection and choose "
                "a vision-capable model, then try again.",
                _TITLE,
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("No AI provider connected")
            return

        image_path = self._pick_image_source(_TITLE)
        if image_path is None:
            return

        api_key = load_assistant_api_key()
        from quill.core.ai.vision import describe_image

        progress_state: dict[str, object] = {"done": False, "text": None, "error": None}

        def run_describe() -> None:
            try:
                text, error = describe_image(connection, api_key, image_path)
                progress_state["text"] = text
                progress_state["error"] = error
            except Exception as exc:  # noqa: BLE001 - surface any failure to the user
                progress_state["error"] = str(exc)
            finally:
                progress_state["done"] = True

        worker = threading.Thread(  # GATE-40-OK: image describe worker; posts via CallAfter.
            target=run_describe, name="describe-image", daemon=True
        )
        worker.start()
        progress = wx.ProgressDialog(
            _TITLE,
            "Asking the model to describe the image...",
            maximum=100,
            parent=self.frame,
            style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_ELAPSED_TIME,
        )
        try:
            step = 10
            while not progress_state["done"]:
                progress.Pulse("Asking the model to describe the image...")
                wx.MilliSleep(100)
                step = min(90, step + 4)
            worker.join()
        finally:
            progress.Destroy()

        error = progress_state["error"]
        if error:
            self._show_message_box(str(error), _TITLE, wx.ICON_ERROR | wx.OK)
            self._set_status("Image description failed")
            return
        description = progress_state["text"]
        if not description:
            self._set_status("No description returned")
            return

        from quill.ui.ocr_review_dialog import OcrReviewDialog

        review_dialog = OcrReviewDialog(self.frame, _TITLE, str(description))
        choice = review_dialog.show_modal(
            announce=self._announce,
            enter_region=self._region_tracker.enter,
            exit_region=self._region_tracker.exit,
        )
        if choice == OcrReviewDialog.ID_INSERT:
            pos = self.editor.GetInsertionPoint()
            self.editor.WriteText(str(description))
            self.editor.SetInsertionPoint(pos + len(str(description)))
            self._set_status("Image description inserted")
        elif choice == OcrReviewDialog.ID_COPY:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(str(description)))
                wx.TheClipboard.Close()
                self._set_status("Image description copied to clipboard")
            else:
                self._set_status("Failed to copy to clipboard")
        else:
            self._set_status("Image description discarded")
        self.editor.SetFocus()
