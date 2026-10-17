"""The Read-Only Guard in QUILL Lite: Tools > Read-Only Guard, Ctrl+Alt+Backspace.

QUILL has had the guard since EDS-8, under Tools > Advanced; QUILL Lite gains
it on 2026-10-16 on the same key (rule 2), with the same memory
(:mod:`quill.core.read_only_guards`, kept in QUILL Lite's own data folder) and
the same sentences. Nothing here is QUILL Lite's own idea, which is the rule:
QUILL Lite may never be ahead of QUILL, and when it catches up it does so with
QUILL's code.

On, the guard:

* makes the control read-only, so typing, Backspace and Delete do nothing;
* refuses the commands that change text by name
  (:data:`quill.core.lite.read_only.TEXT_CHANGING_HANDLERS`), saying
  "Document is read-only" -- a read-only control still obeys a command's own
  writes, so the control alone is not enough;
* leaves reading, the caret, Find, numbered bookmarks and inline notes alone.
  A note added while the guard is on is kept beside the file rather than
  written into it.

A file that cannot be written at all (the read-only attribute, a read-only
share) opens guarded, as it does in QUILL, because typing into it for twenty
minutes and being refused at Ctrl+S is the worst moment to find out.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.lite.read_only import TEXT_CHANGING_HANDLERS
from quill.core.read_only_guards import (
    GUARD_FILENAME,
    READ_ONLY_REFUSAL,
    ReadOnlyGuards,
    toggle_sentence,
)

__all__ = ["DocumentReadOnlyMixin"]


class DocumentReadOnlyMixin:
    """Toggle, remember and enforce the guard on one QUILL Lite window."""

    _read_only: bool = False

    def _read_only_guards(self) -> ReadOnlyGuards:
        """One store for the whole app, so every window agrees about a file."""
        app: Any = getattr(self, "app", None)
        guards = getattr(app, "_read_only_guards", None)
        if not isinstance(guards, ReadOnlyGuards):
            from quill.core.lite import paths as lite_paths

            guards = ReadOnlyGuards(lite_paths.data_file(GUARD_FILENAME))
            if app is not None:
                app._read_only_guards = guards
        return guards

    def read_only_active(self) -> bool:
        return bool(self._read_only)

    def _host_read_only(self) -> bool:
        """The shared editor-host hook: inline notes and word tools ask this."""
        return self.read_only_active()

    def _apply_editable(self) -> None:
        control: Any = getattr(self, "control", None)
        try:
            control.SetEditable(not self._read_only)
        except (AttributeError, RuntimeError):
            pass

    def apply_read_only_guard(self, path: Path | None) -> None:
        """At open: guarded if somebody guarded this file, or it cannot be written."""
        from quill.core.file_access import is_read_only

        guarded = False
        if path is not None:
            guarded = self._read_only_guards().is_guarded(path) or is_read_only(path)
        self._read_only = guarded
        self._apply_editable()

    def cmd_toggle_read_only(self) -> None:
        """Ctrl+Alt+Backspace: lock this document against edits, or unlock it."""
        self._read_only = not self._read_only
        self._apply_editable()
        path = getattr(self, "path", None)
        reason = ""
        if path is not None:
            reason = self._read_only_guards().set(path, self._read_only)
        elif self._read_only:
            reason = "it has no file name yet"
        sync = getattr(self, "_sync_check_items", None)
        if callable(sync):
            sync()
        self._announce(toggle_sentence(self._read_only, saved=not reason, reason=reason))

    def run_unless_read_only(self, handler: str) -> None:
        """Run the command named *handler*, unless the guard refuses it."""
        if not self.refuse_while_read_only(handler):
            getattr(self, handler)()

    def refuse_while_read_only(self, handler: str) -> bool:
        """``True`` (and the sentence) when *handler* would change guarded text."""
        if not self._read_only or handler not in TEXT_CHANGING_HANDLERS:
            return False
        self._announce(READ_ONLY_REFUSAL)
        return True
