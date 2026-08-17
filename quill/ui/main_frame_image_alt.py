"""Image alt-text commands for MainFrame (#899): Insert Image with mandatory
alt text, and Describe Image at Cursor for whatever is already in the
document.

Extracted into a mixin (CQ-1). ``ImageAltMixin`` relies on ``self.editor``,
``self.frame``, ``self.document``, ``self._set_status``, ``self._announce``,
and ``self._document_is_read_only`` staying on ``MainFrame``.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.inline_image_alt import (
    build_image_html,
    build_image_markdown,
    describe_image,
    image_at_position,
)


class ImageAltMixin:
    """Insert Image (mandatory alt text) and Describe Image at Cursor."""

    def insert_image(self) -> None:
        if self._document_is_read_only():
            self._set_status("Document is read-only")
            return
        # Decide Markdown vs HTML up front so the dialog can offer HTML-only
        # sizing/caption fields, and so the markup we build matches the document.
        surface = self._resolve_structured_markup("an image")
        if surface is None:
            self._set_status("Image insertion cancelled")
            return

        from quill.ui.insert_image_dialog import InsertImageDialog

        ai_cb = self._ai_alt_text_for_path if self._ai_alt_text_available() else None
        dlg = InsertImageDialog(
            self.frame,
            announce_cb=self._announce,
            html_mode=(surface == "html"),
            ai_suggest_cb=ai_cb,
        )
        request = dlg.show_request()
        dlg.close()
        if request is None:
            return
        if surface == "html":
            markup = build_image_html(
                request.path,
                request.alt_text,
                decorative=request.decorative,
                width=request.width,
                height=request.height,
                responsive=request.responsive,
                caption=request.caption,
            )
        else:
            markup = build_image_markdown(
                request.path, request.alt_text, decorative=request.decorative
            )
        pos = self.editor.GetInsertionPoint()
        text = self.editor.GetValue()
        updated = text[:pos] + markup + text[pos:]
        self._replace_document_text(updated)
        self.document.set_text(updated)
        new_pos = pos + len(markup)
        self.editor.SetInsertionPoint(new_pos)
        self.editor.SetSelection(new_pos, new_pos)
        self._set_status(f"Image inserted ({surface}).")

    # ------------------------------------------------------------------
    # AI-assisted alt text (optional; reuses the cloud vision pipeline).

    def _ai_alt_text_available(self) -> bool:
        """True when an AI vision model can be called for alt text right now.

        Mirrors the describe-image gate (AI enabled + a provider connected) and
        adds the Safe Mode check the vision path itself omits -- AI must be off
        in Safe Mode. The API key is checked at call time, not here, so a locked
        key surfaces as a clear error rather than a silently missing button.
        """
        try:
            from quill.core.ai.model_manager import load_ai_enabled
            from quill.core.assistant_ai import (
                _safe_mode_active,
                load_assistant_connection_settings,
            )

            if _safe_mode_active():
                return False
            if not load_ai_enabled():
                return False
            conn = load_assistant_connection_settings()
            return conn.provider.strip().lower() != "off"
        except Exception:
            return False

    def _ai_alt_text_for_path(self, image_path: str) -> tuple[str | None, str | None]:
        """Describe an image file with AI; return ``(alt_text, error_message)``.

        Runs the blocking vision call off the UI thread behind a pulsing
        progress dialog, exactly as the existing Describe Image flow does.
        """
        try:
            from quill.core.ai.model_manager import load_ai_enabled
            from quill.core.ai.vision import DEFAULT_IMAGE_DESCRIPTION_PROMPT
            from quill.core.assistant_ai import (
                _safe_mode_active,
                load_assistant_api_key,
                load_assistant_connection_settings,
            )
        except Exception as exc:  # pragma: no cover - import guard
            return None, f"AI image description is unavailable: {exc}"

        if _safe_mode_active():
            return None, "AI is disabled in Safe Mode."
        if not load_ai_enabled():
            return None, "AI features are turned off."
        conn = load_assistant_connection_settings()
        if conn.provider.strip().lower() == "off":
            return None, "No AI provider is connected. Set one up in Preferences."
        api_key = load_assistant_api_key()
        if not api_key and conn.provider.strip().lower() not in {"ollama", "ollama_cloud"}:
            return None, "The AI API key could not be unlocked on this account."

        path = Path(image_path)
        if not path.is_file():
            return None, "That image file could not be found."

        return self._run_vision_describe(conn, api_key, path, DEFAULT_IMAGE_DESCRIPTION_PROMPT)

    def _run_vision_describe(
        self, conn: object, api_key: str, path: Path, prompt: str
    ) -> tuple[str | None, str | None]:
        """Run the blocking describe_image call on a worker thread with progress."""
        import threading

        from quill.core.ai.vision import describe_image as _describe

        wx = self._wx
        outcome: dict[str, tuple[str | None, str | None]] = {}

        def _worker() -> None:
            try:
                outcome["result"] = _describe(conn, api_key, path, prompt=prompt)
            except Exception as exc:  # pragma: no cover - network/runtime guard
                outcome["result"] = (None, f"AI description failed: {exc}")

        # GATE-40-OK below: one-shot describe with its own modal progress; the
        # outcome dict is polled on the UI thread and the dialog is the cancel.
        thread = threading.Thread(target=_worker, daemon=True)  # GATE-40-OK: see above
        progress = wx.ProgressDialog(
            "Describing image",
            "Asking AI to describe this image...",
            maximum=100,
            parent=self.frame,
            style=wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME,
        )
        try:
            thread.start()
            while thread.is_alive():
                progress.Pulse()
                wx.MilliSleep(80)
                wx.SafeYield(self.frame, onlyIfNeeded=True)
            thread.join(timeout=1.0)
        finally:
            progress.Destroy()
        return outcome.get("result", (None, "AI description did not complete."))

    def describe_image_at_cursor(self) -> None:
        text = self.editor.GetValue()
        position = self.editor.GetInsertionPoint()
        record = image_at_position(text, position)
        if record is None:
            self._set_status("No image at the cursor.")
            return
        self._set_status(describe_image(record))
