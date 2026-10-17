"""Office documents as readable text, with or without MarkItDown (2026-10-16).

**Why this exists.** Import / Convert Document used to send every Word,
Excel and PowerPoint file to MarkItDown, and in a shipped build MarkItDown
cannot import at all: the shared QuillVille runtime freezes ``markitdown`` in
but excludes ``onnxruntime``, which markitdown's file sniffer (magika)
imports at module top. Every Office import failed with "MarkItDown is not
installed" -- and the advice it gave could not help, because the "PDF and
Office text extraction" download installs into a folder the frozen copy
shadows, and ``find_spec('markitdown')`` keeps answering "installed" for the
broken copy. (PDFs had the same failure and were fixed first, in
:func:`quill.io.docconvert.convert_pdf_text_layer`.)

So Office files now have QUILL's own readers, and nothing decides between
MarkItDown and them by asking whether MarkItDown is *installed*. The only
test is whether it *worked*:

* :func:`read_office_text` never touches MarkItDown. Word through python-docx
  when it imports, otherwise through the package's own XML
  (:mod:`quill.io.office_word`); Excel through openpyxl, otherwise its XML
  (:mod:`quill.io.office_sheets`); PowerPoint and the OpenDocument formats
  through their XML (:mod:`quill.io.office_slides`). The XML readers need the
  standard library and nothing else, so they work in every build.
* :func:`read_office_text_preferring_markitdown` tries MarkItDown first,
  where it can read the format, and on **any** failure -- an ``ImportError``
  from magika or onnxruntime, an ``OSError`` from a native DLL, MarkItDown's
  own conversion errors, or an empty result -- reads the file with QUILL's
  own reader instead. Why MarkItDown was passed over is kept in
  :attr:`OfficeText.markitdown_failure` for the provenance record; it is
  never the user's problem.
* The legacy binary formats (``.doc``, ``.xls``, ``.ppt``) have no
  pure-Python reader. With LibreOffice installed QUILL converts a temporary
  copy to the modern format and reads that; without it,
  :class:`LegacyOfficeFormatError` says in one sentence what to do instead.

What is kept: headings, list items and their levels, tables (as Markdown
tables), sheet and slide boundaries (as headings), speaker notes, and the
alternative text of pictures. What is not: character formatting, headers,
footers, footnotes, comments, charts and SmartArt. Provenance -- which reader
read the file, whether LibreOffice converted it first, and any sheet that was
cut short -- is in :meth:`OfficeText.metadata`, never in the text.

wx-free; strict-typed.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from quill.core.error_codes import CodedError

__all__ = [
    "LEGACY_SUFFIXES",
    "MARKITDOWN_SUFFIXES",
    "MARKUP_SUFFIXES",
    "OFFICE_SUFFIXES",
    "LegacyOfficeFormatError",
    "OfficeReadError",
    "OfficeText",
    "is_office_path",
    "legacy_advice",
    "markitdown_or_own_reader",
    "read_markup_text",
    "read_office_text",
    "read_office_text_preferring_markitdown",
]

WORD_SUFFIXES = frozenset({".docx", ".docm"})
SHEET_SUFFIXES = frozenset({".xlsx", ".xlsm"})
SLIDE_SUFFIXES = frozenset({".pptx"})
OPEN_DOCUMENT_SUFFIXES = frozenset({".odt", ".ods", ".odp"})
#: Legacy binary format -> the modern format LibreOffice converts it to.
LEGACY_SUFFIXES: dict[str, str] = {".doc": ".docx", ".xls": ".xlsx", ".ppt": ".pptx"}
OFFICE_SUFFIXES = (
    WORD_SUFFIXES
    | SHEET_SUFFIXES
    | SLIDE_SUFFIXES
    | OPEN_DOCUMENT_SUFFIXES
    | frozenset(LEGACY_SUFFIXES)
)
#: Import / Convert Document's other born-digital formats, read by
#: :func:`read_markup_text` when MarkItDown cannot.
MARKUP_SUFFIXES = frozenset({".html", ".htm", ".epub", ".csv"})
#: The formats MarkItDown actually reads. It has no OpenDocument or legacy
#: Word/PowerPoint reader, so those are never offered to it.
MARKITDOWN_SUFFIXES = frozenset({".docx", ".pptx", ".xlsx", ".xls"}) | MARKUP_SUFFIXES

ENGINE_MARKITDOWN = "markitdown"

#: Spoken names, by the first letters of the suffix's family.
_KINDS: dict[str, tuple[str, str]] = {
    ".docx": ("Word", "Microsoft Word"),
    ".docm": ("Word", "Microsoft Word"),
    ".doc": ("Word", "Microsoft Word"),
    ".xlsx": ("Excel", "Microsoft Excel"),
    ".xlsm": ("Excel", "Microsoft Excel"),
    ".xls": ("Excel", "Microsoft Excel"),
    ".pptx": ("PowerPoint", "Microsoft PowerPoint"),
    ".ppt": ("PowerPoint", "Microsoft PowerPoint"),
    ".odt": ("OpenDocument text", "LibreOffice Writer"),
    ".ods": ("OpenDocument spreadsheet", "LibreOffice Calc"),
    ".odp": ("OpenDocument presentation", "LibreOffice Impress"),
    ".html": ("web page", "a web browser"),
    ".htm": ("web page", "a web browser"),
    ".epub": ("EPUB", "an EPUB reader"),
    ".csv": ("CSV", "a spreadsheet program"),
}

#: What a legacy file is, the Save As type that fixes it, and the free app.
_LEGACY_ADVICE: dict[str, tuple[str, str, str]] = {
    ".doc": ("Word 97-2003 document", "Word Document (.docx)", "LibreOffice Writer"),
    ".xls": ("Excel 97-2003 workbook", "Excel Workbook (.xlsx)", "LibreOffice Calc"),
    ".ppt": ("PowerPoint 97-2003 presentation", "PowerPoint Presentation (.pptx)", "Impress"),
}

#: The first bytes of an OLE compound file: what a legacy file, and a
#: password-protected modern one, actually are on disk.
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

LegacyConverter = Callable[[Path, str, Path], Path]


class OfficeReadError(CodedError):
    """An Office file QUILL's own readers could not read; the message says why."""

    code = "QUILL-IO-OFFICE-UNREADABLE"

    @property
    def sentence(self) -> str:
        """The message alone, without the support code ``str()`` prefixes."""
        return str(self.args[0]) if self.args else ""


