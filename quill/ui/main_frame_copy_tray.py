"""Copy Tray commands for MainFrame — 12-slot persistent clipboard.

Extracted into a mixin to keep ``main_frame.py`` within the GATE-11 size budget
(CQ-1). ``CopyTrayMixin`` is mixed into ``MainFrame`` and every method resolves
identically through the MRO; the ``self.editor``, ``self.frame``,
``self._announce``, ``self._set_status``, and ``self._show_modal_dialog`` helpers
it relies on stay on ``MainFrame``.

Multi-press behaviour (Phase 2):
  Single press  — paste immediately.
  Double press  — peek: announce slot content without pasting.
  Triple press  — open the Copy Tray dialog.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.copy_tray import CopyTray
from quill.core.multi_press import MultiPressDispatcher


class _TraySearchDialog:
    """Minimal slot-search dialog: type to filter, Enter to paste.

    Shown via _show_modal_dialog(dlg.dialog, ...) by CopyTrayMixin.search_tray_slots.
    """

    def __init__(
        self,
        parent: object,
        tray: CopyTray,
        announce_fn: Callable[[str], None] | None = None,
    ) -> None:
        self._tray = tray
        self._slot_numbers: list[int] = []
        self._result_slot: int | None = None
        self._announce_fn = announce_fn
        self.dialog = wx.Dialog(
            parent,
            title="Search Copy Tray Slots",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(440, 320))

        root = wx.BoxSizer(wx.VERTICAL)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        search_row.Add(
            wx.StaticText(self.dialog, label="&Search:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4
        )
        self._search = wx.TextCtrl(self.dialog)
        self._search.SetName("Search text in tray slots")
        search_row.Add(self._search, 1, wx.EXPAND)
        root.Add(search_row, 0, wx.EXPAND | wx.ALL, 8)

        self._results = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._results.SetName("Matching slots")
        root.Add(self._results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_paste = wx.Button(self.dialog, wx.ID_OK, "&Paste")
        btn_cancel = wx.Button(self.dialog, wx.ID_CANCEL, "&Cancel")
        btn_row.AddStretchSpacer(1)
        btn_row.Add(self._btn_paste, 0, wx.RIGHT, 4)
        btn_row.Add(btn_cancel, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

        self._search.Bind(wx.EVT_TEXT, self._on_search)
        apply_listbox_activation(self._results, self._on_activate)
        self._btn_paste.Bind(wx.EVT_BUTTON, self._on_paste)

        self._refresh([n for n, s in tray.all_slots() if not s.is_empty()])
        self._search.SetFocus()

    def close(self) -> None:
        self.dialog.Destroy()

    def selected_slot(self) -> int | None:
        return self._result_slot

    def _on_search(self, _event: object) -> None:
        query = self._search.GetValue().strip()
        if not query:
            matching = [n for n, s in self._tray.all_slots() if not s.is_empty()]
        else:
            matching = [n for n, s in self._tray.search_slots(query)]
        self._refresh(matching)

    def _refresh(self, slot_numbers: list[int]) -> None:
        self._slot_numbers = slot_numbers
        labels = []
        for n in slot_numbers:
            s = self._tray.slot(n)
            label_part = f" ({s.label})" if s.label else ""
            pinned_part = " [pinned]" if s.pinned else ""
            preview = s.preview(60)
            labels.append(f"Slot {n}{label_part}{pinned_part}: {preview}")
        self._results.Set(labels)
        if labels:
            self._results.SetSelection(0)
            if self._announce_fn is not None:
                self._announce_fn(labels[0])

    def _on_activate(self, _event: object) -> None:
        sel = self._results.GetSelection()
        if 0 <= sel < len(self._slot_numbers):
            self._result_slot = self._slot_numbers[sel]
            self.dialog.EndModal(wx.ID_OK)

    def _on_paste(self, _event: object) -> None:
        sel = self._results.GetSelection()
        if 0 <= sel < len(self._slot_numbers):
            self._result_slot = self._slot_numbers[sel]
            self.dialog.EndModal(wx.ID_OK)


class CopyTrayMixin:
    """Twelve-slot clipboard accessible by number key or dialog."""

    # -- lazy accessors --

    def _tray(self) -> CopyTray:
        if not hasattr(self, "_copy_tray_instance"):
            from quill.core import paths

            self._copy_tray_instance = CopyTray(paths.app_data_dir())
            wx.CallAfter(self._update_paste_tray_labels)
        return self._copy_tray_instance

    def _tray_dispatcher(self) -> MultiPressDispatcher:
        if not hasattr(self, "_copy_tray_dispatcher"):
            window_ms = int(getattr(getattr(self, "settings", None), "multi_press_window_ms", 400))
            self._copy_tray_dispatcher = MultiPressDispatcher(window_ms=window_ms)
            self._copy_tray_timers: dict[int, object] = {}
        return self._copy_tray_dispatcher

    # -- slot operations --

    def copy_to_tray_slot(self, n: int) -> None:
        start, end = self.editor.GetSelection()
        if start == end:
            self._announce(f"Select text first to copy to slot {n}")
            return
        text = self.editor.GetValue()[start:end]
        self._tray().copy_to(n, text)
        slot = self._tray().slot(n)
        label = f" ({slot.label})" if slot.label else ""
        self._set_status_quiet(f"Copied to slot {n}{label}: {slot.preview(50)}")
        self._announce(f"Copied to slot {n}{label}")
        self._update_paste_tray_labels()
        self._refresh_statusbar()

    def copy_to_next_slot(self) -> None:
        """Copy selection to the first empty, non-pinned slot (1-12)."""
        start, end = self.editor.GetSelection()
        if start == end:
            self._announce("Select text first")
            return
        n = self._tray().first_empty_slot()
        if n is None:
            self._announce("All 12 slots occupied. Open Copy Tray to manage slots.")
            return
        text = self.editor.GetValue()[start:end]
        self._tray().copy_to(n, text)
        slot = self._tray().slot(n)
        label = f" ({slot.label})" if slot.label else ""
        self._set_status_quiet(f"Copied to slot {n}{label} (first empty): {slot.preview(50)}")
        self._announce(f"Copied to slot {n} (first empty){label}")
        self._update_paste_tray_labels()
        self._refresh_statusbar()

    def paste_from_tray_slot(self, n: int) -> None:
        """Route through MultiPressDispatcher: 1=paste, 2=peek, 3=dialog."""
        dispatcher = self._tray_dispatcher()
        count, needs_timer = dispatcher.press(f"tray_{n}")
        existing = self._copy_tray_timers.get(n)
        if existing is not None:
            stop = getattr(existing, "Stop", None)
            if callable(stop):
                stop()
        if needs_timer:
            timer = wx.CallLater(
                dispatcher.window_ms,
                self._fire_tray_action,
                n,
            )
            self._copy_tray_timers[n] = timer
        else:
            self._copy_tray_timers.pop(n, None)
            self._fire_tray_action_with_count(n, count)

    def _fire_tray_action(self, n: int) -> None:
        count = self._tray_dispatcher().timeout(f"tray_{n}")
        self._copy_tray_timers.pop(n, None)
        self._fire_tray_action_with_count(n, count)

    def _fire_tray_action_with_count(self, n: int, count: int) -> None:
        if count == 2:
            self._peek_tray_slot(n)
        elif count >= 3:
            self.open_copy_tray()
        else:
            self._do_paste_from_tray_slot(n)

    def _do_paste_from_tray_slot(self, n: int) -> None:
        text = self._tray().paste_from(n)
        if not text:
            self._announce(f"Slot {n} is empty")
            return
        start, end = self.editor.GetSelection()
        current = self.editor.GetValue()
        if start != end:
            updated = current[:start] + text + current[end:]
            new_pos = start + len(text)
        else:
            pos = self.editor.GetInsertionPoint()
            updated = current[:pos] + text + current[pos:]
            new_pos = pos + len(text)
        self._replace_document_text(updated)
        self.document.set_text(updated)
        self.editor.SetInsertionPoint(new_pos)
        self.editor.SetSelection(new_pos, new_pos)
        slot = self._tray().slot(n)
        label = f" ({slot.label})" if slot.label else ""
        self._set_status(f"Pasted from slot {n}{label}")

    def _peek_tray_slot(self, n: int) -> None:
        slot = self._tray().slot(n)
        if slot.is_empty():
            self._announce(f"Slot {n} is empty")
            return
        label_part = f" ({slot.label})" if slot.label else ""
        pinned_part = " [pinned]" if slot.pinned else ""
        preview = slot.preview(80)
        self._announce(f"Slot {n}{label_part}{pinned_part}: {preview}")
        self._set_status(f"Slot {n}{label_part}: {preview}")

    # -- search --

    def search_tray_slots(self) -> None:
        """Open the slot-search dialog; paste if a match is chosen."""
        tray = self._tray()
        if all(s.is_empty() for _, s in tray.all_slots()):
            self._announce("All copy tray slots are empty")
            return
        dlg = _TraySearchDialog(self.frame, tray, announce_fn=self._announce)
        result = self._show_modal_dialog(dlg.dialog, "Search Copy Tray Slots")
        n = dlg.selected_slot()
        dlg.close()
        if result == wx.ID_OK and n is not None:
            self._do_paste_from_tray_slot(n)

    # -- paste-menu label refresh --

    def _update_paste_tray_labels(self) -> None:
        """Refresh 'Paste from Slot N' menu items to show slot label + preview."""
        bar = getattr(self.frame, "GetMenuBar", lambda: None)()
        if bar is None:
            return
        tray = self._tray()
        ids = getattr(self, "_id_paste_tray_slots", [])
        for n in range(1, 13):
            if n - 1 >= len(ids):
                break
            item = bar.FindItemById(int(ids[n - 1]))
            if item is None:
                continue
            slot = tray.slot(n)
            if slot.is_empty():
                label = f"&{n} (empty)" if n <= 9 else f"{n} (empty)"
            else:
                label_part = f" ({slot.label})" if slot.label else ""
                pinned_part = " [pinned]" if slot.pinned else ""
                preview = slot.preview(40)
                accel = f"&{n}" if n <= 9 else str(n)
                label = f"{accel}{label_part}{pinned_part} — {preview}"
            item.SetItemLabel(label)

    # -- management commands --

    def open_copy_tray(self) -> None:
        from quill.ui.copy_tray_dialog import CopyTrayDialog

        tray = self._tray()
        dlg = CopyTrayDialog(
            self.frame, tray, self._get_editor_selection(), announce_cb=self._announce
        )
        result = self._show_modal_dialog(dlg.dialog, "Copy Tray")
        if result == wx.ID_OK and (text := dlg.selected_text_to_paste()):
            n = dlg.selected_slot()
            # Insert directly — the tray data is already up to date
            start, end = self.editor.GetSelection()
            current = self.editor.GetValue()
            if start != end:
                updated = current[:start] + text + current[end:]
                new_pos = start + len(text)
            else:
                pos = self.editor.GetInsertionPoint()
                updated = current[:pos] + text + current[pos:]
                new_pos = pos + len(text)
            self._replace_document_text(updated)
            self.document.set_text(updated)
            self.editor.SetInsertionPoint(new_pos)
            self.editor.SetSelection(new_pos, new_pos)
            slot = tray.slot(n)
            label = f" ({slot.label})" if slot.label else ""
            self._set_status(f"Pasted from slot {n}{label}")
        dlg.close()
        self._update_paste_tray_labels()
        self._refresh_statusbar()

    def _get_editor_selection(self) -> str:
        start, end = self.editor.GetSelection()
        if start == end:
            return ""
        return self.editor.GetValue()[start:end]

    def clear_all_tray_slots(self) -> None:
        dlg = wx.MessageDialog(
            self.frame,
            "Clear all 12 copy tray slots? This cannot be undone.",
            "Clear Copy Tray",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        result = self._show_modal_dialog(dlg, "Clear Copy Tray")
        dlg.Destroy()
        if result == wx.ID_YES:
            self._tray().clear_all()
            self._announce("All copy tray slots cleared")
            self._set_status("Copy tray cleared")
            self._update_paste_tray_labels()
            self._refresh_statusbar()
