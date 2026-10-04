"""Dictated text in Spanish (and any language with accents or opening marks).

Three small bugs kept dictation English-only even before any Spanish model:
command words lost their accented letters before matching, a sentence opening
with an inverted question mark was not capitalised, and turning automatic
punctuation off left the opening marks behind.
"""

from __future__ import annotations

from quill.core.windows_dictation import RecognizedPhrase, compose, parse, words_from_text
from quill.core.windows_dictation.options import clean_phrase
from quill.core.windows_dictation.parser import _normalise

_OPEN_Q = "¿"
_OPEN_X = "¡"


def _phrase(text: str) -> RecognizedPhrase:
    return RecognizedPhrase(words_from_text(text), text=text)


def _typed(text: str, *, before: str = "") -> str:
    return compose(parse(_phrase(text)).pieces, before=before)


def test_accented_letters_survive_for_command_matching() -> None:
    assert _normalise("línea") == ["línea"]
    assert _normalise("mañana") == ["mañana"]


def test_english_words_normalise_as_before() -> None:
    assert _normalise("Don't") == ["don't"]
    assert _normalise("full-stop") == ["full", "stop"]


def test_a_sentence_opening_with_an_inverted_mark_is_capitalised() -> None:
    typed = _typed(f"{_OPEN_Q}qué tal?", before="Hola.")
    assert typed == f" {_OPEN_Q}Qué tal?"


def test_an_inverted_exclamation_is_capitalised_too() -> None:
    assert _typed(f"{_OPEN_X}vamos!", before="") == f"{_OPEN_X}Vamos!"


def test_opening_marks_go_when_automatic_punctuation_is_off() -> None:
    cleaned = clean_phrase(
        _phrase(f"{_OPEN_Q}Qué tal?"),
        remove_fillers=False,
        strip_punctuation=True,
    )
    assert " ".join(word.display for word in cleaned.words) == "Qué tal"
