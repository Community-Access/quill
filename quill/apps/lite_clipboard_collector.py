"""The clipboard collector in QUILL Lite: copy anywhere, it lands in this window.

QUILL has had it since #964 (Dean Martineau): EdSharp could become a
receptacle for whatever you copy from whatever program, and QUILL's collector
does the same. QUILL Lite had only Collect Selection, which gathers text you
select inside QUILL Lite itself -- and the parity table recorded the two as one
command, which they never were. Dean asked again on QUILLVille in October 2026,
and this is QUILL's collector, on QUILL's key (Alt+Shift+S, rule 2).

The same rules as QUILL's (ui/main_frame_clipboard_collector), and its pieces:
the OS clipboard change counter, so a tick that finds nothing new never opens
the clipboard; ``append_collected`` with QUILL's divider; each distinct copy
once. One window collects at a time, across the app, and the collector stops
when that window closes.

And QUILL's setting, ``clipboard_collector_saves`` (2026-10-15, on by default):
a window with a file name is saved quietly after each clip and says one
sentence, "Collected and saved"; an untitled window just collects, and no Save
As window ever opens. A save that cannot happen is spoken and collecting
carries on. The decision and every word are QUILL's, from
``quill.core.clipboard_collector``.
"""

from __future__ import annotations

from typing import Any

__all__ = ["DocumentClipboardCollectorMixin", "collecting_window"]

_TICK_MS = 750


def collecting_window(app: Any) -> Any:
    """The window collecting right now, or None."""
    return getattr(app, "_collector_window", None)


class DocumentClipboardCollectorMixin:
    """``cmd_clipboard_collector`` and the watcher behind it."""

    app: Any
    control: Any

    def _announce(self, text: str, **kwargs: Any) -> None:  # provided by the window
        raise NotImplementedError

    def collector_is_on(self) -> bool:
        """For the menu's check mark: is *this* window collecting?"""
        return collecting_window(self.app) is self

    def cmd_clipboard_collector(self) -> None:
        """Alt+Shift+S: collect everything copied, in any program, into this window."""
        current = collecting_window(self.app)
        if current is self:
            self._stop_collecting()
            self._announce("Clipboard collector off")
            return
        moved = current is not None
        if moved:
            current._stop_collecting()
        self._start_collecting()
        self._announce(
            "Clipboard collector moved to this document; anything you copy, in any "
            "program, appends here"
            if moved
            else "Clipboard collector on; anything you copy, in any program, appends to "
            "this document"
        )

    def _start_collecting(self) -> None:
        import wx

        from quill.ui.main_frame_clipboard_collector import _clipboard_change_counter

        self.app._collector_window = self
        self._collector_seq = _clipboard_change_counter()
        timer = getattr(self, "_collector_timer", None)
        if timer is None:
            timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self._on_collector_tick, timer)  # type: ignore[attr-defined]
            from quill.ui.surface_lifetime import stop_timer_on_destroy

            stop_timer_on_destroy(self, timer)
            self.Bind(wx.EVT_WINDOW_DESTROY, self._on_collector_window_gone)  # type: ignore[attr-defined]
            self._collector_timer = timer
        timer.Start(_TICK_MS)
        self._refresh_collector_mark()

    def _stop_collecting(self) -> None:
        if collecting_window(self.app) is self:
            self.app._collector_window = None
        timer = getattr(self, "_collector_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - teardown is best effort
                pass
        self._refresh_collector_mark()

    def _on_collector_window_gone(self, event: Any) -> None:
        """The collecting window closed: the collector stops with it."""
        if event.GetEventObject() is self and collecting_window(self.app) is self:
            self.app._collector_window = None
        event.Skip()

    def _refresh_collector_mark(self) -> None:
        sync = getattr(self, "_sync_check_items", None)
        if callable(sync):
            try:
                sync()
            except Exception:  # noqa: BLE001 - a check mark is never worth an error
                pass

    def _on_collector_tick(self, _event: object = None) -> None:
        from quill.ui.main_frame_clipboard_collector import _clipboard_change_counter

        if not self.collector_is_on():
            self._stop_collecting()
            return
        counter = _clipboard_change_counter()
        if counter is not None and counter == getattr(self, "_collector_seq", None):
            return  # nothing new on the clipboard; it is not even opened
        self._collector_seq = counter
        self._collect_clipboard()

    def _collect_clipboard(self) -> bool:
        """Append what is on the clipboard to the end of this window, then maybe save it."""
        from quill.core.clipboard_collector import append_collected
        from quill.ui.atomic_edit import replace_as_one_undo

        editable = getattr(self.control, "IsEditable", lambda: True)()
        if not editable:
            return False
        clip = self._clipboard_text()  # type: ignore[attr-defined]
        if not clip or clip == getattr(self, "_collector_last", None):
            return False
        self._collector_last = clip
        before = self.control.GetValue()
        updated = append_collected(before, clip)
        end = len(before)
        replace_as_one_undo(self.control, end, end, updated[end:])
        final = len(self.control.GetValue())
        self.control.SetSelection(final, final)
        set_modified = getattr(self, "_set_modified", None)
        if callable(set_modified):
            set_modified(True)
        self._announce(self._collector_save())
        return True

    def _collector_save(self) -> str:
        """Save this window quietly when the setting asks; the one sentence to say.

        Never opens a window: an untitled document, or one waiting to be
        renamed, collects as if the setting were off. A reason the save could
        not happen is spoken, with the clip still in the document.
        """
        from quill.core.clipboard_collector import (
            COLLECTED,
            COLLECTED_AND_SAVED,
            collected_but_not_saved,
            saves_after_collect,
        )

        settings = getattr(self.app, "settings", None)
        setting = getattr(settings, "clipboard_collector_saves", True)
        named = getattr(self, "path", None) is not None
        if not saves_after_collect(setting, named) or getattr(self, "_pending_suffix", ""):
            return COLLECTED
        reason = self.save_quietly()  # type: ignore[attr-defined]
        return COLLECTED_AND_SAVED if reason is None else collected_but_not_saved(reason)
