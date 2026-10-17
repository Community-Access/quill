"""The words both editors say about Import / Convert Document, and its file list."""

from __future__ import annotations

from pathlib import Path

from quill.core.import_convert import (
    converted_name,
    failed_sentence,
    import_wildcard,
    opened_sentence,
    scanned_import_question,
)
from quill.io.docconvert import (
    TIER_LOCAL_OCR,
    TIER_MARKITDOWN,
    TIER_OWN_READER,
    ConversionOutcome,
    supported_import_extensions,
)


def test_the_file_list_offers_exactly_what_the_router_accepts() -> None:
    first_mask = import_wildcard().split("|")[1]
    assert {mask.lstrip("*") for mask in first_mask.split(";")} == set(
        supported_import_extensions()
    )
    assert import_wildcard().endswith("|All files (*.*)|*.*")


def test_the_question_names_the_editor_and_promises_no_upload() -> None:
    assert scanned_import_question("scan.pdf").startswith("QUILL could not find readable text")
    lite = scanned_import_question("scan.pdf", app_name="QUILL Lite")
    assert lite.startswith("QUILL Lite could not find readable text in scan.pdf.")
    assert "does not upload anything" in lite
    assert "Cancel: stop." in lite


def test_one_page_is_not_counted_aloud_and_many_are() -> None:
    one = ConversionOutcome(text="x", tier=TIER_LOCAL_OCR, source=Path("a.png"), page_count=1)
    many = ConversionOutcome(
        text="x", tier=TIER_LOCAL_OCR, source=Path("a.pdf"), page_count=4, mean_confidence=91.4
    )
    assert opened_sentence("a.png", one) == "Opened a.png from free on-device OCR."
    assert opened_sentence("a.pdf", many) == (
        "Opened a.pdf from free on-device OCR. 4 pages. Confidence 91 out of 100."
    )


def test_an_own_reader_result_says_who_read_it_and_what_it_held() -> None:
    outcome = ConversionOutcome(
        text="x",
        tier=TIER_OWN_READER,
        source=Path("budget.xlsx"),
        reader="QUILL's own Excel reader",
        units="3 sheets",
    )
    assert opened_sentence("budget.xlsx", outcome) == (
        "Opened budget.xlsx as editable text, read by QUILL's own Excel reader. 3 sheets. "
        "Nothing was uploaded."
    )
    plain = ConversionOutcome(text="x", tier=TIER_MARKITDOWN, source=Path("a.html"))
    assert opened_sentence("a.html", plain).endswith("Nothing was uploaded.")


def test_names_and_failures() -> None:
    assert converted_name("report") == "report (converted)"
    assert failed_sentence("a.pdf", "Damaged.", app_name="QUILL Lite") == (
        "QUILL Lite could not convert a.pdf.\n\nDamaged."
    )
