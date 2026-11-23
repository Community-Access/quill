"""The test documents a live run sends to Scribe.

Two sets:

* **Ours**, made by code in ``tests/corpus/scribe_live/build_scribe_live_sources.py``
  and committed there (their text is our own, dedicated to the public domain,
  CC0). One for each of the 23 input types Scribe takes
  (:data:`quill.core.scribe.inputs.ACCEPTED_TYPES`), plus the hard cases: a
  long document, tables, pictures with and without alt text, a document in
  Spanish, mathematics, a password-protected PDF, a web page (QUILL refuses
  it before uploading) and a ``.pdf`` that is not a PDF (Scribe should
  refuse it).
* **Pneuma's four**, read from the extracted corpus on this computer
  (``<corpus>/sources/``) and never copied into the repository (Jeff,
  2026-11-23). Their stems are the ones the replay tests name, so a run
  that includes them can be replayed by those tests unchanged.

wx-free, no network.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

#: The outcomes a source is planned for.
CONVERTS = "converts"
REFUSED_HERE = "refused_here"  # QUILL refuses it before anything is sent
REFUSED_BY_SCRIBE = "refused_by_scribe"  # sent; Scribe should answer with an error

OURS = "ours"
PNEUMA = "pneuma"

#: The password of our own password-protected test PDF. A test value for a
#: file we made, not a credential: it unlocks nothing else.
LOCKED_PDF_TEST_PASSWORD = "riverbend-test-only"  # gitleaks:allow (a test fixture value)


@dataclass(frozen=True, slots=True)
class Source:
    """One test document."""

    stem: str
    file: str
    kind: str  # Scribe's name for the input type
    pages: int  # roughly what Scribe will charge for one upload
    origin: str
    note: str
    expect: str = CONVERTS
    password: str = ""
    path: Path | None = None

    @property
    def costs(self) -> bool:
        """True when uploading it can use credit (anything sent to Scribe)."""
        return self.expect != REFUSED_HERE


def _ours(stem: str, ext: str, kind: str, pages: int, note: str, **extra: str) -> Source:
    return Source(stem, f"{stem}{ext}", kind, pages, OURS, note, **extra)


#: Our own documents, in the order a run sends them.
OUR_SOURCES: tuple[Source, ...] = (
    _ours("q01-structured", ".docx", "DOCX", 2,
          "Word: headings, lists, a table with a header row, a link, one picture "
          "with alt text and one without"),
    _ours("q02-structured", ".pdf", "PDF", 1, "born-digital PDF of the same text, untagged"),
    _ours("q03-page", ".jpg", "JPEG", 1, "a photographed page of text"),
    _ours("q04-page", ".gif", "GIF", 1, "a page of text as a GIF"),
    _ours("q05-page", ".png", "PNG", 1, "a page of text as a PNG"),
    _ours("q06-pages", ".tif", "TIFF", 2, "two pages of text in one TIFF"),
    _ours("q07-page", ".bmp", "BMP", 1, "a page of text as a bitmap"),
    _ours("q08-page", ".pcx", "PCX", 1, "a page of text as a PCX"),
    _ours("q09-pages", ".dcx", "DCX", 2, "two PCX pages in one DCX fax file"),
    _ours("q10-page", ".jp2", "JPEG 2000", 1, "a page of text as JPEG 2000"),
    _ours("q11-page", ".djvu", "DjVu", 1, "a page of text as DjVu (a JPEG background layer)"),
    _ours("q12-structured", ".doc", "DOC", 2, "Word 97-2003, saved by Word from q01"),
    _ours("q13-structured", ".rtf", "RTF", 1, "rich text: headings, a list and a table"),
    _ours("q14-structured", ".odt", "ODT", 2, "OpenDocument text, saved by Word from q01"),
    _ours("q15-notes", ".txt", "TXT", 1, "plain text with blank-line paragraphs"),
    _ours("q16-budget", ".xls", "XLS", 1, "Excel 97-2003, saved by Excel from q17"),
    _ours("q17-budget", ".xlsx", "XLSX", 1, "a workbook: two sheets with header rows"),
    _ours("q18-budget", ".ods", "ODS", 1, "OpenDocument spreadsheet, saved by Excel from q17"),
    _ours("q19-talk", ".ppt", "PPT", 3, "PowerPoint 97-2003, saved by PowerPoint from q20"),
    _ours("q20-talk", ".pptx", "PPTX", 3, "slides: titles, bullets, a table,"
          " a picture with alt text"),
    _ours("q21-talk", ".odp", "ODP", 3, "OpenDocument presentation, saved by PowerPoint from q20"),
    _ours("q22-story", ".epub", "EPUB", 2, "EPUB 3 with two chapters and a picture"),
    _ours("q23-story", ".mobi", "MOBI", 2, "MOBI 6 (uncompressed) with two chapters"),
    _ours("q24-long-report", ".pdf", "PDF", 25, "a long document: 25 pages, 60 headings"),
    _ours("q25-tables", ".docx", "DOCX", 2,
          "tables: merged cells, two header rows, a table with no header"),
    _ours("q26-spanish", ".docx", "DOCX", 1, "a document in Spanish, its language set to es-ES"),
    _ours("q27-math", ".docx", "DOCX", 1, "mathematics as Word equations (OMML)"),
    _ours("q28-locked", ".pdf", "PDF", 1, "a password-protected PDF (the test password is "
          "in quill/tools/scribe_live/sources.py)", password=LOCKED_PDF_TEST_PASSWORD),
    _ours("q29-web-page", ".html", "HTML", 0, "a web page: QUILL refuses it before uploading",
          expect=REFUSED_HERE),
    _ours("q30-not-a-pdf", ".pdf", "PDF", 1, "text named .pdf: Scribe should refuse it",
          expect=REFUSED_BY_SCRIBE),
)  # fmt: skip

#: Pneuma's four (their README: pages, licenses). Stems the replay tests name.
PNEUMA_SOURCES: tuple[Source, ...] = (
    Source("01-born-digital-nist-csf2-excerpt", "01-born-digital-nist-csf2-excerpt.pdf",
           "PDF", 4, PNEUMA, "Pneuma: born-digital NIST PDF (US government, public domain)"),
    Source("02-scanned-usda-1919", "02-scanned-usda-1919.pdf", "PDF", 3, PNEUMA,
           "Pneuma: image-only USDA scan from 1919 (public domain)"),
    Source("03-word-garden-handbook", "03-word-garden-handbook.docx", "DOCX", 2, PNEUMA,
           "Pneuma: Word handbook with a chart and alt text (CC0)"),
    Source("04-math-arxiv-1602.08328", "04-math-arxiv-1602.08328.pdf", "PDF", 4, PNEUMA,
           "Pneuma: arXiv paper with mathematics (CC BY 4.0)"),
)  # fmt: skip

#: Our stand-ins for Pneuma's four when their corpus is not on this computer:
#: born-digital PDF, a page picture, Word, mathematics.
STAND_INS: tuple[str, ...] = ("q02-structured", "q05-page", "q01-structured", "q27-math")

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OURS = REPO_ROOT / "tests" / "corpus" / "scribe_live"
DEFAULT_PNEUMA = Path(r"D:\scribe-corpus\corpus\scribe-test-corpus-2026-11")
DEFAULT_RUNS = Path(r"D:\scribe-corpus\runs")


@dataclass(frozen=True, slots=True)
class Found:
    """The sources at hand, and a sentence for each set that was not."""

    ours: tuple[Source, ...]
    pneuma: tuple[Source, ...]
    notes: tuple[str, ...]

    @property
    def core(self) -> tuple[Source, ...]:
        """The four every profile converts to all nine formats: Pneuma's when
        they are here, so the replay tests run unchanged; otherwise our stand-ins."""
        if len(self.pneuma) == len(PNEUMA_SOURCES):
            return self.pneuma
        by_stem = {s.stem: s for s in self.ours}
        return tuple(by_stem[s] for s in STAND_INS if s in by_stem)

    @property
    def all(self) -> tuple[Source, ...]:
        return self.pneuma + self.ours


def find_sources(ours_folder: Path | None = None, pneuma_corpus: Path | None = None) -> Found:
    """Our sources from *ours_folder* and Pneuma's from ``<pneuma_corpus>/sources``.

    A file that is missing is left out and named in ``notes``: a plan never
    lists a document that is not there.
    """
    ours_folder = ours_folder or DEFAULT_OURS
    pneuma_corpus = pneuma_corpus or DEFAULT_PNEUMA
    notes: list[str] = []
    ours: list[Source] = []
    missing: list[str] = []
    for source in OUR_SOURCES:
        path = ours_folder / source.file
        if path.is_file():
            ours.append(replace(source, path=path))
        else:
            missing.append(source.file)
    if missing:
        notes.append(
            f"{len(missing)} of our {len(OUR_SOURCES)} test documents are not in {ours_folder}, "
            f"so they are left out: {', '.join(missing)}. "
            "Make them with python tests/corpus/scribe_live/build_scribe_live_sources.py."
        )
    pneuma: list[Source] = []
    folder = pneuma_corpus / "sources"
    if folder.is_dir():
        for source in PNEUMA_SOURCES:
            path = folder / source.file
            if path.is_file():
                pneuma.append(replace(source, path=path))
        if len(pneuma) < len(PNEUMA_SOURCES):
            notes.append(
                f"Only {len(pneuma)} of Pneuma's 4 source documents are in {folder}, "
                "so the replay tests that name them cannot all run on this run."
            )
    else:
        notes.append(
            f"Pneuma's source documents were not found in {folder}, so this run uses only "
            "our own documents, and the replay tests that name Pneuma's files will not run on it."
        )
    return Found(tuple(ours), tuple(pneuma), tuple(notes))


def is_inside(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
    except ValueError:
        return False
    return True


__all__ = [
    "CONVERTS",
    "DEFAULT_OURS",
    "DEFAULT_PNEUMA",
    "DEFAULT_RUNS",
    "LOCKED_PDF_TEST_PASSWORD",
    "OURS",
    "OUR_SOURCES",
    "PNEUMA",
    "PNEUMA_SOURCES",
    "REFUSED_BY_SCRIBE",
    "REFUSED_HERE",
    "REPO_ROOT",
    "STAND_INS",
    "Found",
    "Source",
    "find_sources",
    "is_inside",
]
