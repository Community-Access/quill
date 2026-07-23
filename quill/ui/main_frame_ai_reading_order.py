"""Improve Reading Order — a document-scoped AI repair command (PRD §5.6).

`Tools > Improve Reading Order…` (also on the command palette) sends the current
document's text to the user's configured AI provider to repair a jumbled reading
order — a multi-column PDF, a page with sidebars or text boxes, or lines pulled
out of sequence — and opens the reflowed result as a **new, unsaved document**,
never touching the original. It always confirms before sending (naming the
provider and approximate size), refuses documents over a configurable page limit,
and is off in Safe Mode.

Extracted into its own mixin (GATE-11) rather than grown onto ``main_frame.py``.
Every method resolves ``self`` helpers that live on :class:`MainFrame`
(``self._ai_require_connection``, ``self._get_assistant``, ``self._show_message_box``,
``self._power_tools_open_text_in_new_buffer``, ``self.editor``, ``self.document``,
``self.settings``, ``self._safe_mode``) through the shared MRO.
"""

from __future__ import annotations


class ReadingOrderMixin:
    """The ``Tools > Improve Reading Order…`` command, mixed into MainFrame."""

    def open_ai_improve_reading_order(self) -> None:
        if getattr(self, "_safe_mode", False):
            self._set_status("Improve Reading Order is unavailable in Safe Mode.")
            return
        text = str(self.editor.GetValue())
        if not text.strip():
            self._set_status("Nothing to improve — open or type a document first.")
            return

        # Page guard (PRD default 40): refuse a document that is too large to send.
        pages = self._reading_order_page_count(text)
        limit = int(getattr(self.settings, "reading_order_max_pages", 40) or 40)
        if pages > limit:
            self._set_status(
                f"This document is about {pages} pages, over the {limit}-page limit for "
                f"Improve Reading Order. Raise the limit in Settings, or run it on a "
                f"smaller document."
            )
            return

        # Keyed AI choke point: offers setup when AI isn't configured, else returns
        # the connection so the confirmation can name the provider.
        result = self._ai_require_connection()
        if result is None:
            return
        conn, _api_key = result

        # Always confirm before sending (PRD §5.6): name the provider + approx size.
        if not self._confirm_reading_order_send(conn, pages, len(text)):
            self._set_status("Improve Reading Order cancelled — nothing was sent.")
            return

        self._set_status("Improving reading order… this can take a moment.")

        import threading

        def _run() -> None:
            import wx as _wx

            try:
                assistant = self._get_assistant()
                available, reason = assistant.is_available()
                if not available:
                    _wx.CallAfter(
                        self._set_status,
                        f"Improve Reading Order needs AI: {reason or 'AI is unavailable.'}",
                    )
                    return
                improved = assistant.transform("reading_order", text)
            except Exception as exc:  # noqa: BLE001 - surface any failure on the status line
                _wx.CallAfter(self._set_status, f"Improve Reading Order failed: {exc}")
                return
            if not improved or not improved.strip():
                _wx.CallAfter(
                    self._set_status, "Improve Reading Order returned no text; nothing changed."
                )
                return
            _wx.CallAfter(self._open_reading_order_result, improved)

        threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread

    def _reading_order_page_count(self, text: str) -> int:
        """Best-effort page count for the size guard: the PDF's real page count when
        known, else the form-feed page markers, else a word-based estimate."""
        from quill.core.navigation import estimate_page_count, page_starts

        meta = getattr(getattr(self, "document", None), "source_metadata", None) or {}
        try:
            pages = int(meta.get("page_count") or 0)
        except (TypeError, ValueError):
            pages = 0
        if pages > 0:
            return pages
        starts = page_starts(text)
        if len(starts) > 1:
            return len(starts)
        words_per_page = int(getattr(self.settings, "page_estimate_words_per_page", 300) or 300)
        return estimate_page_count(text, words_per_page)

    def _confirm_reading_order_send(self, conn: object, pages: int, chars: int) -> bool:
        """Ask before sending; name the provider/host and the approximate size."""
        wx = self._wx
        from quill.core.ai.providers import provider_display_name

        provider = str(getattr(conn, "provider", "") or "")
        name = provider_display_name(provider) if provider else "your configured AI provider"
        host = str(getattr(conn, "host", "") or "").strip()
        remote = host and "localhost" not in host and "127.0.0.1" not in host
        where = f" ({host})" if remote else ""
        size = f"about {pages} page" + ("" if pages == 1 else "s")
        message = (
            f"QUILL will send this document — {size} — to {name}{where} to repair its "
            f"reading order (reorder columns and out-of-sequence text). The result opens "
            f"as a new, unsaved document; your current document is not changed, and the "
            f"text is used only for this request.\n\nSend the document now?"
        )
        proceed = self._show_message_box(
            message,
            "Improve Reading Order",
            wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
        )
        return proceed == wx.YES

    def _open_reading_order_result(self, text: str) -> None:
        """Open the reflowed text as a new unsaved document (Save defaults to Save As)."""
        self._power_tools_open_text_in_new_buffer(
            text,
            "Reading order improved — opened as a new unsaved document (Save As to keep it).",
        )
