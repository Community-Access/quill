"""Replace, change, delete by paragraph, a second opinion, and kept revisions.

D-19 of the 2026-10-13 dictation gap plan, with D-10's rule for other programs
(:mod:`~quill.core.windows_dictation.external_edits`). Kept out of
:mod:`~quill.core.windows_dictation.controller`, which is at its GATE-11
ceiling; the controller asks this mixin first about every command (it comes
first in the controller's bases):

* **"replace X with Y"** -- in QUILL's documents, the nearest X before the
  cursor, else after it (:func:`~quill.core.windows_dictation.targets.find_target`);
  in another program, only inside the phrase dictated last, retyped from X on.
* **"change that to Y"** -- Y in place of the last phrase, keeping its leading
  space, its capital and its closing mark.
* **"delete previous paragraph"** -- from the start of the paragraph before the
  cursor up to the cursor. In another program, only words dictation typed.
* **A second opinion** (:meth:`CorrectionsMixin._second_opinion`): "correct
  that" with an engine that gives one answer decodes the last phrase's audio
  again with the other built-in engine -- Whisper after Moonshine, Moonshine
  after Whisper or a downloaded model -- and offers it as choice 2. The audio
  is the phrase's own, in memory, dropped at the next phrase. No disk, no
  network.
* **Kept revisions** (:func:`keep_revision`): what a correction replaced goes
  into Recent Phrases marked "before correction", so it can be put back.

Bare, these work where commands work bare (strict mode off); after the command
word they always work, and a replace that finds nothing then writes nothing
(command_mode_mixin.py). In another program every one is checked first: the
focus, typing since, and a program that corrects as you type.

wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.windows_dictation.composer import compose
from quill.core.windows_dictation.external_edits import EXTERNAL_EDIT_COMMANDS
from quill.core.windows_dictation.history import DictatedPhrase, PhraseHistory
from quill.core.windows_dictation.parser import ParsedPhrase, Piece
from quill.core.windows_dictation.targets import find_target
from quill.core.windows_dictation.vocabulary import Command

if TYPE_CHECKING:
    from quill.core.windows_dictation.parser import RecognizedPhrase
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = [
    "BEFORE_CORRECTION",
    "CorrectionsMixin",
    "fit_to",
    "keep_revision",
    "phrase_from_entry",
    "second_engine",
    "split_replacement",
]

#: The label a replaced phrase carries in Recent Phrases.
BEFORE_CORRECTION = "before correction"
_LABEL = f" ({BEFORE_CORRECTION})"
_ENGINE_NAMES = {"moonshine": "Moonshine", "whisper": "Whisper"}
_WORD = re.compile(r"[\w']+")
_SAID_CHARS = 120


def _short(text: str) -> str:
    said = " ".join(text.split())
    return said if len(said) <= _SAID_CHARS else said[:_SAID_CHARS].rsplit(" ", 1)[0] + "..."


def phrase_from_entry(entry: str) -> str:
    """A Recent Phrases entry as the words to insert or copy: the label off."""
    return entry[: -len(_LABEL)] if entry.endswith(_LABEL) else entry


def keep_revision(recent: Any, before: str, after: str) -> None:
    """*before* was corrected to *after*: the newest copy of *before* in Recent
    Phrases is marked "before correction", and *after* goes in front of it."""
    old = " ".join(before.split())
    new = " ".join(after.split())
    if not old or old == new:
        return
    try:
        recent.remove(old)
    except ValueError:
        pass
    recent.appendleft(old + _LABEL)
    if new:
        recent.appendleft(new)


def second_engine(engine: str, language: str) -> str:
    """The built-in engine that gives a second opinion on *engine*, or ``""``."""
    if language != "en":
        return ""  # only Whisper's multilingual model hears Spanish: there is no second
    if engine == "moonshine":
        return "whisper"
    if engine == "whisper":
        return "moonshine"
    from quill.core.windows_dictation.model_catalog import downloadable

    return "moonshine" if downloadable(engine) is not None else ""


def _normal(text: str) -> str:
    return " ".join(_WORD.findall(text.lower()))


def _text(pieces: tuple[Piece, ...]) -> str:
    """Pieces as words in the middle of a sentence: spacing, no added capital."""
    return compose(pieces, before="and ", after="").strip()


def split_replacement(parsed: ParsedPhrase) -> tuple[tuple[str, ...], str] | None:
    """ "replace the cat with the dog": the words to find and the new text, or
    ``None`` when there is no "with" between two sets of words."""
    argument = parsed.argument
    split = next((i for i, word in enumerate(argument) if word == "with" and i > 0), None)
    if split is None or split == len(argument) - 1:
        return None
    # The same "with" in the written pieces: the first one after "replace" and
    # at least one word.
    seen = 0
    for index, piece in enumerate(parsed.pieces):
        if piece.mark is None and _normal(piece.text):
            if _normal(piece.text) == "with" and seen >= 2:
                new = _text(parsed.pieces[index + 1 :])
                return (tuple(argument[:split]), new) if new else None
            seen += 1
    return None


def _after_opening(parsed: ParsedPhrase, words: int) -> str:
    """The text of a phrase after its first *words* words ("change that to")."""
    seen = 0
    for index, piece in enumerate(parsed.pieces):
        if piece.mark is None and _normal(piece.text):
            seen += 1
            if seen == words:
                return _text(parsed.pieces[index + 1 :])
    return ""


def fit_to(new: str, old: str) -> str:
    """*new* shaped like the *old* text it replaces: its capital, its closing
    mark, and no full stop the engine added that *old* did not have."""
    body = old.strip()
    if not new:
        return new
    if body[:1].isupper() and new[:1].islower():
        new = new[:1].upper() + new[1:]
    closing = body[-1:] if body[-1:] in ".?!" else ""
    if new[-1:] in ".?!" and not closing and not new.endswith(".."):
        new = new[:-1]
    elif closing and new[-1:] not in ".?!":
        new += closing
    return new


class CorrectionsMixin:
    """Replace, change, delete by paragraph, the second opinion, revisions."""

    _document: Any
    _feedback: Any
    _recognizer: Any
    history: PhraseHistory
    recent: Any
    _alternatives: tuple[str, ...]
    _commanding: bool
    _preferences: Callable[[], DictationPreferences]

    #: The audio of the phrase being received, and of the last one written.
    _incoming_audio: Any = None
    _phrase_audio: Any = None
    #: Which written phrase a second opinion belongs to.
    _phrase_round = 0

    if TYPE_CHECKING:  # later in the controller's bases: no stub may shadow them

        def _say(self, message: str) -> None: ...

        def _last_intact(self) -> DictatedPhrase | None: ...

        def _write_instead(
            self, parsed: ParsedPhrase, preferences: DictationPreferences
        ) -> None: ...

    # -- the phrase's audio, for a second opinion --------------------------------- #

    def _receive(self, phrase: RecognizedPhrase) -> bool:
        self._incoming_audio = getattr(phrase, "audio", None)
        return bool(super()._receive(phrase))  # type: ignore[misc]

    def _after_insert(self, text: str) -> None:
        self._phrase_audio, self._incoming_audio = self._incoming_audio, None
        self._phrase_round += 1
        super()._after_insert(text)  # type: ignore[misc]

    def _end_live(self) -> None:
        super()._end_live()  # type: ignore[misc]
        self._phrase_audio = self._incoming_audio = None
        self._phrase_round += 1

    # -- the controller's hooks ---------------------------------------------------- #

    def _live_command(self, command: Command | None) -> bool:
        """Asked first about every command: another program's checks (D-10),
        and "correct that" with nothing offered (the second opinion)."""
        if command in EXTERNAL_EDIT_COMMANDS and getattr(self._document, "external", False):
            check = getattr(self._document, "edit_problem", None)
            problem = str(check(command)) if callable(check) else ""
            if problem:
                self._say(problem)
                return True
        if command is Command.CORRECT and self._second_opinion():
            return True
        return bool(super()._live_command(command))  # type: ignore[misc]

    def _choose(self, index: int) -> None:
        last = self.history.peek()
        super()._choose(index)  # type: ignore[misc]
        changed = self.history.peek()
        if last is not None and changed is not None and changed.inserted != last.inserted:
            keep_revision(self.recent, last.inserted, changed.inserted)

    def _voice_command(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> bool:
        command = parsed.command
        if command is Command.REPLACE_WORDS:
            self._replace_words(parsed, preferences)
        elif command is Command.CHANGE_THAT:
            self._change_that(parsed)
        elif command is Command.DELETE_PARAGRAPH:
            self._delete_paragraph()
        else:
            return bool(super()._voice_command(parsed, preferences))  # type: ignore[misc]
        return True

    # -- replace X with Y ---------------------------------------------------------- #

    def _replace_words(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> None:
        split = split_replacement(parsed)
        if split is None:
            if self._commanding:
                self._say("Say replace, the words, with, and the new words.")
            else:
                self._write_instead(parsed, preferences)
            return
        find, new = split
        if getattr(self._document, "external", False):
            self._replace_in_last(parsed, preferences, find, new)
            return
        document = self._document
        text = document.text_between(0, document.last_position())
        caret = document.selection()[0]
        target = find_target(text, caret, find)
        if target is None:
            self._write_instead(parsed, preferences)
            return
        old = text[target.start : target.end]
        fitted = fit_to(new, old)
        start, end = document.replace(target.start, target.end, fitted)
        delta = (end - start) - (target.end - target.start)
        place = caret + delta if caret >= target.end else min(caret, end)
        document.select(place, place)
        if not self._shift_history(target.start, target.end, fitted, delta):
            keep_revision(self.recent, old, "")
        self._say(f"Replaced {_short(old)} with {_short(fitted)}.")

    def _shift_history(self, start: int, end: int, fitted: str, delta: int) -> bool:
        """Keep "scratch that" right after a replace: the last phrase is changed
        in place when the words were inside it (``True``: its revision is kept),
        untouched when they were after it, and forgotten otherwise (its range
        no longer means what it did)."""
        last = self.history.peek()
        if last is None or start >= last.end:
            return False
        if last.start <= start and end <= last.end:
            inside = last.inserted
            changed = inside[: start - last.start] + fitted + inside[end - last.start :]
            self.history.replace_last(DictatedPhrase(changed, last.start, last.end + delta))
            keep_revision(self.recent, inside, changed)
            return True
        self.history.clear()
        return False

    def _replace_in_last(
        self,
        parsed: ParsedPhrase,
        preferences: DictationPreferences,
        find: tuple[str, ...],
        new: str,
    ) -> None:
        """In another program: inside the phrase dictated last, retyped from the
        words on -- the fewest backspaces that make the change."""
        last = self._last_intact()
        if last is None:
            return
        inside = last.inserted
        target = find_target(inside, len(inside), find)
        if target is None:
            self._write_instead(parsed, preferences)
            return
        old = inside[target.start : target.end]
        fitted = fit_to(new, old)
        changed = inside[: target.start] + fitted + inside[target.end :]
        self._document.replace(last.start + target.start, last.end, changed[target.start :])
        self.history.replace_last(DictatedPhrase(changed, last.start, last.start + len(changed)))
        keep_revision(self.recent, inside, changed)
        self._say(f"Replaced {_short(old)} with {_short(fitted)}.")

    # -- change that to Y ------------------------------------------------------------ #

    def _change_that(self, parsed: ParsedPhrase) -> None:
        new = _after_opening(parsed, 3)  # "change that to"
        if not new:
            self._say("Say change that to, and the new words.")
            return
        last = self._last_intact()
        if last is None:
            return
        inside = last.inserted
        lead = inside[: len(inside) - len(inside.lstrip())]
        changed = lead + fit_to(new, inside)
        same = 0  # retype only from the first character that differs
        while same < min(len(inside), len(changed)) and inside[same] == changed[same]:
            same += 1
        self._document.replace(last.start + same, last.end, changed[same:])
        self.history.replace_last(DictatedPhrase(changed, last.start, last.start + len(changed)))
        self._alternatives = ()
        keep_revision(self.recent, inside, changed)
        self._say(f"Changed to: {_short(changed)}")

    # -- delete previous paragraph ------------------------------------------------------ #

    def _delete_paragraph(self) -> None:
        document = self._document
        start, end = document.selection()
        if start != end:
            document.remove(start, end)
            self.history.clear()
            self._say("Deleted the selection.")
            return
        window = min(end, 100_000)
        before = document.text_between(end - window, end)
        cut = previous_paragraph_start(before)
        removed = before[cut:]
        if not removed.strip():
            self._say("No paragraph before the cursor.")
            return
        document.remove(end - window + cut, end)
        self.history.clear()
        self._say(f"Deleted the paragraph: {_short(removed)}")

    # -- a second opinion ---------------------------------------------------------------- #

    def _second_opinion(self) -> bool:
        """``True`` when the other built-in engine was asked about the last phrase."""
        if self._alternatives or self._phrase_audio is None or self.history.peek() is None:
            return False
        ask = getattr(self._recognizer, "second_opinion", None)
        preferences = self._preferences()
        engine = second_engine(preferences.engine, preferences.speech_language)
        if not callable(ask) or not engine:
            return False
        token = self._phrase_round
        try:
            ask(self._phrase_audio, engine, lambda text: self.on_second_opinion(text, token))
        except Exception:  # noqa: BLE001 - then the one-answer sentence is said
            return False
        self._say(f"Listening again with {_ENGINE_NAMES.get(engine, engine)}.")
        return True

    def on_second_opinion(self, text: str, token: int) -> None:
        """The other engine's answer, on the UI thread. Ignored when a newer
        phrase has been written since: it is about words no longer last."""
        last = self.history.peek()
        if token != self._phrase_round or last is None:
            return
        current = last.inserted.strip()
        heard = " ".join(str(text or "").split())
        if not heard or _normal(heard) == _normal(current):
            self._say(
                f"The other engine heard the same: {_short(current)}. Say scratch that and "
                "say it again, or add a correction in My Words and Phrases."
            )
            return
        self._alternatives = (current, heard)
        self._say(f"1: {_short(current)}. 2: {_short(heard)}. Say choose and the number.")


def previous_paragraph_start(text: str) -> int:
    """Where the paragraph before the end of *text* begins, with the blank line
    in front of it, so the cursor lands at the end of the one before."""
    stripped = text.rstrip()
    breaks = list(re.finditer(r"\r?\n[ \t]*\r?\n", stripped))
    return breaks[-1].start() if breaks else 0
