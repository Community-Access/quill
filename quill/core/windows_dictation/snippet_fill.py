"""Spoken prompts for a snippet's blanks: "insert snippet bug report" asks for each.

D-8 of the 2026-10-13 dictation gap plan. Until now a snippet said by voice
went in with its blanks written as "[title]", because nothing could ask for them
in another program. Now the blanks are asked for by voice, in every host the
controller runs in (QUILL, QUILL Lite, QUILL Transcribe and Quill Inkwell),
whenever the host's library can give the snippet's own text
(``library().snippet_body(name)``):

* ``${input:title}`` -- "Title?" is said; what is dictated next is the answer.
  Spoken punctuation works in it, as in any phrase.
* ``${choice:NVDA|JAWS|Narrator}`` -- the options are read; say one of them, or
  "choose two" (or "number two", or "two").
* "skip" leaves a blank empty; "scratch that" (or "go back") asks the one before
  again; "cancel" stops, and nothing is typed. The stop phrase stops dictation
  and the snippet with it. The command word may come first; it is not needed.
* When the last blank is answered, the whole snippet goes in as one phrase
  (``voice_commands._insert_text``): one undo step in the editors, one checked
  typing in another program, and "scratch that" takes all of it back.
* ``${date}`` and ``${time}`` are filled from this computer's clock.
  ``${cursor}`` moves the cursor back in the editors only: in another program the
  cursor is left at the end, because moving it means reading that program's text.

Nothing is typed while the blanks are asked for, and the answers are never typed
on their own. A host whose library has no ``snippet_body`` (QUILL Lite's
snippets are its abbreviations, which have no blanks) keeps the old behaviour.

wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from quill.core.snippets import Placeholder, extract_placeholders, render_snippet
from quill.core.windows_dictation.command_mode import split_phrase
from quill.core.windows_dictation.composer import compose
from quill.core.windows_dictation.parser import ParsedPhrase, Piece, RecognizedPhrase, parse
from quill.core.windows_dictation.targets import match_names, number_from
from quill.core.windows_dictation.voice_commands import VoiceCommandsMixin
from quill.core.windows_dictation.wake import wake_words

if TYPE_CHECKING:
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = ["CANCELLED", "SnippetFill", "SnippetFillMixin"]

CANCELLED = "Snippet cancelled. Nothing was typed."

_CANCEL = {("cancel",), ("cancel", "snippet"), ("cancel", "that")}
_BACK = {("scratch", "that"), ("go", "back"), ("back",)}
_SKIP = {("skip",), ("skip", "that"), ("skip", "it"), ("leave", "it", "blank")}


def _spoken_name(name: str) -> str:
    words = name.replace("_", " ").replace("-", " ").strip()
    return words[:1].upper() + words[1:] if words else "Blank"


def _or_list(options: list[str]) -> str:
    if len(options) == 1:
        return options[0]
    return ", ".join(options[:-1]) + " or " + options[-1]


@dataclass(slots=True)
class SnippetFill:
    """One snippet's blanks being asked for, in the order they appear."""

    name: str
    body: str
    external: bool
    fields: list[Placeholder]
    values: dict[str, str] = field(default_factory=dict)
    index: int = 0

    @classmethod
    def start(cls, name: str, body: str, *, external: bool) -> SnippetFill | None:
        """The fill for *body*, or ``None`` when it has no blank to ask for (or
        cannot be read, which the old path reports)."""
        try:
            blanks = [p for p in extract_placeholders(body) if p.kind in ("input", "choice")]
        except ValueError:
            return None
        return cls(name, body, external, blanks) if blanks else None

    @property
    def done(self) -> bool:
        return self.index >= len(self.fields)

    @property
    def current(self) -> Placeholder:
        return self.fields[self.index]

    def prompt(self) -> str:
        """What is asked for the blank now: "Title?", or the choices."""
        blank = self.current
        if blank.kind == "choice":
            return f"Choose {_or_list(blank.options)}."
        return f"{_spoken_name(blank.name)}?"

    def opening(self) -> str:
        """The first question, with how many there are and the way out."""
        count = len(self.fields)
        blanks = "1 blank" if count == 1 else f"{count} blanks"
        return f"Snippet {self.name}, {blanks}. Say cancel to stop. {self.prompt()}"

    def answer(self, words: list[str], text: str) -> str:
        """Fill the current blank. ``""`` when it took; otherwise what to say."""
        blank = self.current
        if blank.kind == "choice":
            said = [word for word in words if word not in ("choose", "number")]
            number = number_from(said) if said else None
            if number is not None and 1 <= number <= len(blank.options):
                value = blank.options[number - 1]
            else:
                found = match_names(blank.options, words)
                if len(found) != 1:
                    return f"Say one of {_or_list(blank.options)}, or choose and a number."
                value = found[0]
        else:
            value = text
        self.values[blank.token] = value
        self.index += 1
        return ""

    def skip(self) -> None:
        self.values[self.current.token] = ""
        self.index += 1

    def back(self) -> bool:
        """Ask the blank before again. ``False`` at the first one."""
        if self.index == 0:
            return False
        self.index -= 1
        self.values.pop(self.current.token, None)
        return True

    def render(self) -> tuple[str, int]:
        """The filled text, and how far back from its end the cursor goes."""
        result = render_snippet(self.body, self.values)
        back = 0 if self.external else len(result.text) - result.cursor
        return result.text, back


