"""Highlighted passages, shared by QUILL and QUILL Lite.

Three commands on the same chords in both editors (family rule 2):

* **Next Highlighted Passage** ``Alt+Page Down`` and **Previous Highlighted
  Passage** ``Alt+Page Up`` -- move to the passage's first character and say
  its colour, where it is in the count, and its words. Both wrap at the ends,
  as Next Inline Note does.
* **Highlighted Passages** ``Ctrl+F2`` -- every passage in one list
  (:mod:`quill.ui.highlight_list_dialog`), each row the passage's words, its
  colour and the sentence around it. Enter goes to the passage; Escape leaves
  the caret where it was.

Where the passages come from depends on what the editor is showing, and
:meth:`HighlightCommandsMixin._highlight_passages` asks in this order:

1. **A rich document** (a Word document QUILL edits as Rich Text, or any RTF):
   the live control's own RTF, read through the RTF bridge, then placed on the
   control's text by words and paragraph. Read fresh on every press, so a
   highlight just applied or just removed, and an edit above a passage, are
   already reflected.
2. **A Markdown document**: QUILL's ``[words]{highlight="yellow"}`` hidden code,
   with offsets straight into the buffer.
3. **A Word file shown as text** (QUILL's read-extract choice, and every Word
   file QUILL Lite opens): the highlights in the file on disk
   (:mod:`quill.io.docx_highlights`), placed on the text by their words. A
   passage whose words have since been edited away is left out rather than
   guessed at.

GATE-13: what is spoken is only what the screen reader cannot know -- the
colour, the count and, because a caret moved by a program is not one every
reader reads, the passage's words. Never the window or the list's title.
"""

from __future__ import annotations

from typing import Any

from quill.core.highlights import (
    HighlightPassage,
    align_runs,
    next_passage,
    passage_index_at,
    passages_from_markdown,
    previous_passage,
    runs_from_markdown,
    spoken_passage,
)
from quill.ui.editor_host import EditorHostMixin

__all__ = ["NO_HIGHLIGHTS", "HighlightCommandsMixin"]

#: Said when a document has nothing highlighted, by every command.
NO_HIGHLIGHTS = "No highlighted passages in this document"


class HighlightCommandsMixin(EditorHostMixin):
    """The highlighted-passage commands. Mixed into both editors' document windows."""

    # ------------------------------------------------------------------ #
    # Hooks (QUILL Lite's answers; QUILL overrides in main_frame_editor_host)
    # ------------------------------------------------------------------ #

    def _host_rich_wrapper(self) -> Any:
        """The Rich Edit wrapper when the document is in rich mode, else ``None``."""
        from quill.ui.richedit_editing import RICH

        editor = getattr(self, "editor", None)
        return editor if getattr(editor, "mode", None) == RICH else None

    def _host_go_to(self, position: int) -> None:
        """Put the caret at *position* the way every other jump does (feeds Back)."""
        go_to = getattr(self, "_go_to", None)
        if callable(go_to):
            go_to(position)
            return
        control = self._host_control()
        control.SetInsertionPoint(position)
        show = getattr(control, "ShowPosition", None)
        if callable(show):
            show(position)

    # ------------------------------------------------------------------ #
    # Finding them
    # ------------------------------------------------------------------ #

    def _highlight_passages(self) -> list[HighlightPassage]:
        """Every highlighted passage in the document, as positions in its control."""
        control = self._host_control()
        text = str(control.GetValue())
        wrapper = self._host_rich_wrapper()
        if wrapper is not None:
            rtf: str | None
            try:
                rtf = bytes(wrapper.get_rtf()).decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001 - fall through to the other sources
                rtf = None
            if rtf is not None:
                from quill.io.rtf import rtf_to_markdown

                return align_runs(runs_from_markdown(rtf_to_markdown(rtf)), text)
        if self._host_kind() == "markdown":
            found = passages_from_markdown(text)
            if found:
                return found
        return self._word_file_passages(text)

    def _word_file_passages(self, text: str) -> list[HighlightPassage]:
        from quill.io.docx_highlights import WORD_HIGHLIGHT_SUFFIXES

        path = self._host_path()
        if path is None or path.suffix.lower() not in WORD_HIGHLIGHT_SUFFIXES:
            return []
        try:
            if not path.is_file():
                return []
            from quill.io.docx_highlights import read_docx_highlight_runs

            runs = read_docx_highlight_runs(path)
        except Exception:  # noqa: BLE001 - a damaged package simply has none to offer
            return []
        return align_runs(runs, text)

    # ------------------------------------------------------------------ #
    # Commands
    # ------------------------------------------------------------------ #

    def _go_to_passage(self, passages: list[HighlightPassage], index: int) -> None:
        passage = passages[index]
        self._host_go_to(passage.start)
        self._host_say(spoken_passage(passage, index, len(passages)))

    def cmd_next_highlight(self) -> None:
        """Alt+Page Down: the next highlighted passage, wrapping to the first."""
        passages = self._highlight_passages()
        index = next_passage(passages, int(self._host_control().GetInsertionPoint()))
        if index is None:
            self._host_say(NO_HIGHLIGHTS)
            return
        self._go_to_passage(passages, index)

    def cmd_previous_highlight(self) -> None:
        """Alt+Page Up: the previous highlighted passage, wrapping to the last."""
        passages = self._highlight_passages()
        index = previous_passage(passages, int(self._host_control().GetInsertionPoint()))
        if index is None:
            self._host_say(NO_HIGHLIGHTS)
            return
        self._go_to_passage(passages, index)

    def cmd_list_highlights(self) -> None:
        """Ctrl+F2: every highlighted passage in one list; Enter goes to it."""
        import wx

        from quill.ui.highlight_list_dialog import show_highlight_list

        passages = self._highlight_passages()
        if not passages:
            self._host_say(NO_HIGHLIGHTS)
            return
        start = passage_index_at(passages, int(self._host_control().GetInsertionPoint()))
        chosen = show_highlight_list(
            wx, self._host_parent(), self._host_show_modal, passages, start
        )
        if chosen is None:
            return
        # The caret lands on the passage; the reader reads the line it is on,
        # so nothing is said here -- unlike Next, there is no count to give.
        self._host_go_to(passages[chosen].start)
