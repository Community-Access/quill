"""The typing path: what happens between one keystroke and the next (#1346).

Extracted from ``main_frame.py`` (CQ-1 decomposition) with the #1346 fix, whose
whole subject is *how much* work this path is allowed to do.

The reported symptom -- "long pauses between text entry and reporting from
either NVDA and JAWS", spaces dropped so words run together -- was a blocked
message pump. ``_sync_editor_change`` had accumulated eleven callers, three or
four of which each called ``GetValue()``; on a multiline ``wx.TextCtrl`` that is
a full copy of the document across the wx/native boundary, so a 200 KB file cost
roughly a megabyte of copying *per character*. At typing speed the UI thread
never caught up: the text-change notification the screen reader waits on arrived
late, and queued keystrokes coalesced -- which is what a dropped space is.

Two rules keep it fast, and the budget test in
``tests/unit/ui/test_keystroke_work_budget.py`` keeps them true:

1. **One buffer read per change.** ``_on_text_changed`` reads once and threads
   the string through every consumer.
2. **Only three things are synchronous** -- ``document.set_text``, the dirty
   marker, and the quiet status line. Everything else (previews, browse
   prewarm, spell hint, prediction popup, contextual menu state, language
   detection, autosave) moves behind one restarting timer. That pattern was
   already here; it had just never been applied to anything but the browser
   preview and language detection.

   Be precise about what that buys, because it is *not* mostly coalescing. At
   120 ms the timer only collapses a run of keystrokes when they arrive closer
   together than that -- above roughly 8 characters per second, which is a
   100 wpm typist. Below that the deferred work still runs once per keystroke.
   What changes at every speed is the **order**: it now runs in the gap *after*
   the character has been handed to the screen reader instead of in front of
   it. The coalescing is the safety valve on top, and it engages exactly when
   the typist is fast enough to need it, which is the property worth having.
"""

from __future__ import annotations


class TypingPathMixin:
    #: How long after the last keystroke the non-essential edit work runs.
    #: Short enough that a preview or spell hint still feels immediate at any
    #: ordinary typing speed (it simply runs in the gap between characters);
    #: long enough that a genuinely fast burst -- above ~8 characters per
    #: second -- collapses to a single run instead of one per character, which
    #: is exactly when the UI thread cannot afford one per character.
    _DEFERRED_EDIT_DELAY_MS = 120

    def _on_text_changed(self, _event: object) -> None:
        text = self.editor.GetValue()
        if (
            not self._abbreviation_expansion_guard
            and getattr(self.settings, "abbreviation_expansion", True)
            and self._expand_abbreviation_if_match(text)
        ):
            return
        if (
            not self._snippet_expansion_guard
            and self.settings.snippet_trigger_expansion
            and self._expand_snippet_trigger_if_match(text)
        ):
            return
        self._sync_editor_change("Modified", text=text)

    def _sync_editor_change(self, status: str = "Modified", *, text: str | None = None) -> None:
        # `status` defaults so this doubles as the WordDocumentSurface on_change
        # callback, which invokes it with no arguments (#1198). The plain-editor
        # callers pass "Modified" explicitly; the default matches them.
        if text is None:
            text = self.editor.GetValue()
        self._browse_navigation_cache = None
        self.document.set_text(text)
        self._refresh_title()
        # Quiet: this fires on every keystroke; speaking "Modified" each time is
        # noise for a screen reader (it already echoes the typed character).
        self._set_status_quiet(status)
        self._schedule_deferred_edit_work()

    def _on_csv_surface_changed(self) -> None:
        self._sync_editor_change("Modified")

    def _schedule_deferred_edit_work(self) -> None:
        """Coalesce the non-essential per-edit work onto one restarting timer."""
        call_later = getattr(getattr(self, "_wx", None), "CallLater", None)
        if not callable(call_later):
            # No wx (headless tests, stub surfaces): keep the old synchronous
            # behaviour so callers still see the side effects immediately.
            self._run_deferred_edit_work()
            return
        timer = getattr(self, "_deferred_edit_timer", None)
        stop = getattr(timer, "Stop", None)
        if callable(stop):
            stop()
        self._deferred_edit_timer = call_later(
            self._DEFERRED_EDIT_DELAY_MS, self._run_deferred_edit_work
        )

    def _run_deferred_edit_work(self) -> None:
        """The per-edit work that can wait for a pause in typing."""
        self._deferred_edit_timer = None
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        try:
            text = editor.GetValue()
        except RuntimeError:
            # The editor can be a dead TextCtrl by the time the timer fires
            # (tab closed, document replaced) -- same guard as #603/#269.
            return
        self._schedule_browse_prewarm(text=text)
        if not self._suspend_persistent_undo:
            self._record_persistent_undo_state(text)
        if self.settings.spellcheck_as_you_type:
            self._announce_spellcheck_hint(text=text)
        self._refresh_intellisense_popup()
        self._refresh_side_preview(text=text)
        self._refresh_browser_preview()
        self._maybe_autosave()
        self._refresh_contextual_menu_items()
        # #181: debounced auto language detection (no-op unless enabled in Settings).
        self._schedule_language_detection()
