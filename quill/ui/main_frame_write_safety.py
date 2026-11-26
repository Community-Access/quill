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
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from quill.core.autosave import autosave_document
from quill.core.backups import backup_document
from quill.stability.wx_dispatch import call_ui_safely

if TYPE_CHECKING:  # pragma: no cover - typing only
    from quill.core.document import Document

logger = logging.getLogger(__name__)

#: Background tasks that only read, so trying again cannot do anything twice.
_READING_LABELS = ("Loading ", "Checking ", "Looking for ", "Previewing ")


class WriteSafetyMixin:
    def _backup_before_save(self, document: Document) -> None:
        """Snapshot *document* into the backups folder -- best-effort (#1390).

        A backup exists to protect the user *from* a bad save, so it can never
        be the reason a save does not happen.
        """
        # Logged as well as spoken: the status line is gone by the time anyone
        # asks why there is no backup to restore, and the log is where a support
        # bundle looks.
        name = document.path.name if document.path is not None else "an untitled document"
        try:
            backup_document(document)
        except OSError as error:
            reason = error.strerror or str(error)
            logger.warning("Could not write a backup of %s before saving: %s", name, reason)
            self._set_status(f"Could not write a backup ({reason}); saving anyway")
        except Exception:  # noqa: BLE001 - a backup must never block a save
            logger.exception("Could not write a backup of %s before saving", name)
            self._set_status("Could not write a backup; saving anyway")

    def _report_save_failure(
        self, name: str, error: OSError | UnicodeEncodeError, title: str
    ) -> None:
        """Explain a failed save and offer Save As (#1390, FUX-16).

        The sentence says what went wrong in plain words and that the text is
        still open and unsaved; the error's own text is behind Copy Details.
        Save As is the default button, because a different place is the one
        thing that gets the work onto disk now.
        """
        message = self._save_failure_sentence(name, error)
        self._set_status(f"Could not save {name}")
        if self._show_failure_box(
            message,
            title,
            next_label="Save &As...",
            next_help="Saves the document somewhere else, under a name you choose.",
            error=error,
            context=f"Saving {name}",
        ):
            self.save_file_as()

    def _save_failure_sentence(self, name: str, error: OSError | UnicodeEncodeError) -> str:
        """The words for a failed save, for the box above or for speech.

        The clipboard collector's quiet save speaks this rather than opening the
        box: a copy made in another program must never put a window in front of
        you, and the failure still has to say what to do. The words are shared
        with QUILL Lite (``command_failure.save_failure_sentence``).
        """
        from quill.core.command_failure import save_failure_sentence

        codec = ""
        if isinstance(error, UnicodeEncodeError):
            # Not error.encoding alone: every Windows code page reports itself
            # as "charmap", which names nothing. The document knows what it was
            # opened as, and that is the word the writer will recognise.
            codec = str(error.encoding or "").strip()
            if codec in {"", "charmap"}:
                codec = str(getattr(getattr(self, "document", None), "encoding", "") or "")
        return save_failure_sentence(name, error, codec=codec)

    def _show_failure_box(
        self,
        message: str,
        caption: str,
        *,
        next_label: str = "",
        next_help: str = "",
        error: BaseException | None = None,
        context: str = "",
    ) -> bool:
        """A failure box with one next step and Copy Details (FUX-16).

        True when the person chose the next step. The error's own text goes
        to the details, never into *message*.
        """
        from quill.core.command_failure import failure_details
        from quill.ui.next_step_box import show_next_step

        details = failure_details(error, app="QUILL", context=context) if error else ""
        return show_next_step(
            self.frame,
            message,
            caption,
            next_label=next_label,
            next_help=next_help,
            details=details,
            announce=self._announce,
            show_modal=self._show_modal_dialog,
        )

    def _report_background_failure(
        self, label: str, error: BaseException, retry: Callable[[], None] | None
    ) -> None:
        """A background task failed: say so plainly, with the next step that fits.

        Reading tasks ("Opening", "Loading", "Checking") change nothing, so
        Retry is safe to offer; an open whose file has gone offers Choose
        Another File instead. A task that writes or sends is never offered
        Retry from here, because doing it again could do it twice.
        """
        from quill.core.command_failure import MISSING, plain_failure

        words = plain_failure(error)
        opening = label.startswith("Opening ")
        reading = opening or label.startswith(_READING_LABELS)
        message = f"{label} did not finish. {words.reason}"
        if opening:
            message += " Nothing was opened."
        next_label = next_help = ""
        if opening and words.kind == MISSING:
            next_label, next_help = "Choose Another &File...", "Opens the Open dialog."
        elif reading and retry is not None:
            next_label, next_help = "&Retry", f"Tries {label[0].lower()}{label[1:]} again."
        chosen = self._show_failure_box(
            message,
            label,
            next_label=next_label,
            next_help=next_help,
            error=error,
            context=label,
        )
        if chosen and next_label:
            if next_label.startswith("Choose"):
                self.open_file()
            elif retry is not None:
                retry()

    def _write_named_document(self) -> OSError | UnicodeEncodeError | None:
        """Write the active document to its own path and settle what a save settles.

        Shared by Save and the clipboard collector's quiet save
        (``clipboard_collector_saves``), so the two cannot drift: bookmarks,
        inline notes, the caret, the external-change watcher, persistent undo
        and the title. The error is returned rather than reported, because the
        two say it differently -- Save in a box, the collector aloud.
        """
        from quill.core.external_change import FileSnapshot

        try:
            self._write_document_to_disk(self.document)
        except (OSError, UnicodeEncodeError) as error:
            # UnicodeEncodeError since 2026-09-17 (bad.md P0.9): a cp1252
            # document that gains an em dash used to fail with "Command failed:
            # file.save" and leave the writer to guess which character did it.
            return error
        # Persist this document's bookmarks + cursor position under its path now that
        # it is saved (also migrates an untitled document's in-memory bookmarks).
        self._save_active_bookmarks()
        self._save_inline_notes()
        self._remember_active_caret()
        # FEAT-19: prime the watcher so our own save is not reported as an external change.
        if self._external_change_watcher is not None and self.document.path is not None:
            self._external_change_watcher.prime(FileSnapshot.of(self.document.path))
        self._record_persistent_undo_state(self.document.text)
        self.flush_persistent_undo()
        self._refresh_title()
        return None

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
