"""What a right-click on a misspelled word should offer, worked out without wx.

A context menu is the one place a spell checker is genuinely *convenient*: the
word is already under the pointer or the caret, and everything worth doing about
it -- replace it, teach it, ignore it, go to the next one -- is one press away
without a dialog opening or the caret moving. Every editor on Windows has done
this since Word 97, and it is the shape a sighted user reaches for first.

For a screen-reader user it is not a convenience, it is the *only* affordance in
the app that is anchored to a specific word. A red squiggle says "this one" for
free; a listener has no squiggles. So the Applications key becomes the squiggle:
press it and the first thing the menu says is the suggestion, by name, for the
word the caret is in.

Three decisions are written down here rather than in either app's menu builder,
because both apps have to make them the same way:

**Suggestions go at the top level, not in a submenu.** Word puts them there and
so does Notepad, and the reason is the same one that makes this module exist:
the whole value of the menu is that the first Down arrow lands on the answer. A
"Spelling Suggestions" submenu costs a Right arrow and a wait before anything is
said, which is most of what the menu was saving.

**Ignore is two things and both are needed.** *Ignore Once* is "not this one",
and it has to survive editing elsewhere in the document, so it is anchored to
the word *and* the offset and is dropped the moment the text at that offset is
something else -- self-cleaning rather than shifted, because a shifting offset
is a whole undo stack's worth of bookkeeping for a suppression somebody expects
to be temporary. *Ignore in This Document* is "not this word, not today", which
is the honest halfway house between fixing a name and teaching it to the
dictionary forever. Neither is written to disk: an ignore that outlived the
session would be a dictionary nobody could find to edit.

**Teaching a word says where it went.** There are two dictionaries in play (a
personal one and the document's own sidecar) and "added to dictionary" does not
say which -- so the actions name their scope and the caller announces it.

wx-free, and every decision above is a pure function of text, caret and
dictionary, so the whole menu can be asserted without a display.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from quill.core.spellcheck import Misspelling, misspelling_at_position, suggest_words

__all__ = [
    "MAX_CONTEXT_SUGGESTIONS",
    "IgnoreList",
    "SpellingContext",
    "spelling_context",
]

#: The most suggestions offered on the menu itself. Past this the list stops
#: being one somebody arrows through and starts being one they get lost in --
#: and the full list is one press further on, in the Suggestions window, which
#: is a control built for arrowing rather than a menu that closes if you sneeze.
MAX_CONTEXT_SUGGESTIONS = 8


@dataclass(slots=True)
class IgnoreList:
    """The words and places this document is not to complain about, this session.

    In memory and nowhere else, deliberately. A user who ignores a colleague's
    surname in one document has said something about *this afternoon*, not about
    every document they will ever open, and an ignore that quietly persisted
    would be a dictionary entry they never chose and could not find to remove.
    Teaching a word is the durable answer and it has its own menu item.

    ``once`` is anchored to both the word and the offset it was ignored at, and
    :meth:`skips` drops an anchor whose text no longer matches. That is what
    makes it survive an edit somewhere else in the document without any
    position bookkeeping: an offset that still spells the ignored word is the
    same occurrence for every purpose a reader cares about, and one that does
    not is somebody else's problem now.
    """

    words: set[str] = field(default_factory=set)
    once: set[tuple[int, str]] = field(default_factory=set)

    def ignore_word(self, word: str) -> None:
        """Stop reporting *word* anywhere in this document for this session."""
        self.words.add(word.casefold())

    def ignore_once(self, item: Misspelling) -> None:
        """Stop reporting this one occurrence, at this one place."""
        self.once.add((item.start, item.word.casefold()))

    def clear(self) -> None:
        self.words.clear()
        self.once.clear()

    def skips(self, text: str, item: Misspelling) -> bool:
        """Should *item* be passed over? Prunes anchors the text has outgrown."""
        if item.word.casefold() in self.words:
            return True
        anchor = (item.start, item.word.casefold())
        if anchor not in self.once:
            return False
        if text[item.start : item.end].casefold() == item.word.casefold():
            return True
        self.once.discard(anchor)
        return False

    def survivors(self, text: str, items: Sequence[Misspelling]) -> list[Misspelling]:
        """*items* with the ignored ones removed, in order."""
        return [item for item in items if not self.skips(text, item)]


@dataclass(frozen=True, slots=True)
class SpellingContext:
    """The misspelling a context menu is about, and what to offer for it."""

    item: Misspelling
    suggestions: tuple[str, ...]

    @property
    def word(self) -> str:
        return self.item.word

    @property
    def start(self) -> int:
        return self.item.start

    @property
    def end(self) -> int:
        return self.item.end


def spelling_context(
    text: str,
    position: int,
    dictionary: set[str],
    ignores: IgnoreList | None = None,
    *,
    limit: int = MAX_CONTEXT_SUGGESTIONS,
) -> SpellingContext | None:
    """The misspelling at *position*, with its suggestions, or None.

    None means "there is nothing spelling-shaped here", and the caller's answer
    to that is a menu without a spelling section rather than an empty one: a
    disabled row saying "no misspelling" is a row every right-click in a clean
    document makes somebody arrow past.

    An ignored word is not a misspelling for this purpose either. Offering
    "Ignore in This Document" for a word already ignored would be a menu item
    that does nothing, which is worse than one that is not there.
    """
    item = _word_at_or_before(text, position, dictionary)
    if item is None:
        return None
    if ignores is not None and ignores.skips(text, item):
        return None
    return SpellingContext(
        item=item, suggestions=tuple(suggest_words(item.word, dictionary, limit))
    )


def _word_at_or_before(text: str, position: int, dictionary: set[str]) -> Misspelling | None:
    """The misspelled word the caret is in, counting the caret just past its end.

    ``misspelling_at_position``, never ``misspelling_at``: the latter is the
    as-you-type helper and matches only a word beginning *exactly* at the caret,
    which is where the caret sits for the fraction of a second after a space and
    nowhere else. A context menu is opened with the caret in the middle of a
    word.

    The one-character fallback is for the other end. ``misspelling_at_position``
    treats the caret immediately after the last letter as *outside* the word --
    correct for "which word am I on" in a document, wrong here, because that is
    exactly where the caret is when somebody finishes typing a word and reaches
    for the Applications key. It cannot invent a hit: if the character before
    the caret belongs to a correctly spelled word, the retry answers None just
    as the first attempt did.
    """
    found = misspelling_at_position(text, position, dictionary)
    if found is not None or position <= 0:
        return found
    return misspelling_at_position(text, position - 1, dictionary)
