"""The editor's own clipboard, tray, snippets and abbreviations, by voice.

dict.md 3.2 (gap 7). "copy all", "paste clip three", "insert snippet sign
off", "insert abbreviation addr", "show clips" and "show snippets" run the
editor's own features: the result is what the keyboard route gives. The
controller (``quill/core/windows_dictation/voice_commands.py``) decides what
was said and writes a snippet or a slot in as one dictated phrase; this module
is the bridge to whichever editor it is in.

**Both editors, one set of commands.** The hooks below are QUILL Lite's
answers; QUILL's adapter (:mod:`quill.ui.main_frame_windows_dictation`) gives
its own. Each editor's "snippets" are the list its own Snippets command shows:
in QUILL Lite that is the abbreviation library (its Snippets gallery,
Ctrl+Alt+Shift+Home); in QUILL it is the snippet library (Insert Snippet). A
snippet with blanks to fill in has each blank written as its name in square
brackets, "[title]", so "select title" finds it -- a voice command opens no
question boxes.
"""

from __future__ import annotations

from typing import Any

import wx

__all__ = ["DictationLibrary", "DictationLibraryMixin", "snippet_with_blanks"]


def snippet_with_blanks(body: str) -> tuple[str, int]:
    """A QUILL snippet's text, each blank written as ``[its name]``, and how
    far back from the end the cursor goes (its ``${cursor}``)."""
    from quill.core.snippets import extract_placeholders, render_snippet

    values = {
        placeholder.token: f"[{placeholder.name}]"
        for placeholder in extract_placeholders(body)
        if placeholder.kind in ("input", "choice")
    }
    result = render_snippet(body, values)
    return result.text, len(result.text) - result.cursor


class DictationLibrary:
    """What the controller's library commands reach: one editor's own features."""

    def __init__(self, host: Any) -> None:
        self._host = host

    def copy_all(self) -> None:
        self._host._dictation_copy_all()

    def copy_text(self, text: str) -> bool:
        return bool(self._host._dictation_set_clipboard(text))

    def show_clips(self) -> None:
        # After the phrase: a modal window opened inside a recogniser callback
        # would hold that callback open until it closed.
        self._later(self._host._dictation_show_clips)

    def show_snippets(self) -> None:
        self._later(self._host._dictation_show_snippets)

    def slot_text(self, number: int) -> str | None:
        """Slot *number*'s text, ``""`` when it is empty, ``None`` when there is
        no such slot."""
        return self._host._dictation_slot_text(number)

    def snippet_names(self) -> list[str]:
        return list(self._host._dictation_snippet_names())

    def snippet_text(self, name: str) -> tuple[str, int] | None:
        return self._host._dictation_snippet_text(name)

    def abbreviation_names(self) -> list[str]:
        return list(self._host._dictation_abbreviation_names())

    def abbreviation_text(self, name: str) -> tuple[str, int] | None:
        return self._host._dictation_abbreviation_text(name)

    @staticmethod
    def _later(action: Any) -> None:
        try:
            wx.CallAfter(action)
        except Exception:  # noqa: BLE001 - no event loop (tests): now
            action()


class DictationLibraryMixin:
    """QUILL Lite's answers to the library's questions. QUILL overrides them."""

    def _dictation_copy_all(self) -> None:
        self.cmd_copy_all()  # type: ignore[attr-defined]

    def _dictation_set_clipboard(self, text: str) -> bool:
        setter = getattr(self, "_set_clipboard_text", None)
        if callable(setter):
            return bool(setter(text))
        return False

    def _dictation_show_clips(self) -> None:
        self.cmd_paste_from_tray()  # type: ignore[attr-defined]

    def _dictation_show_snippets(self) -> None:
        self.cmd_snippet_gallery()  # type: ignore[attr-defined]

    def _dictation_slot_text(self, number: int) -> str | None:
        tray = self.app.copy_tray  # type: ignore[attr-defined]
        if not 1 <= number <= tray.SLOT_COUNT:
            return None
        return str(tray.slot(number).text or "")

    def _dictation_clipboard_text(self) -> str:
        """For an abbreviation that writes the clipboard (its ``${clipboard}``)."""
        reader = getattr(self, "_clipboard_text", None)
        return str(reader()) if callable(reader) else ""

    def _dictation_abbreviation_entries(self) -> list[Any]:
        library = getattr(getattr(self, "app", None), "abbreviations", None)
        return list(library.enabled_only()) if library is not None else []

    def _dictation_snippet_names(self) -> list[str]:
        return self._dictation_abbreviation_names()

    def _dictation_snippet_text(self, name: str) -> tuple[str, int] | None:
        return self._dictation_abbreviation_text(name)

    def _dictation_abbreviation_names(self) -> list[str]:
        return [entry.abbreviation for entry in self._dictation_abbreviation_entries()]

    def _dictation_abbreviation_text(self, name: str) -> tuple[str, int] | None:
        from quill.core.abbreviations import resolve_expansion

        entry = next(
            (one for one in self._dictation_abbreviation_entries() if one.abbreviation == name),
            None,
        )
        if entry is None:
            return None
        text, cursor, has_cursor = resolve_expansion(
            entry.expansion, self._dictation_clipboard_text()
        )
        return text, (len(text) - cursor) if has_cursor else 0
