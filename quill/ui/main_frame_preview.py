"""Previews on QUILL's main window: in the browser, in the app, and beside
the editor, with the WebView warmed up and kept in step with the document.

Moved whole out of ``MainFrame`` under qc.md F-08 (2026-10-03); the host
contract is unchanged. ``MainFrame._active_tab`` stays on the window: every
surface uses it. (A second, dead definition of it was removed in the move.)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from quill.core.browser_preview import (
    browser_choice_label_for_value,
    guess_preview_kind,
    normalize_browser_choice,
    open_preview_url,
    preview_anchor_for_text,
    render_preview_body,
    render_preview_html,
)
from quill.core.paths import app_data_dir


@dataclass(slots=True)
class _BrowserPreviewSession:
    tab_index: int
    preview_path: Path
    browser_choice: str
    title: str


class PreviewMixin:
    """Document previews; mixed into ``MainFrame``."""

    def toggle_side_preview(self) -> None:
        """Show / hide a live preview to the right of the editor (split view)."""
        tab = self._active_tab()
        if tab is None or getattr(tab, "splitter", None) is None:
            self._set_status("No document open")
            return
        splitter = tab.splitter
        if tab.preview is not None and splitter.IsSplit():
            splitter.Unsplit(tab.preview.control)
            self._set_status("Preview hidden")
            self.editor.SetFocus()
            self._set_active_region("Editor")
            return
        self._show_side_preview_for(tab)
        self._set_status("Preview shown on the right")

    def focus_preview(self) -> None:
        """Move focus into the preview pane (showing it first if needed).

        The editor is an edit field, so NVDA can't use browse-mode single-letter
        navigation there. The preview is a real web document, so once focus lands
        in it NVDA switches to browse mode and H / heading nav work natively.
        Press Escape or F6 in the preview to come back to the editor.
        """
        tab = self._active_tab()
        if tab is None or getattr(tab, "splitter", None) is None:
            self._set_status("No document open")
            return
        if tab.preview is None or not tab.splitter.IsSplit():
            self.toggle_side_preview()
        if tab.preview is not None and tab.splitter.IsSplit():
            tab.preview.control.SetFocus()
            self._set_active_region("Preview")
            self._set_status("Moved to preview. Press Escape or F6 to return to the editor.")

    def _focus_editor_from_preview(self) -> None:
        if self.editor is not None:
            self.editor.SetFocus()
            self._set_active_region("Editor")
            self._set_status("Back in the editor")

    def _refresh_side_preview(self, text: str | None = None) -> None:
        tab = self._active_tab()
        if tab is None:
            return
        splitter = getattr(tab, "splitter", None)
        if splitter is None:
            return
        if not splitter.IsSplit():
            if getattr(self.settings, "auto_side_preview", True):
                # #1346: the typing path already read the buffer; only fetch it
                # here when some other caller came in without one.
                if text is None:
                    text = tab.editor.GetValue()
                if guess_preview_kind(tab.document.path, text) != "plain":
                    self._show_side_preview_for(tab)
            return
        if tab.preview is None:
            return
        # Debounce: refresh shortly after typing pauses so each keystroke stays
        # snappy (re-rendering on every character can stutter the editor).
        timer = getattr(self, "_side_preview_timer", None)
        if timer is not None and timer.IsRunning():
            timer.Stop()
        self._side_preview_timer = self._wx.CallLater(250, self._update_side_preview, tab)

    def _update_side_preview(self, tab) -> None:
        raw = tab.editor.GetValue()
        kind = guess_preview_kind(tab.document.path, raw)
        text = self._vault_preview_text(raw, kind, tab.document.path)
        # Stamp editor source lines onto the preview blocks only when the
        # rendered text is the editor's text verbatim (#1257). Vault expansion
        # rewrites the markup, so its line offsets no longer point at the editor
        # buffer — leaving source mapping off there avoids a jump landing wrong.
        source_map = kind == "markdown" and text == raw
        try:
            tab.preview.update(
                render_preview_body(
                    text,
                    kind,
                    dark=self._preview_is_dark(),
                    source_map=source_map,
                    notes=True,  # the writer's own view shows notes in the file
                )
            )
        except Exception:
            # WebView2 can enter ERROR_INVALID_STATE (0x8007139f) after a forced
            # close or navigation error; JS/SetPage calls then raise. Discard the
            # faulted control and let _show_side_preview_for rebuild it.
            splitter = getattr(tab, "splitter", None)
            if splitter is not None and splitter.IsSplit():
                try:
                    splitter.Unsplit()
                except Exception:
                    pass
            tab.preview = None
            self._wx.CallAfter(self._show_side_preview_for, tab)

    def _preview_is_dark(self) -> bool:
        """Whether preview surfaces should render with the dark theme (issue #83).

        Dark mode themes the wx editor control; the preview is a separate
        WebView that otherwise stays light, leaving the split view half dark and
        half bright. Mirror the editor's dark state so both panes match.

        The default ``system`` theme follows the OS appearance, so a user on a
        dark desktop saw light preview panes with low-contrast blue links
        (issue #126). Resolve ``system`` against the live wx system appearance so
        the preview tracks the OS instead of staying bright.
        """
        theme = getattr(self.settings, "theme", "system")
        if theme == "dark":
            return True
        if theme in ("system", "auto"):
            return self._system_appearance_is_dark()
        return False

    def _system_appearance_is_dark(self) -> bool:
        """Best-effort detection of an OS-level dark appearance via wx."""
        getter = getattr(self._wx, "SystemSettings", None)
        appearance_getter = getattr(getter, "GetAppearance", None) if getter else None
        if callable(appearance_getter):
            try:
                appearance = appearance_getter()
            except Exception:  # noqa: BLE001 - probing must never crash the preview
                appearance = None
            for probe in ("IsDark", "IsUsingDarkBackground"):
                method = getattr(appearance, probe, None)
                if callable(method):
                    try:
                        return bool(method())
                    except Exception:  # noqa: BLE001
                        continue
        return False

    def _refresh_browser_preview(self) -> None:
        session = self._browser_preview_session
        if session is None:
            return
        if session.tab_index != self._active_tab_index:
            return
        # Debounce like the side preview: re-navigating the external browser on
        # every keystroke flickered the page and re-announced from the top for a
        # braille/screen-reader reader (the "meta refresh" feel). Coalescing to
        # shortly after typing pauses cuts the reload churn; the page also
        # restores scroll on reload (render_preview_html). The fully flicker-free
        # live option is the in-app side preview (F6): in-place WebView swap.
        timer = getattr(self, "_browser_preview_timer", None)
        if timer is not None and timer.IsRunning():
            timer.Stop()
        self._browser_preview_timer = self._wx.CallLater(400, self._do_refresh_browser_preview)

    def _do_refresh_browser_preview(self) -> None:
        session = self._browser_preview_session
        if session is None or session.tab_index != self._active_tab_index:
            return
        if session.tab_index < 0 or session.tab_index >= len(self._document_tabs):
            return
        # Rewrite the file only; never open the browser from the typing path
        # (that spawned a new tab on every pause — #780 review finding).
        self._write_browser_preview(session.tab_index)

    def _write_browser_preview(self, tab_index: int) -> tuple[Path, str]:
        """Render the tab's preview HTML to its stable on-disk path.

        Shared by the explicit Preview in Browser command and the silent
        keep-fresh path; only the explicit command opens the browser.
        Returns the file path and the page title.
        """
        tab = self._document_tabs[tab_index]
        text = tab.editor.GetValue()
        kind = guess_preview_kind(tab.document.path, text)
        anchor = preview_anchor_for_text(text, tab.editor.GetInsertionPoint(), kind)
        text = self._vault_preview_text(text, kind, tab.document.path)
        title = f"{tab.document.name or 'Preview'} - Browser Preview"
        preview_dir = app_data_dir() / "browser-preview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        safe_name = (
            re.sub(r"[^a-zA-Z0-9]+", "-", tab.document.name or "preview").strip("-") or "preview"
        )
        preview_path = preview_dir / f"{tab_index}-{safe_name}.html"
        payload = render_preview_html(title, text, kind, anchor)
        temp_path = preview_path.with_suffix(".tmp")
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, preview_path)
        return preview_path, title

    def preview_in_browser(self) -> None:
        if not self._document_tabs:
            self._set_status("No document open")
            return
        tab_index = (
            self._active_tab_index if self._active_tab_index >= 0 else self._current_tab_index()
        )
        if tab_index < 0 or tab_index >= len(self._document_tabs):
            self._set_status("No document open")
            return
        preview_path, title = self._write_browser_preview(tab_index)
        browser_choice = normalize_browser_choice(self.settings.preview_browser)
        session = self._browser_preview_session
        is_new = (
            session is None
            or session.tab_index != tab_index
            or session.preview_path != preview_path
            or session.browser_choice != browser_choice
        )
        # Opening the browser happens ONLY here, on the explicit user command.
        # The keep-fresh path (_do_refresh_browser_preview) rewrites the file so
        # a reload in the browser shows current text, but never opens a tab —
        # re-opening on every typing pause spammed new tabs (#780 review).
        open_preview_url(preview_path.as_uri(), browser_choice)
        self._browser_preview_session = _BrowserPreviewSession(
            tab_index=tab_index,
            preview_path=preview_path,
            browser_choice=browser_choice,
            title=title,
        )
        opened = f"Opened browser preview in {browser_choice_label_for_value(browser_choice)}"
        self._set_status(opened if is_new else "Refreshed browser preview")

    def preview_in_app(self) -> None:
        if not self._document_tabs:
            self._set_status("No document open")
            return
        tab_index = (
            self._active_tab_index if self._active_tab_index >= 0 else self._current_tab_index()
        )
        if tab_index < 0 or tab_index >= len(self._document_tabs):
            self._set_status("No document open")
            return
        tab = self._document_tabs[tab_index]
        text = tab.editor.GetValue()
        kind = guess_preview_kind(tab.document.path, text)
        anchor = preview_anchor_for_text(text, tab.editor.GetInsertionPoint(), kind)
        title = f"{tab.document.name or 'Preview'} - Preview"
        body = render_preview_body(
            self._vault_preview_text(text, kind, tab.document.path),
            kind,
            dark=self._preview_is_dark(),
            notes=True,
        )

        self._show_preview_in_app(title, body, anchor)

    def _show_preview_in_app(self, title: str, body: str, anchor: str | None) -> None:
        from quill.ui.preview_dialog import MarkdownPreviewDialog

        MarkdownPreviewDialog(self.frame, title, body, anchor).show()
        self._set_status("Opened preview")
