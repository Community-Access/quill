"""When another program changes your file: QUILL Lite watches each document.

QUILL has watched the file you have open since FEAT-19; QUILL Lite only checked
at Save (``lite_window_sources.py``). Since 2026-10-04 each QUILL Lite document
watches its own file too, from the code QUILL uses -- QUILL Lite may never be
ahead of QUILL, and here it is not allowed a second implementation either:

* **what to do** is :func:`quill.core.external_change.decide_for`, read from the
  same six settings under the same names;
* **the clock** is :class:`quill.ui.external_change_timer.ExternalChangeTimer`,
  which waits while a modal window is up and never re-enters;
* **the question** is :func:`quill.ui.external_change_dialog.ask_external_change`,
  with Save As as its third answer and Keep Mine on Enter.

One timer per document, because an MDI child is where the document lives and
where its own timers already are. Each tick is a stat; the file is read and
hashed only when its size or modification time moved, so nine open documents
cost nine stats a poll.

The baseline is the one the save-time check already keeps
(``_disk_baseline``), so the two can never disagree: a reload, Keep Mine and
every save of QUILL Lite's own move it, and a change reported here is not
asked about again at Save.

Composed onto ``DocumentFrame``, which supplies ``app``, ``control``,
``editor``, ``path``, ``modified`` and the announcement hooks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.external_change import (
    CHANGE_DELETED,
    CHANGE_NONE,
    FileSnapshot,
    ReloadAction,
    decide_for,
    deleted_sentence,
    poll_disk,
    poll_interval_ms,
    reloaded_sentence,
    remember_answer,
)

__all__ = ["DocumentDiskWatchMixin"]

#: Where QUILL Lite takes a "do not ask me again" answer back.
_FORGET_HINT = "Preferences, Forget remembered file-change answers, undoes this."


class DocumentDiskWatchMixin:
    """Watch this document's file, and ask before anything replaces what is open."""

    _disk_watch: Any = None
    #: The change already reported for the current baseline, so one change is
    #: said or asked about once however many ticks see it.
    _disk_reported: FileSnapshot | None = None
    _disk_reported_for: FileSnapshot | None = None
    #: A question waiting for this window to be the one in front.
    _disk_pending: tuple[ReloadAction, FileSnapshot] | None = None

    def _start_disk_watch(self) -> None:
        """Start the clock. Safe to call twice; a window with no file just idles."""
        if self._disk_watch is not None:
            return
        from quill.ui.external_change_timer import ExternalChangeTimer

        self._disk_watch = ExternalChangeTimer(
            self,
            self._poll_disk_watch,
            interval=lambda: poll_interval_ms(self.app.settings),
            busy=self._disk_watch_busy,
        )
        self._disk_watch.start()

    def _stop_disk_watch(self) -> None:
        watch, self._disk_watch = self._disk_watch, None
        if watch is not None:
            watch.stop()

    def _disk_watch_busy(self) -> bool:
        """Loading, saving or opening in the background: not the moment to look."""
        return bool(
            getattr(self, "_loading", False)
            or getattr(self, "_saving", False)
            or getattr(self, "opening_path", None) is not None
            or getattr(self.app, "shutting_down", False)
        )

    def _poll_disk_watch(self) -> None:
        """One tick: has the file moved on from the version this window has?"""
        settings = self.app.settings
        if self.path is None or not getattr(settings, "external_change_watch_enabled", True):
            return
        if self._disk_pending is not None:
            self._ask_pending_disk_change()
            return
        baseline = getattr(self, "_disk_baseline", None)
        if baseline is not None and self._disk_reported is not None:
            # A new baseline (a save, a reload, an open) starts the count again.
            if getattr(self, "_disk_reported_for", None) is not baseline:
                self._disk_reported = None
        poll = poll_disk(self.path, baseline, self._disk_reported)
        if poll.change == CHANGE_NONE:
            if poll.current is not None:
                # Touched, not changed: the same bytes. Adopt it, so the next
                # tick is a stat again rather than another read.
                self._disk_baseline = poll.current
            return
        current = poll.current or FileSnapshot(exists=False)
        self._disk_reported = current
        self._disk_reported_for = baseline
        name = Path(self.path).name
        decision = decide_for(
            poll.change, settings, buffer_dirty=bool(self.modified), file_name=name
        )
        if decision.action is ReloadAction.NONE:
            return
        if poll.change == CHANGE_DELETED:
            # No question: there is nothing on disk to reload, and the text is
            # still here. Say so once and make sure Save is not a no-op.
            self._set_modified(True)
            self._announce(deleted_sentence(name))
            return
        if decision.action is ReloadAction.RELOAD:
            if self._reload_from_disk(current):
                self._announce(reloaded_sentence(name))
            return
        if decision.action is ReloadAction.KEEP_MINE:
            self._keep_mine(current)
            self._announce(decision.announcement)
            return
        self._disk_pending = (decision.action, current)
        self._ask_pending_disk_change()

    def _ask_pending_disk_change(self) -> None:
        """Ask now if this document is the one in front; otherwise wait for it.

        A question about a document you are not looking at would be answered
        about the wrong one.
        """
        active = getattr(self.app, "active_frame", None)
        if active is not None and active is not self:
            return
        pending, self._disk_pending = self._disk_pending, None
        if pending is None or self.path is None:
            return
        from quill.ui.external_change_dialog import KEEP, RELOAD, SAVE_AS, ask_external_change

        _action, current = pending
        name = Path(self.path).name
        answer = ask_external_change(
            self,
            name,
            buffer_dirty=bool(self.modified),
            alternative=SAVE_AS,
            default_keep=True,
            forget_hint=_FORGET_HINT,
        )
        if remember_answer(self.app.settings, name, answer.remembered_value):
            self.app.save_settings()
        if answer.action == RELOAD:
            if self._reload_from_disk(current):
                self._announce(f"Reloaded {name} from disk.")
        elif answer.action == KEEP:
            self._keep_mine(current)
            # The status bar only, as QUILL does: the answer was just given, and
            # the reader is already reading the document focus returned to.
            status = getattr(self, "_set_status_message", None)
            if callable(status):
                status(f"Keeping your version. Saving replaces what is on disk in {name}.")
        elif answer.action == SAVE_AS:
            self.cmd_save_as()

    def _keep_mine(self, current: FileSnapshot) -> None:
        """Adopt the disk version as seen: Save may now write over it unasked."""
        self._disk_baseline = current
        self._disk_reported = None

    def _reload_from_disk(self, current: FileSnapshot) -> bool:
        """Read the file again in place, keeping the caret on the same line."""
        from quill.core.lite.filetypes import is_rich_path
        from quill.core.lite.open_prepare import prepare as prepare_document
        from quill.ui.richedit_editing import PLAIN, RICH
        from quill.ui.richedit_rtf_surface import RichEditRtfError

        path = Path(self.path)
        mode = RICH if is_rich_path(path.name) else PLAIN
        line = self._caret_line()
        try:
            self._check_mode_available(mode)
            prepared = prepare_document(path, mode)
            self._loading = True
            try:
                if prepared.mode == RICH:
                    self._commit_rich(prepared)
                else:
                    self._commit_plain(prepared)
            finally:
                self._loading = False
                self.doc_text.invalidate()
        except (OSError, RichEditRtfError) as exc:
            self._announce(f"Could not reload {path.name} from disk: {exc}")
            return False
        self._disk_baseline = current if current.exists else FileSnapshot.of(path)
        self._disk_reported = None
        if getattr(self, "_pending_suffix", ""):
            self._pending_suffix = ""
        self._set_modified(False)
        self._go_to_line(line)
        self._update_title()
        self._touch_status()
        return True

    def _caret_line(self) -> int:
        try:
            found, _column, line = self.control.PositionToXY(self.control.GetInsertionPoint())
        except Exception:  # noqa: BLE001 - an unreadable caret is the first line
            return 0
        return int(line) if found else 0

    def _go_to_line(self, line: int) -> None:
        """The start of *line*, or of the last line if the file is now shorter."""
        last = max(0, int(self.control.GetNumberOfLines()) - 1)
        position = self.control.XYToPosition(0, max(0, min(line, last)))
        if position < 0:
            position = 0
        self.control.SetInsertionPoint(position)
        self.control.ShowPosition(position)
