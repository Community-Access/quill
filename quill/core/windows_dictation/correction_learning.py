"""Learning from corrections the person confirms (D-21, first half).

When "choose N", or "correct X" followed by the new words (D-19), replaces
the same word A with the same word B a **second** time, dictation offers,
once: "Add a correction: A becomes B?" It never adds anything without a yes:

* **In the editors** the host shows a yes/no window, No the default (the
  feedback port's optional ``confirm_correction``).
* **Where no window can be shown** -- QUILL Transcribe, which must not take the
  focus from the field being dictated into -- the question is said, and "QUILL
  yes" adds it, "QUILL no" drops it. The question lapses after
  :data:`ANSWER_SECONDS` so a later "yes" is never taken as an answer to it.

A yes adds a line to the **Corrections** section of ``dictation.md`` through
:mod:`~quill.core.windows_dictation.words_file`, the same model My Words and
Phrases and its Import and Export (D-12) use, so the correction appears there
to edit or remove, and the next phrase uses it.

Counts are kept for this run of the app only, and a pair is offered at most
once per run whatever the answer: nothing about what was said is written
anywhere until the person says yes.

wx-free. :class:`CorrectionLearningMixin` is mixed into the controller (through
:class:`~quill.core.windows_dictation.live.LiveMixin`), which supplies ``_say``,
``_feedback``, ``_clock`` and ``_preferences``.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.windows_dictation.words_file import Entry, load_words, save_words

__all__ = [
    "ANSWER_SECONDS",
    "OFFER_AFTER",
    "CorrectionLearner",
    "CorrectionLearningMixin",
    "add_learned_correction",
    "offer_question",
    "replaced_span",
]

#: How many identical corrections before the offer.
OFFER_AFTER = 2
#: How long a spoken offer waits for "QUILL yes" or "QUILL no".
ANSWER_SECONDS = 30.0
#: A learned correction is a word or a short phrase, never a sentence.
_MAX_WORDS = 4
_EDGE = re.compile(r"^[^\w']+|[^\w']+$")


def _core(word: str) -> str:
    return _EDGE.sub("", word)


def replaced_span(before: str, after: str) -> tuple[str, str] | None:
    """The one word or short phrase *after* put in place of one in *before*.

    ``None`` when the change is anything else: nothing, more than one place,
    only an addition or a removal, only case or punctuation, or more than
    four words on either side.
    """
    old = [w for w in before.split() if _core(w)]
    new = [w for w in after.split() if _core(w)]
    folded_old = [_core(w).lower() for w in old]
    folded_new = [_core(w).lower() for w in new]
    matcher = difflib.SequenceMatcher(a=folded_old, b=folded_new, autojunk=False)
    changes = [op for op in matcher.get_opcodes() if op[0] != "equal"]
    if len(changes) != 1 or changes[0][0] != "replace":
        return None
    _tag, i1, i2, j1, j2 = changes[0]
    if i2 - i1 > _MAX_WORDS or j2 - j1 > _MAX_WORDS:
        return None
    heard = " ".join(_core(w) for w in old[i1:i2])
    written = " ".join(_core(w) for w in new[j1:j2])
    if not heard or not written or heard.lower() == written.lower():
        return None
    return heard, written


def offer_question(heard: str, written: str) -> str:
    """The offer, in the spec's words."""
    return f"Add a correction: {heard} becomes {written}?"


def add_learned_correction(path: Path, heard: str, written: str) -> str:
    """Add "heard => written" to *path*'s Corrections; the sentence to say."""
    words = load_words(path)
    if not words.add(Entry("correction", heard, written)):
        return f"{heard} already has a correction in My Words and Phrases."
    try:
        save_words(path, words)
    except OSError as error:
        return f"The correction could not be saved: {error.strerror or error}."
    return f"Added: {heard} becomes {written}. It is in My Words and Phrases."


