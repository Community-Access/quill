"""Getting from one misspelling to the next, and seeing them all at once.

Split out of :mod:`quill.apps.lite_window_spelling` under GATE-11, and the line
is a real one: that module is about *judging* a word -- the dictionary, the live
check, how a misspelling is said aloud -- and this is about *finding* one.

Three commands, and they answer three different questions. Ctrl+F7 answers
"where is the next one", the list answers "how many are there and which do I
want", and both of them then hand the word to the voicing the other module owns.

The sentence for "there are none in this direction" is
:func:`quill.core.spellcheck.no_misspelling_message`, shared with QUILL: a bare
"No further misspellings" reads as "your document is clean", which is a lie when
seven are sitting behind the caret (bad.md S9).
"""

from __future__ import annotations

from quill.apps.lite_dialogs import choose_from_rows
from quill.core.marks import line_column_for_position

__all__ = ["DocumentSpellingNavigationMixin"]


class DocumentSpellingNavigationMixin:
    """Next, previous, and the whole list."""

    def cmd_misspelling_list(self) -> None:
        """Every misspelling in the document, as one list you can jump from.

        Ctrl+F7 N times is the alternative, and it answers a different question:
        it moves you to the next one, and this tells you how many there are and
        lets you choose. QUILL Lite already builds exactly this data for its live
        check; it had no way to show it (bad.md 4.2, Tier 2).

        Ignored words are left out, because a list that offers you the word you
        just chose to skip is a list you have to re-skip on every visit.
        """
        from quill.core.spellcheck import list_misspellings

        if not self._require_spelling():
            return
        text = self.doc_text.text
        dictionary = self._spell_dictionary()
        items = [
            item
            for item in list_misspellings(text, dictionary)
            if not self.spell_ignores.skips(text, item)
        ]
        if not items:
            self._announce("No misspellings found")
            return
        rows = []
        for index, item in enumerate(items):
            line, _column = line_column_for_position(text, item.start)
            rows.append((index, f"{item.word} -- line {line:,}"))
        chosen = choose_from_rows(
            self,
            title="Misspellings",
            label="&Misspelled words in this document:",
            help_text=(
                "Every word the dictionary does not know, in document order, "
                "with the line it is on. Choose one and press Enter to go to it."
            ),
            rows=rows,
        )
        if chosen is None:
            self.control.SetFocus()
            return
        item = items[int(chosen)]
        self._go_to(item.start)
        self.control.SetSelection(item.start, item.end)
        self._announce(f"Misspelling: {item.word}")

    def cmd_next_misspelling(self) -> None:
        """Ctrl+F7: move to the next word that is not in the dictionary."""
        self._go_to_misspelling(forward=True)

    def cmd_previous_misspelling(self) -> None:
        """Ctrl+Shift+F7: move to the previous one."""
        self._go_to_misspelling(forward=False)

    def _go_to_misspelling(self, *, forward: bool) -> None:
        from quill.core.spellcheck import next_misspelling, previous_misspelling

        if not self._require_spelling():
            return
        text = self.control.GetValue()
        caret = self.control.GetInsertionPoint()
        finder = next_misspelling if forward else previous_misspelling
        # Stepped rather than filtered: an ignored word is not a stop, so the
        # search carries on from where that one was instead of announcing "no
        # further misspellings" at the first word somebody chose to skip. Bounded
        # by the search itself -- each hop starts past the last hit, so a
        # document of nothing but ignored words ends rather than loops.
        dictionary = self._spell_dictionary()
        item = finder(text, caret, dictionary)
        while item is not None and self.spell_ignores.skips(text, item):
            caret = item.end if forward else item.start
            item = finder(text, caret, dictionary)
        if item is None:
            # The count in the other direction, from the shared sentence QUILL
            # has said since #9. "No further misspellings" on its own reads as
            # "your document is clean", which is a lie when seven are sitting
            # behind the caret and the fix is to press the other key (bad.md S9).
            from quill.core.spellcheck import no_misspelling_message

            self._announce(
                no_misspelling_message(
                    text, self.control.GetInsertionPoint(), dictionary, ahead=forward
                )
            )
            return
        # Selected rather than merely arrived at: the word is then what Shift+F7
        # acts on, and what the reader reads on arrival.
        self.control.SetSelection(item.start, item.end)
        self._touch_status()
        self._announce("Misspelling: " + item.word)
        # And then the letters, after a pause. The reader has just said the
        # word, which for a misspelling is the one piece of information that
        # does not help: "recieve" and "receive" are the same sound. The pause
        # is what makes this free for somebody who does not need it -- the next
        # press of Ctrl+F7 cancels it unheard.
        self._spell_after_landing(item.word)
