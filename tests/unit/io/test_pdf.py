"""The PDF reader (quill.io.pdf) with stand-in extractors.

The real-file cases live in ``test_pdf_corpus.py``; these pin the decisions --
which reading wins a page, when the other extractors are skipped, when
MarkItDown is asked and when it is ignored, and the four failure outcomes --
with fakes, so each one is exact.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from quill.core.navigation import page_start_for_number, page_starts
from quill.io import pdf as pdf_module
from quill.io.pdf import (
    PdfExtractionResult,
    document_score,
    doubtful_pages,
    format_pdf_document,
)

_CLEAN = (
    "The committee met on a Tuesday, which was unusual, and agreed that the report "
    "would be circulated before the end of the month. Nobody objected to it."
)
_SPACED = "T h e c o m m i t t e e m e t o n a T u e s d a y w h i c h w a s"


class _FakePlumber:
    """Stands in for ``quill.io.pdf._PlumberSource``."""

    def __init__(self, pages: list[str], *, columns: bool = False, images=()) -> None:
        self.texts = pages
        self.page_count = len(pages)
        self.columns = columns
        self.images = set(images)
        self.read_pages: list[int] = []
        self.released: list[int] = []

    def read(self, index: int) -> tuple[str, bool, bool]:
        self.read_pages.append(index)
        return self.texts[index], self.columns, index in self.images

    def read_deduplicated(self, index: int) -> str:
        return self.texts[index]

    def release(self, index: int) -> None:
        self.released.append(index)

    def close(self) -> None:
        return None


class _FakePypdf:
    """Stands in for ``quill.io.pdf._PypdfSource``."""

    def __init__(self, pages: list[str], layout: list[str] | None = None) -> None:
        self.texts = pages
        self.layouts = layout or pages
        self.page_count = len(pages)
        self.read_pages: list[int] = []

    def read(self, index: int) -> str:
        self.read_pages.append(index)
        return self.texts[index]

    def read_layout(self, index: int) -> str:
        return self.layouts[index]

    def close(self) -> None:
        return None


def _use(monkeypatch, plumber=None, pypdf=None) -> None:
    def _opener(source):
        def _open(_path: Path, *, password: str | None = None):
            if source is None:
                raise ModuleNotFoundError("absent")
            if isinstance(source, Exception):
                raise source
            return source

        return _open

    monkeypatch.setattr(pdf_module, "_open_pdfplumber", _opener(plumber))
    monkeypatch.setattr(pdf_module, "_open_pypdf", _opener(pypdf))


def _no_markitdown(monkeypatch) -> None:
    def _absent(_path: Path) -> str:
        raise ImportError("markitdown not available")

    monkeypatch.setattr(pdf_module, "convert_with_markitdown", _absent)


# -- choosing a page's reading ------------------------------------------------------ #


def test_a_poor_first_reading_loses_to_a_cleaner_one(monkeypatch, tmp_path: Path) -> None:
    # The old reader kept the first non-empty answer: pdfplumber's letters.
    _no_markitdown(monkeypatch)
    _use(monkeypatch, _FakePlumber([_SPACED]), _FakePypdf([_CLEAN]))
    result = pdf_module.extract_pdf_text(tmp_path / "spaced.pdf")
    assert result.text.startswith("The committee met")
    assert result.page_engines == ["pypdf"]
    assert result.page_scores == [100]


def test_a_clean_first_reading_takes_the_fast_path(monkeypatch, tmp_path: Path) -> None:
    pypdf = _FakePypdf([_CLEAN, _CLEAN])
    _use(monkeypatch, _FakePlumber([_CLEAN, _CLEAN]), pypdf)
    result = pdf_module.extract_pdf_text(tmp_path / "clean.pdf")
    assert pypdf.read_pages == []  # pypdf never asked: clean pages pay once
    assert result.page_engines == ["pdfplumber", "pdfplumber"]
    assert result.quality_score == 100


def test_suspected_columns_make_a_clean_page_questionable(monkeypatch, tmp_path: Path) -> None:
    _no_markitdown(monkeypatch)
    pypdf = _FakePypdf([_CLEAN])
    _use(monkeypatch, _FakePlumber([_CLEAN], columns=True), pypdf)
    pdf_module.extract_pdf_text(tmp_path / "columns.pdf")
    assert pypdf.read_pages == [0]


def test_two_columns_run_together_lose_to_the_reading_that_follows_them(
    monkeypatch, tmp_path: Path
) -> None:
    _no_markitdown(monkeypatch)
    left = ["The river rose slowly through the night", "and by morning the lower fields"]
    right = ["Repairs to the bridge will begin in spring", "once the engineers have finished"]
    interleaved = "\n".join(f"{a} {b}" for a, b in zip(left, right, strict=True))
    layout = "\n".join(f"{a:<50}{b}" for a, b in zip(left * 2, right * 2, strict=True))
    in_order = "\n".join(left * 2 + right * 2)
    _use(
        monkeypatch,
        _FakePlumber([interleaved * 2], columns=True),
        _FakePypdf([in_order], layout=[layout]),
    )
    result = pdf_module.extract_pdf_text(tmp_path / "columns.pdf")
    assert result.page_engines == ["pypdf"]
    assert "night\nand by morning" in result.text


def test_pdfplumber_alone_still_reads(monkeypatch, tmp_path: Path) -> None:
    _use(monkeypatch, _FakePlumber(["Page one text here", "Page two text here"]), None)
    result = pdf_module.extract_pdf_text(tmp_path / "a.pdf")
    assert result.text.count("\f") == 1
    assert len(page_starts(result.text)) == 2
    assert result.engine == "pdfplumber"


def test_pypdf_alone_takes_its_own_fast_path(monkeypatch, tmp_path: Path) -> None:
    pypdf = _FakePypdf(["Page one text here", "Page two text here"])
    _use(monkeypatch, None, pypdf)
    result = pdf_module.extract_pdf_text(tmp_path / "a.pdf")
    assert result.engine == "pypdf"
    assert result.text.count("\f") == 1


def test_blank_edge_pages_keep_their_place(monkeypatch, tmp_path: Path) -> None:
    # The old reader stripped a leading form feed, so page 2's text became page 1.
    _use(monkeypatch, _FakePlumber(["", _CLEAN, ""]), _FakePypdf(["", _CLEAN, ""]))
    result = pdf_module.extract_pdf_text(tmp_path / "edges.pdf")
    assert page_start_for_number(result.text, 2) == 1
    assert result.text[1:].startswith("The committee")
    assert result.page_engines == ["blank", "pdfplumber", "blank"]
    assert result.quality_score == 100  # a blank cover is not a fault
    assert doubtful_pages(result.page_scores, result.page_engines) == []


def test_an_image_only_page_is_doubtful_and_lowers_the_score(monkeypatch, tmp_path: Path) -> None:
    _use(
        monkeypatch,
        _FakePlumber([_CLEAN, "", _CLEAN], images={1}),
        _FakePypdf([_CLEAN, "", _CLEAN]),
    )
    result = pdf_module.extract_pdf_text(tmp_path / "mixed.pdf")
    assert result.page_engines == ["pdfplumber", "image-only", "pdfplumber"]
    assert doubtful_pages(result.page_scores, result.page_engines) == [2]
    assert result.quality_score == 83


def test_unreadable_characters_are_kept_and_counted(monkeypatch, tmp_path: Path) -> None:
    text = "The net bo holds a sign that has no letter in it at all."
    _no_markitdown(monkeypatch)
    _use(monkeypatch, _FakePlumber([text]), _FakePypdf([text]))
    result = pdf_module.extract_pdf_text(tmp_path / "pua.pdf")
    assert "net bo" in result.text
    assert result.page_unreadable == [2]
    assert doubtful_pages(result.page_scores, result.page_engines, result.page_unreadable) == [1]


def test_the_page_cap_reads_no_more_than_two_hundred(monkeypatch, tmp_path: Path) -> None:
    plumber = _FakePlumber([f"Page {n} has a little text on it." for n in range(1000)])
    _use(monkeypatch, plumber, None)
    result = pdf_module.extract_pdf_text(tmp_path / "huge.pdf")
    assert result.page_count == 1000
    assert len(result.page_scores) == pdf_module._PDF_MAX_PAGES
    assert max(plumber.read_pages) == pdf_module._PDF_MAX_PAGES - 1
    # One page in memory at a time: every page read is released.
    assert plumber.released == plumber.read_pages


def test_one_failing_page_does_not_sink_the_document(monkeypatch, tmp_path: Path) -> None:
    class _Flaky(_FakePlumber):
        def read(self, index: int):
            if index == 1:
                raise ValueError("bad content stream")
            return super().read(index)

    _no_markitdown(monkeypatch)
    _use(monkeypatch, _Flaky([_CLEAN, _CLEAN, _CLEAN]), None)
    result = pdf_module.extract_pdf_text(tmp_path / "flaky.pdf")
    assert result.page_engines == ["pdfplumber", "failed", "pdfplumber"]
    assert result.text.count("\f") == 2


# -- MarkItDown, scored by the same rules ------------------------------------------ #


def test_markitdown_is_not_asked_about_a_clean_document(monkeypatch, tmp_path: Path) -> None:
    def _never(_path: Path) -> str:
        raise AssertionError("MarkItDown asked about a clean PDF")

    monkeypatch.setattr(pdf_module, "convert_with_markitdown", _never)
    _use(monkeypatch, _FakePlumber([_CLEAN]), _FakePypdf([_CLEAN]))
    assert pdf_module.extract_pdf_text(tmp_path / "clean.pdf").engine == "pdfplumber"


def test_markitdown_pages_replace_only_pages_they_read_clearly_better(
    monkeypatch, tmp_path: Path
) -> None:
    junk = "�" * 40
    monkeypatch.setattr(pdf_module, "convert_with_markitdown", lambda _p: f"{_CLEAN}\f{junk}\n")
    _use(monkeypatch, _FakePlumber([junk, junk]), _FakePypdf([junk, junk]))
    result = pdf_module.extract_pdf_text(tmp_path / "junk.pdf")
    assert result.page_engines[0] == "markitdown"
    assert result.text.startswith("The committee")
    assert result.page_scores[0] == 100  # scored, not handed 85
    assert result.page_engines[1] != "markitdown"
    assert result.text.count("\f") == 1


def test_markitdown_that_loses_page_boundaries_is_not_used(monkeypatch, tmp_path: Path) -> None:
    junk = "�" * 40
    monkeypatch.setattr(
        pdf_module, "convert_with_markitdown", lambda _p: f"{_CLEAN}\f{_CLEAN}\f{_CLEAN}\n"
    )
    _use(monkeypatch, _FakePlumber([junk, junk]), _FakePypdf([junk, junk]))
    result = pdf_module.extract_pdf_text(tmp_path / "junk.pdf")
    assert "markitdown" not in result.page_engines


def test_markitdown_missing_from_the_runtime_changes_nothing(monkeypatch, tmp_path: Path) -> None:
    junk = "�" * 40
    _no_markitdown(monkeypatch)
    _use(monkeypatch, _FakePlumber([junk]), _FakePypdf([junk]))
    result = pdf_module.extract_pdf_text(tmp_path / "junk.pdf")
    assert result.quality_score == 0
    assert result.engine == "pdfplumber"


def test_format_pdf_document_returns_text_without_a_banner(monkeypatch, tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "quill.io.pdf.extract_pdf_text",
        lambda _path: PdfExtractionResult(
            text="Extracted PDF text\n",
            quality_score=12,
            engine="pypdf",
            page_count=1,
            extracted_pages=1,
            page_scores=[12],
        ),
    )

    def _never(_path: Path) -> str:
        raise AssertionError("format_pdf_document must not run its own MarkItDown")

    monkeypatch.setattr(pdf_module, "convert_with_markitdown", _never)
    formatted = format_pdf_document(pdf_path)
    # #1279: the extract is the PDF's text and nothing else.
    assert formatted == "Extracted PDF text\n"


def test_document_score_is_bounded_and_ignores_blank_pages() -> None:
    assert document_score([], []) == 0
    assert document_score([100, 0], ["pdfplumber", "blank"]) == 100
    assert document_score([100, 0], ["pdfplumber", "image-only"]) == 75
    assert 0 <= document_score([0, 0], ["pypdf", "pypdf"]) <= 100


# -- the four failure outcomes ----------------------------------------------------- #


def test_extract_pdf_text_distinguishes_missing_extractor_from_scanned_pdf(
    monkeypatch, tmp_path: Path
) -> None:
    # #909: no extractor installed vs. an extractor that ran but found no text
    # (scanned/image PDF) are different problems with different remedies.
    _use(monkeypatch, None, None)
    missing = pdf_module.extract_pdf_text(tmp_path / "doc.pdf")
    assert missing.engine == "unavailable"
    assert "not" in missing.text.lower() and "install" in missing.text.lower()

    _use(monkeypatch, _FakePlumber([""], images={0}), _FakePypdf([""]))
    scanned = pdf_module.extract_pdf_text(tmp_path / "scan.pdf")
    assert scanned.engine == "empty"
    assert "ocr" in scanned.text.lower()
    assert scanned.page_count == 1  # the OCR offer can say how many pages


def test_encrypted_pdf_reports_encrypted_not_scanned(monkeypatch, tmp_path: Path) -> None:
    # #58: a password-protected PDF must be reported as encrypted, not scanned.
    monkeypatch.setattr(pdf_module, "_is_encrypted_pdf", lambda _path: True)
    _use(monkeypatch, ValueError("password required"), ValueError("password required"))
    result = pdf_module.extract_pdf_text(tmp_path / "locked.pdf")
    assert result.engine == "encrypted"
    assert "encrypted" in result.text.lower() and "password" in result.text.lower()
    assert "ocr" not in result.text.lower()


def test_damaged_pdf_reports_damaged_not_scanned(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pdf_module, "_is_encrypted_pdf", lambda _path: False)
    _use(monkeypatch, ValueError("malformed cross-reference table"), _FakePypdf([]))
    result = pdf_module.extract_pdf_text(tmp_path / "corrupt.pdf")
    assert result.engine == "damaged"
    assert "damaged" in result.text.lower() or "corrupt" in result.text.lower()
    assert "choose ocr" not in result.text.lower()
    assert "file > import" not in result.text.lower()


def test_pages_that_all_fail_read_as_damaged(monkeypatch, tmp_path: Path) -> None:
    class _Broken(_FakePypdf):
        def read(self, index: int) -> str:
            raise ValueError("cannot decode page")

    monkeypatch.setattr(pdf_module, "_is_encrypted_pdf", lambda _path: False)
    _use(monkeypatch, None, _Broken(["", ""]))
    assert pdf_module.extract_pdf_text(tmp_path / "broken.pdf").engine == "damaged"


def test_extract_pdf_text_reports_wrong_password_distinctly(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pdf_module, "_is_encrypted_pdf", lambda _path: True)
    _use(monkeypatch, ValueError("bad password"), ValueError("bad password"))
    result = pdf_module.extract_pdf_text(tmp_path / "locked.pdf", password="wrong")
    assert result.engine == "encrypted"
    assert "not correct" in result.text.lower()
    assert "ocr" not in result.text.lower()


def test_malformed_pdf_returns_text_not_a_crash(monkeypatch, tmp_path: Path) -> None:
    # M-10: a parse error inside an extractor must never reach the caller.
    fake_pdfplumber = types.ModuleType("pdfplumber")

    def _open(_path: str, password: str = "") -> object:
        raise ValueError("malformed cross-reference table")

    fake_pdfplumber.open = _open  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pdfplumber", fake_pdfplumber)

    class _EmptyReader:
        is_encrypted = False

        def __init__(self, _path: str) -> None:
            self.pages: list[object] = []

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _EmptyReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)

    result = pdf_module.extract_pdf_text(tmp_path / "corrupt.pdf")
    assert isinstance(result.text, str)
    assert result.engine == "damaged"


# -- the real openers, with stand-in packages -------------------------------------- #


def test_the_password_reaches_pdfplumber(monkeypatch, tmp_path: Path) -> None:
    seen: list[str] = []

    class _Page:
        chars: list[object] = []
        images: list[object] = []

        def extract_text(self) -> str:
            return "Unlocked page text"

        def close(self) -> None:
            return None

    class _Pdf:
        pages = [_Page()]

        def close(self) -> None:
            return None

    def _open(_path: str, password: str = "") -> _Pdf:
        seen.append(password)
        return _Pdf()

    fake = types.ModuleType("pdfplumber")
    fake.open = _open  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pdfplumber", fake)
    monkeypatch.setitem(sys.modules, "pypdf", None)

    result = pdf_module.extract_pdf_text(tmp_path / "locked.pdf", password="s3cret")
    assert seen == ["s3cret"]
    assert result.engine == "pdfplumber"
    assert "Unlocked page text" in result.text


def test_pypdf_decrypts_with_the_supplied_password(monkeypatch, tmp_path: Path) -> None:
    seen: list[str] = []

    class _Page:
        def extract_text(self, **_kwargs: object) -> str:
            return "Decrypted text on the page"

    class _Reader:
        is_encrypted = True

        def __init__(self, _path: str) -> None:
            self.pages = [_Page()]

        def decrypt(self, pw: str) -> int:
            seen.append(pw)
            return 1

    fake = types.ModuleType("pypdf")
    fake.PdfReader = _Reader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake)
    monkeypatch.setitem(sys.modules, "pdfplumber", None)

    result = pdf_module.extract_pdf_text(tmp_path / "locked.pdf", password="open-me")
    assert seen == ["open-me"]
    assert "Decrypted" in result.text


@pytest.mark.parametrize("absent", ["pdfplumber", "pypdf"])
def test_a_missing_package_is_not_a_failure(monkeypatch, tmp_path: Path, absent: str) -> None:
    monkeypatch.setitem(sys.modules, absent, None)
    with pytest.raises(ModuleNotFoundError):
        (pdf_module._open_pdfplumber if absent == "pdfplumber" else pdf_module._open_pypdf)(
            tmp_path / "x.pdf"
        )


# -- the outline and encryption probes ---------------------------------------------- #


def test_is_encrypted_pdf_false_for_plain_pdf_via_stub(monkeypatch, tmp_path: Path) -> None:
    # A readable (non-encrypted) PDF reads is_encrypted=False -> not encrypted.
    class _PlainReader:
        is_encrypted = False

        def __init__(self, _path: str) -> None: ...

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _PlainReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    assert pdf_module._is_encrypted_pdf(tmp_path / "plain.pdf") is False


def test_is_encrypted_pdf_true_when_empty_password_fails(monkeypatch, tmp_path: Path) -> None:
    class _LockedReader:
        is_encrypted = True

        def __init__(self, _path: str) -> None: ...

        def decrypt(self, _pw: str) -> int:
            return 0  # no password matched

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _LockedReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    assert pdf_module._is_encrypted_pdf(tmp_path / "locked.pdf") is True


def test_is_encrypted_pdf_false_when_empty_password_unlocks(monkeypatch, tmp_path: Path) -> None:
    # Permissions-only encryption (empty user password opens it) is readable ->
    # must NOT be reported as encrypted.
    class _EmptyPasswordReader:
        is_encrypted = True

        def __init__(self, _path: str) -> None: ...

        def decrypt(self, _pw: str) -> int:
            return 1  # user password matched

    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = _EmptyPasswordReader  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
    assert pdf_module._is_encrypted_pdf(tmp_path / "perm.pdf") is False


def test_is_encrypted_pdf_false_when_pypdf_absent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "pypdf", None)
    assert pdf_module._is_encrypted_pdf(tmp_path / "any.pdf") is False


class _OutlineDest:
    def __init__(self, title: object) -> None:
        self.title = title


def _install_outline_reader(monkeypatch, reader_cls: type) -> None:
    fake_pypdf = types.ModuleType("pypdf")
    fake_pypdf.PdfReader = reader_cls  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)


def test_extract_pdf_outline_flattens_tree_and_makes_pages_one_based(
    monkeypatch, tmp_path: Path
) -> None:
    d1 = _OutlineDest("Chapter 1")
    d2 = _OutlineDest("Section 1.1")
    d3 = _OutlineDest("Chapter 2")

    class _Reader:
        is_encrypted = False

        def __init__(self, _path: str) -> None:
            # pypdf nests child bookmarks as a sub-list after their parent.
            self.outline = [d1, [d2], d3]
            self._pages = {id(d1): 0, id(d2): 1, id(d3): 5}

        def get_destination_page_number(self, dest: object) -> int:
            return self._pages[id(dest)]

    _install_outline_reader(monkeypatch, _Reader)

    outline = pdf_module.extract_pdf_outline(tmp_path / "book.pdf")
    assert outline == [("Chapter 1", 1), ("Section 1.1", 2), ("Chapter 2", 6)]


def test_extract_pdf_outline_skips_blank_titles_and_unresolvable_dests(
    monkeypatch, tmp_path: Path
) -> None:
    good = _OutlineDest("Intro")
    blank = _OutlineDest("   ")
    broken = _OutlineDest("Broken")

    class _Reader:
        is_encrypted = False

        def __init__(self, _path: str) -> None:
            self.outline = [good, blank, broken]

        def get_destination_page_number(self, dest: object) -> int:
            if dest is broken:
                raise ValueError("no destination")
            return 0

    _install_outline_reader(monkeypatch, _Reader)

    assert pdf_module.extract_pdf_outline(tmp_path / "book.pdf") == [("Intro", 1)]


def test_extract_pdf_outline_returns_empty_when_pypdf_absent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "pypdf", None)
    assert pdf_module.extract_pdf_outline(tmp_path / "book.pdf") == []


def test_extract_pdf_outline_decrypts_with_password(monkeypatch, tmp_path: Path) -> None:
    seen: list[str] = []
    dest = _OutlineDest("Locked Chapter")

    class _Reader:
        is_encrypted = True

        def __init__(self, _path: str) -> None:
            self.outline = [dest]

        def decrypt(self, pw: str) -> int:
            seen.append(pw)
            return 1

        def get_destination_page_number(self, _dest: object) -> int:
            return 2

    _install_outline_reader(monkeypatch, _Reader)

    outline = pdf_module.extract_pdf_outline(tmp_path / "locked.pdf", password="pw")
    assert seen == ["pw"]
    assert outline == [("Locked Chapter", 3)]


def test_extract_pdf_outline_caps_entry_count(monkeypatch, tmp_path: Path) -> None:
    class _Reader:
        is_encrypted = False

        def __init__(self, _path: str) -> None:
            count = pdf_module._PDF_MAX_OUTLINE_ENTRIES + 50
            self.outline = [_OutlineDest(f"H{i}") for i in range(count)]

        def get_destination_page_number(self, _dest: object) -> int:
            return 0

    _install_outline_reader(monkeypatch, _Reader)

    outline = pdf_module.extract_pdf_outline(tmp_path / "huge-toc.pdf")
    assert len(outline) == pdf_module._PDF_MAX_OUTLINE_ENTRIES


def test_extract_pdf_outline_entries_keep_the_nesting(monkeypatch, tmp_path: Path) -> None:
    d1 = _OutlineDest("Chapter 1")
    d2 = _OutlineDest("Section 1.1")
    d3 = _OutlineDest("Detail")
    d4 = _OutlineDest("Chapter 2")

    class _Reader:
        is_encrypted = False

        def __init__(self, _path: str) -> None:
            self.outline = [d1, [d2, [d3]], d4]
            self._pages = {id(d1): 0, id(d2): 1, id(d3): 1, id(d4): 5}

        def get_destination_page_number(self, dest: object) -> int:
            return self._pages[id(dest)]

    _install_outline_reader(monkeypatch, _Reader)

    entries = pdf_module.extract_pdf_outline_entries(tmp_path / "book.pdf")
    assert entries == [
        ("Chapter 1", 1, 1),
        ("Section 1.1", 2, 2),
        ("Detail", 2, 3),
        ("Chapter 2", 6, 1),
    ]
    # The pairs keep the shape every store already holds.
    assert pdf_module.extract_pdf_outline(tmp_path / "book.pdf") == [
        (title, page) for title, page, _level in entries
    ]
