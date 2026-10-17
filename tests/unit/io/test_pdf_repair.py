from __future__ import annotations

from quill.io.pdf_repair import (
    dehyphenate,
    reflow_paragraphs,
    repair_extracted_text,
    repair_private_use_glyphs,
    repair_spaced_headings,
)

# A page of already-clean text: one paragraph per line, a heading, a list, a
# hyphenated compound, and a sentence that ends a paragraph. Nothing here is
# damaged, so no repair may touch it.
CLEAN_PROSE = (
    "Chapter One\n"
    "\n"
    "The committee met on a Tuesday, which was unusual, and agreed that the "
    "report would be circulated before the end of the month. Nobody objected.\n"
    "\n"
    "Three items remained:\n"
    "\n"
    "- The budget for the Anglo-Saxon collection.\n"
    "- The 2018-2019 attendance figures.\n"
    "1. A decision on the reading room.\n"
    "\n"
    "The meeting closed at four.\n"
)


def test_private_use_ligatures_become_letters() -> None:
    damaged = "The o\uf003ce sta\uf000 con\uf001rmed the \uf002ight."
    assert repair_private_use_glyphs(damaged) == "The office staff confirmed the flight."


def test_unmapped_private_use_characters_are_kept_not_deleted() -> None:
    # Item 28: deleting an unmapped private-use glyph silently changes the text
    # ("next box" read as "net bo" when a font put its "x" there). It is kept,
    # and the readability score reports the page instead.
    assert repair_private_use_glyphs("page \uf8f0break") == "page \uf8f0break"
    assert repair_private_use_glyphs("ne\ue123t bo\ue123") == "ne\ue123t bo\ue123"


def test_a_ligature_slot_away_from_any_letter_is_not_guessed_at() -> None:
    # U+F001 is "fi" only where a ligature can be: touching a letter. Standing
    # alone it could be any glyph the font chose, so it is left as it is.
    assert repair_private_use_glyphs("bullet \uf001 here") == "bullet \uf001 here"
    assert repair_private_use_glyphs("\uf001rst") == "first"


def test_real_unicode_ligatures_are_normalized() -> None:
    assert repair_private_use_glyphs("oﬃce ﬄows") == "office fflows"


def test_private_use_repair_leaves_ordinary_text_alone() -> None:
    prose = "Ordinary text with an em dash — and an accent: café."
    assert repair_private_use_glyphs(prose) == prose


def test_spaced_heading_collapses() -> None:
    assert repair_spaced_headings("H E A D I N G") == "HEADING"


def test_spaced_heading_keeps_word_boundaries() -> None:
    assert repair_spaced_headings("C H A P T E R  O N E") == "CHAPTER ONE"


def test_spaced_heading_leaves_ordinary_prose_alone() -> None:
    prose = "The quick brown fox jumped over the lazy dog."
    assert repair_spaced_headings(prose) == prose


def test_spaced_heading_leaves_a_b_testing_alone() -> None:
    assert repair_spaced_headings("A B testing") == "A B testing"
    assert repair_spaced_headings("A B testing was inconclusive") == (
        "A B testing was inconclusive"
    )


def test_spaced_digits_are_not_treated_as_a_heading() -> None:
    # A spaced-out row of numbers is table data, not a display heading.
    assert repair_spaced_headings("1 2 3 4 5 6") == "1 2 3 4 5 6"


def test_dehyphenate_joins_a_split_word() -> None:
    assert dehyphenate("inter-\nnational") == "international"


def test_dehyphenate_keeps_a_capitalized_compound() -> None:
    assert dehyphenate("Anglo-\nSaxon") == "Anglo-\nSaxon"


def test_dehyphenate_keeps_a_hyphen_after_a_number() -> None:
    assert dehyphenate("2018-\nnineteen") == "2018-\nnineteen"


def test_dehyphenate_keeps_a_standalone_dash() -> None:
    assert dehyphenate("the report --\nand its appendix") == "the report --\nand its appendix"


def test_dehyphenate_chains_consecutive_splits() -> None:
    assert dehyphenate("un-\nfor-\ngettable") == "unforgettable"


def test_reflow_joins_a_hard_wrapped_line() -> None:
    wrapped = (
        "The committee met on a Tuesday, which was unusual, and agreed that\n"
        "the report would be circulated before the end of the month.\n"
    )
    assert reflow_paragraphs(wrapped) == (
        "The committee met on a Tuesday, which was unusual, and agreed that "
        "the report would be circulated before the end of the month.\n"
    )


def test_reflow_does_not_join_across_a_blank_line() -> None:
    text = (
        "The committee met on a Tuesday, which was unusual, and agreed that\n"
        "\n"
        "the report would be circulated before the end of the month.\n"
    )
    assert reflow_paragraphs(text) == text


def test_reflow_does_not_join_a_finished_sentence_to_a_new_one() -> None:
    text = (
        "The committee met on a Tuesday and agreed the report would circulate.\n"
        "Nobody objected to the proposal that had been tabled in the spring.\n"
    )
    assert reflow_paragraphs(text) == text


def test_reflow_does_not_join_list_items() -> None:
    text = (
        "- The budget for the collection, which the trustees approved in full.\n"
        "- The attendance figures, which were lower than the previous season.\n"
        "1. A decision on the reading room and the hours it will keep in June.\n"
    )
    assert reflow_paragraphs(text) == text


def test_reflow_does_not_join_a_short_deliberate_line() -> None:
    text = "Chapter One\nThe committee met on a Tuesday.\n"
    assert reflow_paragraphs(text) == text


