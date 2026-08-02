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
        AccessibleWebView,
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


# Delegated listener injected into the live side preview so a block a
# screen-reader user lands on can hand its source line back to Python (#1257).
# It attaches once to the persistent ``#content`` element (which survives every
# in-place ``innerHTML`` re-render), walks up from the event target to the
# nearest ``[data-src]`` block, and posts the source line + a short label.
#
#   * contextmenu (right-click / Applications key / Shift+F10) is the reliable
#     path under a screen reader's browse mode: it targets the element at the
#     virtual cursor, and we ``preventDefault`` so Quill's own menu replaces the
#     native WebView2 one. When there is no mapped block under the cursor we let
#     the native menu through untouched.
#   * Enter is offered as a convenience for keyboard users; browse mode may
#     swallow it, so it is a bonus, not the contract.
_SOURCE_NAV_JS = """
(function(){
  if (window.__quillSrcNav) { return; }
  window.__quillSrcNav = 1;
  var content = document.getElementById('content');
  if (!content) { return; }
  function nearest(node){
    while (node && node !== content){
      if (node.nodeType === 1 && node.hasAttribute && node.hasAttribute('data-src')){
        return node;
      }
      node = node.parentNode;
    }
    return null;
  }
  function label(el){
    var t = (el.textContent || '').replace(/\\s+/g, ' ').trim();
    return t.length > 80 ? t.slice(0, 79) + '\\u2026' : t;
  }
  function post(el, trigger){
    if (!(window.awv && window.awv.postMessage)) { return; }
    window.awv.postMessage(JSON.stringify({
      type: 'quill-goto-source',
      trigger: trigger,
      src: parseInt(el.getAttribute('data-src'), 10),
      label: label(el)
    }));
  }
  content.addEventListener('contextmenu', function(e){
    var el = nearest(e.target);
    if (el){ e.preventDefault(); post(el, 'context'); }
  });
  content.addEventListener('keydown', function(e){
    if (e.key !== 'Enter') { return; }
    // Never hijack Enter on a real link/control -- let it activate normally.
    if (e.target.closest && e.target.closest('a,button,input,textarea,select')) { return; }
    var el = nearest(e.target);
    if (el){ e.preventDefault(); post(el, 'enter'); }
  });
})();
"""


class SourceMappedSidePreview:
    """A live side preview that can map a preview block back to the editor.

    Behaves like the library's :class:`SidePreview` (``control`` / ``update`` /
    ``focus``) but is built on :class:`AccessibleWebView` directly so it can use
    the JS->Python bridge the plain ``SidePreview`` doesn't expose. Blocks the
    renderer stamps with ``data-src`` become jump targets: right-clicking (or
    pressing Enter on) one calls ``on_goto_source(payload)`` with the source
    line and a short label, and Quill moves the editor caret there (#1257).

    When the WebView library or backend is unavailable it degrades to a plain
    :class:`SidePreview` with no source mapping — the pane still renders.
    """

    def __init__(
        self,
        parent: object,
        *,
        on_return=None,
        on_goto_source=None,
        title: str = "Preview",
    ) -> None:
        self._on_goto_source = on_goto_source
        self._plain = None
        self._view = None
        if not _HAS_WEBVIEW_LIB:
            self._plain = SidePreview(parent, title=title, on_return=on_return)
            return
        self._view = AccessibleWebView(
            parent,
            title=title,
            live_region=False,
            on_return=on_return,
            on_message=self._handle_message,
            open_links_externally=True,
        )
        if self._view.using_webview:
            try:
                import wx.html2 as webview

                self._view.view.Bind(webview.EVT_WEBVIEW_LOADED, self._on_loaded)
            except Exception:  # noqa: BLE001 - source mapping is best-effort
                pass

    @property
    def control(self):
        if self._plain is not None:
            return self._plain.control
        return self._view.control

    def update(self, body_html: str) -> None:
        if self._plain is not None:
            self._plain.update(body_html)
            return
        self._view.set_content(body_html)

    def focus(self) -> None:
        if self._plain is not None:
            self._plain.focus()
            return
        self._view.focus()

    def _on_loaded(self, event: object) -> None:
        # Let AccessibleWebView's own loaded handler still run (it flushes queued
        # content); we only add the one-time source-nav listener on top.
        try:
            event.Skip()
        except Exception:  # noqa: BLE001
            pass
        self._view.run_js(_SOURCE_NAV_JS)

    def _handle_message(self, data: dict) -> None:
        if data.get("type") != "quill-goto-source":
            return
        if self._on_goto_source is not None:
            self._on_goto_source(data)


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


__all__ = [
    "HtmlMessageDialog",
    "SidePreview",
    "SourceMappedSidePreview",
    "MarkdownPreviewDialog",
]


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