class LegacyOfficeFormatError(OfficeReadError):
    """A .doc/.xls/.ppt with no local way to read it (LibreOffice is not installed)."""

    code = "QUILL-IO-OFFICE-LEGACY"


@dataclass(frozen=True, slots=True)
class OfficeText:
    """An Office file's text, and the provenance of how it was read."""

    text: str
    engine: str
    source_kind: str
    #: Sheets in a workbook or slides in a deck; 0 for a text document.
    count: int = 0
    unit: str = ""
    #: "libreoffice" when a legacy file was converted before it was read.
    conversion_engine: str = ""
    notes: tuple[str, ...] = ()
    #: Why MarkItDown was passed over, when it was tried first ("" otherwise).
    markitdown_failure: str = ""

    @property
    def kind(self) -> str:
        return _KINDS.get(f".{self.source_kind}", ("Office", ""))[0]

    @property
    def reader_label(self) -> str:
        """Who read it, in words: "QUILL's own Excel reader", "MarkItDown"."""
        if self.engine == ENGINE_MARKITDOWN:
            return "MarkItDown"
        label = f"QUILL's own {self.kind} reader"
        return f"{label}, after LibreOffice converted it" if self.conversion_engine else label

    @property
    def count_phrase(self) -> str:
        """ "3 sheets", "1 slide", or "" -- for an announcement."""
        if not self.count or not self.unit:
            return ""
        return f"{self.count} {self.unit}{'' if self.count == 1 else 's'}"

    def metadata(self) -> dict[str, object]:
        """``source_metadata`` for the document this text opens as."""
        found: dict[str, object] = {
            "source_kind": self.source_kind,
            "engine": self.engine,
            "quality_score": 90 if self.engine == ENGINE_MARKITDOWN else 85,
            # In words, for the open announcement and the intake report.
            "reader": self.reader_label,
        }
        if self.count_phrase:
            found["units"] = self.count_phrase
        if self.conversion_engine:
            found["conversion_engine"] = self.conversion_engine
        if self.count:
            found[f"{self.unit}_count"] = self.count
        if self.notes:
            found["extraction_notes"] = list(self.notes)
        if self.markitdown_failure:
            found["markitdown_failure"] = self.markitdown_failure
        return found


def is_office_path(path: Path | str) -> bool:
    return Path(path).suffix.lower() in OFFICE_SUFFIXES


def legacy_advice(path: Path) -> str:
    """What to do with a .doc/.xls/.ppt QUILL cannot read here. One paragraph."""
    what, save_as, free_app = _LEGACY_ADVICE[path.suffix.lower()]
    app = _KINDS[path.suffix.lower()][1]
    return (
        f"{path.name} is an older {what}, a format QUILL cannot read by itself. "
        f"Open it in {app} or {free_app}, choose File > Save As, pick "
        f'"{save_as}", and import that copy instead. Or install LibreOffice '
        "(free, from libreoffice.org) and QUILL will convert these files for you."
    )


# ------------------------------------------------------------------ readers


