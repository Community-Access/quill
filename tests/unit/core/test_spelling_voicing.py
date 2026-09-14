"""How a misspelling is said: the letters, the timings, and the alert.

Every rule the two editors share, asserted without a display. The scheduler
takes its timer as a factory precisely so this file can hand it a fake one and
control time.
"""

from __future__ import annotations

from quill.core.spellcheck import misspelling_behind
from quill.core.spelling.voicing import (
    LETTER_STYLES,
    LiveAlertPolicy,
    SpellAloudPolicy,
    SpellAloudVoice,
    spell_out,
)


class _Timer:
    """A wx.CallLater stand-in: records the delay, fires when told."""

    def __init__(self, delay_ms: int, callback, *args) -> None:
        self.delay_ms = delay_ms
        self._callback = callback
        self._args = args
        self.stopped = False

    def Stop(self) -> None:
        self.stopped = True

    def fire(self) -> None:
        if not self.stopped:
            self._callback(*self._args)


class _Clock:
    def __init__(self) -> None:
        self.timers: list[_Timer] = []

    def __call__(self, delay_ms, callback, *args):
        timer = _Timer(delay_ms, callback, *args)
        self.timers.append(timer)
        return timer

    @property
    def last(self) -> _Timer:
        return self.timers[-1]


# ---------------------------------------------------------------------------
# Spelling a word out


def test_letters_are_upper_cased_and_separated_by_a_full_stop() -> None:
    """Upper case because several voices read a lone lower-case letter as a
    word. A full stop rather than a comma because that is the longer of the two
    pauses every synthesiser implements, and the speech rate itself belongs to
    the listener's screen reader -- punctuation is the only pacing we have.
    Asked for on 2026-09-12: a spelling read at conversational speed goes past
    faster than it can be held, which is the one thing it must not do."""
    assert spell_out("recieve") == "R. E. C. I. E. V. E"


def test_capitals_are_named_when_asked() -> None:
    """MacDonald and Macdonald are a spelling question, and upper-casing every
    letter for clarity is exactly what throws the answer away."""
    assert spell_out("MacDonald") == "cap M. A. C. cap D. O. N. A. L. D"


def test_capitals_can_be_left_unnamed() -> None:
    assert spell_out("MacDonald", capitals=False) == "M. A. C. D. O. N. A. L. D"


def test_punctuation_inside_a_word_is_named_not_paused_over() -> None:
    """A pause is not a hyphen, and a listener cannot tell one from the other."""
    assert spell_out("well-known") == "W. E. L. L. dash. K. N. O. W. N"
    assert spell_out("don't") == "D. O. N. apostrophe. T"


def test_the_phonetic_alphabet_is_offered_whole() -> None:
    """For a fast voice or a noisy room, where B, D, E, P, T and V are one
    sound with a rumour attached."""
    assert spell_out("cat", style="phonetic") == "charlie. alpha. tango"


def test_phonetic_names_capitals_too() -> None:
    assert spell_out("Cat", style="phonetic") == "cap charlie. alpha. tango"


def test_both_gives_the_letters_first_then_the_phonetic() -> None:
    assert spell_out("cat", style="both") == "C. A. T.. charlie. alpha. tango"


def test_an_unknown_style_falls_back_to_letters_rather_than_failing() -> None:
    assert spell_out("cat", style="nonsense") == "C. A. T"


def test_an_empty_word_says_nothing() -> None:
    assert spell_out("") == ""


def test_every_offered_style_actually_works() -> None:
    """The settings surface offers these three by name; each has to produce
    something, or a listener picks one and the feature silently stops."""
    for value, _label in LETTER_STYLES:
        assert spell_out("word", style=value)


# ---------------------------------------------------------------------------
# The policy


def test_a_policy_reads_a_settings_object() -> None:
    class Settings:
        spell_aloud_enabled = True
        spell_aloud_delay_ms = 1200
        spell_aloud_style = "phonetic"
        spell_aloud_capitals = False

    policy = SpellAloudPolicy.from_settings(Settings())
    assert policy.delay_ms == 1200
    assert policy.style == "phonetic"
    assert policy.capitals is False


def test_a_settings_object_missing_half_the_fields_still_works() -> None:
    """An older build's settings, or a test double with three attributes, must
    give a working policy rather than an AttributeError mid-keystroke."""

    class Sparse:
        spell_aloud_enabled = False

    assert SpellAloudPolicy.from_settings(Sparse()).enabled is False
    assert SpellAloudPolicy.from_settings(Sparse()).delay_ms == 800


def test_a_nonsense_delay_is_clamped_rather_than_obeyed() -> None:
    class Settings:
        spell_aloud_delay_ms = 999999

    assert SpellAloudPolicy.from_settings(Settings()).delay_ms == 5000


def test_a_switched_off_policy_says_nothing_at_all() -> None:
    assert SpellAloudPolicy(enabled=False).say("recieve") == ""


# ---------------------------------------------------------------------------
# The scheduler


