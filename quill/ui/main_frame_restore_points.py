"""MainFrame mixin for restore points — File > Restore Previous Version.

The first shipped slice of the QUILL Sync plan (docs/planning/quill-sync-plan.md,
section 7). Every successful save snapshots the document's canonical text via
the wx-free :mod:`quill.core.restore_points`; this mixin owns the two UI
surfaces:

- ``_record_save_restore_point(document)`` — the save-path hook. Best-effort by
  contract: a restore-point failure must never be the reason a save fails, so
  everything is guarded and the worst outcome is a log line.
- ``restore_previous_version()`` — the accessible history dialog: a list of
  versions ("Today at 4:12 PM - 2,341 words"), Restore (replaces the editor
  text after taking a snapshot of the current text first, so restoring is
  itself reversible), and Open as Copy (a new untitled tab).

Command id: ``file.restore_previous_version`` (no default key; assignable in
the Keymap Editor).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from quill.core.document import Document
from quill.core.restore_points import (
    RestorePoint,
    list_restore_points,
    prune_restore_points,
    read_restore_point,
    record_restore_point,
)
from quill.ui.dialog_contract import apply_modal_ids

_log = logging.getLogger(__name__)


def _speakable_when(point: RestorePoint, now: datetime | None = None) -> str:
    """A short, front-loaded, screen-reader-friendly time label."""
    saved = point.saved_at_local
    today = (now or datetime.now().astimezone()).date()
    day_delta = (today - saved.date()).days
    clock = saved.strftime("%I:%M %p").lstrip("0")
    if day_delta == 0:
        return f"Today at {clock}"
    if day_delta == 1:
        return f"Yesterday at {clock}"
    return f"{saved.strftime('%B %d, %Y')} at {clock}"


def restore_point_label(point: RestorePoint) -> str:
    """One list row: when, size in words, and how the version came to exist."""
    words = f"{point.word_count:,} word" + ("" if point.word_count == 1 else "s")
    origin = " (before a restore)" if point.source == "restore" else ""
    return f"{_speakable_when(point)} - {words}{origin}"


class RestorePointsMixin:
    _wx: Any
    frame: Any
    editor: Any
    document: Any
    settings: Any

    def register_restore_point_commands(self) -> None:
        self.commands.register(
            "file.restore_previous_version",
            "Restore Previous Version",
            self.restore_previous_version,
            self._binding_for("file.restore_previous_version"),
        )

    # -- save-path hook ------------------------------------------------------ #

    def _record_save_restore_point(self, document: object) -> None:
        """Snapshot ``document`` after a successful save. Never raises."""
        try:
            if not bool(getattr(self.settings, "restore_points_enabled", True)):
                return
            path = getattr(document, "path", None)
            text = getattr(document, "text", None)
            if path is None or not isinstance(text, str):
                return
            if record_restore_point(path, text, source="save") is not None:
                cap = int(getattr(self.settings, "restore_points_max_mb", 200))
                prune_restore_points(path, max_total_mb=cap)
        except Exception:  # noqa: BLE001 - a snapshot must never break a save
            _log.warning("restore point not recorded for %s", document, exc_info=True)

    # -- File > Restore Previous Version ------------------------------------- #

    def restore_previous_version(self) -> None:
        wx = self._wx
        path = getattr(self.document, "path", None)
        if path is None:
            self._set_status("Save the document once before restoring a version")
            return
        points = list_restore_points(path)
        # The newest snapshot usually equals the file just saved; showing it as
        # a "previous version" would be confusing, so it is skipped when it
        # matches the current editor text.
        current = self.editor.GetValue()
        candidates = [p for p in points if read_restore_point(path, p.content_hash) != current]
        if not candidates:
            self._set_status("No earlier versions of this document yet")
            return

        dialog = wx.Dialog(self.frame, title="Restore Previous Version")
        dialog.SetName("Restore Previous Version — earlier saves of this document")
        root = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            dialog,
            label=(
                f"{len(candidates)} earlier version"
                + ("" if len(candidates) == 1 else "s")
                + f" of {self.document.name}. Restoring replaces the editor text; "
                "your current text is kept as a restore point first."
            ),
        )
        root.Add(intro, 0, wx.ALL | wx.EXPAND, 8)
        listbox = wx.ListBox(dialog, choices=[restore_point_label(p) for p in candidates])
        listbox.SetName("Earlier versions")
        listbox.SetSelection(0)
        root.Add(listbox, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        restore_button = wx.Button(dialog, id=wx.ID_OK, label="&Restore")
        copy_button = wx.Button(dialog, id=wx.ID_APPLY, label="Open as &Copy")
        close_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Close")
        buttons.AddStretchSpacer(1)
        buttons.Add(restore_button, 0, wx.RIGHT, 6)
        buttons.Add(copy_button, 0, wx.RIGHT, 6)
        buttons.Add(close_button, 0)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)
        dialog.SetSize((520, 360))
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        copy_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_APPLY))
        try:
            result = self._show_modal_dialog(dialog, "Restore Previous Version")
            selection = listbox.GetSelection()
        finally:
            dialog.Destroy()
        if result not in (wx.ID_OK, wx.ID_APPLY) or not (0 <= selection < len(candidates)):
            return
        point = candidates[selection]
        text = read_restore_point(path, point.content_hash)
        if text is None:
            self._set_status("That version could not be read; it may have been pruned")
            return
        if result == wx.ID_APPLY:
            self._open_restore_point_copy(text)
            return
        self._apply_restore_point(path, point, text, current)

    def _open_restore_point_copy(self, text: str) -> None:
        """Open a version as a new untitled document; the original is untouched."""
        copy = Document(text=text, path=None, modified=True)
        self._create_document_tab(copy, select=True)
        self._announce("Opened the earlier version as a new untitled document.")

    def _apply_restore_point(
        self, path: object, point: RestorePoint, text: str, current: str
    ) -> None:
        wx = self._wx
        confirmed = self._show_message_box(
            f"Replace the current text with the version from "
            f"{_speakable_when(point)}? Your current text is saved as a "
            "restore point first, so this can be undone the same way.",
            "Restore Previous Version",
            wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        )
        if confirmed != wx.YES:
            self._set_status("Restore cancelled")
            return
        try:
            record_restore_point(path, current, source="restore")  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001 - the restore still proceeds
            _log.warning("pre-restore snapshot failed for %s", path, exc_info=True)
        self.document.set_text(text)
        self._replace_document_text(text)
        self._refresh_title()
        self._announce(
            f"Restored the version from {_speakable_when(point)}. "
            "The document is modified; save to keep it."
        )
