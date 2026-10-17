"""Property-based tests for dictation's words file and filler removal (todo P3).

* **My Words and Phrases** (``words_file``): whatever the window can hold,
  saving and reopening gives back -- the same words, phrases and corrections,
  in the same order. A person never sees the file; a save that loses a
  replacement is a phrase that silently stops working.
* **Filler removal** (``fillers.remove_filler_words``): removing fillers from
  text that has none left changes nothing, so a phrase cleaned twice (once by
  the engine path, once by a review) reads the same as one cleaned once.
"""

from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from quill.core.speech.fillers import UNIVERSAL_FILLER_WORDS, remove_filler_words  # noqa: E402
from quill.core.windows_dictation.words_file import (  # noqa: E402
    Entry,
    WordsFile,
    parse_words,
    render_words,
)

# --------------------------------------------------------------------------- #
# My Words and Phrases
# --------------------------------------------------------------------------- #

#: One spoken word: letters from any script, digits, and the joiners names use.
_token = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Lo", "Nd"), whitelist_characters="'&.-"
    ),
    min_size=1,
    max_size=10,
)


def _is_entry_text(text: str) -> bool:
    """What the format can hold as a word or the left side of a line: not a
    heading (#), not a list mark (- * +), no "=>" separator, and -- for a word
    -- not something that reads as a sentence (looks_like_prose, by design)."""
    return not text.startswith(("#", "-", "*", "+")) and "=>" not in text


_spoken = (
    st
    .lists(_token, min_size=1, max_size=4)
    .map(" ".join)
    .filter(_is_entry_text)
    .filter(lambda text: not text.endswith((".", ":", "!", "?")))
)

#: What a phrase writes: any printable text, new lines and tabs included (the
#: file escapes them as \\n and \\t), and backslashes, which a Windows path in a
#: replacement has. Not leading or trailing spaces: the reader strips the right
#: side of "heard => written", a limit of the hand-editable format.
_written = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc"), whitelist_characters="\n\t\\"),
    min_size=1,
    max_size=40,
).filter(lambda text: text == text.strip() and text.strip("\r\n"))


@st.composite
def _words_file(draw: st.DrawFn) -> WordsFile:
    words = WordsFile()
    for spoken in draw(st.lists(_spoken, max_size=6)):
        words.add(Entry("word", spoken))
    for kind in ("phrase", "correction"):
        for spoken, written in draw(st.lists(st.tuples(_spoken, _written), max_size=6)):
            words.add(Entry(kind, spoken, written))
    return words


@given(words=_words_file())
def test_saving_and_reopening_my_words_changes_nothing(words: WordsFile) -> None:
    back = parse_words(render_words(words))
    assert back.words == words.words
    assert back.phrases == words.phrases
    assert back.corrections == words.corrections


@given(words=_words_file())
def test_rendering_is_stable(words: WordsFile) -> None:
    """A file QUILL wrote, read and written again, is byte for byte the same."""
    once = render_words(words)
    assert render_words(parse_words(once)) == once


def test_a_windows_path_in_a_replacement_survives() -> None:
    """Found by the property (2026-10-17): "\\n" inside C:\\new was read back as a
    new line, so a replacement writing a path wrote a broken one."""
    words = WordsFile()
    words.add(Entry("phrase", "my folder", "C:\\new\\temp"))
    assert parse_words(render_words(words)).phrases == [("my folder", "C:\\new\\temp")]


# --------------------------------------------------------------------------- #
# Filler removal
# --------------------------------------------------------------------------- #

_fillers = sorted(UNIVERSAL_FILLER_WORDS)
_prose_word = st.one_of(
    st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll")), min_size=1, max_size=8),
    st.sampled_from(_fillers),
    st.sampled_from([w.capitalize() for w in _fillers]),
)
_punct = st.sampled_from(["", "", "", ",", ".", "?", "!", ";"])
_sentence = st.lists(st.tuples(_prose_word, _punct), min_size=0, max_size=12).map(
    lambda pairs: " ".join(word + mark for word, mark in pairs)
)


@given(text=_sentence, language=st.sampled_from(["", "en", "en-US", "es", "pt-BR", "de"]))
def test_removing_fillers_twice_is_removing_them_once(text: str, language: str) -> None:
    once = remove_filler_words(text, language=language, enabled=True)
    assert remove_filler_words(once, language=language, enabled=True) == once


@given(text=_sentence)
def test_no_filler_survives_and_every_other_word_does(text: str) -> None:
    cleaned = remove_filler_words(text, enabled=True)
    kept = [w.strip(",.?!;").lower() for w in cleaned.split()]
    assert not set(kept) & set(_fillers)
    expected = [
        w.strip(",.?!;").lower()
        for w in text.split()
        if w.strip(",.?!;").lower() not in UNIVERSAL_FILLER_WORDS
    ]
    assert kept == expected


@given(text=_sentence)
def test_switched_off_it_changes_nothing(text: str) -> None:
    assert remove_filler_words(text, enabled=False) == text
