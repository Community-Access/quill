"""Dictation History & Review window (§1.2 dictation follow-ups, PRD §22.4).

Lists the dictation recordings whose transcript was never inserted — crash
orphans and transcripts that could not be safely placed (``insertion_state`` of
``deferred``/``failed``) — so the user can **review** each one and insert it at
the cursor, copy it, or discard it. The same window is the startup-recovery
surface: the caller opens it when :meth:`DictationRecoveryRepository.list_incomplete`
finds anything pending.

Reads its data from the wx-free :class:`DictationRecoveryRepository`; the actual
insertion and clipboard work are injected callbacks so this stays a thin shell.
The result list is a ``wx.ListCtrl`` (Enter activates the selected row), parented
directly on the dialog per the NVDA focus rule.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_message_box


class DictationHistoryDialog:
    """Builds the recovery list and wires Insert / Copy / Discard actions."""

    def __init__(
        self,
        parent: object,
        *,
        repo: Any,
        on_insert: Callable[[str], None],
        on_copy: Callable[[str], None],
    ) -> None:
        import wx

        self._wx = wx
        self._repo = repo
        self._on_insert = on_insert
        self._on_copy = on_copy
        self._items: list[Any] = []

        self.dialog = wx.Dialog(
            parent,
            title="Dictation History & Review",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(620, 420))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(self.dialog, label="Dictation recordings &awaiting review:"),
            0,
            wx.LEFT | wx.TOP,
            8,
        )
        self._list = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        set_accessible_name(self._list, "Dictation recordings awaiting review")
        self._list.InsertColumn(0, "When", width=150)
        self._list.InsertColumn(1, "State", width=140)
        self._list.InsertColumn(2, "Transcript preview", width=300)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._on_insert_clicked())
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (
            ("&Insert at cursor", self._on_insert_clicked),
            ("&Copy", self._on_copy_clicked),
            ("&Discard", self._on_discard_clicked),
            ("&Refresh", lambda: self._reload()),
        ):
            button = wx.Button(self.dialog, label=label)
            button.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            btn_row.Add(button, 0, wx.RIGHT, 6)
        close_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Close")
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)
        self.dialog.SetSizer(root)
        self.dialog.Fit()
        self._reload()

    # ------------------------------------------------------------------ data

    def _reload(self) -> None:
        try:
            self._items = self._repo.list_incomplete()
        except Exception:  # noqa: BLE001 - a broken recovery store must not crash the UI
            self._items = []
        self._list.DeleteAllItems()
        for row, rec in enumerate(self._items):
            session = rec.session
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(session.started_at))
            state = f"{session.transcription_state} / {session.insertion_state}"
            preview = " ".join((self._transcript(rec) or "").split())[:80]
            self._list.InsertItem(row, when)
            self._list.SetItem(row, 1, state)
            self._list.SetItem(row, 2, preview or "(no transcript yet)")
        if self._items:
            self._list.Select(0)
            self._list.Focus(0)

    def _transcript(self, rec: Any) -> str:
        if rec.transcript_path is not None:
            try:
                return rec.transcript_path.read_text(encoding="utf-8")
            except OSError:
                pass
        return rec.session.transcript or ""

    def _selected(self) -> Any | None:
        index = self._list.GetFirstSelected()
        return self._items[index] if 0 <= index < len(self._items) else None

    # ------------------------------------------------------------------ events

    def _on_insert_clicked(self) -> None:
        rec = self._selected()
        if rec is None:
            return
        text = self._transcript(rec).strip()
        if not text:
            self._info("That recording has no transcript yet to insert.")
            return
        self._on_insert(text)
        # The speech now lives in the document; drop the recovery files.
        self._repo.delete(rec.session.session_id)
        self._reload()

    def _on_copy_clicked(self) -> None:
        rec = self._selected()
        if rec is None:
            return
        text = self._transcript(rec).strip()
        if text:
            self._on_copy(text)

    def _on_discard_clicked(self) -> None:
        rec = self._selected()
        if rec is None:
            return
        self._repo.delete(rec.session.session_id)
        self._reload()

    def _info(self, message: str) -> None:
        show_message_box(
            message,
            "Dictation History & Review",
            self._wx.OK | self._wx.ICON_INFORMATION,
            self.dialog,
        )

    # ------------------------------------------------------------------ public

    def show(self, show_modal_dialog: Callable[[object, str], int]) -> None:
        """Open the window modally; nothing is returned (actions apply immediately)."""
        show_modal_dialog(self.dialog, "Dictation History & Review")
        self.dialog.Destroy()
