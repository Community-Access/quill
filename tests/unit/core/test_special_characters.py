"""The Insert Special Character catalogue: what is in it, and how it is found.

Three hundred and fifty rows built partly from ``unicodedata`` and partly from a
hand-written grouping is exactly the shape that rots quietly -- a character
listed twice, a group emptied by a typo, a name in ``find_model`` renamed out
from under this one. None of that shows up when you open the picker and see a
list; all of it shows up here.

The search tests are about *ranking* rather than membership. A picker that finds
the right row and puts it thirtieth is a picker you arrow through to check,
which is the thing a list was supposed to save.
"""

from __future__ import annotations

import unicodedata

from quill.core.find_model import NAMED_CHARACTERS
from quill.core.special_characters import (
    CATALOGUE,
    describe,
    entry_by_char,
    inserted_message,
    list_by_category,
    list_categories,
    search,
)

EM_DASH = "—"
COPYRIGHT = "©"
E_ACUTE = "é"
E_ACUTE_CAPITAL = "É"
# Written as escapes, not as the characters themselves: a stray whitespace
# tidy would silently turn a no-break space into a space and the test would
# then assert the wrong character while still passing its own name.
NBSP = " "
ZERO_WIDTH_SPACE = "​"


# --------------------------------------------------------------------- #
# The catalogue holds together


def test_no_character_is_listed_twice() -> None:
    """Two rows for one character is two rows a listener has to tell apart and
    cannot -- and it is what a hand-grouped table does when a character belongs
    to two groups (the omega that is also an ohm, the bullet that is also
    punctuation)."""
    seen: dict[str, str] = {}
    for row in CATALOGUE:
        assert row.char not in seen, (
            f"{row.char!r} is in both {seen[row.char]!r} and {row.category!r}"
        )
        seen[row.char] = row.category


def test_no_two_rows_share_a_name() -> None:
    names = [row.name for row in CATALOGUE]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    assert duplicates == [], f"rows a listener cannot tell apart: {duplicates}"


def test_every_row_is_exactly_one_character() -> None:
    """A multi-character row would insert something the read-back, which
    describes a single character, cannot describe."""
    wrong = [row.name for row in CATALOGUE if len(row.char) != 1]
    assert wrong == []


def test_every_group_has_something_in_it() -> None:
    """An empty group is a row in the Group list that answers with nothing."""
    empty = [name for name in list_categories() if not list_by_category(name)]
    assert empty == []


def test_the_find_catalogue_is_a_strict_subset_used_exactly_once() -> None:
    """Find's forty characters and the picker's three hundred are one list read
    two ways. A rename in find_model raises at import here; this catches the
    other half -- a character quietly dropped from the grouping."""
    picker = {row.char for row in CATALOGUE}
    missing = sorted(name for name, char in NAMED_CHARACTERS.items() if char not in picker)
    assert missing == [], f"in Find's list and not in the picker: {missing}"


def test_the_shared_rows_keep_the_names_find_gave_them() -> None:
    """Not Unicode's: "Line break" is what the Find dialog calls U+000A, and two
    windows in one app calling one character two things is the drift this
    grouping exists to prevent."""
    assert entry_by_char(NAMED_CHARACTERS["Line break"]).name == "Line break"
    assert entry_by_char(NAMED_CHARACTERS["Non-breaking space"]).name == "Non-breaking space"


def test_the_writers_characters_that_were_missing_are_all_there_now() -> None:
    """The gap that prompted the expansion: none of these could be typed from
    either picker, and the emoji catalogue carries only their emoji-presentation
    forms, which put a variation selector in the document."""
    for char in (COPYRIGHT, "®", "™", E_ACUTE, "£", "€", "±", "½", "→", "π", "ñ", "¿"):
        assert entry_by_char(char) is not None, f"{char!r} is not in the catalogue"


def test_a_small_letter_and_its_capital_are_two_readably_different_rows() -> None:
    """Lowercasing the whole Unicode name would render both as "letter e", which
    is the single distinction a listener most needs from this list."""
    small = entry_by_char(E_ACUTE)
    capital = entry_by_char(E_ACUTE_CAPITAL)
    assert small.name == "Latin small letter e with acute"
    assert capital.name == "Latin capital letter E with acute"


