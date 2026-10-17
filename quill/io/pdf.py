"""Reading a PDF's text: every entry point's one reader.

File > Open in both editors (through :mod:`quill.core.pdf_open`), Import /
Convert Document's text-layer tier (:mod:`quill.io.docconvert`) and Document
Q&A all read a PDF here, so a page reads the same wherever it is opened.

**Per page, the most readable reading wins.** Each page is read first by
pdfplumber. When that reading scores at or above the fast-path threshold
(:data:`quill.io.pdf_score.FAST_PATH_SCORE`) and the page shows no sign of two
columns, it is kept: a clean page pays for one extractor. Otherwise the page is
*questionable* and pypdf reads it too, plainly and in layout mode, and -- when
the layout reading shows two columns -- once more column by column; when
pdfplumber's reading shows fake-bold doubling, pdfplumber reads it again with
the duplicates removed. Every reading is scored before and after repair
(:mod:`quill.io.pdf_select`) and the best one is kept. A non-empty bad
reading can no longer hide a better one.

**Only when the whole document still reads poorly** (score below
:data:`_MARKITDOWN_BELOW`) is MarkItDown asked, and its pages are scored by the
same rules and used one page at a time, only when they line up with the PDF's
own pages and read clearly better. MarkItDown cannot import in the shipped
runtime (it needs onnxruntime, which the runtime leaves out), so nothing
depends on it. Nothing here touches the network, and OCR is never run from
here: it stays a separate, opt-in step.

What is kept: the password (used for this read only, never stored), page order,
a form feed between pages (blank pages included, so page N is always the N-th
form-feed section), the 200-page cap, one page in memory at a time, and the
four failure outcomes -- no reader installed, encrypted, damaged, no text.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.io.markitdown_bridge import convert_with_markitdown
from quill.io.pdf_outline import (  # the outline cap stays reachable here, as it always was
    _PDF_MAX_OUTLINE_ENTRIES,  # noqa: F401
    extract_pdf_outline,
    extract_pdf_outline_entries,
)
from quill.io.pdf_score import DOUBTFUL_PAGE_SCORE, unreadable_count
from quill.io.pdf_select import (
    ENGINE_COLUMNS,
    ENGINE_MARKITDOWN,
    ENGINE_PDFPLUMBER,
    ENGINE_PDFPLUMBER_DEDUPE,
    ENGINE_PYPDF,
    ENGINE_PYPDF_LAYOUT,
    PAGE_BLANK,
    PAGE_FAILED,
    PAGE_IMAGE_ONLY,
    ROSTER,
    Candidate,
    PageChoice,
    choose_page,
    column_ordered,
    column_rows,
    fast_choice,
    has_doubled_letters,
    tidy_layout,
)

__all__ = [
    "PdfExtractionResult",
    "document_score",
    "doubtful_pages",
    "extract_pdf_outline",
    "extract_pdf_outline_entries",
    "extract_pdf_text",
    "format_pdf_document",
]

# PERF-13: bound how many pages we pull text from so a very large PDF cannot
# materialize every page at once. Pages beyond this cap are counted but skipped.
_PDF_MAX_PAGES = 200


#: Below this document score MarkItDown is offered the pages too.
_MARKITDOWN_BELOW = 50
#: How much better a MarkItDown page must score to replace the reader's page.
_MARKITDOWN_MARGIN = 10

#: Outcomes that are not text.
_FAILURE_ENGINES = frozenset({"unavailable", "encrypted", "damaged", "empty"})


@dataclass(slots=True)
class PdfExtractionResult:
    text: str
    quality_score: int
    engine: str
    page_count: int
    extracted_pages: int
    page_scores: list[int]
    #: Per page read: the engine whose reading was kept, or ``blank``,
    #: ``image-only`` or ``failed`` (:mod:`quill.io.pdf_select`).
    page_engines: list[str] = field(default_factory=list)
    #: Per page read: characters the page holds that could not be read as text
    #: (replacement characters, private-use glyphs, ``(cid:N)`` placeholders).
    page_unreadable: list[int] = field(default_factory=list)


# -- the sources ---------------------------------------------------------------- #


class _PlumberSource:
    """pdfplumber, one page at a time, each page released after it is read."""

    def __init__(self, pdf: Any) -> None:
        self.pdf = pdf
        self.pages = pdf.pages
        self.page_count = len(self.pages)

    def read(self, index: int) -> tuple[str, bool, bool]:
        """``(text, columns_suspected, has_image)`` for one page."""
        page = self.pages[index]
        text = page.extract_text() or ""
        return (
            text,
            _suspect_columns(getattr(page, "chars", None)),
            bool(getattr(page, "images", None)),
        )

    def read_deduplicated(self, index: int) -> str:
        page = self.pages[index]
        dedupe = getattr(page, "dedupe_chars", None)
        if not callable(dedupe):
            return ""
        return dedupe().extract_text() or ""

    def release(self, index: int) -> None:
        page = self.pages[index]
        for name in ("close", "flush_cache"):
            method = getattr(page, name, None)
            if callable(method):
                method()
                return

    def close(self) -> None:
        close = getattr(self.pdf, "close", None)
        if callable(close):
            close()


class _PypdfSource:
    """pypdf, plain and layout readings of one page."""

    def __init__(self, reader: Any) -> None:
        self.reader = reader
        self.pages = reader.pages
        self.page_count = len(self.pages)

    def read(self, index: int) -> str:
        return self.pages[index].extract_text() or ""

    def read_layout(self, index: int) -> str:
        try:
            return self.pages[index].extract_text(extraction_mode="layout") or ""
        except TypeError:  # an older pypdf, or a stand-in, without layout mode
            return ""

    def close(self) -> None:
        return None


def _open_pdfplumber(path: Path, *, password: str | None = None) -> _PlumberSource:
    """Raises ``ModuleNotFoundError`` when absent, anything else when unreadable."""
    import pdfplumber

    # A supplied user password unlocks an encrypted PDF; a wrong one raises,
    # which the caller records as a parse failure.
    pdf = pdfplumber.open(str(path), password=password or "")
    try:
        return _PlumberSource(pdf)
    except Exception:
        close = getattr(pdf, "close", None)
        if callable(close):
            close()
        raise


def _open_pypdf(path: Path, *, password: str | None = None) -> _PypdfSource:
    """Raises ``ModuleNotFoundError`` when absent, anything else when unreadable."""
    from pypdf import PdfReader  # type: ignore[import-not-found]

    reader = PdfReader(str(path))
    if getattr(reader, "is_encrypted", False):
        # An empty string unlocks a permissions-only ("empty user password") PDF;
        # a supplied password unlocks a locked one. A failed decrypt leaves the
        # reader locked so page access raises, recorded upstream as a failure.
        try:
            reader.decrypt(password or "")
        except Exception:  # noqa: BLE001 - decrypt API differs across pypdf versions
            pass
    return _PypdfSource(reader)


@dataclass(slots=True)
class _Opened:
    plumber: _PlumberSource | None = None
    pypdf: _PypdfSource | None = None
    available: bool = False
    failures: int = 0


@contextmanager
def _opened(path: Path, password: str | None) -> Iterator[_Opened]:
    opened = _Opened()
    for name, opener in (("plumber", _open_pdfplumber), ("pypdf", _open_pypdf)):
        try:
            source = opener(path, password=password)
        except ModuleNotFoundError:
            continue  # this extractor's package is absent
        except Exception:  # noqa: BLE001 - corrupt xref, locked, malformed object...
            opened.available = True
            opened.failures += 1
            continue
        opened.available = True
        setattr(opened, name, source)
    try:
        yield opened
    finally:
        for held in (opened.plumber, opened.pypdf):
            if held is not None:
                try:
                    held.close()
                except Exception:  # noqa: BLE001 - closing must not mask the result
                    pass


# -- one page -------------------------------------------------------------------- #


def _suspect_columns(chars: object) -> bool:
    """Whether pdfplumber's characters leave an empty vertical band mid-page.

    Two columns of text leave a gutter that almost no line crosses; one column
    of prose crosses the middle on nearly every line. A table leaves gutters
    too, which is fine: this only decides whether the page is worth comparing,
    never how it is read.
    """
    if not isinstance(chars, list) or len(chars) < 150:
        return False
    lines: dict[int, list[tuple[float, float]]] = {}
    for char in chars:
        if not str(char.get("text", "")).strip():
            continue
        try:
            span = (float(char["x0"]), float(char["x1"]))
            lines.setdefault(round(float(char["top"])), []).append(span)
        except (KeyError, TypeError, ValueError):
            continue
    if len(lines) < 6:
        return False
    left = min(x0 for spans in lines.values() for x0, _ in spans)
    right = max(x1 for spans in lines.values() for _, x1 in spans)
    width = right - left
    if width < 200:
        return False
    low, high = int(left + 0.3 * width), int(left + 0.7 * width)
    # How many lines cover each point of the middle band: each line's glyphs
    # merged into runs (a word gap of a few points still counts as covered),
    # then added to a difference array.
    delta = [0] * (high - low + 2)
    runs_by_line: list[list[list[float]]] = []
    for spans in lines.values():
        spans.sort()
        merged: list[list[float]] = []
        for x0, x1 in spans:
            if merged and x0 <= merged[-1][1] + 6:
                merged[-1][1] = max(merged[-1][1], x1)
            else:
                merged.append([x0, x1])
        runs_by_line.append(merged)
        for x0, x1 in merged:
            first, last = max(low, int(x0)), min(high, int(x1))
            if first <= last:
                delta[first - low] += 1
                delta[last - low + 1] -= 1
    allowance = max(1, len(lines) // 10)
    run = widest = covering = 0
    gap_end = low
    for offset, change in enumerate(delta[:-1]):
        covering += change
        run = run + 1 if covering <= allowance else 0
        if run > widest:
            widest, gap_end = run, low + offset
    if widest < 12:
        return False
    gap_start = gap_end - widest + 1
    left_lines = sum(1 for runs in runs_by_line if any(x1 <= gap_start for _, x1 in runs))
    right_lines = sum(1 for runs in runs_by_line if any(x0 >= gap_end for x0, _ in runs))
    return left_lines >= 3 and right_lines >= 3


def _read_page(index: int, opened: _Opened) -> tuple[PageChoice | None, str]:
    """The kept reading for page *index*, or ``None`` and the page's status."""
    candidates: list[Candidate] = []
    columns_suspected = has_image = False
    failed = 0
    plumber = opened.plumber if opened.plumber and index < opened.plumber.page_count else None
    reader = opened.pypdf if opened.pypdf and index < opened.pypdf.page_count else None
    if plumber is not None:
        try:
            raw, columns_suspected, has_image = plumber.read(index)
            if not columns_suspected:
                kept = fast_choice(ENGINE_PDFPLUMBER, raw)
                if kept is not None:
                    return kept, kept.engine
            candidates.append(Candidate(ENGINE_PDFPLUMBER, raw))
            if has_doubled_letters(raw):
                candidates.append(
                    Candidate(ENGINE_PDFPLUMBER_DEDUPE, plumber.read_deduplicated(index))
                )
        except Exception:  # noqa: BLE001 - one bad page must not sink the document
            failed += 1
        finally:
            try:
                plumber.release(index)
            except Exception:  # noqa: BLE001
                pass
    rows: list[tuple[str, str]] = []
    if reader is not None:
        try:
            plain = reader.read(index)
            if plumber is None:
                kept = fast_choice(ENGINE_PYPDF, plain)
                if kept is not None:
                    return kept, kept.engine
            candidates.append(Candidate(ENGINE_PYPDF, plain))
            if plain.strip() or any(c.raw.strip() for c in candidates):
                layout = reader.read_layout(index)
                gutter, rows = column_rows(layout)
                candidates.append(Candidate(ENGINE_PYPDF_LAYOUT, tidy_layout(layout)))
                if gutter is not None:
                    candidates.append(Candidate(ENGINE_COLUMNS, column_ordered(layout, gutter)))
        except Exception:  # noqa: BLE001
            failed += 1
    kept = choose_page(candidates, rows=rows)
    if kept is not None:
        return kept, kept.engine
    if failed and not candidates:
        return None, PAGE_FAILED
    return None, PAGE_IMAGE_ONLY if has_image else PAGE_BLANK


