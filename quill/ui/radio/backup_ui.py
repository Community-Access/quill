"""Station-menu Back Up / Restore actions for Quill Radio (#1193).

Thin wx wiring over :mod:`quill.core.radio.backup`: the file dialogs, the
include-recordings and restore-confirm prompts, running the (potentially large)
zip work off the UI thread, and reloading the running app's favorites + history
after a restore so the change takes effect without a restart. Kept out of
radio.py so that at-budget module stays lean.

The host ``frame`` provides the app-shell contract already used across the radio
UI: ``frame.frame`` (the wx.Frame), ``frame.settings``, ``frame._announce``,
``frame._set_status``, ``frame._show_message_box``, ``frame._show_modal_dialog``,
``frame._radio_favorites``, ``frame._radio_history``, ``frame._reload_favorites_tree``.
"""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Any


def _recordings_dir(frame: Any) -> Path | None:
    try:
        from quill.core.radio.recordings_index import recordings_dir

        folder = Path(recordings_dir(frame.settings))
    except Exception:  # noqa: BLE001 - a missing/odd setting just means "no recordings"
        return None
    return folder if folder.is_dir() else None


def back_up_radio_data(frame: Any) -> None:
    """Save a .qrbackup of the listener's stations, settings, and (optionally)
    recordings to a location they choose."""
    import wx

    from quill.core.paths import app_data_dir
    from quill.core.radio import backup

    rec_dir = _recordings_dir(frame)
    has_recordings = rec_dir is not None and any(rec_dir.iterdir())
    include_recordings = False
    if has_recordings:
        answer = frame._show_message_box(
            "Include your recorded audio in the backup? Recordings can be large. "
            "Choose No to back up just your stations and settings.",
            "Back Up Quill Radio",
            wx.ICON_QUESTION | wx.YES_NO | wx.CANCEL,
        )
        if answer == wx.CANCEL:
            return
        include_recordings = answer == wx.YES

    default_name = f"quill-radio-backup-{datetime.now().strftime('%Y-%m-%d')}{backup.BACKUP_SUFFIX}"
    wildcard = f"Quill Radio backup (*{backup.BACKUP_SUFFIX})|*{backup.BACKUP_SUFFIX}"
    with wx.FileDialog(
        frame.frame,
        "Save Quill Radio Backup",
        wildcard=wildcard,
        defaultFile=default_name,
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as dlg:
        if frame._show_modal_dialog(dlg, "Back Up Quill Radio") != wx.ID_OK:
            return
        dest = Path(dlg.GetPath())

    app_version = str(getattr(frame, "_app_version", "") or "")
    frame._set_status("Backing up Quill Radio...")
    frame._announce("Backing up Quill Radio.")

    def _run() -> None:
        try:
            backup.create_backup(
                app_data_dir(),
                dest,
                recordings_dir=rec_dir,
                include_recordings=include_recordings,
                app_version=app_version,
            )
        except Exception as exc:  # noqa: BLE001 - surface a clean message
            wx.CallAfter(frame._set_status, f"Backup failed: {exc}")
            wx.CallAfter(frame._announce, f"Backup failed. {exc}")
            return
        done = f"Backup saved to {dest.name}."
        wx.CallAfter(frame._set_status, done)
        wx.CallAfter(frame._announce, done)

    threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: backup worker.


def restore_radio_data(frame: Any) -> None:
    """Restore stations, settings, and any recordings from a .qrbackup the
    listener chooses, then reload the running app so it takes effect at once."""
    import wx

    from quill.core.paths import app_data_dir
    from quill.core.radio import backup

    wildcard = f"Quill Radio backup (*{backup.BACKUP_SUFFIX})|*{backup.BACKUP_SUFFIX}"
    with wx.FileDialog(
        frame.frame,
        "Restore Quill Radio Backup",
        wildcard=wildcard,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as dlg:
        if frame._show_modal_dialog(dlg, "Restore Quill Radio") != wx.ID_OK:
            return
        src = Path(dlg.GetPath())

    try:
        manifest = backup.read_manifest(src)
    except backup.RadioBackupError as exc:
        frame._show_message_box(str(exc), "Restore Quill Radio", wx.ICON_ERROR | wx.OK)
        return

    when = manifest.created or "an earlier date"
    extra = f" and {manifest.recordings} recording(s)" if manifest.recordings else ""
    confirm = frame._show_message_box(
        f"Restore {len(manifest.data_files)} settings file(s){extra} from this backup "
        f"(made {when})?\n\nThis replaces your current stations and settings.",
        "Restore Quill Radio",
        wx.ICON_WARNING | wx.YES_NO,
    )
    if confirm != wx.YES:
        return

    rec_dir = _recordings_dir(frame)
    frame._set_status("Restoring Quill Radio...")

    def _run() -> None:
        try:
            result = backup.restore_backup(src, app_data_dir(), recordings_dir=rec_dir)
        except Exception as exc:  # noqa: BLE001 - surface a clean message
            wx.CallAfter(frame._set_status, f"Restore failed: {exc}")
            wx.CallAfter(frame._announce, f"Restore failed. {exc}")
            return
        wx.CallAfter(_apply_restore, frame, result)

    threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: restore worker.


def _apply_restore(frame: Any, result: Any) -> None:
    """On the UI thread: reload favorites + history from the just-restored files
    and refresh the tree so the restore is live without a restart."""
    from quill.core.paths import app_data_dir
    from quill.core.radio import favorites as radio_favorites
    from quill.core.radio import history as radio_history

    data_dir = app_data_dir()
    try:
        frame._radio_favorites = radio_favorites.load_favorites(data_dir)
        frame._radio_history = radio_history.load_history(data_dir)
        frame._reload_favorites_tree()
    except Exception as exc:  # noqa: BLE001 - restore succeeded on disk; report reload trouble
        frame._set_status(
            f"Restored, but could not refresh the view ({exc}). Restart Quill Radio to see it."
        )
        return
    count = len(result.data_files)
    rec = f" and {len(result.recordings)} recording(s)" if result.recordings else ""
    done = f"Restored {count} settings file(s){rec}. Your stations are back."
    frame._set_status(done)
    frame._announce(done)
