"""How a misspelling is *said*: the letters, the timing, and the alert.

A misspelling is the one thing in an editor that speech alone cannot convey.
"receive" and "recieve" are the same sound. A sighted user gets a red squiggle
under the wrong letters; a listener who is told "not in dictionary, recieve"
has been told a word they cannot tell from the right one, which is a report
rather than an answer. **The letters are the answer**, and everything in this
module exists to deliver them without becoming a nuisance.

Four decisions, and each is a setting because listeners disagree about all four.

**Spelling comes after a pause, as a second utterance.** Not "recieve, R E C I E
V E" in one breath: a single utterance cannot be interrupted, and somebody who
recognised the word from its first syllable would have to sit through eleven
more. A pause and a separate utterance means a fast user never hears the
spelling at all -- they have already pressed the next key, and the pending
spell-aloud is cancelled -- while somebody who waits gets it in full. The pause
is tunable because "fast" is a fact about a person and their speech rate, not
about a program.

**Timings differ by surface.** In the review dialog you are stopped and
deciding, so the default pause is long. Moving through a document with the
next-misspelling key you may be travelling, so its default is shorter -- a
spell-aloud you always outrun is one more thing to cancel, and one you always
wait for is a metronome. Two numbers, two defaults, both tunable.

**Letters can be said three ways.** Plain letters are fastest and are what most
people want. The phonetic alphabet is unambiguous over a bad synthesiser or a
noisy room, where B, D, E, P, T and V are one sound with a rumour attached. Both
is for somebody learning a word rather than checking one. Capitals are named
when asked ("cap M") because a name is a spelling question too.

**While you are typing, the alert is a sound and not a voice.** Speech there
interrupts the very sentence it is commenting on, and a listener composing a
paragraph is the person least able to afford it. The earcon is short, quiet and
distinct, it can be silenced outright, and its repeat interval is tunable so a
document full of proper nouns does not become a drum. Speaking the alert is
available for somebody who wants it, and is off by default.

wx-free. The scheduling needs a one-shot timer, which arrives as a factory the
UI supplies (``wx.CallLater``); with none, the delayed half simply does not
happen and the immediate half still does. That is what lets every rule here be
tested without a display.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "LETTER_STYLES",
    "LiveAlertPolicy",
    "SpellAloudPolicy",
    "SpellAloudVoice",
    "spell_out",
]

#: The three ways to say a word's letters, as ``(stored value, human label)``.
#: Shared by both apps' settings surfaces so the words on screen match.
LETTER_STYLES: tuple[tuple[str, str], ...] = (
    ("letters", "Letters (R, E, C)"),
    ("phonetic", "Phonetic alphabet (romeo, echo, charlie)"),
    ("both", "Letters, then the phonetic alphabet"),
)

#: NATO/ICAO, the one phonetic alphabet a listener is likely to already know.
#: Lower case on purpose: a synthesiser reads "romeo" as a word and "ROMEO" as a
#: word it may decide to spell.
_PHONETIC: dict[str, str] = {
    "a": "alpha",
    "b": "bravo",
    "c": "charlie",
    "d": "delta",
    "e": "echo",
    "f": "foxtrot",
    "g": "golf",
    "h": "hotel",
    "i": "india",
    "j": "juliet",
    "k": "kilo",
    "l": "lima",
    "m": "mike",
    "n": "november",
    "o": "oscar",
    "p": "papa",
    "q": "quebec",
    "r": "romeo",
    "s": "sierra",
    "t": "tango",
    "u": "uniform",
    "v": "victor",
    "w": "whiskey",
    "x": "x-ray",
    "y": "yankee",
    "z": "zulu",
}

#: Characters a synthesiser will not say usefully on their own. A bare "-" is
#: read as a pause by some voices and as nothing by others, and either way the
#: listener does not learn there is a hyphen in the word.
_NAMED: dict[str, str] = {
    "-": "dash",
    "_": "underscore",
    "'": "apostrophe",
    "’": "apostrophe",
    ".": "dot",
    "/": "slash",
    "\\": "backslash",
    "&": "ampersand",
    "@": "at",
    "#": "hash",
    "+": "plus",
    "=": "equals",
    ":": "colon",
    ",": "comma",
}


def spell_out(word: str, *, style: str = "letters", capitals: bool = True) -> str:
    """*word*, one character at a time, ready to be spoken.

    Comma-separated because a comma is the one piece of punctuation every
    synthesiser turns into a short pause, and the pause is what stops "E C" being
    heard as "easy".

    Letters are upper-cased whatever the source says, because a lower-case
    letter alone is read as a word by several voices ("a", "i") and as a letter
    by others; upper case is read as a letter by all of them. That loses the
    information that a letter *was* capitalised, which is why *capitals* puts it
    back explicitly rather than relying on case -- "cap M, C, cap D" is how you
    hear that a surname is MacDonald and not Macdonald.

    Digits, punctuation and anything else keep their own name (see
    :data:`_NAMED`) so a hyphen or an apostrophe in the word is heard rather
    than merely paused over.
    """
    if not word:
        return ""
    if style == "phonetic":
        return ", ".join(_phonetic_pieces(word, capitals=capitals))
    letters = ", ".join(_letter_pieces(word, capitals=capitals))
    if style != "both":
        return letters
    phonetic = ", ".join(_phonetic_pieces(word, capitals=capitals))
    return f"{letters}. {phonetic}" if phonetic else letters


def _letter_pieces(word: str, *, capitals: bool) -> list[str]:
    pieces: list[str] = []
    for character in word:
        if character.isalpha():
            said = character.upper()
            if capitals and character.isupper():
                said = f"cap {said}"
            pieces.append(said)
        elif character.isspace():
            pieces.append("space")
        elif character in _NAMED:
            pieces.append(_NAMED[character])
        else:
            pieces.append(character)
    return pieces


def _phonetic_pieces(word: str, *, capitals: bool) -> list[str]:
    pieces: list[str] = []
    for character in word:
        lowered = character.lower()
        if lowered in _PHONETIC:
            said = _PHONETIC[lowered]
            if capitals and character.isupper():
                said = f"cap {said}"
            pieces.append(said)
        elif character.isspace():
            pieces.append("space")
        elif character in _NAMED:
            pieces.append(_NAMED[character])
        else:
            pieces.append(character)
    return pieces


@dataclass(frozen=True, slots=True)
class SpellAloudPolicy:
    """Whether to spell a word out, how, and how long to wait first.

    Read off a settings object rather than passed around as eight arguments,
    because both apps store the same eight names and the point of that is that
    a listener who tunes them in one editor finds the other already tuned.
    """

    enabled: bool = True
    delay_ms: int = 800
    navigation: bool = True
    navigation_delay_ms: int = 600
    suggestions: bool = True
    suggestion_delay_ms: int = 600
    first_suggestion: bool = False
    style: str = "letters"
    capitals: bool = True

    @classmethod
    def from_settings(cls, settings: Any) -> SpellAloudPolicy:
        """Build a policy from whatever settings object the app has.

        ``getattr`` with the dataclass's own defaults throughout, so a settings
        object from an older build -- or a test double with three attributes --
        produces a working policy instead of an AttributeError in the middle of
        a keystroke.
        """
        if settings is None:
            return cls()
        return cls(
            enabled=bool(_get(settings, "spell_aloud_enabled", True)),
            delay_ms=_clamp(_get(settings, "spell_aloud_delay_ms", 800), 100, 5000),
            navigation=bool(_get(settings, "spell_aloud_on_navigation", True)),
            navigation_delay_ms=_clamp(
                _get(settings, "spell_aloud_navigation_delay_ms", 600), 100, 5000
            ),
            suggestions=bool(_get(settings, "spell_aloud_suggestions", True)),
            suggestion_delay_ms=_clamp(
                _get(settings, "spell_aloud_suggestion_delay_ms", 600), 100, 5000
            ),
            first_suggestion=bool(_get(settings, "spell_aloud_first_suggestion", False)),
            style=_style(_get(settings, "spell_aloud_style", "letters")),
            capitals=bool(_get(settings, "spell_aloud_capitals", True)),
        )

    def say(self, word: str) -> str:
        """*word* spelled out under this policy, or "" when it is switched off."""
        if not self.enabled:
            return ""
        return spell_out(word, style=self.style, capitals=self.capitals)


@dataclass(frozen=True, slots=True)
class LiveAlertPolicy:
    """What happens when a misspelling appears under the caret as you type.

    A sound by default and speech never, unless somebody asks for it. The repeat
    interval is the throttle that stops one stubborn proper noun becoming a
    drum: the same word at the same place inside that window is silent.
    """

    sound: bool = True
    speech: bool = False
    repeat_ms: int = 750

    @classmethod
    def from_settings(cls, settings: Any) -> LiveAlertPolicy:
        if settings is None:
            return cls()
        return cls(
            sound=bool(_get(settings, "spelling_alert_sound", True)),
            speech=bool(_get(settings, "spelling_alert_speech", False)),
            repeat_ms=_clamp(_get(settings, "spelling_alert_repeat_ms", 750), 0, 10000),
        )


class SpellAloudVoice:
    """Schedules "and here is how it is spelled", and takes it back on demand.

    One instance per surface that can land on a word. It owns exactly one
    pending utterance: scheduling a second cancels the first, which is what
    makes travelling through a document with the next-misspelling key quiet
    rather than a queue of spellings for words you have already left.

    The timer factory is ``(delay_ms, callable, *args) -> timer`` --
    ``wx.CallLater``'s own shape. Without one the delayed utterance is skipped
    rather than spoken immediately: speaking it at once would talk over the
    announcement it is meant to follow, which is the exact thing the pause
    exists to prevent.
    """

    __slots__ = ("_announce", "_pending", "_timer_factory", "policy")

    def __init__(
        self,
        announce: Callable[[str], None],
        policy: SpellAloudPolicy | None = None,
        timer_factory: Callable[..., object] | None = None,
    ) -> None:
        self._announce = announce
        self.policy = policy or SpellAloudPolicy()
        self._timer_factory = timer_factory
        self._pending: object | None = None

    # -- scheduling --------------------------------------------------------- #

    def spell_later(self, word: str, *, delay_ms: int | None = None) -> bool:
        """Spell *word* after the pause. True when something was scheduled.

        False covers every reason nothing will be said -- switched off, no word,
        no timer -- so a caller can fall back without asking three questions.
        """
        self.cancel()
        text = self.policy.say(word)
        if not text or self._timer_factory is None:
            return False
        wait = self.policy.delay_ms if delay_ms is None else delay_ms
        if wait <= 0:
            self._announce(text)
            return True
        try:
            self._pending = self._timer_factory(wait, self._speak, text)
        except Exception:  # noqa: BLE001 - a missing timer backend is not an error
            return False
        return True

    def spell_word_now(self, word: str) -> bool:
        """Spell *word* immediately. For a key whose whole purpose is to spell it."""
        self.cancel()
        text = spell_out(word, style=self.policy.style, capitals=self.policy.capitals)
        if not text:
            return False
        self._announce(text)
        return True

    def cancel(self) -> None:
        """Drop a pending spelling. Called on every move, and it must not raise."""
        pending = self._pending
        self._pending = None
        if pending is None:
            return
        try:
            stop = getattr(pending, "Stop", None)
            if callable(stop):
                stop()
        except Exception:  # noqa: BLE001 - a timer that will not stop is not fatal
            return

    @property
    def pending(self) -> bool:
        """Whether a spelling is waiting to be said. For tests and for status."""
        return self._pending is not None

    def _speak(self, text: str) -> None:
        self._pending = None
        self._announce(text)


def _get(settings: Any, name: str, default: Any) -> Any:
    value = getattr(settings, name, None)
    return default if value is None else value


def _clamp(value: Any, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return low if low > 0 else 0
    return max(low, min(high, number))


def _style(value: Any) -> str:
    text = str(value or "letters")
    return text if text in {name for name, _label in LETTER_STYLES} else "letters"