# -- the document ----------------------------------------------------------------- #


def document_score(page_scores: Sequence[int], page_engines: Sequence[str]) -> int:
    """One 0-100 number for the whole read: the pages' mean, discounted for pictures.

    Pages with text are averaged; a page that is only a picture (a likely scan)
    counts against the document by half a page, and a blank page not at all, so
    a clean report with a blank cover still scores 100.
    """
    texted = [
        score
        for score, engine in zip(page_scores, page_engines, strict=False)
        if engine not in {PAGE_BLANK, PAGE_IMAGE_ONLY, PAGE_FAILED}
    ]
    if not texted:
        return 0
    pictures = sum(1 for engine in page_engines if engine in {PAGE_IMAGE_ONLY, PAGE_FAILED})
    considered = len(texted) + pictures
    mean = sum(texted) / len(texted)
    return round(mean * (1 - 0.5 * pictures / considered))


def doubtful_pages(
    page_scores: Sequence[int],
    page_engines: Sequence[str],
    page_unreadable: Sequence[int] = (),
) -> list[int]:
    """1-based numbers of the pages that may read poorly.

    A page with text that scored below :data:`DOUBTFUL_PAGE_SCORE`, a page that
    is only a picture, or a page holding characters that could not be read (a
    private-use glyph is kept rather than guessed at, so the listener is told
    instead). A blank page is not doubtful: there is nothing on it.
    """
    numbers = []
    for number, score in enumerate(page_scores, start=1):
        engine = page_engines[number - 1] if number <= len(page_engines) else ""
        unreadable = page_unreadable[number - 1] if number <= len(page_unreadable) else 0
        if engine == PAGE_BLANK:
            continue
        if engine in {PAGE_IMAGE_ONLY, PAGE_FAILED} or score < DOUBTFUL_PAGE_SCORE or unreadable:
            numbers.append(number)
    return numbers


