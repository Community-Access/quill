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

from quill.core.windows_dictation.composer import compose
from quill.core.windows_dictation.controller import (
    DictationController,
    DictationPreferences,
    DictationState,
    Moment,
)
from quill.core.windows_dictation.history import DictatedPhrase, PhraseHistory
from quill.core.windows_dictation.parser import (
    ParsedPhrase,
    RecognizedPhrase,
    RecognizedWord,
    parse,
    words_from_text,
)
from quill.core.windows_dictation.vocabulary import Command

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
