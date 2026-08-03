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


def test_unmapped_private_use_characters_are_dropped() -> None:
    # An unmapped private-use codepoint carries no recoverable meaning, so it is
    # removed rather than read out as an unknown character.
    assert repair_private_use_glyphs("page \uf8f0break") == "page break"


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