def _engine_label(page_engines: list[str]) -> str:
    used = {engine for engine in page_engines if engine in ROSTER}
    return " + ".join(engine for engine in ROSTER if engine in used)


def extract_pdf_text(path: Path, *, password: str | None = None) -> PdfExtractionResult:
    """Read *path*'s text, choosing each page's most readable reading.

    ``password`` (when the UI has collected one) unlocks the file for this read
    only and is never persisted. See the module docstring for how pages are
    chosen; the outcomes are text, or ``unavailable`` / ``encrypted`` /
    ``damaged`` / ``empty`` with a sentence saying what to do (#909, #58).
    """
    texts: list[str] = []
    scores: list[int] = []
    engines: list[str] = []
    with _opened(path, password) as opened:
        sources = [s for s in (opened.plumber, opened.pypdf) if s is not None]
        page_count = max((s.page_count for s in sources), default=0)
        for index in range(min(page_count, _PDF_MAX_PAGES)):
            kept, status = _read_page(index, opened)
            texts.append(kept.text if kept else "")
            scores.append(kept.score if kept else 0)
            engines.append(status)
        available, failures = opened.available, opened.failures
    extracted = sum(1 for text in texts if text.strip())
    if not extracted:
        if failures == 0 and sources and PAGE_FAILED in engines:
            failures = 1
        return _failure(
            path, password, available=available, parse_error=failures > 0, page_count=page_count
        )
    result = PdfExtractionResult(
        text=_joined(texts),
        quality_score=document_score(scores, engines),
        engine=_engine_label(engines),
        page_count=page_count,
        extracted_pages=extracted,
        page_scores=scores,
        page_engines=engines,
        page_unreadable=[unreadable_count(text) for text in texts],
    )
    if result.quality_score < _MARKITDOWN_BELOW and not password and page_count <= _PDF_MAX_PAGES:
        return _with_markitdown_pages(path, result, texts)
    return result


