"""The language dictation listens for: English, or Spanish (dict.md section 9).

One setting, ``windows_dictation_speech_language``, shared by name between QUILL
and QUILL Lite, decides five things, each of which lives beside the code it
changes and asks this module what the language is:

* **The model.** English uses the engine the user chose. Spanish needs a model
  that knows Spanish, and Moonshine has none, so both built-in engines use the
  multilingual Whisper model, told ``language="es"``
  (:func:`quill.core.windows_dictation.engines.model_for`). Windows speech
  recognition is asked for a Spanish recogniser (es-ES, es-MX, ...) and says
  so plainly when Windows has none installed.
* **Filler removal**, which is told the language so the Spanish list is used.
* **The wake and stop phrases**: "Quill dicta" and "deja de dictar" by default
  in Spanish. Both are *awaiting native-speaker review* (dict.md 9.8, question
  3), and both stay editable in Dictation Settings, as the English ones are.
* **Spoken punctuation.** In Spanish, "coma", "punto" and the rest count only
  when the engine is not punctuating by itself -- automatic punctuation off, or
  Windows speech recognition -- because "coma" and "punto" are also everyday
  Spanish words (dict.md 9.4 C, option 1, chosen 2026-10-03).
* **Commands** stay English in the first release (dict.md 9.8, answer 4). A
  drafted Spanish command table exists in
  :mod:`~quill.core.windows_dictation.vocabulary_es`, switched off and
  reachable only in a development build -- see :func:`spanish_commands_enabled`.

Matching ignores accents (:func:`fold`): a recogniser may write "linea" or
"línea", and both must reach the same table entry.

Pure and wx-free.
"""

from __future__ import annotations

import os
import re
import unicodedata

__all__ = [
    "DEFAULT_SPEECH_LANGUAGE",
    "SPANISH_COMMANDS_VARIABLE",
    "SPEECH_LANGUAGES",
    "STOP_PHRASES",
    "WAKE_PHRASES",
    "coerce_speech_language",
    "fold",
    "folded_words",
    "localised_phrase",
    "speech_language_label",
    "spanish_commands_enabled",
]

#: ``(value, label)`` for the chooser, in the order it lists them.
SPEECH_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("es", "Spanish (new; commands stay in English for now)"),
)
DEFAULT_SPEECH_LANGUAGE = "en"

#: The default wake and stop phrase for each language. The Spanish pair is a
#: first draft, awaiting native-speaker review with the command table.
WAKE_PHRASES: dict[str, str] = {"en": "Quill dictate", "es": "Quill dicta"}
STOP_PHRASES: dict[str, str] = {"en": "stop dictation", "es": "deja de dictar"}

#: Set to ``1`` in a development build to try the drafted Spanish commands.
SPANISH_COMMANDS_VARIABLE = "QUILL_DICTATION_SPANISH_COMMANDS"

_WORDS = re.compile(r"[\w']+")


def coerce_speech_language(value: object) -> str:
    """The language *value* names (``"es"``, ``"es-MX"``, ``"Spanish"``), or English."""
    text = str(value or "").strip().lower().replace("_", "-")
    primary = text.split("-")[0]
    if primary in {"es", "spa", "spanish", "espanol", "español"}:
        return "es"
    return DEFAULT_SPEECH_LANGUAGE


def speech_language_label(language: str) -> str:
    return dict(SPEECH_LANGUAGES)[coerce_speech_language(language)]


def fold(text: str) -> str:
    """*text* in lower case with its accents taken off: "Línea" -> "linea".

    For matching only -- what is written keeps every accent the recogniser gave
    it. "ñ" becomes "n" here too, which costs nothing because no two entries in
    either table differ by a tilde alone.
    """
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def folded_words(text: str) -> list[str]:
    """*text*'s words, folded, with punctuation (including "¿" and "¡") dropped."""
    return _WORDS.findall(fold(text).replace("_", " "))


def localised_phrase(saved: str, language: str, defaults: dict[str, str]) -> str:
    """The wake or stop phrase to listen for in *language*.

    A phrase the user typed is theirs, in any language, and is kept. One that is
    empty, or is still *some* language's default, follows the dictation
    language -- so switching to Spanish turns "Quill dictate" into "Quill dicta"
    without anybody retyping it, and switching back undoes it.
    """
    language = coerce_speech_language(language)
    text = " ".join(str(saved or "").split())
    if not text or folded_words(text) in [folded_words(d) for d in defaults.values()]:
        return defaults.get(language, defaults[DEFAULT_SPEECH_LANGUAGE])
    return text


def spanish_commands_enabled() -> bool:
    """Whether the drafted Spanish command table is switched on. Off in releases.

    The first release is Spanish text with English commands (dict.md 9.8). The
    table is reachable only in a development build (``QUILL_DEV_BUILD=1``) with
    :data:`SPANISH_COMMANDS_VARIABLE` set to ``1``, so a tester can try it
    before a native speaker has checked it -- and nobody else meets it.
    """
    from quill.core import paths

    if not getattr(paths, "_DEV_BUILD", False):
        return False
    return os.environ.get(SPANISH_COMMANDS_VARIABLE, "").strip() == "1"
