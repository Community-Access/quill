"""Clipboard collector mode -- copy anywhere, it lands in this document.

Extracted from ``main_frame_power_tools.py`` on 2026-09-18 to keep that module
inside its GATE-11 budget, and it is the natural seam: the collector is the one
feature in there that owns state across time (a poll timer, a change counter, a
bind on the editor) rather than transforming the text in front of it.

Issue #964 (Dean Martineau) is why it watches the whole system: EdSharp collects
from any application, and a collector that only sees QUILL's own copies is a
collector for the one case you did not need it in.

What changed with the move is what it no longer does (bad.md C4): it does not
save the file. It used to call ``save_file()`` on every collected clip whenever
the document had a path, so one copy in another program wrote to disk *and*
produced two spoken sentences. And its three refusals -- read-only, an empty
clipboard, a clip already collected -- were silent, which is how a feature that
is working exactly as designed comes to be reported as broken.

Mixed into :class:`~quill.ui.main_frame_power_tools.PowerToolsActionsMixin` as a
base, so every method resolves through the same MRO as before and the command
table is unchanged.
"""

from __future__ import annotations

import sys
from functools import partial

from quill.core.clipboard_collector import append_collected

__all__ = ["ClipboardCollectorMixin"]


def _clipboard_change_counter() -> int | None:
    """The OS clipboard change counter, or None where unavailable.

    Windows: ``GetClipboardSequenceNumber`` — one cheap user32 call, no
    clipboard open, bumps on every copy from ANY application (#964). macOS:
    ``NSPasteboard.generalPasteboard().changeCount()`` via PyObjC when
    present. None (Linux / missing bridge) makes the watcher fall back to
    reading and comparing the clipboard text each tick.
    """
    if sys.platform == "win32":
        try:
            import ctypes

            return int(ctypes.windll.user32.GetClipboardSequenceNumber())
        except Exception:  # noqa: BLE001 - a probe must never raise
            return None
    if sys.platform == "darwin":
        try:
            from AppKit import NSPasteboard  # type: ignore[import-not-found]

            return int(NSPasteboard.generalPasteboard().changeCount())
        except Exception:  # noqa: BLE001
            return None
    return None


class ClipboardCollectorMixin:
    """Collector mode: the toggle, the system watcher, and one append."""

    def toggle_clipboard_collector(self) -> None:
        active = not getattr(self, "_power_tools_clipboard_collector", False)
        self._power_tools_clipboard_collector = active
        copy_event = getattr(self._wx, "EVT_TEXT_COPY", None)
        previous = getattr(self, "_power_tools_collector_editor", None)
        if copy_event is not None and previous is not None:
            previous.Unbind(copy_event)
        self._power_tools_collector_editor = (
            self.editor if (copy_event is not None and active) else None
        )
        if copy_event is not None and active:
            self.editor.Bind(copy_event, self._on_power_tools_collect_copy)
        # #964 (Dean Martineau): the collector is system-wide, EdSharp-style —
        # copy anywhere in Windows and it lands in the QUILL document. The
        # in-app EVT_TEXT_COPY bind above stays for instant response; this
        # watcher catches every other application's copies by polling the OS
        # clipboard change counter (a single cheap Win32 call per tick, no
        # clipboard open unless it actually changed).
        if active:
            self._start_collector_watch()
        else:
            self._stop_collector_watch()
        self._announce(
            "Clipboard collector on; anything you copy, in any program, appends to this document"
            if active
            else "Clipboard collector off"
        )

    def _start_collector_watch(self) -> None:
        wx = self._wx
        timer_cls = getattr(wx, "Timer", None)
        if timer_cls is None:  # headless tests
            return
        self._power_tools_collector_seq = _clipboard_change_counter()
        timer = getattr(self, "_power_tools_collector_timer", None)
        if timer is None:
            timer = timer_cls(self.frame)
            self.frame.Bind(wx.EVT_TIMER, self._on_collector_tick, timer)
            self._power_tools_collector_timer = timer
        timer.Start(750)

    def _stop_collector_watch(self) -> None:
        timer = getattr(self, "_power_tools_collector_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - teardown is best-effort
                pass

    def _on_collector_tick(self, _event: object) -> None:
        if not getattr(self, "_power_tools_clipboard_collector", False):
            self._stop_collector_watch()
            return
        counter = _clipboard_change_counter()
        if counter is not None and counter == getattr(self, "_power_tools_collector_seq", None):
            return  # nothing new on the clipboard; no clipboard open needed
        self._power_tools_collector_seq = counter
        self.collect_clipboard_now(announce_refusals=False)

    def _on_power_tools_collect_copy(self, event: object) -> None:
        event.Skip()
        collect = partial(self.collect_clipboard_now, announce_refusals=False)
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after):
            call_after(collect)
        else:
            collect()

    def collect_clipboard_now(self, *, announce_refusals: bool = True) -> None:
        """Append what is on the clipboard to the end of this document.

        Two things it no longer does (bad.md C4). It does not **save the file**:
        it used to call ``save_file()`` on every collected clip whenever the
        document had a path, driven by a 750 ms poll, so copying anything in
        any program wrote to disk and said "Saved <name>" *and* "Collected
        clipboard text" -- two sentences per copy, and a file written without
        anybody asking. A collector is a buffer; Ctrl+S is how a buffer reaches
        the disk, and the unsaved marker is how you know it has not.

        And it no longer refuses in silence. Read-only, an empty clipboard and
        a clip already at the end each said nothing, so the feature looked
        broken exactly when it was working as designed. Refusals are spoken
        when a person asked for this collection (the menu row, the key) and
        stay quiet when the poll or the in-app copy hook asked -- those fire
        many times a minute, and narrating each one would be its own bug.
        """
        if self._document_is_read_only():
            if announce_refusals:
                self._set_status("This document is read-only; nothing was collected.")
            return
        clip = self._power_tools_clipboard_text()
        if not clip:
            if announce_refusals:
                self._set_status("The clipboard is empty; there is nothing to collect.")
            return
        # The system watcher and the in-app copy event can both fire for one
        # copy (and the counter ticks for our own writes): collect each
        # distinct clipboard payload once.
        if clip == getattr(self, "_power_tools_last_collected", None):
            if announce_refusals:
                self._set_status("That is already the last thing collected.")
            return
        self._power_tools_last_collected = clip
        updated = append_collected(self.editor.GetValue(), clip)
        self._replace_document_text(updated)
        self.document.set_text(updated)
        end = len(updated)
        self.editor.SetInsertionPoint(end)
        self.editor.SetSelection(end, end)
        self._set_status("Collected clipboard text")