@dataclass
class CorrectionLearner:
    """Counts confirmed corrections and decides when to offer one."""

    counts: dict[tuple[str, str], int] = field(default_factory=dict)
    offered: set[tuple[str, str]] = field(default_factory=set)

    def note(self, before: str, after: str) -> tuple[str, str] | None:
        """Record that *before* became *after*; the pair to offer, if it is time."""
        pair = replaced_span(before, after)
        if pair is None:
            return None
        key = (pair[0].lower(), pair[1].lower())
        self.counts[key] = self.counts.get(key, 0) + 1
        if self.counts[key] < OFFER_AFTER or key in self.offered:
            return None
        self.offered.add(key)
        return pair


class CorrectionLearningMixin:
    """The controller's half: notice, offer, and answer "QUILL yes"."""

    _feedback: Any
    _clock: Callable[[], float]
    history: Any
    _correcting: tuple[str, int] | None
    _learn_pending: tuple[str, str, float] | None = None
    _preferences: Callable[[], Any]

    def _say(self, message: str) -> None:  # provided by the controller
        raise NotImplementedError

    def _learner(self) -> CorrectionLearner:
        learner = getattr(self, "_correction_learner", None)
        if learner is None:
            learner = CorrectionLearner()
            self._correction_learner = learner
        return learner

    def _words_path(self) -> Path | None:
        provider = getattr(self._feedback, "words_path", None)
        try:
            path = provider() if callable(provider) else None
        except Exception:  # noqa: BLE001 - no word list here: no learning here
            return None
        return Path(path) if path else None

    def _note_correction(self, before: str, after: str) -> None:
        """A correction the person made by voice ("choose 2", "correct X").

        Called after the document has been changed. Offers to remember it the
        second time the same word is corrected the same way.
        """
        if self._words_path() is None:
            return  # a host with no word list (Quill Inkwell) learns nothing
        pair = self._learner().note(before, after)
        if pair is None:
            return
        heard, written = pair
        question = offer_question(heard, written)
        confirm = getattr(self._feedback, "confirm_correction", None)
        if callable(confirm):
            confirm(question, lambda: self._add_learned(heard, written))
            return
        prefix = str(getattr(self._preferences(), "command_prefix", "") or "")
        if prefix:
            how = f"Say {prefix} yes to add it, or {prefix} no."
        else:
            how = "Say yes to add it, or no."
        self._learn_pending = (heard, written, self._clock() + ANSWER_SECONDS)
        self._say(f"{question} {how}")

    def _learn_from_correcting(self, text: str) -> None:
        """The phrase after "correct X" replaced X: count it as a correction.

        Only when it landed where X was (``voice_commands._land`` noted both);
        a phrase written anywhere else, or after another command, counts for
        nothing."""
        pending = getattr(self, "_correcting", None)
        if pending is None:
            return
        self._correcting = None
        old, start = pending
        last = self.history.peek()
        if last is None or last.start != start or last.inserted != text:
            return
        self._note_correction(old, text)

    def _learn_answer(self, words: tuple[str, ...] | list[str]) -> bool:
        """ "QUILL yes" or "QUILL no" to a spoken offer: ``True`` when it was one."""
        from quill.core.windows_dictation.vocabulary_es import spanish_answer

        pending = getattr(self, "_learn_pending", None)
        if pending is None:
            return False
        language = str(getattr(self._preferences(), "speech_language", "en") or "en")
        # "QUILL sí": a draft, off until a native speaker checks it (vocabulary_es).
        answer = spanish_answer(words, language) or " ".join(words)
        if answer not in ("yes", "no"):
            return False
        self._learn_pending = None
        heard, written, until = pending
        if self._clock() > until:
            return False  # lapsed: "yes" is not an answer to anything now
        if answer == "yes":
            self._add_learned(heard, written)
        else:
            self._say("Not added.")
        return True

    def _add_learned(self, heard: str, written: str) -> None:
        path = self._words_path()
        if path is None:
            return
        self._say(add_learned_correction(path, heard, written))
