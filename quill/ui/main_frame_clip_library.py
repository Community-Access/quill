"""Clip Library commands for MainFrame (#895) — a rolling history of kept
Fragments beneath Copy Tray's curated 12 slots.

Extracted into a mixin (CQ-1) so new command handlers don't grow
``main_frame.py``. ``ClipLibraryMixin`` relies on ``self.editor``, ``self.frame``,
``self._announce``, ``self._set_status``, and ``self._show_modal_dialog`` staying
on ``MainFrame``, exactly like ``CopyTrayMixin``.
"""

from __future__ import annotations

import wx

from quill.core.clip_library import ClipLibrary
from quill.core.fragment import Fragment


class ClipLibraryMixin:
    """A rolling clip history, complementary to the 12-slot Copy Tray."""

    def _clip_library(self) -> ClipLibrary:
        if not hasattr(self, "_clip_library_instance"):
            from quill.core import paths

            self._clip_library_instance = ClipLibrary(paths.app_data_dir())
        return self._clip_library_instance

    def keep_selection_in_clip_library(self) -> None:
        """Remember the current editor selection as a new Clip Library entry."""
        start, end = self.editor.GetSelection()
        if start == end:
            self._announce("Select text first to keep it in the Clip Library")
            return
        text = self.editor.GetValue()[start:end]
        frag = Fragment(markup=text, source="Document")
        if self._clip_library().remember(frag):
            self._set_status("Kept in the Clip Library.")
        else:
            self._set_status("Already in the Clip Library.")

    def _on_editor_text_copy(self, event: object) -> None:
        """Auto-capture a copy into the Clip Library, when opted in.

        Bound to ``wx.EVT_TEXT_COPY``, which the native control fires for
        every copy regardless of trigger (menu, Ctrl+C, or right-click) --
        the one mechanism that does not require guessing which UI path was
        used. Off by default (``clip_library_autocapture``); always skips
        the event so the native copy itself is never affected.
        """
        if getattr(self.settings, "clip_library_autocapture", False):
            start, end = self.editor.GetSelection()
            if start != end:
                text = self.editor.GetValue()[start:end]
                self._clip_library().remember(Fragment(markup=text, source="Document"))
        skip = getattr(event, "Skip", None)
        if callable(skip):
            skip()

    def keep_fragment_in_clip_library(self, frag: Fragment) -> None:
        """Remember an already-built Fragment (e.g. a Look Up encyclopedia entry)."""
        if self._clip_library().remember(frag):
            self._set_status(f"Kept {frag.title or 'this'} in the Clip Library.")
        else:
            self._set_status("Already in the Clip Library.")

    def open_clip_library(self) -> None:
        from quill.core.fragment import FragmentFormat
        from quill.ui.clip_library_dialog import ClipLibraryDialog

        library = self._clip_library()
        raw_format = str(getattr(self.settings, "content_handoff_format", "text"))
        try:
            content_format = FragmentFormat(raw_format)
        except ValueError:
            content_format = FragmentFormat.TEXT

        def _promote(index: int) -> None:
            self._promote_clip_to_tray(index)

        dlg = ClipLibraryDialog(
            self.frame,
            library,
            announce_cb=self._announce,
            promote_cb=_promote,
            content_format=content_format,
        )
        dlg.show()
        dlg.close()

    def _promote_clip_to_tray(self, index: int) -> None:
        from quill.core.copy_tray import CopyTray

        tray: CopyTray = self._tray()
        with wx.TextEntryDialog(
            self.frame,
            f"Copy Tray slot to promote this clip into (1-{tray.SLOT_COUNT}):",
            "Promote to Copy Tray",
        ) as entry_dlg:
            if self._show_modal_dialog(entry_dlg, "Promote to Copy Tray") != wx.ID_OK:
                return
            raw = entry_dlg.GetValue().strip()
        try:
            slot = int(raw)
        except ValueError:
            self._set_status("Enter a slot number.")
            return
        if not 1 <= slot <= tray.SLOT_COUNT:
            self._set_status(f"Slot must be 1-{tray.SLOT_COUNT}.")
            return
        self._clip_library().promote_to_tray(index, tray, slot)
        self._set_status(f"Promoted to Copy Tray slot {slot}.")
