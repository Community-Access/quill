"""Back Up / Restore for QUILL Cast (list.md 5.6).

Thin wx wiring over :mod:`quill.core.podcasts.backup`: the file dialogs, the
include-episodes and restore-confirm prompts, running the (potentially large)
zip work off the UI thread, and reloading the running app afterwards so a
restore takes effect without a restart. Shaped after Quill Radio's
``ui/radio/backup_ui`` because the two should behave alike; the words and the
data differ, and so does one decision:

**A restore reloads the library in place.** Radio reloads favorites and the
history and refreshes its tree. Cast has to do the same for subscriptions,
folders, playlists, positions and notes, and it has one extra hazard: if
something is playing while the library is replaced underneath it, the position
being written when it stops would be written against a library that no longer
knows about that episode. So playback is stopped first, deliberately and out
loud, rather than left to find out.

The host contract is the app-shell one already used across Cast:
``frame.frame``, ``frame._announce``, ``frame._set_status``,
``frame._show_message_box``, ``frame._show_modal_dialog``,
``frame._podcast_library``, ``frame._podcast_history``,
``frame._podcast_controller``, ``frame._reload_library_tree``.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

__all__ = ["back_up_cast_data", "restore_cast_data"]


def _downloads_dir(frame: Any) -> Path | None:
    """Where downloaded episodes live, or ``None`` when there are none."""
    try:
        folder = Path(frame._podcast_download_root())
    except Exception:  # noqa: BLE001 - an odd setting just means "no downloads"
        return None
    return folder if folder.is_dir() else None


def _has_any_file(folder: Path | None) -> bool:
    if folder is None:
        return False
    try:
        return any(path.is_file() for path in folder.rglob("*"))
    except OSError:
        return False


def back_up_cast_data(frame: Any) -> None:
    """Save a ``.qcbackup`` of the listener's library to a place they choose."""
    import wx

    from quill.core.paths import app_data_dir
    from quill.core.podcasts import backup

    downloads = _downloads_dir(frame)
    include_episodes = False
    if _has_any_file(downloads):
        answer = frame._show_message_box(
            "Include your downloaded episodes in the backup? They can be very "
            "large, and they can be downloaded again. Choose No to back up just "
            "your subscriptions, playlists, positions and notes -- the part that "
            "cannot be got back.",
            "Back Up QUILL Cast",
            wx.ICON_QUESTION | wx.YES_NO | wx.CANCEL,
        )
        if answer == wx.CANCEL:
            return
        include_episodes = answer == wx.YES

    wildcard = f"QUILL Cast backup (*{backup.BACKUP_SUFFIX})|*{backup.BACKUP_SUFFIX}"
    with wx.FileDialog(
        frame.frame,
        "Save QUILL Cast Backup",
        wildcard=wildcard,
        defaultFile=backup.suggested_filename(),
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as dlg:
        if frame._show_modal_dialog(dlg, "Back Up QUILL Cast") != wx.ID_OK:
            return
        dest = Path(dlg.GetPath())

    app_version = str(getattr(frame, "_app_version", "") or "")
    shows = len(getattr(getattr(frame, "_podcast_library", None), "shows", ()) or ())
    frame._set_status("Backing up QUILL Cast...")
    frame._announce("Backing up QUILL Cast.")

    def _run() -> None:
        try:
            backup.create_backup(
                app_data_dir(),
                dest,
                downloads_dir=downloads,
                include_episodes=include_episodes,
                app_version=app_version,
                shows=shows,
            )
        except Exception as exc:  # noqa: BLE001 - surface a clean message
            wx.CallAfter(frame._set_status, f"Backup failed: {exc}")
            wx.CallAfter(frame._announce, f"Backup failed. {exc}")
            return
        done = f"Backup saved to {dest.name}."
        wx.CallAfter(frame._set_status, done)
        wx.CallAfter(frame._announce, done)

    threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: backup worker.


def restore_cast_data(frame: Any) -> None:
    """Restore a library from a ``.qcbackup``, then reload so it is live."""
    import wx

    from quill.core.paths import app_data_dir
    from quill.core.podcasts import backup

    wildcard = f"QUILL Cast backup (*{backup.BACKUP_SUFFIX})|*{backup.BACKUP_SUFFIX}"
    with wx.FileDialog(
        frame.frame,
        "Restore QUILL Cast Backup",
        wildcard=wildcard,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as dlg:
        if frame._show_modal_dialog(dlg, "Restore QUILL Cast") != wx.ID_OK:
            return
        src = Path(dlg.GetPath())

    try:
        manifest = backup.read_manifest(src)
    except backup.CastBackupError as exc:
        frame._show_message_box(str(exc), "Restore QUILL Cast", wx.ICON_ERROR | wx.OK)
        return

    # The description carries when it was made and how big the library is,
    # which are the two facts somebody needs to spot the wrong file *before*
    # it replaces the right one.
    confirm = frame._show_message_box(
        f"{manifest.describe()}\n\nRestoring replaces your current subscriptions, "
        "playlists, positions and notes. Anything playing will stop.",
        "Restore QUILL Cast",
        wx.ICON_WARNING | wx.YES_NO,
    )
    if confirm != wx.YES:
        return

    # Stop first, on this thread, while the library on disk is still the one
    # the player was started from: a position written after the swap would be
    # written against a library that has never heard of that episode.
    _stop_playback(frame)
    downloads = _downloads_dir(frame)
    frame._set_status("Restoring QUILL Cast...")

    def _run() -> None:
        try:
            result = backup.restore_backup(src, app_data_dir(), downloads_dir=downloads)
        except Exception as exc:  # noqa: BLE001 - surface a clean message
            wx.CallAfter(frame._set_status, f"Restore failed: {exc}")
            wx.CallAfter(frame._announce, f"Restore failed. {exc}")
            return
        wx.CallAfter(_apply_restore, frame, result)

    threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: restore worker.


def _stop_playback(frame: Any) -> None:
    """Stop the player before a library is replaced underneath it."""
    controller = getattr(frame, "_podcast_controller", None)
    stop = getattr(controller, "stop", None)
    if not callable(stop):
        return
    try:
        stop()
    except Exception:  # noqa: BLE001 - a restore must not fail on the way in
        return


def _apply_restore(frame: Any, result: Any) -> None:
    """On the UI thread: reload the library and history from the restored files
    and refresh the view, so the restore is live without a restart."""
    from quill.core.paths import app_data_dir
    from quill.core.podcasts import history as podcast_history
    from quill.core.podcasts import subscriptions

    data_dir = app_data_dir()
    try:
        frame._podcast_library = subscriptions.load_library(data_dir)
        frame._podcast_history = podcast_history.load_history(data_dir)
        frame._reload_library_tree()
    except Exception as exc:  # noqa: BLE001 - it worked on disk; report the reload
        frame._set_status(
            f"Restored, but could not refresh the view ({exc}). "
            "Restart QUILL Cast to see your library."
        )
        return
    done = f"{result.summary()} Your podcasts are back."
    frame._set_status(done)
    frame._announce(done)
