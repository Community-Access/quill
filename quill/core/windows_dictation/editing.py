"""The whole-phrase commands that edit the document, and sentence joining.

Split out of :mod:`~quill.core.windows_dictation.controller` (GATE-11): the
state machine decides *when* a command runs; this is *what* each one does to
the text -- scratch, select, change case, delete back, move the caret -- and the
one rule that edits between phrases, taking back a full stop a pause put in.

Every edit that touches a dictated phrase first checks the phrase is still
exactly as it was written. A phrase somebody has typed into since is left alone,
and they are told, because its range no longer means what it did.

wx-free; mixed into :class:`~quill.core.windows_dictation.controller.DictationController`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from quill.core.windows_dictation.history import DictatedPhrase, PhraseHistory
from quill.core.windows_dictation.vocabulary import Command

__all__ = ["EditingMixin"]

#: Words that continue a sentence rather than start one. When a phrase begins
#: with one of these straight after a phrase the recogniser closed with a full
#: stop, the pause was a breath, not the end of a sentence.
_CONTINUATIONS = frozenset({
    "and",
    "but",
    "or",
    "nor",
    "so",
    "yet",
    "because",
    "which",
    "who",
    "whom",
    "whose",
    "that",
    "when",
    "while",
    "where",
    "whereas",
    "although",
    "though",
    "unless",
    "until",
    "if",
    "then",
    "than",
    "to",
    "with",
    "without",
    "for",
    "of",
    "in",
    "on",
    "at",
    "by",
    "from",
    "as",
    "like",
    "about",
    "after",
    "before",
    "since",
})

_WORD = re.compile(r"[a-z0-9']+")


def same_text(left: str, right: str) -> bool:
    """Equal once Windows and Unix line endings are treated alike."""

    def normal(text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n")

    return normal(left) == normal(right)


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text[:1].isupper() and not text[:2].isupper() else text


class EditingMixin:
    """The document-editing half of the controller."""

    _document: Any
    history: PhraseHistory

    def _say(self, message: str) -> None:  # provided by the controller
        raise NotImplementedError

    def _continue_sentence(self, pieces: tuple[Any, ...]) -> tuple[Any, ...] | None:
        """Undo a full stop a pause put in, when the new phrase carries on.

        An engine that punctuates ends every phrase as a sentence, so "I went to
        the store" [breath] "and bought milk" arrives as two sentences. When the
        new phrase opens with a word that continues one (and, but, which, to...)
        and the last phrase's full stop was the engine's -- not a spoken
        "period" -- and nothing has been typed since, that full stop comes back
        out and the capital with it.
        """
        last = self.history.peek()
        first = next((piece for piece in pieces if piece.mark is None and piece.text), None)
        if last is None or not last.auto_period or first is None or pieces[0] is not first:
            return None
        word = "".join(_WORD.findall(first.text.lower()))
        if word not in _CONTINUATIONS:
            return None
        start, end = self._document.selection()
        if start != end or start != last.end:
            return None
        if self._document.text_between(last.end - 1, last.end) != ".":
            return None
        self._document.remove(last.end - 1, last.end)
        self.history.replace_last(
            DictatedPhrase(last.inserted[:-1], last.start, last.end - 1, auto_period=False)
        )
        return (type(first)(_lower_first(first.text), first.mark, first.verbatim), *pieces[1:])

    def _edit(self, command: Command) -> None:
        """A whole-phrase command that changes the document or moves the caret."""
        document = self._document
        if command is Command.SCRATCH:
            self._scratch()
        elif command is Command.UNDO:
            # The ranges history holds were measured before the undo.
            self.history.clear()
            self._say("Undone." if document.undo() else "Nothing to undo.")
        elif command in (Command.SELECT, Command.CAPITALIZE, Command.UPPERCASE, Command.LOWERCASE):
            self._change_last(command)
        elif command is Command.DELETE_WORD:
            self._delete_back(_previous_word_start, "word")
        elif command is Command.DELETE_SENTENCE:
            self._delete_back(_previous_sentence_start, "sentence")
        elif command is Command.LINE_START:
            start, _end = document.line_bounds()
            document.select(start, start)
            self._say("Start of line.")
        elif command is Command.LINE_END:
            _start, end = document.line_bounds()
            document.select(end, end)
            self._say("End of line.")
        elif command is Command.DOCUMENT_START:
            document.select(0, 0)
            self._say("Top of document.")
        elif command is Command.DOCUMENT_END:
            end = document.last_position()
            document.select(end, end)
            self._say("End of document.")

    def _last_intact(self) -> DictatedPhrase | None:
        """The newest phrase, if it is still exactly as it was written."""
        phrase = self.history.peek()
        if phrase is None:
            self._say("Nothing has been dictated yet.")
            return None
        if not same_text(self._document.text_between(phrase.start, phrase.end), phrase.inserted):
            self.history.clear()
            self._say("That phrase has changed since it was dictated, so it was left alone.")
            return None
        return phrase

    def _scratch(self) -> None:
        phrase = self._last_intact()
        if phrase is None:
            return
        self.history.pop()
        self._document.remove(phrase.start, phrase.end)
        spoken = " ".join(phrase.inserted.split())
        self._say(f"Scratched: {spoken}" if spoken else "Scratched.")

    def _change_last(self, command: Command) -> None:
        phrase = self._last_intact()
        if phrase is None:
            return
        if command is Command.SELECT:
            # Selected without its leading space, so typing over it keeps the
            # gap in front of it.
            lead = len(phrase.inserted) - len(phrase.inserted.lstrip())
            self._document.select(phrase.start + lead, phrase.end)
            self._say("Selected: " + " ".join(phrase.inserted.split()))
            return
        if command is Command.CAPITALIZE:
            changed = re.sub(
                r"[A-Za-z][\w']*",
                lambda m: m.group(0)[:1].upper() + m.group(0)[1:],
                phrase.inserted,
            )
        elif command is Command.UPPERCASE:
            changed = phrase.inserted.upper()
        else:
            changed = phrase.inserted.lower()
        start, end = self._document.replace(phrase.start, phrase.end, changed)
        self.history.replace_last(DictatedPhrase(changed, start, end))
        self._say(" ".join(changed.split()) or "Changed.")

    def _delete_back(self, find_start: Callable[[str], int], what: str) -> None:
        start, end = self._document.selection()
        if start != end:
            self._document.remove(start, end)
            self.history.clear()
            self._say("Deleted the selection.")
            return
        window = min(end, 2000)
        before = self._document.text_between(end - window, end)
        cut = find_start(before)
        if cut >= len(before):
            self._say(f"No {what} before the cursor.")
            return
        removed = before[cut:]
        self._document.remove(end - window + cut, end)
        self.history.clear()
        self._say(f"Deleted: {' '.join(removed.split()) or what}")


def _previous_word_start(text: str) -> int:
    """Where the last word in *text* begins, with the space before it."""
    stripped = text.rstrip()
    index = len(stripped)
    while index > 0 and not stripped[index - 1].isspace():
        index -= 1
    while index > 0 and stripped[index - 1] in " \t":
        index -= 1
    return index


def _previous_sentence_start(text: str) -> int:
    """Where the sentence the caret is in (or just ended) begins."""
    stripped = text.rstrip()
    body = stripped[:-1] if stripped[-1:] in ".?!" else stripped
    index = len(body)
    while index > 0 and body[index - 1] not in ".?!\n":
        index -= 1
    # The space after the previous sentence goes with the one being deleted,
    # except at the start of a line, where there is nothing to join.
    return index