def test_a_character_with_no_glyph_still_has_something_in_the_character_column() -> None:
    """A blank cell reads as nothing at all, which is indistinguishable from a
    row that failed to render."""
    assert entry_by_char(ZERO_WIDTH_SPACE).display.strip() != ""
    assert entry_by_char(NAMED_CHARACTERS["Tab"]).display.strip() != ""


def test_the_code_point_column_is_the_unicode_one() -> None:
    assert entry_by_char(EM_DASH).code_point == "U+2014"
    assert entry_by_char(NBSP).code_point == "U+00A0"


# --------------------------------------------------------------------- #
# Finding one


def test_an_empty_search_finds_nothing_rather_than_everything() -> None:
    """Clearing the box goes back to browsing the group, which the dialog does;
    a full list of 350 rows dumped into the results is not an answer."""
    assert search("") == []
    assert search("   ") == []


def test_a_code_point_wins_over_a_name_that_merely_contains_it() -> None:
    """Somebody who typed 2014 meant U+2014."""
    assert search("2014")[0].char == EM_DASH
    assert search("U+2014")[0].char == EM_DASH
    assert search("d8212")[0].char == EM_DASH


def test_a_code_point_outside_every_group_still_resolves() -> None:
    """This is the old Insert Special Character, folded into the search box: the
    picker reaches every character Unicode has, not only the grouped ones."""
    found = search("1F600")
    assert found and found[0].char == "\U0001f600"
    assert entry_by_char("\U0001f600") is None


def test_an_exact_name_comes_first() -> None:
    assert search("Em dash")[0].char == EM_DASH
    assert search("apostrophe")[0].name == "Straight single quote (apostrophe)"


def test_the_words_unicode_does_not_use_are_searchable_anyway() -> None:
    """Unicode calls it a POUND SIGN and nobody types that when they mean GBP;
    "Latin small letter e with acute" does not contain a bare "e"."""
    assert search("gbp")[0].char == "£"
    assert search("sterling")[0].char == "£"
    assert search("eur")[0].char == "€"
    assert search("eszett")[0].char == "ß"
    assert E_ACUTE in [row.char for row in search("e")]


def test_pasting_the_character_itself_finds_its_row() -> None:
    """Somebody who found the character somewhere else and wants to know what it
    is, or wants it again."""
    assert search(EM_DASH)[0].char == EM_DASH
    assert search(COPYRIGHT)[0].char == COPYRIGHT


def test_a_search_that_matches_nothing_returns_nothing_rather_than_raising() -> None:
    assert search("zzzznotacharacter") == []


def test_searching_a_group_word_finds_that_group() -> None:
    arrows = [row.char for row in search("arrow")]
    assert "→" in arrows
    assert "←" in arrows


# --------------------------------------------------------------------- #
# Saying what happened


def test_the_read_back_names_the_character_rather_than_showing_it() -> None:
    """ "Inserted" followed by a no-break space is "Inserted" followed by
    silence, which is the whole problem this sentence exists to solve."""
    said = inserted_message(NBSP)
    assert "U+00A0" in said
    assert "No-break space" in said


def test_the_read_back_is_describe_characters_own_wording() -> None:
    """So "what did I just insert" and "what is under the cursor" answer alike
    rather than describing one character two ways."""
    assert inserted_message(EM_DASH).endswith(describe(entry_by_char(EM_DASH)).summary)


def test_every_catalogued_character_can_be_described() -> None:
    """describe() is called on every selection change, so one row that raises is
    a picker that dies while somebody is arrowing through it."""
    for row in CATALOGUE:
        detail = describe(row).detail
        assert detail
        assert f"U+{ord(row.char):04X}" in detail


def test_no_row_falls_back_to_a_bare_code_point_for_its_name() -> None:
    """The generated names come from unicodedata, which does not name the
    control characters -- so a group written as characters rather than as Find
    names would ship "U+0009" where "Tab" should be. The four that unicodedata
    cannot name are exactly the four the Find catalogue names by hand."""
    unnamed = [row.code_point for row in CATALOGUE if row.name == row.code_point]
    assert unnamed == []
    control = [row.name for row in CATALOGUE if not unicodedata.name(row.char, "")]
    assert sorted(control) == ["Carriage return", "Line break", "Page break (form feed)", "Tab"]
