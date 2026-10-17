"""Real Office files through QUILL's own readers: the corpus in tests/corpus/office.

Every file here was written by ``tests/corpus/office/build_office_corpus.py``
(python-docx, openpyxl and python-pptx for the Microsoft formats, hand-built
zips for OpenDocument), so its text is known exactly.

The point of these readers (todo P1 4b, 2026-10-16) is that an Office import
must not depend on MarkItDown. In a shipped build MarkItDown cannot import --
the shared runtime excludes onnxruntime, which magika (imported at the top of
markitdown) needs -- and ``find_spec`` still reports it installed. The tests
marked "shipped build" reproduce exactly that and prove the fallback runs.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from quill.io.docconvert import TIER_OWN_READER, _Deps, convert_document
from quill.io.office_text import (
    LegacyOfficeFormatError,
    OfficeReadError,
    markitdown_or_own_reader,
    read_office_text,
    read_office_text_preferring_markitdown,
)

CORPUS = Path(__file__).resolve().parents[2] / "corpus" / "office"


def _break_markitdown_like_a_shipped_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """``import markitdown`` fails on onnxruntime, as in the QuillVille runtime.

    The runtime freezes markitdown and magika in and excludes onnxruntime, so
    the import dies inside magika. Blocking onnxruntime reproduces it; and
    ``find_spec`` is made to say "installed", as the frozen copy makes it say.
    """
    for name in [
        n for n in sys.modules if n == "markitdown" or n.startswith(("markitdown.", "magika"))
    ]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "onnxruntime", None)
    real_find_spec = importlib.util.find_spec

    def _stale_find_spec(name: str, *args: object, **kwargs: object) -> object:
        if name in {"markitdown", "pdfplumber", "pypdf"}:
            return object()  # "installed" -- the stale answer the frozen copy gives
        return real_find_spec(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(importlib.util, "find_spec", _stale_find_spec)


def _block(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)


# ------------------------------------------------------------- the corpus


def test_every_file_the_build_script_names_is_committed() -> None:
    script = (CORPUS / "build_office_corpus.py").read_text(encoding="utf-8")
    for name in (
        "report.docx",
        "budget.xlsx",
        "deck.pptx",
        "minutes.odt",
        "scores.ods",
        "talk.odp",
        "locked.docx",
        "legacy.doc",
    ):
        assert f'"{name}"' in script
        assert (CORPUS / name).is_file(), name


@pytest.mark.parametrize("blocked", [False, True], ids=["python-docx", "word-xml"])
def test_word_keeps_headings_lists_tables_and_breaks(
    monkeypatch: pytest.MonkeyPatch, blocked: bool
) -> None:
    if blocked:
        # The shared runtime excludes lxml, so python-docx cannot import there.
        _block(monkeypatch, "docx", "lxml")
    found = read_office_text(CORPUS / "report.docx")
    assert found.engine == ("word-xml" if blocked else "python-docx")
    text = found.text
    assert text.startswith("# Quarterly Report\n")
    assert "\n# Summary\n" in text
    assert "\n## Highlights\n" in text
    assert "- North grew fastest\n- South held steady\n" in text
    assert "1. Hire two editors\n1. Open the Leeds office\n" in text
    assert "| Region | Total |\n| --- | --- |\n| North | 1,200 |\n" in text
    assert "| South \\| West | 950 |" in text  # a pipe in a cell stays in its cell
    assert "First line of the address\\\nSecond line of the address" in text
    assert text.rstrip().endswith("End of report.")


@pytest.mark.parametrize("blocked", [False, True], ids=["openpyxl", "sheet-xml"])
def test_excel_keeps_sheet_boundaries_and_cell_values(
    monkeypatch: pytest.MonkeyPatch, blocked: bool
) -> None:
    if blocked:
        _block(monkeypatch, "openpyxl")
    found = read_office_text(CORPUS / "budget.xlsx")
    assert found.engine == ("sheet-xml" if blocked else "openpyxl")
    assert found.count_phrase == "2 sheets"
    text = found.text
    assert text.index("## Sheet: Budget") < text.index("## Sheet: Notes")
    assert "| Item | Amount | Paid |" in text
    assert "| Rent | 950 | TRUE |" in text
    assert "| Snacks | 12.5 | FALSE |" in text
    assert "| Due | 2026-11-01 |" in text  # a date, not the day count 46327
    assert "| Pay rent \\| early |" in text


def test_powerpoint_reads_in_presentation_order_with_notes_and_tables() -> None:
    found = read_office_text(CORPUS / "deck.pptx")
    assert found.engine == "slide-xml"
    assert found.count_phrase == "3 slides"
    text = found.text
    # "Figures" was made third and moved to second; the deck's order wins.
    assert text.index("# Slide 1: Welcome") < text.index("# Slide 2: Figures")
    assert text.index("# Slide 2: Figures") < text.index("# Slide 3: Agenda")
    assert "- Results\n  - By region\n- Questions" in text
    assert "## Notes\n\nKeep this under five minutes." in text
    assert "## Tables\n\n| Region | Total |\n| --- | --- |\n| North | 1,200 |" in text


def test_opendocument_text_spreadsheet_and_presentation() -> None:
    odt = read_office_text(CORPUS / "minutes.odt").text
    assert odt.startswith("# Minutes\n")
    assert "Present: everyone." in odt
    assert "## Actions" in odt
    assert "- Book the hall\n  - Ask about ramps\n- Send the agenda" in odt
    assert "| Who | When |" in odt and "| Sam | Friday |" in odt
    assert "Line one\\\nLine two" in odt

    ods = read_office_text(CORPUS / "scores.ods")
    # A million repeated blank rows and sixteen thousand blank columns are
    # how ODF says "nothing more here"; they must not become a million rows.
    assert ods.count_phrase == "2 sheets"
    assert "| Name | Score |\n| --- | --- |\n| Ada | 91 |" in ods.text
    assert "## Sheet: Empty\n\n(This sheet is empty.)" in ods.text
    assert len(ods.text) < 500

    odp = read_office_text(CORPUS / "talk.odp")
    assert odp.count_phrase == "2 slides"
    assert "# Slide 1: Hello\n\n- First point\n- Second point" in odp.text
    assert "## Notes\n\nSmile." in odp.text
    assert "# Slide 2\n\n- No title here" in odp.text


def test_a_sheet_cut_short_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    _block(monkeypatch, "openpyxl")
    monkeypatch.setattr("quill.io.office_sheets.MAX_ROWS", 2)
    found = read_office_text(CORPUS / "budget.xlsx")
    assert any('"Budget"' in note for note in found.notes)
    assert found.metadata()["extraction_notes"] == list(found.notes)


# ------------------------------------------------- refusals that say what to do


def test_password_protected_file_is_named_as_such() -> None:
    with pytest.raises(OfficeReadError) as excinfo:
        read_office_text(CORPUS / "locked.docx")
    assert "password-protected" in excinfo.value.sentence
    assert "File > Info" in excinfo.value.sentence


def test_legacy_doc_without_libreoffice_names_the_save_as(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("quill.core.external_tools.libreoffice_executable", lambda: None)
    with pytest.raises(LegacyOfficeFormatError) as excinfo:
        read_office_text(CORPUS / "legacy.doc")
    sentence = excinfo.value.sentence
    assert "Word 97-2003" in sentence
    assert '"Word Document (.docx)"' in sentence
    assert "libreoffice.org" in sentence


def test_legacy_doc_is_read_after_libreoffice_converts_it() -> None:
    def _convert(source: Path, target_suffix: str, out_dir: Path) -> Path:
        assert target_suffix == ".docx"
        converted = out_dir / f"{source.stem}{target_suffix}"
        shutil.copyfile(CORPUS / "report.docx", converted)
        return converted

    found = read_office_text(CORPUS / "legacy.doc", legacy_converter=_convert)
    assert found.source_kind == "doc"
    assert found.conversion_engine == "libreoffice"
    assert "## Highlights" in found.text
    assert found.reader_label == "QUILL's own Word reader, after LibreOffice converted it"


def test_legacy_conversion_failure_still_names_the_save_as() -> None:
    def _fail(source: Path, target_suffix: str, out_dir: Path) -> Path:
        raise subprocess.CalledProcessError(1, ["soffice"])

    with pytest.raises(LegacyOfficeFormatError) as excinfo:
        read_office_text(CORPUS / "legacy.doc", legacy_converter=_fail)
    assert "LibreOffice could not convert legacy.doc" in excinfo.value.sentence


# -------------------------------------------- shipped build: MarkItDown broken


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("report.docx", "## Highlights"),
        ("budget.xlsx", "## Sheet: Budget"),
        ("deck.pptx", "# Slide 2: Figures"),
    ],
)
def test_shipped_build_import_falls_back_when_markitdown_cannot_import(
    monkeypatch: pytest.MonkeyPatch, name: str, expected: str
) -> None:
    """The bug itself: Import / Convert with MarkItDown dying on onnxruntime."""
    _break_markitdown_like_a_shipped_build(monkeypatch)
    with pytest.raises(ImportError):
        import markitdown  # noqa: F401
    # find_spec says installed -- and must not matter.
    assert importlib.util.find_spec("markitdown") is not None

    outcome = convert_document(CORPUS / name)

    assert outcome.tier == TIER_OWN_READER
    assert expected in outcome.text
    assert outcome.reader.startswith("QUILL's own")


def test_shipped_build_records_why_markitdown_was_passed_over(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _break_markitdown_like_a_shipped_build(monkeypatch)
    found = read_office_text_preferring_markitdown(CORPUS / "report.docx")
    assert found.engine in {"python-docx", "word-xml"}
    assert "onnxruntime" in found.markitdown_failure
    assert found.metadata()["markitdown_failure"] == found.markitdown_failure


def test_shipped_build_file_open_reads_office_files_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.io.structured import read_structured_document

    _break_markitdown_like_a_shipped_build(monkeypatch)
    for name, engines in (
        ("report.docx", {"python-docx", "word-xml"}),
        ("budget.xlsx", {"openpyxl", "sheet-xml"}),
        ("deck.pptx", {"slide-xml"}),
    ):
        document = read_structured_document(CORPUS / name)
        assert document.source_metadata["engine"] in engines, name
        assert "extraction_pack_missing" not in document.source_metadata


def test_open_announcement_and_intake_report_name_the_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.intake import build_intake_report, build_intake_summary
    from quill.io.structured import read_structured_document

    _break_markitdown_like_a_shipped_build(monkeypatch)
    document = read_structured_document(CORPUS / "budget.xlsx")

    summary = build_intake_summary(document)
    assert "read by QUILL's own Excel reader" in summary
    assert "2 sheets" in summary
    assert "Download Optional Components" not in summary

    report = build_intake_report(document)
    assert "Read by: QUILL's own Excel reader" in report
    assert "Contents: 2 sheets" in report
    assert "MarkItDown: not used." in report and "onnxruntime" in report


def test_shipped_build_convert_file_names_the_stand_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _break_markitdown_like_a_shipped_build(monkeypatch)
    text, stand_in = markitdown_or_own_reader(CORPUS / "deck.pptx")
    assert "# Slide 1: Welcome" in text
    assert stand_in == "QUILL's own PowerPoint reader"


def test_any_markitdown_failure_falls_back_not_just_import_errors() -> None:
    def _explodes(path: Path) -> str:
        raise OSError("DLL load failed while importing onnxruntime_pybind11_state")

    outcome = convert_document(CORPUS / "budget.xlsx", deps=_Deps(markitdown=_explodes))
    assert outcome.tier == TIER_OWN_READER
    assert outcome.units == "2 sheets"


def test_html_and_csv_import_without_markitdown(tmp_path: Path) -> None:
    def _missing(path: Path) -> str:
        raise ImportError("markitdown not available")

    page = tmp_path / "page.html"
    page.write_text(
        "<html><head><title>T</title></head><body><h1>Hello</h1><ul><li>One</li></ul>"
        "</body></html>",
        encoding="utf-8",
    )
    table = tmp_path / "data.csv"
    table.write_text("Name,Score\nAda,91\n", encoding="utf-8")

    html = convert_document(page, deps=_Deps(markitdown=_missing))
    assert html.tier == TIER_OWN_READER
    assert "# Hello" in html.text and "One" in html.text

    csv_outcome = convert_document(table, deps=_Deps(markitdown=_missing))
    assert "| Name | Score |\n| --- | --- |\n| Ada | 91 |" in csv_outcome.text