def read_office_text(path: Path, *, legacy_converter: LegacyConverter | None = None) -> OfficeText:
    """Read an Office file with QUILL's own readers. Never uses MarkItDown.

    Raises :class:`OfficeReadError` with a sentence fit to say aloud when the
    file cannot be read (damaged, password-protected, empty), and
    :class:`LegacyOfficeFormatError` for a legacy file with no local route.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in LEGACY_SUFFIXES:
        return _read_legacy(path, legacy_converter)
    if suffix not in OFFICE_SUFFIXES:
        raise OfficeReadError(f"{path.name} is not an Office document QUILL can read.")
    try:
        found = _read_modern(path, suffix)
    except (zipfile.BadZipFile, KeyError, ET.ParseError, ValueError, UnicodeDecodeError) as exc:
        raise OfficeReadError(_unreadable_sentence(path, exc)) from exc
    if not found.text.strip():
        raise OfficeReadError(
            f"{path.name} opened, but it has no text in it to read. If it holds "
            "only pictures or scanned pages, those need OCR, which reads PDFs and images."
        )
    return found


def _read_modern(path: Path, suffix: str) -> OfficeText:
    kind = suffix.lstrip(".")
    if suffix in WORD_SUFFIXES:
        from quill.io.docx_text import read_docx_text
        from quill.io.office_word import read_docx_xml

        rendered = read_docx_text(path)
        if rendered is not None:
            return OfficeText(rendered, "python-docx", kind)
        return OfficeText(read_docx_xml(path), "word-xml", kind)
    if suffix == ".odt":
        from quill.io.office_word import read_odt_xml

        return OfficeText(read_odt_xml(path), "odf-xml", kind)
    if suffix in SHEET_SUFFIXES or suffix == ".ods":
        from quill.io.office_sheets import read_ods_text, read_xlsx_text

        sheets = read_ods_text(path) if suffix == ".ods" else read_xlsx_text(path)
        return OfficeText(
            sheets.text, sheets.engine, kind, sheets.sheets, "sheet", notes=sheets.notes
        )
    from quill.io.office_slides import read_odp_text, read_pptx_text

    slides = read_odp_text(path) if suffix == ".odp" else read_pptx_text(path)
    return OfficeText(slides.text, slides.engine, kind, slides.slides, "slide")


def _unreadable_sentence(path: Path, exc: BaseException) -> str:
    kind, app = _KINDS.get(path.suffix.lower(), ("Office", "the program that made it"))
    try:
        with path.open("rb") as handle:
            head = handle.read(8)
    except OSError as error:
        return f"QUILL could not read {path.name}: {error.strerror or error}."
    if head == _OLE_MAGIC:
        return (
            f"{path.name} is password-protected, or it is an older Office file with a "
            f"new name. QUILL cannot open protected files. Remove the password in {app} "
            "(File > Info), save it again, and try once more."
        )
    if isinstance(exc, ValueError) and str(exc):
        return str(exc)
    return (
        f"{path.name} does not look like a valid {kind} file; it may be damaged. "
        f"Open it in {app}, save it again, and try once more."
    )


def _read_legacy(path: Path, converter: LegacyConverter | None) -> OfficeText:
    target = LEGACY_SUFFIXES[path.suffix.lower()]
    run = converter or _libreoffice_converter()
    if run is None:
        raise LegacyOfficeFormatError(legacy_advice(path))
    with tempfile.TemporaryDirectory(prefix="quill-office-") as raw:
        try:
            converted = run(path, target, Path(raw))
        except (OSError, subprocess.SubprocessError) as exc:
            raise LegacyOfficeFormatError(
                f"LibreOffice could not convert {path.name}. {legacy_advice(path)}"
            ) from exc
        found = read_office_text(converted)
    return replace(
        found, source_kind=path.suffix.lower().lstrip("."), conversion_engine="libreoffice"
    )


def _libreoffice_converter() -> LegacyConverter | None:
    from quill.core.external_tools import libreoffice_executable

    soffice = libreoffice_executable()
    if soffice is None:
        return None

    def convert(source: Path, target_suffix: str, out_dir: Path) -> Path:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        subprocess.run(  # noqa: S603 - argv list, resolved soffice, no shell
            [
                soffice,
                "--headless",
                "--convert-to",
                target_suffix.lstrip("."),
                "--outdir",
                str(out_dir),
                str(source),
            ],
            check=True,
            capture_output=True,
            timeout=90,
            creationflags=flags,
        )
        converted = out_dir / f"{source.stem}{target_suffix}"
        if not converted.is_file():
            raise FileNotFoundError(f"LibreOffice wrote no {target_suffix} for {source.name}")
        return converted

    return convert


def _default_markitdown(path: Path) -> str:
    from quill.io.markitdown_bridge import convert_with_markitdown

    return convert_with_markitdown(path)


def markitdown_failure_reason(exc: BaseException) -> str:
    """One line for the provenance record: why MarkItDown was not used."""
    cause: BaseException = exc
    while cause.__cause__ is not None:
        cause = cause.__cause__
    detail = str(cause) or type(cause).__name__
    if isinstance(cause, ImportError):
        return f"MarkItDown could not start here ({detail})."
    return f"MarkItDown could not read the file ({type(cause).__name__}: {detail})."


def read_office_text_preferring_markitdown(
    path: Path,
    *,
    markitdown: Callable[[Path], str] | None = None,
    legacy_converter: LegacyConverter | None = None,
) -> OfficeText:
    """MarkItDown when it can read the format and works; QUILL's own reader otherwise.

    Takes every Office format plus HTML, EPUB and CSV (Import / Convert
    Document's whole born-digital list); a format MarkItDown has no reader
    for (OpenDocument, .doc, .ppt) goes straight to QUILL's own.

    Nothing here asks whether MarkItDown is installed: a frozen copy that
    cannot import reports "installed" to ``find_spec``, so the only honest
    test is to try it. Any exception -- including the magika/onnxruntime
    ``ImportError`` a shipped build raises -- falls through to
    :func:`read_office_text`, whose own errors are the ones the user hears.
    """
    path = Path(path)
    kind = path.suffix.lower().lstrip(".")
    if path.suffix.lower() not in MARKITDOWN_SUFFIXES:
        return read_office_text(path, legacy_converter=legacy_converter)
    try:
        text = (markitdown or _default_markitdown)(path)
    except Exception as exc:  # noqa: BLE001 - every MarkItDown failure has the same answer
        reason = markitdown_failure_reason(exc)
    else:
        if text.strip():
            return OfficeText(text.rstrip() + "\n", ENGINE_MARKITDOWN, kind)
        reason = "MarkItDown returned no text."
    if path.suffix.lower() in MARKUP_SUFFIXES:
        try:
            text = read_markup_text(path)
        except (ValueError, UnicodeDecodeError, zipfile.BadZipFile, KeyError) as exc:
            raise OfficeReadError(_unreadable_sentence(path, exc)) from exc
        if not text.strip():
            raise OfficeReadError(f"{path.name} has no text in it to read.")
        return OfficeText(text, f"quill-{kind}", kind, markitdown_failure=reason)
    own = read_office_text(path, legacy_converter=legacy_converter)
    return replace(own, markitdown_failure=reason)


def markitdown_or_own_reader(path: Path) -> tuple[str, str]:
    """File > Convert File's MarkItDown engine: ``(markdown, stand_in)``.

    ``stand_in`` is ``""`` when MarkItDown did the work, or the reader that did
    it instead ("QUILL's own Word reader") when MarkItDown could not run here,
    so the caller can say so. A PDF stands in with QUILL's own PDF reader.
    Raises ``ValueError`` with a sentence fit to say aloud when nothing can.
    """
    path = Path(path)
    if path.suffix.lower() != ".pdf":
        try:
            found = read_office_text_preferring_markitdown(path)
        except OfficeReadError as exc:
            raise ValueError(exc.sentence) from exc
        return found.text, "" if found.engine == ENGINE_MARKITDOWN else found.reader_label
    try:
        return _default_markitdown(path), ""
    except Exception:  # noqa: BLE001 - every MarkItDown failure has the same answer
        pass
    from quill.io.pdf import extract_pdf_text

    text = str(extract_pdf_text(path).text).replace("\f", "\n\n").strip()
    if not text:
        raise ValueError(
            f"{path.name} has no text QUILL could read; it may be scanned or locked. "
            "Import / Convert Document can read a scanned PDF with OCR."
        )
    return text + "\n", "QUILL's own PDF reader"


def read_markup_text(path: Path) -> str:
    """HTML, EPUB and CSV -- Import / Convert's other born-digital formats -- without MarkItDown.

    The same readers File > Open uses. Raises ``ValueError`` for a suffix it
    does not handle.
    """
    suffix = path.suffix.lower()
    if suffix == ".epub":
        from quill.core.epub import load_epub_book, render_epub_book

        return render_epub_book(load_epub_book(path))
    from quill.io.text import read_text_document

    raw = read_text_document(path).text
    if suffix in {".html", ".htm"}:
        from quill.core.html_to_markdown import html_to_markdown

        return html_to_markdown(raw)
    if suffix == ".csv":
        import csv
        import io

        from quill.io.office_sheets import escape_cell, markdown_table

        rows = [[escape_cell(cell) for cell in row] for row in csv.reader(io.StringIO(raw))]
        return "\n".join(markdown_table(rows)) + "\n"
    raise ValueError(f"{path.suffix or 'This file type'} has no built-in reader.")