def _joined(texts: list[str]) -> str:
    """Pages joined by form feeds (#872), blank pages kept as empty sections."""
    text = "\f".join(page.strip("\n") for page in texts).strip(" \t\r\n")
    return text + "\n" if text.strip() else ""


def _with_markitdown_pages(
    path: Path, result: PdfExtractionResult, texts: list[str]
) -> PdfExtractionResult:
    """Offer each page MarkItDown's reading; keep it only where it reads clearly better.

    MarkItDown separates pages with form feeds too. Its reading is used only
    when its pages line up with the PDF's (a trailing blank page may be
    missing), so page boundaries survive; otherwise it is not used at all.
    """
    try:
        other = convert_with_markitdown(path)
    except (ImportError, ValueError, RuntimeError, OSError):
        return result
    pages = other.rstrip().split("\f")
    count = len(texts)
    if len(pages) > count or any(texts[i].strip() for i in range(len(pages), count)):
        return result
    pages += [""] * (count - len(pages))
    scores, engines = list(result.page_scores), list(result.page_engines)
    replaced = False
    for index, page in enumerate(pages):
        if not page.strip():
            continue
        contest = choose_page([
            Candidate(engines[index], texts[index]),
            Candidate(ENGINE_MARKITDOWN, page),
        ])
        if contest is None or contest.engine != ENGINE_MARKITDOWN:
            continue
        if texts[index].strip() and contest.score < scores[index] + _MARKITDOWN_MARGIN:
            continue
        texts[index], scores[index], engines[index] = contest.text, contest.score, ENGINE_MARKITDOWN
        replaced = True
    if not replaced:
        return result
    return PdfExtractionResult(
        text=_joined(texts),
        quality_score=document_score(scores, engines),
        engine=_engine_label(engines),
        page_count=result.page_count,
        extracted_pages=sum(1 for text in texts if text.strip()),
        page_scores=scores,
        page_engines=engines,
        page_unreadable=[unreadable_count(text) for text in texts],
    )


