"""GATE-PERF for PDFs: a 200-page PDF opens within a ceiling, in both editors.

QUILL and QUILL Lite open a PDF through one shared path -- ``quill.core.pdf_open``
over QUILL's reader in ``quill.io.pdf`` -- and both read at most 200 pages
(``_PDF_MAX_PAGES``, PERF-13). So 200 pages is the most either editor is ever
asked to read at once, and this gate times exactly that: QUILL Lite's whole
prepare step (``open_prepare.prepare``, which is the reader plus the outline
plus the scanned check), then the page machinery both editors run once the text
is in the window -- the Go To list of pages and the Page cell at the last page.

Against a ceiling, not against the other editor, for the reason the 50 MB gate
gives (``test_large_document_budget.py``): comparing the two would pass a build
where both had become slow together. The ceiling is generous on purpose. On the
development machine, with other work running (31 % CPU), the 200 pages opened
in 6.3 seconds -- about 31 ms a page -- on 2026-10-17; the ceiling is 150 ms a
page, about five times that. What it catches is a change of shape: a reader that
pays for every extractor on clean pages, or page lookups that rescan the text
per page, come in many times over, not slightly.

Time only. Memory has its own gate on 60 pages
(``tests/unit/io/test_pdf_corpus.py``), traced in a separate read, because a
traced read runs four times slower and would make this one measure the tracer.
"""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import pytest

pytest.importorskip("pdfplumber")
pytest.importorskip("pypdf")

from quill.core.lite.open_prepare import PLAIN, prepare  # noqa: E402
from quill.core.navigation import page_position  # noqa: E402
from quill.core.pdf_open import page_places  # noqa: E402

_PAGES = 200
#: Per page, for the whole open. About five times the loaded development machine.
_OPEN_MS_PER_PAGE = 150
#: The page machinery once the text is in: the Page kind's rows and the Page
#: cell. Linear scans of a few hundred kilobytes; a per-page rescan is what fails.
_PAGES_MACHINERY_MS = 500

_CORPUS = Path(__file__).resolve().parents[2] / "corpus" / "pdf"


def _build_long(path: Path, pages: int) -> Path:
    spec = importlib.util.spec_from_file_location(
        "build_pdf_corpus", _CORPUS / "build_pdf_corpus.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_long(path, pages)


@pytest.mark.perf
def test_a_200_page_pdf_opens_within_the_ceiling(tmp_path: Path) -> None:
    path = _build_long(tmp_path / "two-hundred.pdf", _PAGES)
    # The reader's imports are paid once per process, on the first PDF of a
    # session; this gate is about the pages, so they are paid before the clock.
    prepare(_build_long(tmp_path / "warm.pdf", 1), PLAIN)

    start = time.perf_counter()
    prepared = prepare(path, PLAIN)
    open_ms = (time.perf_counter() - start) * 1000

    found = prepared.pdf
    assert found is not None and found.page_count == _PAGES
    assert found.extracted_pages == _PAGES  # all 200: the cap is not reached early
    assert prepared.text.count("\f") == _PAGES - 1
    assert open_ms / _PAGES < _OPEN_MS_PER_PAGE, (
        f"{open_ms / _PAGES:.0f} ms a page for {_PAGES} pages; the ceiling is "
        f"{_OPEN_MS_PER_PAGE}. Check the reader's clean-page path first."
    )

    start = time.perf_counter()
    rows = page_places(prepared.text)
    where = page_position(prepared.text, len(prepared.text) - 1)
    pages_ms = (time.perf_counter() - start) * 1000
    assert len(rows) == _PAGES and rows[-1][0] == str(_PAGES)
    assert where == (_PAGES, _PAGES)
    assert pages_ms < _PAGES_MACHINERY_MS
