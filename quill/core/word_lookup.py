"""The word under the caret, its replacements, and the shape they must take.

Shared by QUILL and QUILL Lite (wx-free, strict-typed). The thesaurus file is
a list of *headwords* -- "run", not "running"; "happy", not "happier" -- so a
lookup of the word somebody is actually on fails for most words in running
prose, and a replacement offered as "sprint" for "running" is a replacement
nobody can use without retyping it. This module closes both gaps:

* :func:`lemma_candidates` walks a word back to the forms the thesaurus knows
  (running -> run, studies -> study, happier -> happy, stopped -> stop), and
  remembers *how* it walked;
* :func:`inflect` walks each synonym forward the same way (sprint ->
  sprinting), and :func:`match_case` gives it the original's capitals;
* :func:`thesaurus_choices` puts the two together: the senses of the word you
  are on, each with replacements ready to drop in, opposites kept apart.

English inflection is irregular and this is a handful of rules, not a
morphology engine. Two things keep that honest: a lemma is only accepted when
the thesaurus actually has it, so a wrong walk-back finds nothing rather than
something wrong; and a replacement whose inflection the rules cannot vouch for
(a multi-word phrase on a noun, an irregular verb) is offered in its headword
form rather than invented.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from quill.core import thesaurus

# -- finding the word ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WordSpan:
    """A word in the document: its text and where it sits."""

    word: str
    start: int
    end: int


_WORD = re.compile(r"^[^\W\d_]+(?:['’-][^\W\d_]+)*$")


def is_single_word(text: str) -> bool:
    """Letters, with inner apostrophes or hyphens only: "don't", "well-known"."""
    return bool(_WORD.match(text.strip()))


def find_word(text: str, caret: int, selection: tuple[int, int] | None = None) -> WordSpan | None:
    """The word to look up: the selection when it is one word, else the caret's.

    A selection wins because it is the most explicit thing a person can say;
    it is only refused when it is not a word (a sentence, a number), and then
    the caret's word is used instead of nothing.
    """
    if selection is not None:
        start, end = sorted(selection)
        chosen = text[start:end]
        if start != end and is_single_word(chosen):
            lead = len(chosen) - len(chosen.lstrip())
            stripped = chosen.strip()
            return WordSpan(stripped, start + lead, start + lead + len(stripped))
    found = thesaurus.word_at(text, caret)
    if found is None:
        return None
    word, start, end = found
    # Trim a leading or trailing apostrophe -- a closing quote is not part of
    # the word, and "'tis" is rare enough to lose.
    while word and word[0] in "'’":
        word, start = word[1:], start + 1
    while word and word[-1] in "'’":
        word, end = word[:-1], end - 1
    return WordSpan(word, start, end) if word else None


def sentence_around(text: str, start: int, end: int, *, limit: int = 400) -> str:
    """The sentence holding ``text[start:end]``, trimmed to *limit* characters.

    The context an AI word tool needs -- "bank" by a river and "bank" with a
    loan are different words -- and nothing more: the rest of the document
    stays on this computer.
    """
    left = max(text.rfind(mark, 0, start) for mark in (".", "!", "?", "\n"))
    right_candidates = [i for i in (text.find(m, end) for m in (".", "!", "?", "\n")) if i != -1]
    right = min(right_candidates) + 1 if right_candidates else len(text)
    sentence = text[left + 1 : right].strip()
    if len(sentence) <= limit:
        return sentence
    middle = start - (left + 1)
    lo = max(0, middle - limit // 2)
    return sentence[lo : lo + limit].strip()


# -- capitals ------------------------------------------------------------------------


def match_case(original: str, replacement: str) -> str:
    """*replacement* with *original*'s capitalisation: ALL CAPS, Title or lower."""
    if not original or not replacement:
        return replacement
    letters = [c for c in original if c.isalpha()]
    if len(letters) > 1 and all(c.isupper() for c in letters):
        return replacement.upper()
    if original[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement


# -- inflection ------------------------------------------------------------------------

#: How a word was walked back to its headword, so a synonym can walk forward.
PLAIN = ""
PLURAL = "plural"  # cats -> cat, boxes -> box, studies -> study
THIRD = "third"  # runs -> run (same spelling rules as PLURAL)
ING = "ing"  # running -> run, making -> make
PAST = "past"  # stopped -> stop, baked -> bake, carried -> carry
COMPARATIVE = "er"  # happier -> happy, bigger -> big
SUPERLATIVE = "est"  # happiest -> happy

_VOWELS = "aeiou"


def _undouble(stem: str) -> list[str]:
    if len(stem) >= 3 and stem[-1] == stem[-2] and stem[-1] not in _VOWELS + "lsz":
        return [stem[:-1], stem]
    return [stem]


#: Common irregular verbs: headword -> simple past. Enough for the verbs a
#: thesaurus actually offers ("give up" -> "gave up", "seek" -> "sought"), and
#: the reverse walk ("ran" -> "run") reads the same table.
_IRREGULAR_PAST: dict[str, str] = dict(
    pair.split(":")
    for pair in (
        "arise:arose awake:awoke be:was bear:bore beat:beat become:became begin:began "
        "behold:beheld bend:bent bet:bet bid:bid bind:bound bite:bit bleed:bled blow:blew "
        "break:broke breed:bred bring:brought broadcast:broadcast build:built burst:burst "
        "buy:bought cast:cast catch:caught choose:chose cling:clung come:came cost:cost "
        "creep:crept cut:cut deal:dealt dig:dug do:did draw:drew drink:drank drive:drove "
        "eat:ate fall:fell feed:fed feel:felt fight:fought find:found flee:fled fling:flung "
        "fly:flew forbid:forbade forecast:forecast foresee:foresaw forget:forgot "
        "forgive:forgave forsake:forsook freeze:froze get:got give:gave go:went grind:ground "
        "grow:grew hang:hung have:had hear:heard hide:hid hit:hit hold:held hurt:hurt "
        "keep:kept kneel:knelt know:knew lay:laid lead:led leap:leapt leave:left lend:lent "
        "let:let light:lit lose:lost make:made mean:meant meet:met mislead:misled "
        "outdo:outdid overcome:overcame overtake:overtook pay:paid put:put quit:quit "
        "read:read rid:rid ride:rode ring:rang rise:rose run:ran say:said see:saw seek:sought "
        "sell:sold send:sent set:set shake:shook shed:shed shine:shone shoot:shot shrink:shrank "
        "shut:shut sing:sang sink:sank sit:sat slay:slew sleep:slept slide:slid sling:slung "
        "slit:slit speak:spoke speed:sped spend:spent spin:spun split:split spread:spread "
        "spring:sprang stand:stood steal:stole stick:stuck sting:stung stride:strode "
        "strike:struck strive:strove swear:swore sweep:swept swim:swam swing:swung "
        "take:took teach:taught tear:tore tell:told think:thought throw:threw thrust:thrust "
        "tread:trod undergo:underwent understand:understood undertake:undertook "
        "uphold:upheld upset:upset wake:woke wear:wore weave:wove weep:wept win:won "
        "wind:wound withdraw:withdrew withhold:withheld wring:wrung write:wrote"
    ).split()
)
#: Past form -> headword, for the walk back. A form shared by two verbs
#: ("found", "lay") keeps the first; the thesaurus check decides the rest.
_IRREGULAR_BASE: dict[str, str] = {}
for _base, _past in _IRREGULAR_PAST.items():
    _IRREGULAR_BASE.setdefault(_past, _base)
#: Third person singular forms the -s rule gets wrong.
_IRREGULAR_THIRD = {"be": "is", "have": "has", "do": "does", "go": "goes"}


def lemma_candidates(word: str) -> list[tuple[str, str]]:
    """``(headword, how)`` guesses for *word*, the word itself first."""
    w = word.lower()
    found: list[tuple[str, str]] = [(w, PLAIN)]

    def add(stem: str, how: str) -> None:
        if len(stem) >= 2 and (stem, how) not in found:
            found.append((stem, how))

    if w.endswith("ies") and len(w) > 4:
        add(w[:-3] + "y", PLURAL)
    if w.endswith("es") and len(w) > 3:
        add(w[:-2], PLURAL)
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        add(w[:-1], PLURAL)
    if w in _IRREGULAR_BASE:
        add(_IRREGULAR_BASE[w], PAST)
    if w.endswith("ying") and len(w) > 4:
        add(w[:-4] + "ie", ING)  # lying -> lie, dying -> die
    if w.endswith("ing") and len(w) > 5:
        stem = w[:-3]
        for candidate in _undouble(stem):
            add(candidate, ING)
        add(stem + "e", ING)
    if w.endswith("ied") and len(w) > 4:
        add(w[:-3] + "y", PAST)
    if w.endswith("ed") and len(w) > 4:
        stem = w[:-2]
        for candidate in _undouble(stem):
            add(candidate, PAST)
        add(w[:-1], PAST)  # baked -> bake
    if w.endswith("iest") and len(w) > 5:
        add(w[:-4] + "y", SUPERLATIVE)
    elif w.endswith("est") and len(w) > 5:
        for candidate in _undouble(w[:-3]):
            add(candidate, SUPERLATIVE)
        add(w[:-2], SUPERLATIVE)  # widest -> wide
    if w.endswith("ier") and len(w) > 4:
        add(w[:-3] + "y", COMPARATIVE)
    elif w.endswith("er") and len(w) > 4:
        for candidate in _undouble(w[:-2]):
            add(candidate, COMPARATIVE)
        add(w[:-1], COMPARATIVE)  # wider -> wide
    return found


def _ends_consonant_vowel_consonant(word: str) -> bool:
    return (
        len(word) >= 3
        and word[-1] not in _VOWELS + "wxy"
        and word[-2] in _VOWELS
        and word[-3] not in _VOWELS
        and len(re.findall(f"[{_VOWELS}]+", word)) == 1  # one syllable: stop, not visit
    )


def _inflect_word(word: str, how: str) -> str:
    w = word
    if how == PAST and w in _IRREGULAR_PAST:
        return _IRREGULAR_PAST[w]
    if how == THIRD and w in _IRREGULAR_THIRD:
        return _IRREGULAR_THIRD[w]
    if how in (PLURAL, THIRD):
        if w.endswith("y") and len(w) > 1 and w[-2] not in _VOWELS:
            return w[:-1] + "ies"
        if w.endswith(("s", "x", "z", "ch", "sh")):
            return w + "es"
        return w + "s"
    if how == ING:
        if w.endswith("ie"):
            return w[:-2] + "ying"
        if w.endswith("e") and not w.endswith(("ee", "ye", "oe")):
            return w[:-1] + "ing"
        if _ends_consonant_vowel_consonant(w):
            return w + w[-1] + "ing"
        return w + "ing"
    if how == PAST:
        if w.endswith("e"):
            return w + "d"
        if w.endswith("y") and len(w) > 1 and w[-2] not in _VOWELS:
            return w[:-1] + "ied"
        if _ends_consonant_vowel_consonant(w):
            return w + w[-1] + "ed"
        return w + "ed"
    if how in (COMPARATIVE, SUPERLATIVE):
        suffix = "er" if how == COMPARATIVE else "est"
        # Only short adjectives take -er/-est: one syllable ("big", "large"),
        # or two ending in y ("happy"). Everything else is "more"/"most" --
        # "more blessed", never "blesseder".
        syllables = len(re.findall(f"[{_VOWELS}y]+", w[:-1] if w.endswith("e") else w))
        if not (syllables <= 1 or (syllables == 2 and w.endswith("y"))):
            return ("more " if how == COMPARATIVE else "most ") + w
        if w.endswith("y") and len(w) > 1 and w[-2] not in _VOWELS:
            return w[:-1] + "i" + suffix
        if w.endswith("e"):
            return w + suffix[1:]
        if _ends_consonant_vowel_consonant(w):
            return w + w[-1] + suffix
        return w + suffix
    return w


def inflect(term: str, how: str, part_of_speech: str = "") -> str:
    """*term* (a headword or phrase) put into the form *how* names.

    Verbs inflect their first word ("run away" -> "running away"); nouns and
    adjectives their last ("ice cream" -> "ice creams"). A phrase whose head is
    not where the rule expects is left in its headword form rather than mangled.
    """
    if how == PLAIN or not term:
        return term
    words = term.split()
    if len(words) == 1:
        return _inflect_word(term, how)
    if how in (ING, PAST, THIRD) or (how == PLURAL and part_of_speech == "verb"):
        return " ".join([_inflect_word(words[0], how), *words[1:]])
    if how == PLURAL:
        return " ".join([*words[:-1], _inflect_word(words[-1], how)])
    return term  # comparatives of phrases: leave them be


# -- the thesaurus, ready to use ------------------------------------------------------

#: Senses shown and replacements per sense in a context menu: enough to choose
#: from by ear, few enough that a submenu is not a wall.
MENU_SENSES = 5
MENU_TERMS = 8


@dataclass(frozen=True, slots=True)
class Sense:
    """One meaning: how it is introduced, and replacements ready to insert."""

    label: str
    part_of_speech: str
    replacements: tuple[str, ...]
    headwords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WordChoices:
    """What the thesaurus offers for one word in one place."""

    word: str
    headword: str
    how: str
    senses: tuple[Sense, ...]
    opposites: tuple[str, ...]

    @property
    def all_replacements(self) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for sense in self.senses:
            for term in sense.replacements:
                if term.lower() not in seen:
                    seen.add(term.lower())
                    ordered.append(term)
        return tuple(ordered)

    def summary(self) -> str:
        """One sentence: what was looked up, and how much there is."""
        senses = len(self.senses)
        meaning = "meaning" if senses == 1 else "meanings"
        via = f", looked up as {self.headword}" if self.headword != self.word.lower() else ""
        return f"{self.word}{via}: {senses} {meaning}, {len(self.all_replacements)} replacements."


_POS_WORDS = {"adj": "adjective", "adv": "adverb", "noun": "noun", "verb": "verb"}
#: Which parts of speech each walk-back can belong to -- "running" as a noun
#: is not "run" as a noun.
_HOW_POS = {
    PLAIN: None,
    PLURAL: {"noun", "verb"},
    THIRD: {"verb"},
    ING: {"verb"},
    PAST: {"verb"},
    COMPARATIVE: {"adj", "adv"},
    SUPERLATIVE: {"adj", "adv"},
}


def thesaurus_choices(
    word: str,
    *,
    lookup: Callable[[str], thesaurus.ThesaurusEntry | None] = thesaurus.lookup,
    senses: int = MENU_SENSES,
    terms: int = MENU_TERMS,
) -> WordChoices | None:
    """The thesaurus's answer for *word* as it is written, or ``None``.

    The walked-back headwords come **first** and the word itself last:
    "running" is a headword too (an adjective, a noun), but somebody on the
    word "running" in a sentence nearly always means the verb, and the verb's
    senses are only reachable through "run". Each walk-back keeps only senses
    of a part of speech that form can have -- "running" is never "run" as a
    noun. Senses already offered are not offered twice.
    """
    clean = word.strip()
    if not clean:
        return None
    candidates = lemma_candidates(clean)
    ordered = candidates[1:] + candidates[:1]
    kept: list[Sense] = []
    opposites: list[str] = []
    seen_heads: set[tuple[str, ...]] = set()
    first: tuple[str, str] | None = None
    for headword, how in ordered:
        if len(kept) >= senses:
            break
        entry = lookup(headword)
        if entry is None:
            continue
        allowed = _HOW_POS.get(how)
        for meaning in entry.meanings:
            pos = meaning.part_of_speech.strip("() ").lower()
            if allowed is not None and pos not in allowed:
                continue
            heads = tuple(t for t in meaning.synonyms if t.lower() != headword)[:terms]
            if not heads or heads in seen_heads:
                continue
            seen_heads.add(heads)
            if first is None:
                first = (headword, how)
            ready = tuple(match_case(clean, inflect(t, how, pos)) for t in heads)
            pos_word = _POS_WORDS.get(pos, pos or "word")
            article = "an" if pos_word[0] in "aeiou" else "a"
            kept.append(Sense(f"As {article} {pos_word}: {heads[0]}", pos_word, ready, heads))
            for opposite in meaning.antonyms:
                shaped = match_case(clean, inflect(opposite, how, pos))
                if shaped.lower() not in {o.lower() for o in opposites}:
                    opposites.append(shaped)
            if len(kept) >= senses:
                break
    if not kept or first is None:
        return None
    return WordChoices(clean, first[0], first[1], tuple(kept), tuple(opposites[:terms]))


# -- the thesaurus picker, by headword -------------------------------------------------

#: Terms previewed in a sense's row, as the existing picker does.
_PREVIEW_TERMS = 4


def picker_senses(
    word: str,
    *,
    lookup: Callable[[str], thesaurus.ThesaurusEntry | None] = thesaurus.lookup,
) -> tuple[str, str, tuple[thesaurus.SenseRow, ...]]:
    """Every sense for *word*, shaped for the two-pane picker, replacements inflected.

    ``(headword, how, senses)``. The picker (``quill.ui.thesaurus_dialog``)
    takes :class:`~quill.core.thesaurus.SenseRow` values; this builds them the
    way :func:`quill.core.thesaurus.sense_rows` does -- antonym-only senses
    dropped, the part of speech leading the row, broader terms and opposites
    labelled -- but over the **walked-back headwords first** and with every
    term already in the form the document needs, so choosing "sprint" for
    "running" inserts "sprinting". A sense reached through a headword says so
    in its row ("verb, from run: ..."), because the listener typed one word and
    is being offered another's senses. Empty when nothing is known.
    """
    clean = word.strip()
    if not clean:
        return clean, PLAIN, ()
    candidates = lemma_candidates(clean)
    ordered = candidates[1:] + candidates[:1]
    senses: list[thesaurus.SenseRow] = []
    seen: set[tuple[str, ...]] = set()
    first: tuple[str, str] | None = None
    for headword, how in ordered:
        entry = lookup(headword)
        if entry is None:
            continue
        allowed = _HOW_POS.get(how)
        for meaning in entry.meanings:
            if not meaning.synonyms and not meaning.broader:
                continue
            pos = meaning.part_of_speech.strip("() ").lower()
            if allowed is not None and pos not in allowed:
                continue
            key = tuple(t.lower() for t in meaning.synonyms[:_PREVIEW_TERMS]) + (pos,)
            if key in seen:
                continue
            seen.add(key)
            if first is None:
                first = (headword, how)

            def shape(term: str, how: str = how, pos: str = pos) -> str:
                return match_case(clean, inflect(term, how, pos))

            pos_word = _POS_WORDS.get(pos, pos or "other")
            preview_from = [shape(t) for t in (meaning.synonyms or meaning.broader)]
            qualifier = "" if meaning.synonyms else " (broader)"
            via = f", from {headword}" if how != PLAIN else ""
            shown = preview_from[:_PREVIEW_TERMS]
            remaining = len(preview_from) - len(shown)
            if remaining > 0:
                shown.append(f"{remaining} more")
            rows: list[tuple[str, str]] = [(shape(t), shape(t)) for t in meaning.synonyms]
            rows.extend((f"broader: {shape(t)}", shape(t)) for t in meaning.broader)
            rows.extend((f"opposite: {shape(t)}", shape(t)) for t in meaning.antonyms)
            senses.append(
                thesaurus.SenseRow(
                    label=f"{pos_word}{qualifier}{via}: {', '.join(shown)}",
                    part_of_speech=pos_word,
                    rows=tuple(rows),
                )
            )
    if first is None:
        return clean, PLAIN, ()
    return first[0], first[1], tuple(senses)


def word_summary(
    word: str, *, lookup: Callable[[str], thesaurus.ThesaurusEntry | None] = thesaurus.lookup
) -> str:
    """One spoken paragraph: what the thesaurus knows about *word*, by part of speech.

    For a listener who wants the shape of the entry before opening it: which
    headword it was looked up as, how many meanings each part of speech has,
    the first few replacements of the first sense, and the opposites. Offline.
    """
    choices = thesaurus_choices(word, lookup=lookup, senses=50, terms=MENU_TERMS)
    if choices is None:
        return f"The thesaurus has no entry for {word.strip()}."
    by_pos: dict[str, int] = {}
    for sense in choices.senses:
        by_pos[sense.part_of_speech] = by_pos.get(sense.part_of_speech, 0) + 1
    parts = ", ".join(
        f"{count} meaning{'s' if count != 1 else ''} as {'an' if pos[0] in 'aeiou' else 'a'} {pos}"
        for pos, count in by_pos.items()
    )
    via = f", looked up as {choices.headword}" if choices.headword != choices.word.lower() else ""
    first = ", ".join(choices.senses[0].replacements[:5])
    text = f"{choices.word}{via}: {parts}. First: {first}."
    if choices.opposites:
        text += " Opposites: " + ", ".join(choices.opposites[:5]) + "."
    return text


__all__ = [
    "COMPARATIVE",
    "ING",
    "MENU_SENSES",
    "MENU_TERMS",
    "PAST",
    "PLAIN",
    "PLURAL",
    "SUPERLATIVE",
    "THIRD",
    "Sense",
    "WordChoices",
    "WordSpan",
    "find_word",
    "inflect",
    "is_single_word",
    "lemma_candidates",
    "match_case",
    "picker_senses",
    "sentence_around",
    "thesaurus_choices",
    "word_summary",
]
