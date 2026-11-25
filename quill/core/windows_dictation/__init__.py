"""Windows Dictation: speak into the document, one phrase at a time.

Press the key, speak, pause, hear the phrase land, keep talking. Windows
recognises the words (the built-in SAPI recogniser, through
:mod:`quill.platform.windows.sapi_dictation`); everything about what those words
*do* to the document is decided here, in plain Python, with no speech model and
no network.

This package is the wx-free half, shared by QUILL and QUILL Lite:

* :mod:`~quill.core.windows_dictation.vocabulary` -- the spoken commands, as a
  table ("new paragraph", "comma", "scratch that", "literal ...").
* :mod:`~quill.core.windows_dictation.parser` -- recognised words into pieces
  of text and punctuation, longest command phrase first.
* :mod:`~quill.core.windows_dictation.composer` -- those pieces into the exact
  string to insert, with the spacing and capitals the text around the caret
  calls for.
* :mod:`~quill.core.windows_dictation.history` -- every inserted phrase as a
  transaction, which is what lets "scratch that" remove exactly one.
* :mod:`~quill.core.windows_dictation.controller` -- the state machine, and the
  one place the earcons and the spoken read-back are decided.

It is **not** QUILL's offline Locked Dictation (``quill.core.speech.dictation``,
Whisper, Ctrl+F9 in QUILL), and not the Win+H panel shim in
``quill.core.dictation``. Those record first and transcribe afterwards; this
inserts as you go and keeps listening.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "Command",
    "DictatedPhrase",
    "DictationController",
    "DictationPreferences",
    "DictationState",
    "Moment",
    "ParsedPhrase",
    "PhraseHistory",
    "RecognizedPhrase",
    "RecognizedWord",
    "compose",
    "parse",
    "words_from_text",
]

_EXPORTS = {
    "Command": ("quill.core.windows_dictation.vocabulary", "Command"),
    "DictatedPhrase": ("quill.core.windows_dictation.history", "DictatedPhrase"),
    "DictationController": ("quill.core.windows_dictation.controller", "DictationController"),
    "DictationPreferences": (
        "quill.core.windows_dictation.controller",
        "DictationPreferences",
    ),
    "DictationState": ("quill.core.windows_dictation.controller", "DictationState"),
    "Moment": ("quill.core.windows_dictation.controller", "Moment"),
    "ParsedPhrase": ("quill.core.windows_dictation.parser", "ParsedPhrase"),
    "PhraseHistory": ("quill.core.windows_dictation.history", "PhraseHistory"),
    "RecognizedPhrase": ("quill.core.windows_dictation.parser", "RecognizedPhrase"),
    "RecognizedWord": ("quill.core.windows_dictation.parser", "RecognizedWord"),
    "compose": ("quill.core.windows_dictation.composer", "compose"),
    "parse": ("quill.core.windows_dictation.parser", "parse"),
    "words_from_text": ("quill.core.windows_dictation.parser", "words_from_text"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(import_module(module_name), attribute)
    globals()[name] = value
    return value
