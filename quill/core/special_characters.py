"""The catalogue behind Insert Special Character, shared by both editors.

Insert Special Character started as a code-point prompt: type ``2014``, get an
em dash. That is the right *escape hatch* and the wrong front door, so the list
came first (2026-09-13) -- and then the list turned out to be the wrong list,
which is what this module is really about.

The forty characters it opened with are
:data:`~quill.core.find_model.NAMED_CHARACTERS`, and they were chosen for the
**Find** dialog: whitespace, dashes, quotes, invisibles and typography, which is
exactly what you need to hunt down a bad space in a search box. What a *writer*
reaches for was not in it at all -- no accented letters, no currency, no
``(c)``, no ``+/-``, no fractions, no arrows, no Greek. Nor was any of that
reachable from the emoji picker, which carries only the emoji-presentation forms
(``(c)`` there is U+00A9 followed by a variation selector, which renders as a
coloured emoji glyph rather than as the typographic sign). So neither picker
could type a plain copyright sign into prose, and none of them could type
``resume`` with its accents.

The shape of the answer:

* **Find keeps its forty and this is a superset of them**, built from the same
  dict under the same names, so the two lists cannot drift and a rename in
  ``find_model`` fails loudly here rather than quietly diverging.
* **Names come from Unicode, not from an author.** Three hundred hand-written
  names is three hundred chances to disagree with what the screen reader says
  when the character is actually in the document; ``unicodedata`` is where
  Describe Character gets its wording too, so the picker and the cursor answer
  alike. :func:`_pretty` only fixes the case -- and it keeps the letter's own
  case, because "latin small letter E" and "latin capital letter E" are the two
  rows a listener has to tell apart.
* **Keywords are for what Unicode does not say.** "Pound sign" does not contain
  "GBP" or "sterling"; "Latin small letter e with acute" does not contain a bare
  "e". Both are what somebody types.
* **A code point is a search term, not a separate dialog.** Typing ``2014``,
  ``U+2014`` or ``d8212`` finds the em dash, and a valid code point that is in
  no group at all is synthesised as a one-row result -- which is the old prompt,
  folded into the box that was going to be there anyway.

Framework-agnostic on purpose: QUILL's Insert Special Character lives on a
``MainFrame`` mixin, QuillLite's on a document window, and the dialog they share
knows only this.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from quill.core.char_describe import CharacterDescription, describe_character, display_glyph
from quill.core.find_model import NAMED_CHARACTERS
from quill.core.unicode_insert import CodepointError, parse_codepoint

__all__ = [
    "SEARCH_HELP",
    "CodepointError",
    "SpecialCharacter",
    "describe",
    "display_glyph",
    "entry_by_char",
    "inserted_message",
    "list_by_category",
    "list_categories",
    "parse_codepoint",
    "search",
]

#: What F1 says on the search box. Examples rather than a grammar, because the
#: three spellings of a code point are the part nobody guesses.
SEARCH_HELP = (
    "Type part of a character's name -- dash, quote, euro, acute, arrow -- or a "
    "Unicode code point: 2014 for hexadecimal, U+2014, or d8212 for decimal. A "
    "code point that is in no group still finds its character. Clear the box to "
    "browse by group instead."
)


@dataclass(frozen=True)
class SpecialCharacter:
    """One row of the picker: the character, what to call it, where it lives."""

    char: str
    name: str
    category: str
    keywords: tuple[str, ...] = field(default=())

    @property
    def code_point(self) -> str:
        """``U+2014``. The column that tells two rows that sound alike apart."""
        return f"U+{ord(self.char):04X}"

    @property
    def display(self) -> str:
        """What to show in the character column, for something with no glyph."""
        return display_glyph(self.char)


def _pretty(char: str) -> str:
    """Unicode's own name for *char*, in sentence case, keeping letter case.

    ``str.lower()`` on the whole name would turn "LATIN CAPITAL LETTER E WITH
    ACUTE" into a row indistinguishable from the small one, which is the single
    thing a reader of this list most needs to tell apart -- so a one-character
    token keeps the case the Unicode name gave it, except in a "SMALL LETTER"
    name where lowercase is the truthful rendering.
    """
    raw = unicodedata.name(char, "")
    if not raw:  # pragma: no cover - every catalogued character is named
        return f"U+{ord(char):04X}"
    small = "SMALL LETTER" in raw
    words = [
        (token.lower() if small else token)
        if len(token) == 1 and token.isalpha()
        else token.lower()
        for token in raw.split()
    ]
    text = " ".join(words)
    return text[0].upper() + text[1:]


# --------------------------------------------------------------------------- #
# The groups
# --------------------------------------------------------------------------- #

#: The Find catalogue, grouped. Written as *names* rather than characters so the
#: two lists share one spelling of each: a rename in ``find_model`` raises a
#: KeyError here at import, and ``test_special_characters`` asserts that every
#: name in that dict is used here exactly once.
_FROM_FIND: dict[str, tuple[str, ...]] = {
    "Whitespace": (
        "Tab",
        "Line break",
        "Carriage return",
        "Page break (form feed)",
        "Non-breaking space",
        "Narrow no-break space",
        "Thin space",
        "Hair space",
        "Figure space",
        "Em space",
        "En space",
    ),
    "Dashes and hyphens": (
        "Em dash",
        "En dash",
        "Soft hyphen",
        "Non-breaking hyphen",
        "Minus sign",
    ),
    "Quotes": (
        "Left double curly quote",
        "Right double curly quote",
        "Left single curly quote",
        "Right single curly quote",
        "Straight double quote",
        "Straight single quote (apostrophe)",
        "Double angle quote, opening",
        "Double angle quote, closing",
        "Single angle quote, opening",
        "Single angle quote, closing",
    ),
    "Invisible and control": (
        "Zero-width space",
        "Zero-width non-joiner",
        "Zero-width joiner",
        "Word joiner",
        "Byte order mark",
        "Object replacement character",
    ),
    "Typography": (
        "Ellipsis",
        "Bullet",
        "Middle dot",
        "Degree sign",
        "Section sign",
        "Pilcrow (paragraph mark)",
        "Dagger",
        "Double dagger",
    ),
}

#: Everything the Find list never needed, as plain strings of characters. Names
#: come from Unicode; only the grouping and the order are decided here. No
#: character may appear twice, in this table or against ``_FROM_FIND`` -- the
#: catalogue test asserts it rather than a dedupe hiding a typo.
_EXTRA: dict[str, str] = {
    "Legal and reference marks": "©®™℠℗№※‽⁂",
    "Currency": "£€¥¢₹₽₩₪₺₴₦₱₫₡₲₵¤ƒ",
    "Maths and units": "±×÷≠≤≥≈≡∞√∛∑∏∫∂∆∇∈∉⊂⊃∪∩∅∴∵′″‰‱µ¬∧∨⌀‖",
    "Fractions": "½⅓⅔¼¾⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞⅐⅑⅒↉",
    "Superscripts and ordinals": "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾₀₁₂₃₄₅₆₇₈₉ªº",
    "Arrows": "←→↑↓↔↕↖↗↘↙⇐⇒⇑⇓⇔↵⇥⇧⇪↺↻",
    "Accented letters, small": "àáâãäåāăçćčďđèéêëēĕėęěìíîïīĭįñńňòóôõöøōŏőùúûüūŭůűýÿžźżšśßæœðþıŋ",
    "Accented letters, capital": "ÀÁÂÃÄÅĀĂÇĆČĎĐÈÉÊËĒĔĖĘĚÌÍÎÏĪĬĮÑŃŇÒÓÔÕÖØŌŎŐÙÚÛÜŪŬŮŰÝŸŽŹŻŠŚÆŒÐÞŊ",
    "Greek letters": "αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ",
    "Punctuation from other languages": "¿¡‚„‣⁃〈〉「」『』،؛۔",
}

#: What Unicode's own name does not contain and somebody would type anyway.
#: Currency codes, the everyday word for a sign, and the shapes people describe
#: rather than name. Everything else is searchable by its Unicode name already.
_EXTRA_KEYWORDS: dict[str, tuple[str, ...]] = {
    "£": ("gbp", "sterling", "british"),
    "€": ("eur", "euro"),
    "¥": ("jpy", "cny", "japanese", "chinese"),
    "¢": ("usd", "cents"),
    "₹": ("inr", "indian", "rupee"),
    "₽": ("rub", "russian", "rouble"),
    "₩": ("krw", "korean", "won"),
    "₪": ("ils", "israeli", "shekel"),
    "©": ("copyright",),
    "®": ("registered", "trademark"),
    "™": ("trademark", "tm"),
    "±": ("plus or minus", "tolerance"),
    "×": ("times", "multiply", "multiplication", "dimensions"),
    "÷": ("divide", "division", "obelus"),
    "≈": ("approximately", "roughly", "about"),
    "≠": ("not equal", "unequal"),
    "µ": ("micro", "micron", "mu"),
    "Ω": ("ohm", "resistance", "omega"),
    "′": ("prime", "feet", "minutes", "arcminute"),
    "″": ("double prime", "inches", "seconds", "arcsecond"),
    "‰": ("per mille", "per thousand"),
    "ß": ("eszett", "sharp s", "german", "double s"),
    "¿": ("spanish", "inverted question"),
    "¡": ("spanish", "inverted exclamation"),
    "№": ("numero", "number sign"),
    "↵": ("return", "enter", "carriage return key"),
    "⇥": ("tab key",),
    "⇧": ("shift key",),
    "⇪": ("caps lock",),
}

#: Words worth attaching to every row of a group, because a listener thinks in
#: the group's noun ("currency", "accent") before they think of Unicode's.
_GROUP_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Currency": ("currency", "money"),
    "Maths and units": ("maths", "math", "science", "unit"),
    "Fractions": ("fraction", "vulgar"),
    "Superscripts and ordinals": ("superscript", "subscript", "ordinal", "power"),
    "Arrows": ("arrow",),
    "Accented letters, small": ("accent", "accented", "diacritic"),
    "Accented letters, capital": ("accent", "accented", "diacritic", "capital"),
    "Greek letters": ("greek",),
    "Legal and reference marks": ("mark", "symbol"),
    "Punctuation from other languages": ("punctuation", "foreign"),
}


def _base_letter(char: str) -> tuple[str, ...]:
    """The unaccented letter inside *char*, so typing "e" narrows to e-variants.

    Unicode's name says "with acute" but never says "e" on its own, and a bare
    letter is what somebody types when they are looking for one of its accented
    forms and cannot remember which accent it was.
    """
    stripped = "".join(
        c for c in unicodedata.normalize("NFKD", char) if not unicodedata.combining(c)
    )
    return (stripped.lower(),) if stripped and stripped != char else ()


def _entry(char: str, name: str, category: str) -> SpecialCharacter:
    keywords = (
        (char,)
        + _base_letter(char)
        + _EXTRA_KEYWORDS.get(char, ())
        + _GROUP_KEYWORDS.get(category, ())
    )
    return SpecialCharacter(char=char, name=name, category=category, keywords=keywords)


def _build() -> tuple[SpecialCharacter, ...]:
    rows: list[SpecialCharacter] = []
    for category, names in _FROM_FIND.items():
        rows.extend(_entry(NAMED_CHARACTERS[name], name, category) for name in names)
    for category, characters in _EXTRA.items():
        rows.extend(_entry(char, _pretty(char), category) for char in characters)
    return tuple(rows)


#: Every catalogued character, in group order then within-group order.
CATALOGUE: tuple[SpecialCharacter, ...] = _build()

_BY_CHAR: dict[str, SpecialCharacter] = {row.char: row for row in CATALOGUE}


# --------------------------------------------------------------------------- #
# Reading it
# --------------------------------------------------------------------------- #


def list_categories() -> list[str]:
    """The group names, in the order the picker shows them."""
    return [*_FROM_FIND, *_EXTRA]


def list_by_category(category: str) -> list[SpecialCharacter]:
    """Every character in *category*, in order. Unknown category -> empty."""
    return [row for row in CATALOGUE if row.category == category]


def entry_by_char(char: str) -> SpecialCharacter | None:
    """The catalogue row for *char*, or ``None`` when it is not in any group."""
    return _BY_CHAR.get(char)


def _code_point_entry(query: str) -> SpecialCharacter | None:
    """*query* read as a code point, as a one-row result. ``None`` if it is not.

    This is the old Insert Special Character, folded into the search box: a code
    point that is in no group still resolves, so the picker can reach every
    character Unicode has rather than only the ones somebody grouped.
    """
    try:
        char = parse_codepoint(query)
    except CodepointError:
        return None
    known = _BY_CHAR.get(char)
    if known is not None:
        return known
    return SpecialCharacter(char=char, name=_pretty(char), category="Code point", keywords=(char,))


def search(query: str) -> list[SpecialCharacter]:
    """Every row matching *query*, best first. Empty query -> nothing.

    Matches are ranked rather than merely collected, because a list that puts
    "Right single curly quote" above "Straight single quote (apostrophe)" for
    the query "apostrophe" is a list you have to arrow through to check. Name
    first, then keyword, then anything containing the text.
    """
    text = query.strip().casefold()
    if not text:
        return []
    exact: list[SpecialCharacter] = []
    starts: list[SpecialCharacter] = []
    contains: list[SpecialCharacter] = []
    keyword: list[SpecialCharacter] = []
    for row in CATALOGUE:
        name = row.name.casefold()
        if name == text or row.char == query or row.code_point.casefold() == text:
            exact.append(row)
        elif name.startswith(text):
            starts.append(row)
        elif any(word.casefold() == text for word in row.keywords):
            keyword.append(row)
        elif text in name or any(text in word.casefold() for word in row.keywords):
            contains.append(row)
    results = [*exact, *starts, *keyword, *contains]
    # A code point is a search term too, and it wins: somebody who typed 2014
    # meant U+2014, not the four rows whose names happen to contain "2014".
    coded = _code_point_entry(query.strip())
    if coded is not None:
        results = [coded, *(row for row in results if row.char != coded.char)]
    return results


def describe(entry: SpecialCharacter) -> CharacterDescription:
    """The full description of *entry*, in Describe Character's own words."""
    return describe_character(entry.char, 0)


def inserted_message(character: str) -> str:
    """What to say after inserting *character*.

    Said because nothing else will: a screen reader is silent when an app writes
    text on its own behalf, so without this the command is a keystroke after
    which something invisible may or may not have appeared. Reuses Describe
    Character's summary, so "what did I just insert" and "what is under the
    cursor" answer in the same words.
    """
    return f"Inserted {describe_character(character, 0).summary}"
