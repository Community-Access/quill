"""Last session's documents in QUILL Lite: ask when it matters, remember the rest.

Extracted from ``lite.py`` under GATE-11 when the chooser landed, and the
extraction is the right shape rather than only the cheap one: QUILL's half is a
mixin of its own for the same reason (``main_frame_session_restore.py``), and the
two now read as the same feature written twice in the same order rather than as
one app's startup code.

The decisions -- whether to ask at all, what to say afterwards -- are
``quill.core.session_restore``, which is wx-free and shared, so the two editors
cannot drift on a question they answer identically. The window is
``quill.ui.session_restore_dialog``, shared for the same reason.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["LiteSessionMixin"]


class LiteSessionMixin:
    """Reopening, forgetting, and remembering what was open."""

    def _restore_session(self) -> bool:
        """Reopen last session's documents, in the order they were numbered.

        Silent when the answer is obvious -- one or two files, all still there,
        which is what this did for every case until 2026-09-19. Otherwise it
        asks, because four windows appearing unbidden is four things to identify
        before you can start, and a file that has *moved* is the one case where
        saying nothing is actively misleading. The decision and the window are
        both shared with QUILL.
        """
        from quill.core.session_restore import (
            ASK_WHEN_IT_MATTERS,
            openable,
            read_entries,
            should_ask,
        )

        entries = read_entries(list(self.settings.session_files))
        if not entries:
            return False
        mode = str(getattr(self.settings, "session_restore_ask", ASK_WHEN_IT_MATTERS))
        if not should_ask(entries, mode=mode):
            return bool(self._open_session_entries(tuple(e.path for e in openable(entries))))
        return self.choose_session_documents()

    def _open_session_entries(self, paths: tuple[str, ...]) -> int:
        """Open each remembered path that is still a file. Returns how many did.

        A count rather than a flag: the sentence said afterwards is "Reopened 2
        of 4", and a caller that only needs "did anything open" can ask whether
        the count is nonzero.
        """
        opened = 0
        for entry in paths:
            path = Path(entry)
            if path.is_file() and self.open_path(path):
                opened += 1
        return opened

    def choose_session_documents(self) -> bool:
        """Ask which remembered documents to reopen, and which to forget.

        Reached at launch when :func:`should_ask` says so, and from **File >
        Reopen Last Session...** at any time -- which is what makes "Not Now"
        safe: the answer is deferred, not lost.
        """
        from quill.core.session_restore import (
            ASK_WHEN_IT_MATTERS,
            describe_opened,
            read_entries,
        )
        from quill.ui.session_restore_dialog import ask_session_restore

        entries = read_entries(list(self.settings.session_files))
        if not entries:
            self.voice.speak(
                "Nothing was open last time. This list fills itself when you close "
                "QUILL Lite with documents open."
            )
            return False
        # The mode goes in as well as coming back: it decides which half of
        # the Never Ask Again / Ask Me Next Time pair the window offers, and
        # without it the way back out of *never* is greyed out in the one
        # window that can undo it.
        answer = ask_session_restore(
            self.shell,
            entries,
            mode=str(getattr(self.settings, "session_restore_ask", ASK_WHEN_IT_MATTERS)),
        )
        # Saved unconditionally: Forget and Clear change the list even when
        # nothing is opened, and this is the only write.
        self.settings.session_files = list(answer.remembered)
        if answer.ask_mode:
            self.settings.session_restore_ask = answer.ask_mode
        self.save_settings()
        opened_paths = answer.open_paths
        opened = self._open_session_entries(opened_paths)
        parts = [describe_opened(opened, len(opened_paths))]
        if answer.spoken:
            parts.append(answer.spoken)
        said = " ".join(part for part in parts if part).strip()
        if said and (opened_paths or answer.spoken):
            self.voice.speak(said)
        return bool(opened)

    def remember_session(self) -> None:
        """Record which files are open, for the next launch.

        Saved documents only. An untitled window has nothing to reopen *from*,
        and its content -- if it has any -- is the recovery store's business,
        which is a different promise with a different guarantee.
        """
        self.settings.session_files = [
            str(frame.path) for frame in self.frames if frame.path is not None
        ]
        self.save_settings()