def _failure(
    path: Path, password: str | None, *, available: bool, parse_error: bool, page_count: int
) -> PdfExtractionResult:
    # Four outcomes (#909, #58): (1) no extractor installed, (2) an encrypted PDF,
    # (3) a damaged PDF that parse-fails, and (4) a scanned/image-only PDF with no
    # text layer. They are different problems with different remedies; telling
    # someone with a corrupt or locked file to run OCR is the wrong fix.
    if not available:
        message = (
            f"(No PDF text extractor is installed, so QUILL could not read "
            f"{path.name}. Open Help > Download Optional Components and download "
            f'"PDF and Office text extraction".)\n'
        )
        engine = "unavailable"
    elif _is_encrypted_pdf(path):
        # ``password`` distinguishes "no password tried yet" (prompt for one) from
        # "the password just tried was wrong" (re-prompt); both keep
        # ``engine="encrypted"`` so the open flow knows to ask. Never stored.
        if password:
            message = (
                f"(The password for {path.name} was not correct, so the encrypted "
                f"PDF could not be opened. Check the password and try again.)\n"
            )
        else:
            message = (
                f"({path.name} is encrypted (password-protected). Enter its password "
                f"to open it; QUILL uses the password only to unlock this file and "
                f"never stores it.)\n"
            )
        engine = "encrypted"
    elif parse_error:
        message = (
            f"({path.name} could not be parsed -- it is likely damaged or corrupt. "
            f"OCR will not help a corrupt file. Try re-downloading or re-exporting it "
            f"from the original application; a tool like `qpdf --check` can confirm "
            f"whether the file is still valid.)\n"
        )
        engine = "damaged"
    else:
        message = (
            f"(No selectable text was found in {path.name}. It is likely a scanned "
            f"or image-only PDF — use File > Import and choose OCR to read it.)\n"
        )
        engine = "empty"
    return PdfExtractionResult(
        text=message,
        quality_score=0,
        engine=engine,
        # A scanned PDF still has pages, and the OCR offer says how many.
        page_count=page_count if engine == "empty" else 0,
        extracted_pages=0,
        page_scores=[],
    )


def _is_encrypted_pdf(path: Path) -> bool:
    """Return True when *path* is a password-protected PDF (#58).

    Uses pypdf's ``is_encrypted`` flag and attempts an empty-user-password decrypt:
    a permissions-only "encrypted" PDF (empty password, common) is still readable
    and must not be reported as encrypted, so only treat it as locked when the
    empty password fails to unlock it. Any construction/parse failure reads as
    "not encrypted" (a corrupt file is handled by the ``damaged`` branch instead).
    """
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return False
    try:
        reader = PdfReader(str(path))
    except Exception:  # noqa: BLE001 - corrupt/unreadable -> not our encryption path
        return False
    if not getattr(reader, "is_encrypted", False):
        return False
    try:
        matched = reader.decrypt("")
    except Exception:  # noqa: BLE001 - decrypt API differs across pypdf versions
        return True
    return not bool(matched)


def format_pdf_document(path: Path | PdfExtractionResult) -> str:
    """Return the PDF's extracted text -- the text only, with nothing prepended.

    #1279: the extract used to open with a "# PDF Extract / Engine / Quality
    score" banner, so every PDF the user opened began with text that is not in
    their file (and the AI document-QA path fed that banner to the model). The
    provenance lives in ``source_metadata`` instead, where the open announcement
    (:func:`quill.core.intake.build_intake_summary`) and the Document Intake
    Report (:func:`quill.core.intake.build_intake_report`) report engine, page
    counts, quality score and the pages that may read poorly.

    This used to try MarkItDown itself and keep whichever answer was *longer*;
    the reader now offers MarkItDown the pages, scored by the same rules, so
    Document Q&A reads exactly what File > Open shows.
    """
    result = path if isinstance(path, PdfExtractionResult) else extract_pdf_text(path)
    return result.text.rstrip(" \t\r\n") + "\n"  # a blank last page keeps its form feed