class SnippetFillMixin(VoiceCommandsMixin):
    """The controller's spoken prompts for snippet blanks."""

    _fill: SnippetFill | None = None

    def _writing_reason(self) -> str:  # live.py
        raise NotImplementedError

    def _abandon(self, message: str) -> None:  # provided by the controller
        raise NotImplementedError

    if TYPE_CHECKING:  # target_hold.py, later in the controller's bases than this

        def _hold(self, parsed: ParsedPhrase, reason: str) -> bool: ...

    @property
    def filling_snippet(self) -> bool:
        """Whether a snippet's blanks are being asked for."""
        return self._fill is not None

    def _end_voice_modes(self) -> None:
        super()._end_voice_modes()
        self._fill = None  # stopping dictation stops the snippet; nothing typed

    def _insert_named(
        self,
        library: Any,
        parsed: ParsedPhrase,
        preferences: DictationPreferences,
        *,
        snippet: bool,
    ) -> None:
        if snippet and self._fill_begin(library, parsed):
            return
        super()._insert_named(library, parsed, preferences, snippet=snippet)

    def _fill_begin(self, library: Any, parsed: ParsedPhrase) -> bool:
        body_of = getattr(library, "snippet_body", None)
        if not callable(body_of):
            return False
        found = match_names(library.snippet_names(), parsed.argument)
        if len(found) != 1:
            return False  # none, or several: the old path says which
        body = body_of(found[0])
        if not body:
            return False
        fill = SnippetFill.start(
            found[0], str(body), external=bool(getattr(self._document, "external", False))
        )
        if fill is None:
            return False
        self._fill = fill
        self._say(fill.opening())
        return True

    def _fill_utterance(self, phrase: RecognizedPhrase, preferences: DictationPreferences) -> bool:
        """An utterance while blanks are asked for: an answer, never typed.
        ``False`` when no snippet is being filled."""
        fill = self._fill
        if fill is None:
            return False
        rest = split_phrase(phrase, preferences.command_prefix)
        if rest is not None and rest.words:
            phrase = rest  # the command word is allowed, and not part of the answer
        words = wake_words(phrase.text or " ".join(word.display for word in phrase.words))
        key = tuple(words)
        if not words:
            self._say(fill.prompt())
        elif key in _CANCEL:
            self._fill = None
            self._say(CANCELLED)
        elif key in _BACK:
            if fill.back():
                self._say(fill.prompt())
            else:
                self._fill = None
                self._say(CANCELLED)
        elif key in _SKIP:
            fill.skip()
            self._fill_next(fill, preferences)
        else:
            refused = fill.answer(words, self._fill_text(phrase, preferences))
            if refused:
                self._say(refused)
            else:
                self._fill_next(fill, preferences)
        return True

    def _fill_text(self, phrase: RecognizedPhrase, preferences: DictationPreferences) -> str:
        """What an answer writes: its words, with spoken punctuation obeyed."""
        parsed = parse(phrase, vocabulary=preferences.vocabulary)
        if parsed.command is not None or not parsed.pieces:
            return " ".join(word.display for word in phrase.words)
        text = compose(parsed.pieces, before="", after="")
        return text.strip()

    def _fill_next(self, fill: SnippetFill, preferences: DictationPreferences) -> None:
        if not fill.done:
            self._say(fill.prompt())
            return
        self._fill = None
        try:
            text, back = fill.render()
        except ValueError:
            self._say(f"The snippet {fill.name} could not be put in.")
            return
        reason = self._writing_reason()
        if reason:
            held = ParsedPhrase(pieces=(Piece(text, verbatim=True),))
            if not self._hold(held, reason):  # paused for its field: kept, typed on Resume
                self._abandon(reason)
            return
        self._insert_text(text, back, f"Snippet {fill.name}", preferences)
