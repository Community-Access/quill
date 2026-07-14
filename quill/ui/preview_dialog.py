"""Preview and HTML-dialog surfaces — thin adapters over the published
``wx-accessible-webview`` library.

Quill's accessible WebView stack was extracted into the standalone
``wx-accessible-webview`` package so any wxPython app can reuse it. These
adapters keep Quill's original call sites working while delegating all the
WebView / HTML / ARIA / JS work to the library:

  * :data:`HtmlMessageDialog` — the library's ``AccessibleHtmlDialog`` (same
    ``(parent, title, body_html, buttons)`` constructor and ``show_modal()->int``).
  * :data:`SidePreview` — the library's live preview pane (``update`` / ``control``).
  * :class:`MarkdownPreviewDialog` — a modal preview (single Close button,
    optional anchor scroll, links open in the browser) built on the library.

Markdown -> HTML rendering stays in :mod:`quill.core.browser_preview`; the
library is deliberately dependency-light and renders whatever HTML it's given.
"""

from __future__ import annotations

import json

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

try:
    from wx_accessible_webview import (
        AccessibleHtmlDialog as _LibraryAccessibleHtmlDialog,
    )
    from wx_accessible_webview import (
        SidePreview,
    )

    AccessibleHtmlDialog = _LibraryAccessibleHtmlDialog

    _HAS_WEBVIEW_LIB = True
except ImportError:
    # Resilience: if the wx-accessible-webview package isn't installed, don't
    # crash Preview / About / update dialogs with a ModuleNotFoundError. Fall
    # back to wxPython's built-in wx.html.HtmlWindow (always present), which
    # renders basic HTML. Install wx-accessible-webview for the full accessible
    # WebView experience (run-from-source auto-installs it from requirements.txt).
    _HAS_WEBVIEW_LIB = False

    class AccessibleHtmlDialog:  # type: ignore[no-redef]
        """Minimal wx.html fallback used when wx-accessible-webview is absent."""

        def __init__(
            self,
            parent: object,
            title: str,
            body_html: str,
            buttons=None,
            *,
            size=(640, 560),
            open_links_externally: bool = True,
            lang: str = "en",
            styles: str | None = None,
        ) -> None:
            import wx
            import wx.html as wxhtml

            self._wx = wx
            self._result = wx.ID_CANCEL
            if not buttons:
                buttons = [("Close", wx.ID_CANCEL)]
            self.dialog = wx.Dialog(
                parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
            )
            self.dialog.SetName(title)
            self.dialog.SetSize(size)
            outer = wx.BoxSizer(wx.VERTICAL)
            view = wxhtml.HtmlWindow(self.dialog)
            view.SetName(title)
            view.SetPage("<html><body>" + (body_html or "") + "</body></html>")
            self._view = view
            outer.Add(view, 1, wx.EXPAND)
            row = wx.BoxSizer(wx.HORIZONTAL)
            row.AddStretchSpacer()
            buttons = list(buttons)
            for index, (label, return_id) in enumerate(buttons):
                button = wx.Button(self.dialog, return_id, label=label)
                if index == len(buttons) - 1:
                    button.SetDefault()
                button.Bind(wx.EVT_BUTTON, lambda _e, r=return_id: self._end(r))
                row.Add(button, 0, wx.LEFT, 8)
            outer.Add(row, 0, wx.EXPAND | wx.ALL, 12)
            self.dialog.SetSizer(outer)
            self.dialog.Bind(
                wx.EVT_CHAR_HOOK,
                lambda e: self._end(wx.ID_CANCEL) if e.GetKeyCode() == wx.WXK_ESCAPE else e.Skip(),
            )

        def _end(self, return_id: int) -> None:
            self._result = return_id
            self.dialog.EndModal(return_id)

        def show_modal(self) -> int:
            self.dialog.CentreOnParent()
            apply_modal_ids(  # dialog_button_contract: exempt
                self.dialog,
                affirmative_id=self._wx.ID_CANCEL,
                escape_id=self._wx.ID_CANCEL,
            )
            # Land initial focus on the readable content, not the Close button,
            # so screen-reader users enter the dialog on its text (FOCUS-001).
            try:
                self._view.SetFocus()
            except Exception:  # noqa: BLE001 - focus is best-effort
                pass
            try:
                show_modal_dialog(self.dialog, self.dialog.GetTitle())
            finally:
                self.dialog.Destroy()
            return self._result

    class SidePreview:  # type: ignore[no-redef]
        """Minimal wx.html fallback live-preview pane."""

        def __init__(
            self, parent: object, *, title: str = "Preview", on_return=None, **_kw
        ) -> None:
            import wx.html as wxhtml

            self._view = wxhtml.HtmlWindow(parent)
            self._view.SetName(title)

        @property
        def control(self):
            return self._view

        def update(self, body_html: str) -> None:
            self._view.SetPage("<html><body>" + (body_html or "") + "</body></html>")

        def focus(self) -> None:
            self._view.SetFocus()


def _build_accessible_dialog_body(
    body_html: str,
    *,
    start_anchor: str | None = None,
) -> str:
    """Optionally inject an anchor-scroll script into an HTML dialog body.

    The wx-accessible-webview library owns the WebView document structure,
    focus management, and keyboard bridging inside its dialogs.  Do not add
    focus calls, tabindex overrides, or keydown listeners here — they fight
    the library's own DOM and prevent screen readers (JAWS/NVDA) from entering
    virtual cursor mode.

    The only Quill-specific addition is scrolling to a heading anchor when
    ``MarkdownPreviewDialog`` is opened with ``start_anchor`` set.
    """
    if not start_anchor:
        return body_html or ""

    safe_anchor = json.dumps(start_anchor)
    script = (
        "<script>(function(){"
        "window.addEventListener('load',function(){"
        f"var n=document.getElementById({safe_anchor});"
        "if(n){n.scrollIntoView();}"
        "});"
        "})();</script>"
    )
    return (body_html or "") + script


class HtmlMessageDialog:
    """Thin Quill alias for AccessibleHtmlDialog.

    Passes ``body_html`` straight to the library — the library wraps it in
    ``<main id="content">`` and handles all focus and keyboard logic.
    """

    def __init__(
        self,
        parent: object,
        title: str,
        body_html: str,
        buttons=None,
        **kwargs,
    ) -> None:
        self._dialog = AccessibleHtmlDialog(
            parent,
            title,
            body_html or "",
            buttons,
            **kwargs,
        )

    def show_modal(self) -> int:
        return self._dialog.show_modal()


__all__ = ["HtmlMessageDialog", "SidePreview", "MarkdownPreviewDialog"]


class MarkdownPreviewDialog:
    """A modal preview of rendered Markdown/HTML, with a single Close button.

    ``start_anchor`` scrolls to a heading id on load; ``open_links_externally``
    opens ``http(s)`` links in the system browser. Built on the library's
    ``AccessibleHtmlDialog``.
    """

    def __init__(
        self,
        parent: object,
        title: str,
        body_html: str,
        start_anchor: str | None = None,
        open_links_externally: bool = False,
    ) -> None:
        import wx

        self._dialog = AccessibleHtmlDialog(
            parent,
            title,
            _build_accessible_dialog_body(body_html, start_anchor=start_anchor),
            [("Close", wx.ID_CANCEL)],
            size=(820, 760),
            open_links_externally=open_links_externally,
        )

    def show(self) -> None:
        self._dialog.show_modal()
