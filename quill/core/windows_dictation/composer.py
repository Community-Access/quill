"""The exact text one phrase inserts, given the text around the caret.

Every phrase is joined to what is already there, and the joins are where
dictation usually goes wrong: ``Sentence one.Sentence two.``, a space before a
comma, a stray space at the start of a line, a lower-case letter after a full
stop. The rules here are deliberately few and deliberately conservative:

* A word takes one space before it, unless it starts the document or a line,
  follows whitespace, or follows something that hugs the next word (an opening
  bracket or quote, a hyphen, a tab).
* A mark sits by its :class:`~quill.core.windows_dictation.vocabulary.Glue`.
  Spaces this phrase itself put in front of a closing mark are taken back;
  spaces already in the document are **never** touched -- the user's text is
  not dictation's to tidy.
* A word takes a capital at the start of the document, after a line break, and
  after a sentence ends. Nothing is ever lowered: the recogniser's capitals are
  its knowledge of proper nouns, and a rule that lowered "Windows" mid-sentence
  would be wrong far more often than one that leaves it.
* When the caret sits against the next word, one space is added after the
  phrase so the two do not run together.

Pure and wx-free, so every rule is a unit test.
"""

from __future__ import annotations

from collections.abc import Iterable

from quill.core.windows_dictation.parser import Piece
from quill.core.windows_dictation.vocabulary import DASH_PLACEHOLDER, Glue, dash_text

__all__ = ["compose", "spoken_form"]

_SENTENCE_END = ".?!"
#: Characters that may close a sentence *after* its full stop: ``He said "no."``
_TRAILING_CLOSERS = "\"')]\u201d\u2019"
_HORIZONTAL_SPACE = " \t"


def _starts_sentence(before: str) -> bool:
    """Whether a word typed after *before* begins a sentence."""
    text = before.rstrip(" ")
    if not text:
        return True
    last = text[-1]
    if last in "\n\r":
        return True
    stripped = text.rstrip(_TRAILING_CLOSERS)
    return bool(stripped) and stripped[-1] in _SENTENCE_END


def _capitalise(word: str) -> str:
    return word[:1].upper() + word[1:] if word[:1].islower() else word


def compose(
    pieces: Iterable[Piece],
    *,
    before: str = "",
    after: str = "",
    dash: str = "em",
    close_paragraphs: bool = False,
) -> str:
    """The string to insert for *pieces* between *before* and *after*.

    *before* is the text immediately in front of the insertion point -- a
    sentence's worth is plenty -- and *after* the character or two behind it.
    With a selection, both are measured from outside it, because the selection
    is what the phrase replaces.

    *dash* is the style "dash" writes (:data:`~.vocabulary.DASH_STYLES`).
    *close_paragraphs* puts a full stop before "new paragraph" when the text in
    front ends in a word: an engine that punctuates by itself hears "new
    paragraph" as a command and so never ends the sentence before it, which left
    every paragraph but the last without its full stop.
    """
    out: list[str] = []
    # What the character in front of the next piece is, across the boundary
    # between the document and this phrase.
    previous = before[-1:] if before else ""
    capital = _starts_sentence(before)
    # True after something that hugs whatever comes next.
    attach = False
    # How many trailing characters of ``out`` are spaces *this phrase* added,
    # so a closing mark can take exactly those back and nothing else.
    own_space = 0

    def emit(text: str) -> None:
        nonlocal previous
        out.append(text)
        previous = text[-1:] if text else previous

    def take_back_space() -> None:
        nonlocal own_space, previous
        while own_space and out and out[-1] == " ":
            out.pop()
            own_space -= 1
        own_space = 0
        previous = out[-1][-1:] if out else (before[-1:] if before else "")

    def space_before() -> None:
        nonlocal own_space
        if attach or not previous or previous in _HORIZONTAL_SPACE or previous in "\r\n":
            return
        emit(" ")
        own_space = 1

    for piece in pieces:
        mark = piece.mark
        if mark is None:
            if not piece.text:
                continue
            space_before()
            emit(_capitalise(piece.text) if capital and not piece.verbatim else piece.text)
            own_space = 0
            capital = False
            attach = False
            continue
        text = dash_text(dash) if mark.text == DASH_PLACEHOLDER else mark.text
        if mark.glue is Glue.WORD:
            space_before()
            emit(text)
            own_space = 0
            attach = False
            continue
        if mark.glue is Glue.LEFT:
            take_back_space()
            emit(text)
            attach = False
        elif mark.glue is Glue.OPEN:
            space_before()
            emit(text)
            own_space = 0
            attach = True
        elif mark.glue is Glue.JOIN:
            # A spaced dash brings its own spaces, so any this phrase added go
            # first and nothing more is added after it.
            take_back_space()
            emit(text)
            attach = not text.endswith(" ")
        else:  # Glue.BREAK
            take_back_space()
            if close_paragraphs and text == "\n\n" and previous.isalnum():
                emit(".")
            emit(text)
            attach = True
        if mark.ends_sentence:
            capital = True

    text = "".join(out)
    if (
        text
        and not attach
        and text[-1] not in " \t\r\n"
        and after[:1]
        and (after[:1].isalnum() or after[:1] in '("[')
    ):
        text += " "
    return text


def spoken_form(pieces: Iterable[Piece], inserted: str) -> str:
    """What the read-back says for a phrase that inserted *inserted*.

    The text itself, when it has any words. A phrase that was only a line break
    or a tab inserts nothing a voice can say, and silence would be
    indistinguishable from nothing having happened -- so it says the name of
    what it did instead.
    """
    words = " ".join(inserted.split())
    if any(character.isalnum() for character in words):
        return words
    names = [piece.mark.spoken or piece.text for piece in pieces if piece.mark is not None]
    names = [name for name in names if name.strip()]
    if names:
        return ", ".join(names)
    return words
