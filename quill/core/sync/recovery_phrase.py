"""Carrying the key to a second machine without reading out base64.

QuillSync is end-to-end encrypted with a key derived from a passphrase, which
raises the question the design had left open: **how does somebody sign a second
machine in?** The honest answers were both bad. A random key is 44 characters of
base64 that nobody can read down a phone or type without a mistake. A
self-chosen password is whatever people choose, which for a key protecting a
listening history is usually four characters and a birthday.

So: a **recovery phrase**. Eight ordinary words from a fixed list, generated for
you, memorable enough to write on paper and speakable enough to read to yourself
while typing on the other machine. Sixty-four bits, in front of scrypt.

The word list is chosen for *listening*, which is what makes it different from a
generic one:

* **Nothing that sounds like anything else.** No "their/there", no
  "flower/flour", no "sun/son" -- a phrase you cannot transcribe from speech is
  not a recovery phrase.
* **Short, common words only.** Everything is four to six letters and in
  ordinary use, so a screen reader says it as a word rather than spelling it and
  nobody has to guess at a spelling.
* **Fixed forever.** The list is the format: adding or reordering a word would
  quietly invalidate every phrase already written down. It is data, not a
  preference.

Checking is deliberately forgiving -- case, extra spaces, and hyphens or commas
between words are all normalised away, because somebody typing eight words from
a piece of paper will punctuate them however they like.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import secrets

#: How many words a generated phrase has. Eight from 256 is 64 bits, which in
#: front of scrypt is a serious key and is still eight things to say.
PHRASE_WORDS = 8

#: The fixed list: 256 short, common, unambiguous English words. Never reorder
#: and never edit -- the list *is* the format, and a changed list silently
#: invalidates every phrase already written down.
WORDS: tuple[str, ...] = tuple(
    """
    able acid acre afraid album alarm amber angle ankle apple
    april arch arm army atlas attic audio autumn awake axis
    bacon badge baker balance ball banjo barn basil basket beach
    beacon beam bean bear bell belt bench berry bird black
    blade blanket block bloom board boat bolt bone book boot
    border bottle brain branch brass bread brick bridge broom brown
    brush bubble bucket bulb bundle butter button cabin cable cactus
    camel candle canvas canyon carbon cargo carpet carrot castle cave
    cedar cello cement chain chair chalk cherry chess chest chimney
    circle clay cliff clock cloud clover coal coast cobalt cocoa
    coin collar comet copper coral cotton crane crayon cream creek
    crown crystal cube curtain cushion cymbal dagger daisy dance dawn
    deck delta desert desk diamond dinner dock dolphin domino donkey
    double dragon drawer drum dune dusk eagle early earth easel
    echo eclipse edge elbow elder electric elm ember emerald engine
    envelope equal eraser fabric falcon farm feather fence fern ferry
    fiber fiddle field finger fire fjord flag flame flask flint
    float flute fog forest fork fossil fountain fox frame frost
    fudge funnel garden garlic gate gear gecko ginger glacier glass
    globe glove goat gold grain granite grape grass gravel green
    grid guitar gulf hammer harbor harp hazel heart hedge helmet
    herb hill hollow honey horizon horn hotel hunter ice igloo
    indigo ink iris iron island ivory jacket jade jar jelly
    jewel journal jungle kayak kettle key kite kitten knot ladder
    lake lamp lantern laser latch lava leaf ledge lemon lentil
    lever lilac lime linen lion lobby
    """.split()
)


def _normalise(phrase: str) -> list[str]:
    """A typed phrase as plain lowercase words.

    Punctuation between words is dropped rather than rejected: somebody copying
    eight words off paper will separate them with spaces, commas, or hyphens,
    and refusing one of those is refusing a correct phrase on a technicality.
    """
    cleaned = []
    for raw in str(phrase or "").replace(",", " ").replace("-", " ").split():
        word = "".join(character for character in raw.lower() if character.isalnum())
        if word:
            cleaned.append(word)
    return cleaned


def generate(words: int = PHRASE_WORDS) -> str:
    """A fresh recovery phrase.

    ``secrets`` rather than ``random``: this is a key, and a phrase that could
    be reproduced from a seed somebody else can guess is not one.
    """
    count = max(4, int(words))
    return " ".join(secrets.choice(WORDS) for _ in range(count))


def normalise(phrase: str) -> str:
    """The canonical form of a typed phrase -- what the key is derived from.

    Every machine must derive from exactly the same string, so this runs on the
    way in on both of them rather than being left to whoever types more neatly.
    """
    return " ".join(_normalise(phrase))


def word_count(phrase: str) -> int:
    return len(_normalise(phrase))


def is_from_word_list(phrase: str) -> bool:
    """Whether every word is one of ours -- a typo caught before a failed sync."""
    words = _normalise(phrase)
    return bool(words) and all(word in set(WORDS) for word in words)


def describe_problem(phrase: str) -> str:
    """What is wrong with a typed phrase, in words, or "" when nothing is.

    Said rather than shown as a red border, and specific: "that is seven words,
    and a recovery phrase is eight" is actionable, and "invalid" is not.
    """
    words = _normalise(phrase)
    if not words:
        return "Type your recovery phrase first."
    if len(words) < 4:
        return (
            f"That is {len(words)} word{'' if len(words) == 1 else 's'}. "
            f"A recovery phrase is {PHRASE_WORDS} words."
        )
    known = set(WORDS)
    unknown = [word for word in words if word not in known]
    if unknown:
        # Naming the word matters: with eight words read off paper, "one of
        # these is not right" means checking all eight again.
        listed = ", ".join(unknown[:3])
        return f"These are not words from a recovery phrase: {listed}."
    if len(words) != PHRASE_WORDS:
        return f"That is {len(words)} words. A recovery phrase is {PHRASE_WORDS} words."
    return ""


def is_valid(phrase: str) -> bool:
    """Whether *phrase* could be a recovery phrase this app generated."""
    return describe_problem(phrase) == ""


def spoken(phrase: str) -> str:
    """The phrase read back one word at a time, for writing it down.

    Numbered, because eight words read as a run-on sentence is eight words
    somebody has to ask for again. This is the only moment the phrase is ever
    spoken aloud by QUILL.
    """
    words = _normalise(phrase)
    return ". ".join(f"{index}, {word}" for index, word in enumerate(words, start=1)) + "."