def test_reflow_never_joins_across_a_page_break() -> None:
    text = (
        "The committee met on a Tuesday, which was unusual, and agreed that\n"
        "\f"
        "the report would be circulated before the end of the month.\n"
    )
    assert reflow_paragraphs(text) == text


def test_pipeline_repairs_a_realistically_damaged_page() -> None:
    damaged = (
        "R E P O R T\n"
        "The o\uf003ce con\uf001rmed that the inter-\n"
        "national delegation would arrive before the end of the month and\n"
        "stay for a week.\n"
    )
    assert repair_extracted_text(damaged) == (
        "REPORT\n"
        "The office confirmed that the international delegation would arrive "
        "before the end of the month and stay for a week.\n"
    )


def test_pipeline_leaves_clean_prose_unchanged() -> None:
    # The repairs must be safe on text that needs no repair at all.
    assert repair_extracted_text(CLEAN_PROSE) == CLEAN_PROSE


def test_pipeline_is_idempotent() -> None:
    damaged = (
        "S U M M A R Y\n"
        "The o\uf003ce con\uf001rmed that the inter-\n"
        "national delegation would arrive before the end of the month and\n"
        "stay for a week. Nobody objected.\n"
        "\n"
        "- The budget for the Anglo-\n"
        "Saxon collection.\n"
    )
    once = repair_extracted_text(damaged)
    assert repair_extracted_text(once) == once


def test_every_repair_accepts_empty_text() -> None:
    for repair in (
        repair_private_use_glyphs,
        repair_spaced_headings,
        dehyphenate,
        reflow_paragraphs,
        repair_extracted_text,
    ):
        assert repair("") == ""


# -- item 28: protect lines before reflow, keep meaningful hyphens -------------- #

_LONG_BODY = "The committee met on a Tuesday, which was unusual, and agreed that the"


def test_a_long_body_line_does_not_swallow_the_title_under_it() -> None:
    for title in ("CHAPTER TWO", "Chapter 2", "2.1 Methods", "Results and Discussion"):
        text = f"{_LONG_BODY}\n{title}\nThe next paragraph begins here."
        assert reflow_paragraphs(text) == text, title


def test_a_wrapped_lowercase_continuation_still_joins() -> None:
    text = f"{_LONG_BODY}\nreport would be circulated before the end of the month."
    assert reflow_paragraphs(text) == (
        f"{_LONG_BODY} report would be circulated before the end of the month."
    )


def test_two_long_table_like_rows_stay_separate() -> None:
    rows = (
        "Northern regional distribution centre and warehouse 1,250 18.75 23,437.50\n"
        "Southern regional distribution centre and warehouse 980 18.75 18,375.00"
    )
    assert repair_extracted_text(rows) == rows


def test_a_column_spaced_row_is_never_joined() -> None:
    rows = (
        "Northern regional distribution centre and warehouse   1,250   18.75\n"
        "covering the whole of the upper valley and the coast   980   18.75"
    )
    assert reflow_paragraphs(rows) == rows


def test_an_address_line_under_a_long_line_stays_its_own_line() -> None:
    for line in ("221 Baker Street", "Springfield, IL 62704", "London NW1 6XE"):
        text = f"{_LONG_BODY}\n{line}"
        assert reflow_paragraphs(text) == text, line


def test_lettered_and_roman_list_starts_are_list_items() -> None:
    text = (
        f"{_LONG_BODY}\n"
        "a) the first lettered item in the list, which is long enough to wrap\n"
        "(b) the second lettered item in the list, which is long enough too\n"
        "iv. the fourth item numbered in roman figures, long enough to wrap"
    )
    assert reflow_paragraphs(text) == text


def test_spaced_letters_with_no_word_gaps_are_not_run_together() -> None:
    # pdfplumber reads a widely spaced sentence one letter at a time with single
    # spaces only; closing it up would make one long nonsense word.
    line = "W i d e l e t t e r s a r e h a r d t o r e a d"
    assert repair_spaced_headings(line) == line
    # A short or all-capitals display word still closes up.
    assert repair_spaced_headings("C H A P T E R") == "CHAPTER"
    assert repair_spaced_headings("A C K N O W L E D G E M E N T S") == "ACKNOWLEDGEMENTS"


def test_an_identifier_keeps_its_hyphen_and_its_line_break() -> None:
    assert dehyphenate("ISBN-\nnumber") == "ISBN-\nnumber"
    assert dehyphenate("form A4-\nsized") == "form A4-\nsized"


def test_an_always_hyphenated_prefix_joins_and_keeps_the_hyphen() -> None:
    assert dehyphenate("a self-\naware reader") == "a self-aware reader"
    assert dehyphenate("well-\nknown") == "well-known"


def test_numbers_and_identifiers_survive_every_repair() -> None:
    text = (
        "In 2024 the library lent 1,234 books and added ISBN 978-0-306-40615-7,\n"
        "a balance of 4,512.75 pounds, code X-17b and the 2018-2019 figures."
    )
    repaired = repair_extracted_text(text)
    for token in ("2024", "1,234", "978-0-306-40615-7", "4,512.75", "X-17b", "2018-2019"):
        assert token in repaired


def test_the_new_protections_are_idempotent() -> None:
    damaged = (
        f"{_LONG_BODY}\n"
        "CHAPTER TWO\n"
        "Northern regional distribution centre and warehouse 1,250 18.75 23,437.50\n"
        "Southern regional distribution centre and warehouse 980 18.75 18,375.00\n"
        "a self-\naware reader and an ISBN-\nnumber, net to  alone\n"
        "W i d e l e t t e r s a r e h a r d t o r e a d"
    )
    once = repair_extracted_text(damaged)
    assert repair_extracted_text(once) == once
