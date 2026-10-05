"""Station-menu Back Up / Restore actions for Quill Radio (#1193).

Thin wx wiring over :mod:`quill.core.radio.backup`: the file dialogs, the
include-recordings and restore-confirm prompts, running the (potentially large)
zip work off the UI thread, and reloading the running app's favorites + history
after a restore so the change takes effect without a restart. Kept out of
radio.py so that at-budget module stays lean.

The recordings folder is the one Recording Settings names
(``frame._radio_recording_settings``), not the app's general settings: until
2026-10-04 this read the wrong object, so a listener whose recordings live in
OneDrive had them looked for in the default Music folder instead.

The host ``frame`` provides the app-shell contract already used across the radio
UI: ``frame.frame`` (the wx.Frame), ``frame._announce``, ``frame._set_status``,
``frame._show_message_box``, ``frame._show_modal_dialog``,
``frame._radio_favorites``, ``frame._radio_history``, ``frame._reload_favorites_tree``.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

#: How often the status bar may change while recordings copy (seconds).
_PROGRESS_EVERY = 0.5


def _recordings_dir(frame: Any) -> Path | None:
    """The folder Recording Settings names, or the default when none is set."""
    try:
        from quill.core.radio.recordings_index import recordings_dir

        settings = getattr(frame, "_radio_recording_settings", None)
        if settings is None:
            from quill.core.paths import app_data_dir
            from quill.core.radio.recording import load_recording_settings

            settings = load_recording_settings(app_data_dir())
        return Path(recordings_dir(settings))
    except Exception:  # noqa: BLE001 - a missing/odd setting just means "no recordings"
        return None


def _record_problems(subject: str, items: Any) -> None:
    """Write what was left out to Recent Problems, so it outlives the message."""
    rows = list(items)
    if not rows:
        return
    try:
        from quill.core import problem_log
        from quill.core.paths import app_data_dir

        listed = "; ".join(item.line() for item in rows[:20])
        more = f"; and {len(rows) - 20} more" if len(rows) > 20 else ""
        problem_log.record_problem(
            app_data_dir(), problem_log.KIND_OTHER, subject, f"{listed}{more}"
        )
    except Exception:  # noqa: BLE001 - a problem list is never worth a crash
        return


def back_up_radio_data(frame: Any) -> None:
    """Save a .qrbackup of the listener's stations, podcasts, settings, and
    (optionally) recordings to a location they choose."""
    import wx

    from quill.core.paths import app_data_dir
    from quill.core.radio import backup

    rec_dir = _recordings_dir(frame)
    plan = backup.plan_recordings(rec_dir)
    include_recordings = False
    if plan.files:
        answer = frame._show_message_box(
            plan.question(),
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
    last = [0.0]

    def _progress(done: int, total: int, name: str) -> None:
        now = time.monotonic()
        if now - last[0] < _PROGRESS_EVERY and done != total:
            return
        last[0] = now
        wx.CallAfter(frame._set_status, f"Backing up recording {done} of {total}: {name}")

    def _run() -> None:
        try:
            report = backup.create_backup_report(
                app_data_dir(),
                dest,
                recordings_dir=rec_dir,
                include_recordings=include_recordings,
                app_version=app_version,
                progress=_progress,
            )
        except Exception as exc:  # noqa: BLE001 - surface a clean message
            wx.CallAfter(_backup_failed, frame, str(exc))
            return
        wx.CallAfter(_backup_done, frame, report)

    threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: backup worker.


def _backup_failed(frame: Any, reason: str) -> None:
    """A failed backup is a message box, not a passing status line: it is the
    one result somebody about to reset a computer must not miss."""
    import wx

    frame._set_status(f"Backup failed: {reason}")
    frame._show_message_box(
        f"The backup was not saved.\n\n{reason}",
        "Back Up Quill Radio",
        wx.ICON_ERROR | wx.OK,
    )


def _backup_done(frame: Any, report: Any) -> None:
    frame._set_status(report.outcome())
    if not report.skipped:
        frame._announce(report.outcome())
        return
    _record_problems(f"Backup {report.path.name} left files out", report.skipped)
    from quill.ui.radio.skipped_items_dialog import offer_skipped_list

    offer_skipped_list(
        frame.frame,
        report.outcome() + " The list is also in Recent Problems.",
        report.skipped,
        caption="Back Up Quill Radio",
        announce=frame._announce,
    )


def restore_radio_data(frame: Any) -> None:
    """Restore stations, podcasts, settings, and any recordings from a .qrbackup
    the listener chooses, then reload the running app so it takes effect at once."""
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

    rec_dir = _recordings_dir(frame)
    when = manifest.created or "an earlier date"
    holds = backup.describe_data_files(manifest.data_files)
    extra = ""
    if manifest.recordings:
        extra = (
            f"\n\nIt also holds {manifest.recordings} recording(s), which go into "
            f"{rec_dir or 'your recordings folder'}. Recordings already there are left alone."
        )
    confirm = frame._show_message_box(
        f"Restore this backup (made {when})?\n\nIt holds your {holds}.{extra}\n\n"
        "This replaces your current stations, podcast subscriptions and settings.",
        "Restore Quill Radio",
        # NO_DEFAULT (2026-09-25): this overwrites every station and setting,
        # so Enter must not be the key that does it.
        wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
    )
    if confirm != wx.YES:
        return

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


def restore_outcome(result: Any) -> str:
    """The counted restore sentence (pure, for the tests)."""
    count = len(result.data_files)
    rec = f" and {len(result.recordings)} recording(s)" if result.recordings else ""
    done = f"Restored {count} settings file(s){rec}. Your stations are back."
    present, problems = _split_skipped(result)
    if present:
        noun = "recording was" if len(present) == 1 else "recordings were"
        done += f" {len(present)} {noun} already in your recordings folder and left alone."
    if problems:
        noun = "recording was" if len(problems) == 1 else "recordings were"
        done += f" {len(problems)} {noun} left out."
    return done


def _split_skipped(result: Any) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    """(already there, everything else) -- only the second is news worth a list."""
    from quill.core.skipped_files import REASON_ALREADY_THERE

    skipped = tuple(getattr(result, "skipped", ()) or ())
    present = tuple(item for item in skipped if item.reason == REASON_ALREADY_THERE)
    return present, tuple(item for item in skipped if item.reason != REASON_ALREADY_THERE)


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
    done = restore_outcome(result)
    frame._set_status(done)
    _present, problems = _split_skipped(result)
    if not problems:
        frame._announce(done)
        return
    from quill.ui.radio.skipped_items_dialog import offer_skipped_list

    offer_skipped_list(
        frame.frame, done, problems, caption="Restore Quill Radio", announce=frame._announce
    )
