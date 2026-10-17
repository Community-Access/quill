"""Review before inserting: dictated words held, changed on request, then put in.

D-2 of the 2026-10-13 dictation gap plan (the owner's request): "compose by
talking". Dictation can be held in a review window instead of going straight
into the document or the other program; the person reads it, asks the AI to
change it ("make it shorter", "more formal"), hears what changed, and inserts it
once. Nothing reaches the target before Insert.

This module is the state and the words, wx-free:

* :class:`ReviewSession` -- ``original`` (what was said), every revision as
  ``(instruction, before, after)``, ``current``, and the ``target`` it is going
  to. The operations are :meth:`~ReviewSession.revise`,
  :meth:`~ReviewSession.undo_revision`, :meth:`~ReviewSession.restore_original`
  and :meth:`~ReviewSession.diff`. "What I said" is the text as it stood
  before the first change was asked for: words dictated or typed into the
  review before then are part of it; after it, they are edits to ``current``.
* :func:`review_request` -- what one AI request carries: the text marked as
  data, the person's instruction, and My Dictation Instructions. Never any
  other text, unless the person turned on the document's dictation context.
* The rescue file -- an open review is written to ``dictation-review.json`` in
  the data folder as it changes, so a crash or a closed window loses nothing,
  and the next Review Dictation brings it back (:func:`save_rescue`,
  :func:`load_rescue`, :func:`clear_rescue`).
* :data:`REVIEW_HELP` -- the phrases said after the command word, for the
  command table and the published reference.

The conversation (what each command says and does) is
:mod:`~quill.core.windows_dictation.review_conversation`; the controller's half
is :mod:`~quill.core.windows_dictation.review_mixin`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.diffing import LARGE_CHANGE, change_fraction, spoken_changes
from quill.core.windows_dictation.vocabulary_types import Command, CommandHelp

__all__ = [
    "AI_OFF",
    "CONSENT_VERSION",
    "NOTHING_TO_REVIEW",
    "RESCUE_FILE",
    "REVIEW_COMMANDS",
    "REVIEW_FEATURE",
    "REVIEW_HELP",
    "Revision",
    "ReviewSession",
    "clear_rescue",
    "consent_question",
    "load_rescue",
    "not_reviewing",
    "review_request",
    "save_rescue",
]

#: The AI feature id (``quill.core.ai.own_key.INSTRUCTIONS``). Direct routes only.
REVIEW_FEATURE = "revise_dictation"
#: The consent the person gave for sending reviewed words to an AI provider.
#: Raise it when what is sent changes, so the question is asked again.
CONSENT_VERSION = 1
RESCUE_FILE = "dictation-review.json"
_RESCUE_SCHEMA = 1

#: "QUILL review that" with AI off: the phrase stays where it was written.
AI_OFF = "AI is off. Your words were written as you said them."

#: "Polish my dictation" (P3): the one fixed request "polish that" sends. It
#: is an ordinary review instruction, so the words stay data, the consent is
#: the review's, and the result is a revision Undo Change takes back.
POLISH_INSTRUCTION = (
    "Polish this dictation: fix punctuation, capital letters, spelling and "
    "obvious grammar slips only. Keep my words, my meaning, my order and my tone. "
    "Do not add or remove ideas."
)
#: What the status line and "what changed" call that request.
POLISH_LABEL = "polish"
#: "polish that" with the setting off. Nothing is sent.
POLISH_OFF = (
    "Polish my dictation is off. Turn on Allow polishing my dictation with AI in "
    "More Dictation Settings."
)
NOTHING_TO_REVIEW = "Nothing to review yet. Dictate something first."

_GROUP = "Review before inserting"

#: Said after the command word. "review that" opens the review; the rest work
#: while one is open (and, with Talk About It on, without the command word).
REVIEW_HELP: tuple[CommandHelp, ...] = (
    CommandHelp(
        Command.REVIEW_THAT,
        ("review that", "review it"),
        "Takes the last phrase back out, or the words held while paused, and opens "
        "it in Review Dictation to read, change and insert. With AI off, the words "
        "stay where they were written.",
        _GROUP,
    ),
    CommandHelp(
        Command.REVIEW_REVISE,
        ("make it shorter", "more formal", "fix the grammar only"),
        "While reviewing: asks the AI to change the words. Anything else said after "
        "the command word while reviewing is an instruction too. You hear what changed.",
        _GROUP,
    ),
    CommandHelp(
        Command.REVIEW_WHAT_CHANGED,
        ("what changed",),
        "While reviewing: says again what the last change did.",
        _GROUP,
    ),
    CommandHelp(
        Command.REVIEW_READ,
        ("read it back", "read it"),
        "While reviewing: reads the whole text.",
        _GROUP,
    ),
    CommandHelp(
        Command.REVIEW_UNDO,
        ("undo that change", "undo the change"),
        "While reviewing: takes back the last change.",
        _GROUP,
    ),
    CommandHelp(
        Command.REVIEW_RESTORE,
        ("back to what i said",),
        "While reviewing: puts back the words exactly as you said them.",
        _GROUP,
    ),
    CommandHelp(
        Command.REVIEW_POLISH,
        ("polish that", "polish it"),
        "Asks the AI to fix punctuation, capitals and small slips in the words, "
        "keeping your words; opens the last phrase in Review Dictation first. Only "
        "when Allow polishing my dictation with AI is on, and only after you agree "
        "to send. You hear what changed; nothing is inserted until you insert it.",
        _GROUP,
    ),
    CommandHelp(
        Command.REVIEW_INSERT,
        ("insert it",),
        "While reviewing: writes the text where it was going, once.",
        _GROUP,
    ),
    CommandHelp(
        Command.REVIEW_DISCARD,
        ("discard it",),
        "While reviewing: throws the text away; nothing is written.",
        _GROUP,
    ),
)

#: Every review command, by the words that say it (folded, as wake_words gives).
REVIEW_COMMANDS: dict[tuple[str, ...], Command] = {
    tuple(phrase.split()): entry.command
    for entry in REVIEW_HELP
    if entry.command is not Command.REVIEW_REVISE
    for phrase in entry.phrases
}


def not_reviewing(prefix: str) -> str:
    """Said when a review command arrives with nothing being reviewed."""
    word = prefix or "the command word"
    return f"Nothing is being reviewed. Say {word} review that first."


def consent_question(provider: str) -> str:
    """Asked once, before the first request on a cloud route. No is the default."""
    return (
        f"Review with AI sends the words you are reviewing, and what you ask for, to "
        f"{provider}. No other text from your document is sent, unless you turn on "
        "Include This Document's Dictation Context. Each thing you ask for is one "
        "request. Send them?"
    )


@dataclass(frozen=True, slots=True)
class Revision:
    """One change asked for: the instruction, and the text before and after it."""

    instruction: str
    before: str
    after: str


@dataclass(slots=True)
class ReviewSession:
    """Words held for review. ``original`` is never changed once a revision exists."""

    _original: str = ""
    target: Any = None
    revisions: list[Revision] = field(default_factory=list)
    current: str = ""
    #: The spoken summary of the last change, for "what changed".
    last_summary: str = ""
    #: The last change touched more than half the words.
    large: bool = False

    def __post_init__(self) -> None:
        if not self.current:
            self.current = self._original

    @property
    def original(self) -> str:
        """What was said: the text as it stood before the first change."""
        return self._original

    @property
    def changed(self) -> bool:
        """Whether anything an AI did is part of ``current``."""
        return bool(self.revisions)

    def edited(self, text: str) -> None:
        """The words in the review changed by dictation or typing. Before any
        revision they are still what was said; after, an edit to ``current``."""
        if not self.revisions:
            self._original = text
        self.current = text

    def diff(self, before: str, after: str) -> str:
        """What changed from *before* to *after*, said in two sentences at most."""
        return spoken_changes(before, after)

    def revise(self, instruction: str, text: str) -> str:
        """The AI's reply replaces ``current``; returns the spoken summary.

        Computed here from the two texts, never from the model's own account.
        """
        before = self.current
        self.revisions.append(Revision(instruction, before, text))
        self.current = text
        self.large = change_fraction(before, text) > LARGE_CHANGE
        self.last_summary = self.diff(before, text)
        return self.last_summary

    def undo_revision(self) -> str:
        """Back to before the last change; ``""`` when there was none."""
        if not self.revisions:
            return ""
        revision = self.revisions.pop()
        self.current = revision.before
        self.large = False
        self.last_summary = self.diff(revision.after, revision.before)
        return self.last_summary

    def restore_original(self) -> bool:
        """``current`` becomes exactly what was said. ``False`` when it already was."""
        if self.current == self._original:
            return False
        self.last_summary = self.diff(self.current, self._original)
        self.current = self._original
        self.large = False
        return True

    def what_changed(self) -> str:
        return self.last_summary or "Nothing has changed yet."


def review_request(
    text: str, instruction: str, *, my_instructions: str = "", context: str = ""
) -> str:
    """One request: the instruction, then the text marked as data.

    *context* is this document's dictation context ("a formal letter"), sent
    only when the person turned it on; *my_instructions* are My Dictation
    Instructions. Nothing else from any document is ever part of it.
    """
    parts: list[str] = []
    notes = my_instructions.strip()
    if context.strip():
        line = f"This document is: {context.strip()}"
        notes = f"{notes}\n{line}" if notes else line
    if notes:
        parts.append(f"<dictation-instructions>\n{notes}\n</dictation-instructions>")
    parts.append(f"<request>\n{instruction.strip()}\n</request>")
    parts.append(f"<dictated-text>\n{text}\n</dictated-text>")
    return "\n\n".join(parts)


# -- the rescue file ----------------------------------------------------------- #


def save_rescue(path: Path, session: ReviewSession) -> bool:
    """Keep *session* on disk, so a crash or a closed window loses nothing.
    ``False`` when it could not be written; a review never fails for this."""
    from quill.core.storage import write_json_atomic

    data = {
        "schema": _RESCUE_SCHEMA,
        "original": session.original,
        "current": session.current,
        "revisions": [
            {"instruction": r.instruction, "before": r.before, "after": r.after}
            for r in session.revisions
        ],
    }
    try:
        write_json_atomic(Path(path), data)
    except Exception:  # noqa: BLE001 - the review carries on in memory
        return False
    return True


def load_rescue(path: Path) -> ReviewSession | None:
    """The review kept from last time, or ``None``. Never raises."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    original = str(data.get("original", "") or "")
    current = str(data.get("current", "") or "")
    if not (original.strip() or current.strip()):
        return None
    revisions = [
        Revision(str(r.get("instruction", "")), str(r.get("before", "")), str(r.get("after", "")))
        for r in data.get("revisions", [])
        if isinstance(r, dict)
    ]
    return ReviewSession(original, revisions=revisions, current=current or original)


def clear_rescue(path: Path) -> None:
    """The review ended on purpose (Insert or Discard): nothing to bring back."""
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass
