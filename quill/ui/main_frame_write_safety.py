"""What QUILL does when a write fails -- backups, saves, autosave (#1390/#1386).

Extracted from ``main_frame.py`` (CQ-1 decomposition) because these four
concerns are one story: QUILL writes a document's text in three places, and
until #1390 it handled a failure in each of them differently and badly.

The rules this module encodes:

* **The save is the thing that must survive.** A backup is a convenience
  artifact; a backup that cannot be written degrades to a spoken status line and
  the save proceeds. Letting it abort the save inverts its whole purpose -- and
  that is exactly what happened on a full disk, with the close path then
  swallowing the exception and exiting with the document unsaved.
* **An error message must say what to do.** "[Errno 28] No space left on
  device" is true and useless.
* **A failed save is not consent to close.** #210 says the window must always
  close; it does not say it must close on unsaved work. The veto here fires
  once, so a bug in this path can still never trap the window open.
* **Autosave must never break editing -- but must not fail silently either.**
  Going quiet on a full disk means the user's crash-recovery net is gone with
  nothing said. It is announced once per failure streak.

``_write_autosave_snapshot`` also moves the autosave disk write off the UI
thread (#1346): it was a periodic multi-hundred-millisecond hitch mid-sentence
on a large file. Everything the writers need is captured on the UI thread by
the caller; nothing below that line touches wx.
"""

from __future__ import annotations

import errno
from typing import TYPE_CHECKING

from quill.core.autosave import autosave_document
from quill.core.backups import backup_document
from quill.stability.wx_dispatch import call_ui_safely

if TYPE_CHECKING:  # pragma: no cover - typing only
    from quill.core.document import Document


class WriteSafetyMixin:
    def _backup_before_save(self, document: Document) -> None:
        """Snapshot *document* into the backups folder -- best-effort (#1390).

        A backup exists to protect the user *from* a bad save, so it can never
        be the reason a save does not happen.
        """
        try:
            backup_document(document)
        except OSError as error:
            reason = error.strerror or str(error)
            self._set_status(f"Could not write a backup ({reason}); saving anyway")
        except Exception:  # noqa: BLE001 - a backup must never block a save
            self._set_status("Could not write a backup; saving anyway")

    def _report_save_failure(self, name: str, error: OSError, title: str) -> None:
        """Explain a failed save in words that say what to do about it (#1390).

        The disk-full and read-only cases get their own sentence; everything
        else keeps the errno text, which at least names the fault.
        """
        if error.errno == errno.ENOSPC:
            message = (
                f"The disk is full. QUILL could not save {name}. Free some space "
                "and try again -- your text is still open and unsaved."
            )
        elif error.errno in (errno.EACCES, errno.EPERM, errno.EROFS):
            message = (
                f"QUILL could not save {name}: the file or folder is read-only, "
                "or another program has it open. Try File > Save As to a "
                "different location -- your text is still open and unsaved."
            )
        else:
            message = f"Could not save {name}: {error}"
        self._show_message_box(message, title, self._wx.ICON_ERROR | self._wx.OK)
        self._set_status(f"Could not save {name}")

    def _veto_close_after_failed_save(self) -> bool:
        """Whether to cancel this close because a save failed (#1390).

        True only the first time, and only while something is genuinely
        unsaved: the second attempt closes, so #210's "the window must always
        close" guarantee still holds even if this path itself has a bug.
        """
        if getattr(self, "_close_vetoed_after_failed_save", False):
            return False
        try:
            unsaved = any(
                getattr(getattr(tab, "document", None), "modified", False)
                for tab in getattr(self, "_document_tabs", [])
            )
        except Exception:  # noqa: BLE001 - never trap the window open
            return False
        if not unsaved:
            return False
        self._close_vetoed_after_failed_save = True
        self._show_message_box(
            "QUILL could not save your document, so it has not been closed. "
            "Free some disk space or use File > Save As to another location, "
            "then close again. Closing a second time will discard the changes.",
            "Save failed",
            self._wx.ICON_ERROR | self._wx.OK,
        )
        return True

    def _note_autosave_failure(self, error: OSError) -> None:
        """Say once that autosave has stopped working (#1386).

        Two failures in a row is enough to rule out a transient blip; after
        that we say it once -- not on every attempt -- and stay quiet until
        autosave succeeds again. Spoken, not just written: a status-bar line
        nobody reads is exactly how the user would find out too late.
        """
        self._autosave_failures = int(getattr(self, "_autosave_failures", 0)) + 1
        if self._autosave_failures < 2 or getattr(self, "_autosave_failure_announced", False):
            return
        self._autosave_failure_announced = True
        if error.errno == errno.ENOSPC:
            detail = "the disk is full"
        elif error.errno in (errno.EACCES, errno.EPERM):
            detail = "QUILL cannot write to its data folder"
        else:
            detail = error.strerror or str(error)
        self._announce(f"Autosave paused -- {detail}. Your work is not being snapshotted.")

    def _write_autosave_snapshot(
        self, snapshot: Document, rich_payload: bytes | None, caret: int | None
    ) -> None:
        """Write the autosave artifacts, off the UI thread when one is available.

        Falls back to a synchronous write when there is no task manager (early
        startup, headless tests) so the snapshot is never simply skipped.
        """
        manager = getattr(self, "_task_manager", None)
        submit = getattr(manager, "submit", None)
        if not callable(submit):
            self._autosave_worker(snapshot, rich_payload, caret)
            return
        submit(
            name="autosave-snapshot",
            func=lambda **_kw: self._autosave_worker(snapshot, rich_payload, caret),
        )

    def _autosave_worker(
        self, snapshot: Document, rich_payload: bytes | None, caret: int | None
    ) -> None:
        """The autosave writes themselves. Runs on a worker thread; no wx here."""
        failure: OSError | None = None
        try:
            autosave_document(snapshot, self.session_id)
        except OSError as error:  # autosave must never break editing
            failure = error
        except Exception:  # noqa: BLE001 - autosave must never break editing
            pass
        # Rich tabs also snapshot the RTF bytes: TOM formatting never changes
        # the plain text, so a text-only snapshot would lose formatting in a
        # crash. Best-effort by the same contract as the text snapshot.
        if rich_payload is not None:
            try:
                from quill.core.autosave import autosave_rich_document

                autosave_rich_document(snapshot, self.session_id, rich_payload)
            except Exception:  # noqa: BLE001 - autosave must never break editing
                pass
        # §8.4 "Resume from where I left off": persist cursor position alongside
        # every autosave so the next session can restore it.
        if caret is not None:
            try:
                from quill.core.recovery import save_cursor_position

                save_cursor_position(self.session_id, caret)
            except Exception:  # noqa: BLE001
                pass
        if failure is not None:
            call_ui_safely(self._note_autosave_failure, failure)
        else:
            self._autosave_failures = 0
            self._autosave_failure_announced = False