def test_the_spelling_arrives_after_the_pause_and_not_before() -> None:
    """A separate utterance, so it can be interrupted -- and so a fast reader
    who moves on never hears it at all."""
    said: list[str] = []
    clock = _Clock()
    voice = SpellAloudVoice(said.append, SpellAloudPolicy(), clock)
    assert voice.spell_later("recieve") is True
    assert said == []  # nothing yet: the reader is still saying the word
    clock.last.fire()
    assert said == ["R. E. C. I. E. V. E"]


def test_the_pause_is_the_one_the_caller_asked_for() -> None:
    clock = _Clock()
    voice = SpellAloudVoice(lambda _m: None, SpellAloudPolicy(delay_ms=800), clock)
    voice.spell_later("word", delay_ms=250)
    assert clock.last.delay_ms == 250


def test_scheduling_a_second_spelling_cancels_the_first() -> None:
    """Travelling through a document with the next-misspelling key has to be
    quiet, not a queue of spellings for words already left behind."""
    said: list[str] = []
    clock = _Clock()
    voice = SpellAloudVoice(said.append, SpellAloudPolicy(), clock)
    voice.spell_later("recieve")
    voice.spell_later("teh")
    clock.timers[0].fire()
    clock.timers[1].fire()
    assert said == ["T. E. H"]


def test_cancel_takes_back_a_pending_spelling() -> None:
    said: list[str] = []
    clock = _Clock()
    voice = SpellAloudVoice(said.append, SpellAloudPolicy(), clock)
    voice.spell_later("recieve")
    assert voice.pending
    voice.cancel()
    clock.last.fire()
    assert said == []
    assert not voice.pending


def test_a_switched_off_voice_schedules_nothing() -> None:
    clock = _Clock()
    voice = SpellAloudVoice(lambda _m: None, SpellAloudPolicy(enabled=False), clock)
    assert voice.spell_later("recieve") is False
    assert clock.timers == []


def test_with_no_timer_the_delayed_half_is_skipped_not_rushed() -> None:
    """Speaking it immediately would talk over the announcement it is meant to
    follow, which is the exact thing the pause exists to prevent."""
    said: list[str] = []
    voice = SpellAloudVoice(said.append, SpellAloudPolicy(), None)
    assert voice.spell_later("recieve") is False
    assert said == []


def test_spelling_now_ignores_the_pause_and_the_master_switch() -> None:
    """For a key whose entire purpose is to spell the word: pressing it is
    asking, and a request is not something a default gets to refuse."""
    said: list[str] = []
    voice = SpellAloudVoice(said.append, SpellAloudPolicy(enabled=False), None)
    assert voice.spell_word_now("teh") is True
    assert said == ["T. E. H"]


# ---------------------------------------------------------------------------
# The alert while you type


def test_the_alert_is_a_sound_and_not_a_voice_by_default() -> None:
    """Speech there interrupts the sentence it is commenting on."""
    policy = LiveAlertPolicy()
    assert policy.sound is True
    assert policy.speech is False


def test_the_alert_can_be_silenced_outright() -> None:
    class Settings:
        spelling_alert_sound = False

    assert LiveAlertPolicy.from_settings(Settings()).sound is False


def test_the_repeat_throttle_can_be_switched_off_entirely() -> None:
    """ "Every time" is a real answer: a throttle that cannot be turned off is
    one that eventually hides something."""

    class Settings:
        spelling_alert_repeat_ms = 0

    assert LiveAlertPolicy.from_settings(Settings()).repeat_ms == 0


# ---------------------------------------------------------------------------
# The word the alert is about


def test_the_alert_fires_on_the_word_you_have_just_finished() -> None:
    """The bug this replaced: both editors asked for a word beginning exactly
    at the caret, which typing left to right never produces -- so the whole
    as-you-type alert had settings, an earcon, a status line, and had never
    once fired."""
    text = "the wrold "
    found = misspelling_behind(text, len(text), set())
    assert found is not None
    assert found.word == "wrold"


def test_the_alert_stays_quiet_on_a_word_you_are_still_typing() -> None:
    """Otherwise it judges "recie" on the way to "receive" and cries wolf
    before every long word."""
    assert misspelling_behind("the wrold", 9, set()) is None


def test_any_terminator_will_do() -> None:
    for text in ("wrold ", "wrold,", "wrold.\n", "wrold; "):
        assert misspelling_behind(text, len(text), set()) is not None, text


def test_a_correctly_spelled_word_is_silent() -> None:
    assert misspelling_behind("the world ", 10, set()) is None


def test_an_ordinal_is_not_a_misspelling() -> None:
    """ "the 13th of May" used to report "th" -- at an offset inside a number,
    for a word nobody typed."""
    assert misspelling_behind("the 13th ", 9, set()) is None


def test_letters_after_digits_are_never_a_misspelling() -> None:
    """The whole family the ordinal guard covers: every one was a spoken
    interruption and none was ever a spelling mistake."""
    for text in ("a 3D ", "at 1080p ", "add 500ml ", "size 12pt "):
        assert misspelling_behind(text, len(text), set()) is None, text


def test_the_start_of_the_document_is_not_an_error() -> None:
    assert misspelling_behind("", 0, set()) is None
    assert misspelling_behind("   ", 3, set()) is None
