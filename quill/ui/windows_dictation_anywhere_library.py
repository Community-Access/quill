"""Your snippets, abbreviations and clips, by voice, in any program (D-8 slice).

"insert snippet sign off", "insert abbreviation addr" and "paste clip three"
work in the editors through their own libraries
(:mod:`quill.ui.windows_dictation_library`). In another program -- QUILL
Transcribe, and Quill Inkwell's Dictate Anywhere -- they work too, because they
only *insert*: nothing in the other program is read. This is the library they
reach there, read from the family's own files, the same ones QUILL uses:

* **snippets** -- QUILL's snippet library (``snippets.json``);
* **abbreviations** -- the shared abbreviation library QUILL and Inkwell use;
* **clips** -- QUILL's twelve copy-tray slots.

The controller types the text through the shared external document as one
phrase (``voice_commands._insert_text``), so "scratch that" takes all of it
back, and every target check a dictated phrase gets applies.

Two limits, both said in the guides. A snippet's blanks are written as their
names in square brackets, "[title]", as in the editors; no question is asked
(spoken prompts are the rest of D-8). And a ``${cursor}`` mark is dropped: the
cursor cannot be moved back inside another program's text without reading it,
so it is left at the end.

The commands that read or show something -- "copy that", "copy all", "show
clips", "show snippets" -- stay QUILL's own (``anywhere.EXTERNAL_COMMANDS``).
"""

from __future__ import annotations

from typing import Any

__all__ = ["AnywhereLibrary"]


class AnywhereLibrary:
    """The insert-only half of the editors' library, from the family's files."""

    def slot_text(self, number: int) -> str | None:
        """Clip *number*'s text, ``""`` when empty, ``None`` when there is no slot."""
        from quill.core import paths
        from quill.core.copy_tray import CopyTray

        tray = CopyTray(paths.app_data_dir())
        if not 1 <= number <= tray.SLOT_COUNT:
            return None
        return str(tray.slot(number).text or "")

    def _snippets(self) -> list[Any]:
        from quill.core.snippets import load_snippet_library

        try:
            library = load_snippet_library()
        except Exception:  # noqa: BLE001 - an unreadable library has no snippets
            return []
        return [one for one in library.snippets if one.enabled and one.name]

    def snippet_names(self) -> list[str]:
        return [snippet.name for snippet in self._snippets()]

    def snippet_text(self, name: str) -> tuple[str, int] | None:
        from quill.ui.windows_dictation_library import snippet_with_blanks

        for snippet in self._snippets():
            if snippet.name == name:
                try:
                    text, _back = snippet_with_blanks(snippet.body)
                except ValueError:
                    return None
                return text, 0  # ${cursor} is dropped outside the editors
        return None

    def _abbreviations(self) -> list[Any]:
        from quill.core.abbreviations import load_abbreviation_library

        try:
            return list(load_abbreviation_library().enabled_only())
        except Exception:  # noqa: BLE001 - an unreadable library has no entries
            return []

    def abbreviation_names(self) -> list[str]:
        return [entry.abbreviation for entry in self._abbreviations()]

    def abbreviation_text(self, name: str) -> tuple[str, int] | None:
        from quill.core.abbreviations import resolve_expansion

        entry = next((one for one in self._abbreviations() if one.abbreviation == name), None)
        if entry is None:
            return None
        clipboard = _clipboard_text() if "${clipboard}" in entry.expansion else ""
        text, _cursor, _has_cursor = resolve_expansion(entry.expansion, clipboard)
        return text, 0  # ${cursor} is dropped outside the editors

    # Not reachable in another program (anywhere.EXTERNAL_COMMANDS), and safe if asked.
    def copy_all(self) -> None:
        pass

    def copy_text(self, text: str) -> bool:
        del text
        return False

    def show_clips(self) -> None:
        pass

    def show_snippets(self) -> None:
        pass


def _clipboard_text() -> str:
    """For an abbreviation that writes the clipboard (its ``${clipboard}``)."""
    try:
        import wx

        if not wx.TheClipboard.Open():
            return ""
        try:
            data = wx.TextDataObject()
            return str(data.GetText()) if wx.TheClipboard.GetData(data) else ""
        finally:
            wx.TheClipboard.Close()
    except Exception:  # noqa: BLE001 - no clipboard is an empty one
        return ""
