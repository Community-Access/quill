"""Reopening last session, with a say in it (QUILL's half).

Extracted from ``main_frame.py``, where ``restore_session`` reopened every
remembered file silently and skipped a missing one without a word. The decision
about *whether to ask* is ``quill.core.session_restore``; the window is
``quill.ui.session_restore_dialog``; both are shared with QUILL Lite, so the two
editors cannot drift on a question they answer identically.

``File > Reopen Last Session...`` (``Alt+Shift+F12``) opens the same window on
demand, which is what makes "Not Now" safe to press: the answer is deferrable
rather than lost, and there is a way back to it in the same session.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.session_restore import (
    ASK_WHEN_IT_MATTERS,
    SessionEntry,
    describe_opened,
    openable,
    read_entries,
    should_ask,
    summarise,
)

__all__ = ["SessionRestoreMixin"]


class SessionRestoreMixin:
    """Last session's documents: ask when it matters, then open what was chosen."""

    def _session_entries(self) -> tuple[SessionEntry, ...]:
        """The remembered list, capped, each row told whether its file is there.

        The cap was already 20 in both halves of the old code; it stays here so
        there is one place that knows it.
        """
        remembered = list(getattr(self.settings, "session_files", []) or [])[:20]
        return read_entries(remembered)

    def _save_session_list(self, paths: tuple[str, ...]) -> None:
        from quill.core.settings import save_settings

        self.settings.session_files = list(paths)
        save_settings(self.settings)

    def restore_session(self) -> int:
        """Reopen last session's documents. Returns how many opened.

        Silent when the answer is obvious -- one or two files that are all still
        there -- which is what both editors did for every case until 2026-09-19.
        Otherwise the chooser opens, because three windows appearing unbidden is a
        map to build before any work and a file that has *moved* is the one case
        where saying nothing is actively misleading.
        """
        if not getattr(self.settings, "restore_session", True):
            return 0
        entries = self._session_entries()
        if not entries:
            return 0
        mode = str(getattr(self.settings, "session_restore_ask", ASK_WHEN_IT_MATTERS))
        if not should_ask(entries, mode=mode):
            return self._open_session_paths(tuple(entry.path for entry in openable(entries)))
        return self._ask_and_open(entries)

    def reopen_last_session(self) -> int:
        """``File > Reopen Last Session...`` -- the chooser, on demand.

        The same window the launch may have shown, so "Not Now" costs nothing and
        a list that needs tidying can be tidied without waiting for a restart.
        Says so when there is nothing remembered rather than opening an empty
        window.
        """
        entries = self._session_entries()
        if not entries:
            self._set_status(
                "Nothing was open last time. This list fills itself when you close QUILL "
                "with documents open."
            )
            return 0
        return self._ask_and_open(entries)

    def _ask_and_open(self, entries: tuple[SessionEntry, ...]) -> int:
        from quill.ui.session_restore_dialog import ask_session_restore

        # The mode goes in as well as coming back: it is what decides which
        # half of the Never Ask Again / Ask Me Next Time pair the window
        # offers, and without it the way back out of *never* is greyed out
        # in the one window that can undo it.
        answer = ask_session_restore(
            self.frame,
            entries,
            mode=str(getattr(self.settings, "session_restore_ask", ASK_WHEN_IT_MATTERS)),
        )
        # Saved unconditionally: Forget and Clear change the list even when
        # nothing is opened, and this is the only write.
        self._save_session_list(answer.remembered)
        if answer.ask_mode:
            from quill.core.settings import save_settings

            self.settings.session_restore_ask = answer.ask_mode
            save_settings(self.settings)
        opened = self._open_session_paths(answer.open_paths)
        parts = (describe_opened(opened, len(answer.open_paths)), answer.spoken)
        said = " ".join(part for part in parts if part)
        if answer.open_paths or answer.spoken:
            self._announce(said.strip())
        return opened

    def _open_session_paths(self, paths: tuple[str, ...]) -> int:
        """Open each path, counting successes. One bad file never stops a launch."""
        opened = 0
        for entry in paths:
            candidate = Path(entry)
            if not candidate.is_file():
                continue
            try:
                self.open_file(candidate, record_recent=False)
            except Exception:  # noqa: BLE001 - one bad file must not stop launch
                continue
            opened += 1
        return opened

    def describe_session_list(self) -> str:
        """The remembered list as one sentence, for the status bar and tests."""
        return summarise(self._session_entries())
