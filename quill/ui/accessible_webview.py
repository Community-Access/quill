"""Ask Quill's accessible chat surface — a thin adapter over the published
``wx-accessible-webview`` library.

The WebView/ARIA/JS chat stack Quill pioneered lives in
``wx_accessible_webview.AccessibleChatView`` now. This adapter keeps Quill's
original API — ``intro`` and :meth:`append_message` accept **Markdown** (rendered
here via :func:`quill.core.browser_preview._render_markdown`), and ``set_status``
matches Quill's existing call sites — while delegating everything else to the
library.

Two additions of Quill's own (2026-10-17, todo item 44):

* **Headings nest under the speaker.** The library names each turn with a
  level-2 heading; a reply's own Markdown headings are moved down beneath it
  (:func:`quill.core.ai.chat_navigation.nest_reply_headings`), so a reply that
  opens with ``# Title`` is a level-3 heading inside its message rather than
  a level-1 heading that looks like a new conversation in the heading list.
* **Alt+1 .. Alt+0 from inside the page.** The page has focus while somebody
  types, and the browser keeps Alt and a digit for itself, so the window's
  own keys never see them. A small script posts the digit back over the same
  bridge Escape already uses, and ``on_recent(n)`` reads the *n*-th newest
  message aloud. Nothing on the page moves.
"""

from __future__ import annotations

import json

from wx_accessible_webview import AccessibleChatView

from quill.core.ai.chat_navigation import nest_reply_headings
from quill.core.browser_preview import _render_markdown

#: Alt with a digit on the page, posted back as {"type": "recent", "n": 1..10}.
_RECENT_KEYS_JS = """
(function() {
  if (window.__quillRecentKeys) { return; }
  window.__quillRecentKeys = true;
  document.addEventListener('keydown', function(e) {
    if (!e.altKey || e.ctrlKey || e.shiftKey || e.metaKey) { return; }
    var m = /^(?:Digit|Numpad)([0-9])$/.exec(e.code || '');
    if (!m) { return; }
    e.preventDefault();
    var n = parseInt(m[1], 10) || 10;
    if (window.awv && window.awv.postMessage) {
      window.awv.postMessage(JSON.stringify({type: 'recent', n: n}));
    }
  }, true);
})();
"""


class AccessibleWebView(AccessibleChatView):
    """Quill's chat surface: Markdown in, accessible WebView out."""

    def __init__(
        self,
        parent: object,
        title: str = "Conversation",
        intro: tuple | None = None,
        suggestions: tuple[str, ...] = (),
        on_send=None,
        on_close=None,
        on_recent=None,
    ) -> None:
        self._on_recent = on_recent
        rendered_intro = None
        if intro is not None:
            rendered_intro = (intro[0], _render_markdown(intro[1] or ""))
        super().__init__(
            parent,
            title=title,
            intro=rendered_intro,
            suggestions=tuple(suggestions),
            placeholder="Ask Quill to write, edit, or run something…",
            composer_label="Your message to Quill",
            on_send=on_send,
            on_close=on_close,
        )

    def append_message(self, speaker: str, markdown_text: str) -> None:
        """Append a turn; ``markdown_text`` is rendered to HTML before display,
        its headings nested beneath the speaker's level-2 heading."""
        super().append_message(speaker, _render_markdown(nest_reply_headings(markdown_text or "")))

    def set_status(self, text: str) -> None:
        """Announce transient status (Quill's name for the library's ``status``)."""
        self.status(text)

    def _on_loaded(self, event: object) -> None:
        super()._on_loaded(event)
        if self._on_recent is not None:
            self._run(_RECENT_KEYS_JS)

    def _on_script_message(self, event: object) -> None:
        try:
            data = json.loads(event.GetString())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - not ours to read; the library decides
            data = None
        if isinstance(data, dict) and data.get("type") == "recent":
            self.recent_key(data.get("n"))
            return
        super()._on_script_message(event)

    def recent_key(self, n: object) -> None:
        """The page posted Alt and a digit: read that recent message aloud."""
        try:
            number = int(n)  # type: ignore[call-overload]
        except (TypeError, ValueError):
            return
        if self._on_recent is not None and 1 <= number <= 10:
            self._on_recent(number)
