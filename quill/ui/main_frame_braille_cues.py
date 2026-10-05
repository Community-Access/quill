"""Braille Mode's caret cues and status data, as a MainFrame mixin.

The UI end of :mod:`quill.core.braille_cues`: on every caret move in a braille
file, say the page, print page or line-overflow crossing the user asked for
under **Settings > Braille Mode**, and feed the detailed status the proofing
state from the companion file. The decisions live in core; this only gathers
the inputs.

Fed from ``MainFrame._on_editor_caret_activity`` (key-up and click), never
from a focus handler: a page crossing is something the screen reader cannot
know, which is what makes it worth saying (GATE-13).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class BrailleCuesMixin:
    """Page, print-page and overflow cues; proofing data for the status."""

    # Relies on MainFrame helpers: _active_brf_resolver, editor, settings,
    # document, _announce, _status_message.

    def _maybe_announce_braille_movement(self) -> None:
        """Say what the caret just crossed, if the user asked to hear it."""
        from quill.core.braille_cues import already_said, movement_cues, snapshot

        settings = getattr(self, "settings", None)
        wanted = any(
            bool(getattr(settings, name, False))
            for name in (
                "braille_auto_announce_page_changes",
                "braille_auto_announce_print_page_changes",
                "braille_auto_announce_line_overflow",
            )
        )
        resolver = self._active_brf_resolver() if wanted else None  # type: ignore[attr-defined]
        editor = getattr(self, "editor", None)
        if resolver is None or editor is None:
            self._braille_caret_snapshot = None
            return
        try:
            position = resolver.resolve(editor.GetCurrentPos())
        except (ValueError, TypeError, IndexError, RuntimeError):
            return
        text = resolver.document.text
        print_page = None
        if bool(getattr(settings, "braille_auto_announce_print_page_changes", False)):
            print_page = self._braille_print_page_for(resolver, position.page)
        current = snapshot(text, position, print_page)
        document = getattr(self, "document", None)
        previous = getattr(self, "_braille_caret_snapshot", None)
        if getattr(self, "_braille_caret_document", None) is not document:
            # A different document starts fresh: switching files is not a
            # page crossing, and opening one announces itself.
            previous = None
        self._braille_caret_snapshot = current
        self._braille_caret_document = document
        last = str(getattr(self, "_status_message", "") or "")
        cues = movement_cues(previous, current, settings)
        cues = [cue for cue in cues if not already_said(last, cue)]
        if cues:
            self._announce(" ".join(cues))  # type: ignore[attr-defined]

    def _braille_print_page_for(self, resolver: Any, braille_page: int) -> int | None:
        """The print page on *braille_page*, detecting once per page map."""
        from quill.core.braille_cues import print_page_at
        from quill.core.brf_page_detection import detect_print_pages

        cache = getattr(self, "_braille_print_page_cache", None)
        if cache is None or cache[0] is not resolver:
            try:
                indicators = detect_print_pages(resolver.document.text, resolver.page_map)
            except Exception:  # noqa: BLE001 - no indicators means no print-page cue
                indicators = []
            cache = (resolver, indicators)
            self._braille_print_page_cache = cache
        return print_page_at(cache[1], braille_page)

    def _braille_proofing_status(self, page_count: int) -> object:
        """Proofing state for the detailed status, read without side effects.

        Unlike the proofing commands, this never asks the user to save first:
        an unsaved file simply has no proofing to report.
        """
        from quill.core.braille_cues import proofing_status_from_sidecar
        from quill.core.brf_sidecar import BRFSidecarError, read_sidecar

        path = getattr(getattr(self, "document", None), "path", None)
        sidecar = None
        if path is not None:
            try:
                sidecar = read_sidecar(Path(path))
            except (BRFSidecarError, OSError, ValueError):
                sidecar = None
        return proofing_status_from_sidecar(sidecar, page_count)
