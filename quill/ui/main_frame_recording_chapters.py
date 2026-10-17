"""Tools > Speech > Find Chapters in a Recording: chapters for any MP3, by silence.

Item 42 of the 2026-10-16 checklist. QUILL could already propose chapters
from a recording's silences -- in the Chapter Workbench -- but the only way
into the Workbench was the Audio Studio's "edit an existing audiobook"
journey, and nobody with a lecture or a meeting recording thinks of it as an
audiobook. This is a plain door: pick a recording (MP3, M4A or M4B), and the
Workbench opens on it and starts "Propose chapters from silences" straight
away. Everything after that is the Workbench's own -- the two knobs, keep or
replace your existing chapters, stop the scan, hear and move each boundary,
rename, Restore original, Save -- and is described in
:mod:`quill.ui.audio_studio.chapter_workbench_silence`.

``tools.find_recording_chapters`` is on the QUILL leader (Ctrl+Shift+Grave,
Shift+O): a once-in-a-while command gets *a* key, not a short one (rule 9),
and QUILL Lite has no audio tools, so nothing it reaches plainly is moved
here (rule 6). Quill Studio has the same command on its Studio menu.
"""

from __future__ import annotations

from typing import Any

__all__ = ["RecordingChaptersMixin"]

COMMAND_ID = "tools.find_recording_chapters"


class RecordingChaptersMixin:
    """Registration, the Speech menu row, and the one handler."""

    def register_recording_chapter_commands(self) -> None:
        self.commands.try_register(  # type: ignore[attr-defined]
            COMMAND_ID,
            "Find Chapters in a Recording",
            self.find_chapters_in_recording,
            self._binding_for(COMMAND_ID),  # type: ignore[attr-defined]
        )

    def _append_recording_chapters_row(self, speech_menu: Any) -> None:
        """Tools > Speech > Find Chapters in a Recording..., bound once."""
        import wx

        from quill.core.i18n import _

        menu_id = getattr(self, "_id_find_recording_chapters", None)
        if menu_id is None:
            menu_id = self._id_find_recording_chapters = wx.NewIdRef()
        speech_menu.Append(
            menu_id,
            self._menu_label(_("&Find Chapters in a Recording..."), COMMAND_ID),  # type: ignore[attr-defined]
        )
        if not getattr(self, "_recording_chapters_wired", False):
            self._recording_chapters_wired = True
            self.frame.Bind(  # type: ignore[attr-defined]
                wx.EVT_MENU, lambda _e: self.find_chapters_in_recording(), id=menu_id
            )

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        menu_id = getattr(self, "_id_find_recording_chapters", None)
        if menu_id is not None:
            mapping[COMMAND_ID] = menu_id
        return mapping

    def find_chapters_in_recording(self) -> None:
        """Pick a recording; open the Chapter Workbench on it, proposing chapters."""
        from quill.ui.audio_studio.chapter_workbench import open_book_in_workbench
        from quill.ui.audio_studio.chapter_workbench_silence import pick_recording

        path = pick_recording(self.frame)  # type: ignore[attr-defined]
        if path is None:
            return
        open_book_in_workbench(self, path, propose_silences=True)
