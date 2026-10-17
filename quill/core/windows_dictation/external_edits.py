"""Correcting in another program, on the session's own words only (D-10).

QUILL Transcribe and Quill Inkwell type into programs they cannot read. Until
2026-10-16 the only correction there was "scratch that", sent as backspaces.
D-10 adds the rest of the correcting commands -- correct that and choose N,
caps that, uppercase that and lowercase that, replace X with Y, change that to
Y, delete last sentence and delete previous paragraph -- on one condition each:
they act only on words **this session typed**, and each is a
backspace-and-retype pair. Nothing in the other program is ever read: what
dictation knows is what it typed, kept in memory by the external document
(``quill/ui/windows_dictation_external.py``).

An edit is refused, with one sentence, when the words can no longer be trusted
to be where dictation left them (:func:`edit_problem`):

* **The focus moved** -- the field lock (``target_lock.py``) or the external
  document says the field in front is not the one the words went into.
* **The person typed or clicked since** (:class:`OwnWordsGuard`). Windows says
  *when* it last saw a key or the mouse, never what it was
  (``quill/platform/windows/input_activity.py``); anything after dictation's
  own typing means the cursor or the text may have moved, so the backspaces
  could land on somebody's own words. Moving the mouse counts too: refusing is
  safe, guessing is not.
* **The program corrects as you type** (:data:`AUTOCORRECTING_PROGRAMS`).
  Word and Outlook change words as they are typed (a capital, a symbol, a
  spelling), so the count of characters dictation remembers is not the count
  in the field, and retyping would land wrong. "scratch that" still works
  there, as it always has; the retyping commands are refused, until the
  compatibility matrix (D-4) proves a program safe.

The never-type list and the password and administrator refusals are not
repeated here: they stop the words going in at all (``never_type.py``).

Pure and wx-free.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.windows_dictation.vocabulary_types import Command

__all__ = [
    "AUTOCORRECTING_PROGRAMS",
    "EXTERNAL_EDIT_COMMANDS",
    "MOVED_SINCE",
    "SETTLE_MS",
    "TYPED_SINCE",
    "OwnWordsGuard",
    "autocorrect_refusal",
    "edit_problem",
    "retypes",
]

#: The commands that change words dictation already typed into another program.
#: Every one is checked by :func:`edit_problem` before anything is sent.
EXTERNAL_EDIT_COMMANDS = frozenset({
    Command.SCRATCH,
    Command.CHOOSE_1,
    Command.CHOOSE_2,
    Command.CHOOSE_3,
    Command.CAPITALIZE,
    Command.UPPERCASE,
    Command.LOWERCASE,
    Command.DELETE_SENTENCE,
    Command.DELETE_PARAGRAPH,
    Command.REPLACE_WORDS,
    Command.CHANGE_THAT,
})

#: Of those, the ones that only take words away: no retyping, so a program
#: that corrects as you type is no reason to refuse them.
_ONLY_REMOVES = frozenset({Command.SCRATCH, Command.DELETE_SENTENCE, Command.DELETE_PARAGRAPH})

#: Programs that change words as they are typed, by file name. Word's
#: AutoCorrect is Outlook's editor too. Until the D-4 matrix measures them,
#: retyping there is refused rather than guessed at.
AUTOCORRECTING_PROGRAMS: dict[str, str] = {
    "winword.exe": "Word",
    "outlook.exe": "Outlook",
}

MOVED_SINCE = "The focus has moved since dictation typed those words, so they were left alone."
TYPED_SINCE = (
    "You have typed or clicked since dictation typed those words, so they were "
    "left alone. Change them with the keyboard, or say them again."
)

#: Windows notes dictation's own typing a moment after it is sent. Input this
#: soon after it is taken to be dictation's own; nobody types a key and then
#: speaks a command inside a third of a second.
SETTLE_MS = 300


def retypes(command: Command) -> bool:
    """Whether *command* types words back in, not only takes them away."""
    return command not in _ONLY_REMOVES


def autocorrect_refusal(program: str) -> str:
    """Why words cannot be retyped in *program* (a file name), or ``""``."""
    name = AUTOCORRECTING_PROGRAMS.get((program or "").strip().lower())
    if not name:
        return ""
    return (
        f"{name} can change words as they are typed, so dictation does not retype "
        "them there. Say scratch that and say it again."
    )


class OwnWordsGuard:
    """Whether the person has typed or clicked since dictation last typed.

    *last_input* is when Windows last saw a key or the mouse (a millisecond
    tick), or ``None`` when it cannot say -- which is never taken as "nobody
    typed": without an answer there is no check, the same as before D-10.
    """

    def __init__(self, last_input: Callable[[], int | None] | None = None) -> None:
        self._last_input = last_input
        self._after: int | None = None

    def wrote(self) -> None:
        """Dictation has just typed (or erased): this is its own input."""
        self._after = self._tick()

    def forget(self) -> None:
        """The focus moved: there are no own words to protect."""
        self._after = None

    def typed_since(self) -> bool:
        if self._after is None:
            return False
        now = self._tick()
        if now is None:
            return False
        # The tick wraps after 49 days; a wrap is a difference that is negative.
        return (now - self._after) % (1 << 32) > SETTLE_MS

    def _tick(self) -> int | None:
        if self._last_input is None:
            return None
        try:
            value = self._last_input()
        except Exception:  # noqa: BLE001 - cannot tell
            return None
        return None if value is None else int(value)


def edit_problem(
    *, moved: bool, typed: bool, program: str = "", command: Command = Command.SCRATCH
) -> str:
    """The one sentence that refuses *command* in another program, or ``""``."""
    if moved:
        return MOVED_SINCE
    if typed:
        return TYPED_SINCE
    if retypes(command):
        return autocorrect_refusal(program)
    return ""
