"""What dictation has been told to do: the settings, as one frozen value.

Read afresh for every phrase (:meth:`DictationPreferences.from_settings`), so a
change in Dictation Settings applies to the very next thing said. Moved out of
the controller when the five finer choices arrived; the controller re-exports
both names, so nothing that imported them from there changes.

Pure and wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from quill.core.action_feedback import ActionFeedback
from quill.core.action_feedback import coerce as coerce_feedback
from quill.core.windows_dictation.engines import coerce_engine
from quill.core.windows_dictation.options import PAUSE_SECONDS, coerce_pause, coerce_silence
from quill.core.windows_dictation.speech_language import (
    STOP_PHRASES,
    WAKE_PHRASES,
    coerce_speech_language,
    localised_phrase,
)
from quill.core.windows_dictation.vocabulary import DASH_STYLES, Vocabulary, vocabulary_for
from quill.core.windows_dictation.wake import DEFAULT_STOP_PHRASE, DEFAULT_WAKE_PHRASE

__all__ = ["DEFAULT_PHRASE_FEEDBACK", "DictationPreferences"]

#: The read-back is on by default, with the tone: hearing the words is how a
#: listener knows the recogniser got it right, which a tone alone cannot say.
DEFAULT_PHRASE_FEEDBACK = ActionFeedback.BOTH.value


@dataclass(frozen=True, slots=True)
class DictationPreferences:
    """The dictation settings, read from either editor's settings object."""

    #: The microphone's name; empty means the Windows default microphone.
    microphone: str = ""
    #: ``moonshine``, ``whisper``, ``windows`` or ``voice_typing`` -- see
    #: :mod:`quill.core.windows_dictation.engines`.
    engine: str = "moonshine"
    phrase_feedback: str = DEFAULT_PHRASE_FEEDBACK
    cue_sounds: bool = True
    announce: bool = True
    #: How "dash" is written: ``em``, ``en`` or ``hyphens``.
    dash: str = "em"
    #: Listen for the wake phrase while dictation is off.
    wake_enabled: bool = False
    wake_phrase: str = DEFAULT_WAKE_PHRASE
    #: Said on its own, stops dictation (as "stop dictation" always does).
    stop_phrase: str = DEFAULT_STOP_PHRASE
    #: For Windows speech recognition only: a recogniser's language name, or
    #: empty for the one Windows uses by default.
    language: str = ""
    #: The language dictation listens for: ``en`` or ``es`` (dict.md 9;
    #: :mod:`quill.core.windows_dictation.speech_language`).
    speech_language: str = "en"
    #: How long a pause ends a phrase: ``short``, ``normal`` or ``long``
    #: (:data:`quill.core.windows_dictation.options.PAUSE_SECONDS`).
    pause: str = "normal"
    #: Drop "um", "uh" and their kin before anything is written.
    remove_fillers: bool = False
    #: Let Moonshine and Whisper punctuate. Off: the user says every mark.
    auto_punctuation: bool = True
    #: Minutes of silence after which dictation stops; 0 is never.
    silence_minutes: int = 0
    #: Just write what I say: a pause does nothing -- no full stop, no tone, no
    #: read-back, no command but the stop phrase.
    continuous: bool = False
    #: ``text -> text``, the user's own replacements and vocabulary
    #: (quill.core.speech.dictation_profile). Identity when they have none.
    rewrite: Callable[[str], str] | None = field(default=None, compare=False)

    @property
    def engine_punctuates(self) -> bool:
        """Whether the engine adds punctuation by itself, and is allowed to."""
        return self.engine in {"moonshine", "whisper"} and self.auto_punctuation

    @property
    def strips_punctuation(self) -> bool:
        """Whether the engine's own marks are to be taken out again."""
        return self.engine in {"moonshine", "whisper"} and not self.auto_punctuation

    @property
    def pause_seconds(self) -> float:
        return PAUSE_SECONDS[coerce_pause(self.pause)]

    @property
    def filler_language(self) -> str:
        """The language filler removal is told, or ``""`` when it is not known.

        Known for the built-in engines, and for any engine in Spanish (Windows
        speech is then held to a Spanish recogniser). English Windows speech may
        be running whatever recogniser the user picked, so it stays unknown and
        only the universal hesitations go.
        """
        if self.speech_language != "en" or self.engine in {"moonshine", "whisper"}:
            return self.speech_language
        return ""

    @property
    def vocabulary(self) -> Vocabulary:
        """The table a phrase is matched against: Spanish punctuation words
        count only while the engine is not punctuating (dict.md 9.4, option 1)."""
        return vocabulary_for(self.speech_language, spoken_marks=not self.engine_punctuates)

    @classmethod
    def from_settings(
        cls, settings: object, *, rewrite: Callable[[str], str] | None = None
    ) -> DictationPreferences:
        """The preferences *settings* holds, under the names both editors share."""
        dash = str(getattr(settings, "windows_dictation_dash", "em") or "em")
        language = coerce_speech_language(
            getattr(settings, "windows_dictation_speech_language", "")
        )
        return cls(
            microphone=str(getattr(settings, "windows_dictation_microphone", "") or ""),
            engine=coerce_engine(getattr(settings, "windows_dictation_engine", "")),
            phrase_feedback=str(
                coerce_feedback(
                    getattr(settings, "windows_dictation_phrase_feedback", DEFAULT_PHRASE_FEEDBACK)
                )
            ),
            cue_sounds=bool(getattr(settings, "windows_dictation_cue_sounds", True)),
            announce=bool(getattr(settings, "windows_dictation_announce", True)),
            dash=dash if dash in DASH_STYLES else "em",
            wake_enabled=bool(getattr(settings, "windows_dictation_wake_enabled", False)),
            wake_phrase=localised_phrase(
                str(getattr(settings, "windows_dictation_wake_phrase", "") or DEFAULT_WAKE_PHRASE),
                language,
                WAKE_PHRASES,
            ),
            stop_phrase=localised_phrase(
                str(getattr(settings, "windows_dictation_stop_phrase", "") or DEFAULT_STOP_PHRASE),
                language,
                STOP_PHRASES,
            ),
            language=str(getattr(settings, "windows_dictation_language", "") or ""),
            speech_language=language,
            pause=coerce_pause(getattr(settings, "windows_dictation_pause", "normal")),
            remove_fillers=bool(getattr(settings, "windows_dictation_remove_fillers", False)),
            auto_punctuation=bool(getattr(settings, "windows_dictation_auto_punctuation", True)),
            silence_minutes=coerce_silence(
                getattr(settings, "windows_dictation_silence_minutes", 0)
            ),
            continuous=bool(getattr(settings, "windows_dictation_continuous", False)),
            rewrite=rewrite,
        )
