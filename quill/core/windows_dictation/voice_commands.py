"""The 2026-10-05 voice commands: modes, words as targets, units, the library,
the language switch and the document's context.

dict.md sections 3.2 to 3.5 and 3.8 (gaps 7, 6, 5, 10 and 9), kept out of
:mod:`~quill.core.windows_dictation.controller` because that module is at its
size ceiling. The controller asks two questions of this mixin for every
command: :meth:`VoiceCommandsMixin._mode_command` before it checks the document
can be written to (a mode or the language changes nothing in the document), and
:meth:`VoiceCommandsMixin._voice_command` after.

* **Modes** -- "caps on", "all caps on", "no space on", and their "off": they
  last until turned off or dictation stops, and the status bar says which is on.
* **Words as targets** -- "select the cat", "go to Tuesday", "go after the
  date", "correct the cat", "select the cat through the hat", "select again"
  (:mod:`~quill.core.windows_dictation.targets`). Not found: what was said is
  written as text and "Not found, written as text" is said (dict.md question
  3), so nothing said is lost and "scratch that" removes it.
* **Units** -- select the sentence, line or paragraph; go to the start or end
  of the paragraph.
* **"spell that"** -- the last phrase selected, the next phrase spelled over it.
* **The library** -- Copy All, copy that, the Copy Tray's slots, snippets and
  abbreviations, through the editor's own features: the feedback port's
  optional ``library()`` answers (``quill/ui/windows_dictation_library.py``).
  A snippet goes in as one phrase -- one undo step, and "scratch that" takes it
  back out.
* **The language** -- "switch to Spanish", "cambiar a inglés": the setting
  changes and the engine is reopened in the new language; models already
  loaded stay loaded, so switching back is quick.
* **The context** -- "dictation context formal letter" picks a saved context
  for this document (:mod:`~quill.core.windows_dictation.contexts`).

Every outcome is spoken once (GATE-13): a selection made by a program in a rich
edit control is not reliably announced by the screen reader, so it is said here,
and shown in the status bar for braille.

wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.action_feedback import resolve
from quill.core.windows_dictation.anywhere import EXTERNAL_COMMANDS, external_refusal
from quill.core.windows_dictation.history import DictatedPhrase, PhraseHistory
from quill.core.windows_dictation.parser import ParsedPhrase, Piece
from quill.core.windows_dictation.targets import (
    Target,
    find_target,
    line_number,
    match_names,
    number_from,
    paragraph_bounds,
    unit_bounds,
)
from quill.core.windows_dictation.vocabulary import Command

if TYPE_CHECKING:
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = ["VoiceCommandsMixin"]

_CAPS = {
    Command.CAPS_ON: ("words", "Caps on."),
    Command.CAPS_OFF: ("", "Caps off."),
    Command.ALL_CAPS_ON: ("all", "All caps on."),
    Command.ALL_CAPS_OFF: ("", "All caps off."),
}
_SPACE = {
    Command.NO_SPACE_ON: (True, "No space on."),
    Command.NO_SPACE_OFF: (False, "No space off."),
}
_LANGUAGES = {Command.SWITCH_SPANISH: "es", Command.SWITCH_ENGLISH: "en"}
_TARGETS = (
    Command.SELECT_WORDS,
    Command.GO_TO_WORDS,
    Command.GO_AFTER_WORDS,
    Command.CORRECT_WORDS,
)
_UNITS = {
    Command.SELECT_SENTENCE: "sentence",
    Command.SELECT_LINE: "line",
    Command.SELECT_PARAGRAPH: "paragraph",
}
_LIBRARY = (
    Command.COPY_ALL,
    Command.COPY_THAT,
    Command.SHOW_CLIPS,
    Command.SHOW_SNIPPETS,
    Command.PASTE_SLOT,
    Command.INSERT_SNIPPET,
    Command.EXPAND,
)
#: A match this many lines from the cursor or more says which line it is on.
_FAR_LINES = 3
_SAID_CHARS = 120


def _short(text: str) -> str:
    said = " ".join(text.split())
    return said if len(said) <= _SAID_CHARS else said[:_SAID_CHARS].rsplit(" ", 1)[0] + "..."


class VoiceCommandsMixin:
    """Modes, words as targets, units, the library, the language and context."""

    _document: Any
    _feedback: Any
    _recognizer: Any
    spelling: bool
    history: PhraseHistory
    recent: Any
    _preferences: Callable[[], DictationPreferences]

    def _say(self, message: str) -> None:  # provided by the controller
        raise NotImplementedError

    def _apply(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> None:
        raise NotImplementedError  # provided by the controller

    def _last_intact(self) -> DictatedPhrase | None:  # editing.py
        raise NotImplementedError

    def _go_to_anchor(self) -> None:  # live.py
        raise NotImplementedError

    def _after_insert(self, text: str) -> None:  # live.py
        raise NotImplementedError

    def _close_recognizer(self) -> None:  # provided by the controller
        raise NotImplementedError

    def _open(
        self, preferences: DictationPreferences, *, quiet: bool = False, report: bool = True
    ) -> bool:
        raise NotImplementedError  # provided by the controller

    def _set_state(self, state: Any) -> None:  # provided by the controller
        raise NotImplementedError

    def _init_voice_commands(self) -> None:
        #: ``""``, ``"words"`` (caps on) or ``"all"`` (all caps on).
        self.caps = ""
        #: No space on: words are written joined.
        self.no_space = False
        self._spell_once = False
        self._target: Target | None = None
        self._target_mode = Command.SELECT_WORDS

    def _end_voice_modes(self) -> None:
        """Dictation stopped: every mode goes back to normal."""
        self.caps = ""
        self.no_space = False
        self._spell_once = False
        self._target = None

    @property
    def mode_text(self) -> str:
        """The modes that are on, for the status bar: "all caps, no space"."""
        modes = {"words": "caps", "all": "all caps"}.get(self.caps, "")
        parts = [part for part in (modes, "no space" if self.no_space else "") if part]
        return ", ".join(parts)

    # -- before the document is checked ---------------------------------------- #

    def _mode_command(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> bool:
        """``True`` when *parsed* changed a mode, the language or the context."""
        command = parsed.command
        if command in _CAPS:
            self.caps, said = _CAPS[command]
            self._say(said)
            return True
        if command in _SPACE:
            self.no_space, said = _SPACE[command]
            self._say(said)
            return True
        if command in _LANGUAGES:
            self.switch_language(_LANGUAGES[command])
            return True
        if command is Command.USE_CONTEXT:
            use = getattr(self._feedback, "use_context", None)
            self._say(str(use(parsed.argument)) if callable(use) else "Not available here.")
            return True
        del preferences
        return False

    def _in_mode(self, pieces: tuple[Piece, ...]) -> tuple[Piece, ...]:
        """*pieces* with the capitals the modes ask for. Spelled and pasted text
        is left exactly as it is."""
        if not self.caps:
            return pieces
        out = []
        for piece in pieces:
            if piece.mark is None and not piece.verbatim and piece.text:
                text = piece.text.upper() if self.caps == "all" else piece.text[:1].upper()
                if self.caps == "words":
                    text += piece.text[1:]
                piece = Piece(text, None, piece.verbatim)
            out.append(piece)
        return tuple(out)

    def switch_language(self, language: str) -> None:
        """Dictate in *language* (``en`` or ``es``) from the next phrase on."""
        from quill.core.windows_dictation.ports import DictationState

        name = "Español." if language == "es" else "English."
        setter = getattr(self._feedback, "set_speech_language", None)
        if not callable(setter):
            self._say("The dictation language can be changed in Dictation Settings.")
            return
        changed = self._preferences().speech_language != language
        setter(language)
        if changed and self._recognizer is not None:
            # The engine is told its language when it opens, so it is reopened.
            # A model already loaded stays loaded (local_recognizer's cache).
            standing_by = getattr(self, "standing_by", False)
            self._close_recognizer()
            if not self._open(self._preferences()):
                return
            self._set_state(DictationState.STANDBY if standing_by else DictationState.LISTENING)
        self._feedback.say(name)
        self._feedback.show("Dictation language: " + ("Spanish" if language == "es" else "English"))

    # -- after the document is checked ------------------------------------------ #

    def _voice_command(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> bool:
        """``True`` when *parsed* was one of this mixin's commands, now handled."""
        command = parsed.command
        if command is None:
            return False
        if getattr(self._document, "external", False) and command not in EXTERNAL_COMMANDS:
            # Dictate Anywhere: nothing here can read the other program's text.
            self._say(external_refusal())
            return True
        if command in _TARGETS:
            self._to_words(parsed, preferences)
        elif command in (Command.SELECT_NEXT, Command.SELECT_PREVIOUS):
            self._step_target(parsed, preferences)
        elif command in _UNITS:
            self._select_unit(_UNITS[command])
        elif command in (Command.PARAGRAPH_START, Command.PARAGRAPH_END):
            self._paragraph_edge(command is Command.PARAGRAPH_START)
        elif command is Command.SPELL_THAT:
            self._spell_that()
        elif command in _LIBRARY:
            self._library_command(parsed, preferences)
        else:
            return False
        return True

    def _after_phrase(self) -> None:
        """A phrase was written: "spell that" lasts for one phrase only."""
        if self._spell_once:
            self._spell_once = False
            self.spelling = False

    def _text_and_caret(self) -> tuple[str, int]:
        document = self._document
        return document.text_between(0, document.last_position()), document.selection()[0]

    def _write_instead(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> None:
        """Nothing to act on: write what was said, so nothing is lost."""
        if parsed.pieces:
            self._say("Not found, written as text.")
            self._apply(ParsedPhrase(pieces=parsed.pieces), preferences)
        else:
            self._say("Not found.")

    def _to_words(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> None:
        text, caret = self._text_and_caret()
        target = find_target(text, caret, parsed.argument)
        if target is None:
            self._write_instead(parsed, preferences)
            return
        self._target = target
        self._target_mode = parsed.command or Command.SELECT_WORDS
        self._land(target, text, caret)

    def _step_target(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> None:
        if self._target is None:
            # "select again" with nothing selected by voice before it.
            self._write_instead(parsed, preferences)
            return
        text, caret = self._text_and_caret()
        step = 1 if parsed.command is Command.SELECT_NEXT else -1
        moved = self._target.moved(step)
        if moved is None:
            self._say("No more." if step > 0 else "None before that.")
            return
        self._target = moved
        self._land(moved, text, caret)

    def _land(self, target: Target, text: str, caret: int) -> None:
        """Select or move to *target*, and say where, once."""
        matched = _short(text[target.start : target.end])
        mode = self._target_mode
        if mode is Command.GO_TO_WORDS:
            self._document.select(target.start, target.start)
            said = f"Before {matched}"
        elif mode is Command.GO_AFTER_WORDS:
            self._document.select(target.end, target.end)
            said = f"After {matched}"
        elif mode is Command.CORRECT_WORDS:
            self._document.select(target.start, target.end)
            said = f"Correcting {matched}. Say the new words"
        else:
            self._document.select(target.start, target.end)
            said = f"Selected: {matched}"
        line = line_number(text, target.start)
        if abs(line - line_number(text, caret)) >= _FAR_LINES:
            said += f", line {line}"
        self._say(said + ".")

    def _select_unit(self, unit: str) -> None:
        text, caret = self._text_and_caret()
        start, end = unit_bounds(text, caret, unit)
        if not text[start:end].strip():
            self._say(f"There is no {unit} here.")
            return
        self._document.select(start, end)
        self._say(f"Selected the {unit}: {_short(text[start:end])}")

    def _paragraph_edge(self, at_start: bool) -> None:
        text, caret = self._text_and_caret()
        start, end = paragraph_bounds(text, caret)
        place = start if at_start else end
        self._document.select(place, place)
        self._say("Start of paragraph." if at_start else "End of paragraph.")

    def _spell_that(self) -> None:
        phrase = self._last_intact()
        if phrase is None:
            return
        lead = len(phrase.inserted) - len(phrase.inserted.lstrip())
        self._document.select(phrase.start + lead, phrase.end)
        self.history.pop()  # it is being replaced by what is spelled next
        self.spelling = True
        self._spell_once = True
        self._say(f"Spell {_short(phrase.inserted)}.")

    # -- the editor's own library ---------------------------------------------------- #

    def _library_command(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> None:
        provider = getattr(self._feedback, "library", None)
        library = provider() if callable(provider) else None
        if library is None:
            self._say("That is not available here.")
            return
        command = parsed.command
        if command is Command.COPY_ALL:
            library.copy_all()  # the editor says what it copied, as its own key does
        elif command is Command.COPY_THAT:
            phrase = self._last_intact()
            if phrase is not None:
                copied = library.copy_text(phrase.inserted.strip())
                self._say(f"Copied: {_short(phrase.inserted)}" if copied else "Not copied.")
        elif command is Command.SHOW_CLIPS:
            library.show_clips()
        elif command is Command.SHOW_SNIPPETS:
            library.show_snippets()
        elif command is Command.PASTE_SLOT:
            number = number_from(parsed.argument)
            text = library.slot_text(number) if number is not None else None
            if number is None or text is None:
                self._say("Say a slot number, like paste clip three.")
            elif not text:
                self._say(f"Slot {number} is empty.")
            else:
                self._insert_text(text, 0, f"Pasted slot {number}", preferences)
        elif command is Command.INSERT_SNIPPET:
            self._insert_named(library, parsed, preferences, snippet=True)
        else:
            self._insert_named(library, parsed, preferences, snippet=False)

    def _insert_named(
        self,
        library: Any,
        parsed: ParsedPhrase,
        preferences: DictationPreferences,
        *,
        snippet: bool,
    ) -> None:
        kind = "snippet" if snippet else "abbreviation"
        said = " ".join(parsed.argument)
        names = library.snippet_names() if snippet else library.abbreviation_names()
        found = match_names(names, parsed.argument)
        if not found:
            self._say(f"No {kind} called {said}.")
            return
        if len(found) > 1:
            self._say(f"{len(found)} {kind}s match {said}.")
            if snippet:
                library.show_snippets()
            return
        name = found[0]
        resolved = library.snippet_text(name) if snippet else library.abbreviation_text(name)
        if resolved is None:
            self._say(f"The {kind} {name} could not be put in.")
            return
        text, back = resolved
        self._insert_text(text, back, f"{kind.capitalize()} {name}", preferences)

    def _insert_text(
        self, text: str, back: int, spoken: str, preferences: DictationPreferences
    ) -> None:
        """Put *text* in as one dictated phrase: one undo step, and "scratch
        that" takes it out. The read-back says *spoken* -- a snippet's name,
        not three paragraphs of it."""
        from quill.core.windows_dictation.composer import compose
        from quill.core.windows_dictation.ports import Moment

        self._go_to_anchor()
        before, after = self._document.context()
        written = compose((Piece(text, verbatim=True),), before=before, after=after)
        start, end = self._document.insert(written)
        self.history.push(DictatedPhrase(written, start, end))
        self._after_insert(written)
        self.recent.appendleft(" ".join(written.split()))
        if back:
            place = max(start, end - back)
            self._document.select(place, place)
        play, speak = resolve(
            preferences.phrase_feedback, has_sound=self._feedback.has_cue(Moment.PHRASE)
        )
        if play:
            self._feedback.cue(Moment.PHRASE)
        if speak:
            self._feedback.read_back(spoken)
        self._feedback.show(f"Dictated: {spoken}")
