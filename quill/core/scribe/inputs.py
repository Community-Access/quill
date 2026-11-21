"""What Scribe for Documents accepts, checked before anything is sent (PRD 3.1).

Pneuma confirmed the API's inputs on 2026-11-21: 23 types, and no web pages
(HTML as a file or a link answers ``not_a_document``). Uploads are limited
to 500 MB. QUILL offers Scribe only for these types and checks the size
before uploading, so a refused file costs nothing and sends nothing.

wx-free, no I/O beyond reading a file's size.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from quill.core.scribe import PRODUCT_NAME

#: The 23 types, as (name, extensions), in the PRD's order.
ACCEPTED_TYPES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("PDF", (".pdf",)),
    ("JPEG", (".jpg", ".jpeg", ".jpe", ".jfif")),
    ("GIF", (".gif",)),
    ("PNG", (".png",)),
    ("TIFF", (".tif", ".tiff")),
    ("BMP", (".bmp",)),
    ("DCX", (".dcx",)),
    ("PCX", (".pcx",)),
    ("JPEG 2000", (".jp2", ".j2k", ".jpf", ".jpx", ".jpm")),
    ("DjVu", (".djvu", ".djv")),
    ("DOC", (".doc",)),
    ("DOCX", (".docx",)),
    ("RTF", (".rtf",)),
    ("ODT", (".odt",)),
    ("TXT", (".txt",)),
    ("XLS", (".xls",)),
    ("XLSX", (".xlsx",)),
    ("ODS", (".ods",)),
    ("PPT", (".ppt",)),
    ("PPTX", (".pptx",)),
    ("ODP", (".odp",)),
    ("EPUB", (".epub",)),
    ("MOBI", (".mobi",)),
)
ACCEPTED_EXTENSIONS: frozenset[str] = frozenset(
    ext for _name, extensions in ACCEPTED_TYPES for ext in extensions
)
#: Web pages, refused with their own sentence (``not_a_document``).
WEB_PAGE_EXTENSIONS: frozenset[str] = frozenset({
    ".html",
    ".htm",
    ".xhtml",
    ".shtml",
    ".mht",
    ".mhtml",
    ".php",
    ".asp",
    ".aspx",
    ".jsp",
})
#: 500 MB per upload (Pneuma, 2026-11-21).
MAX_UPLOAD_BYTES = 500 * 1024 * 1024


def size_words(size: int) -> str:
    if size >= 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024 * 1024):.1f}".removesuffix(".0") + " GB"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f}".removesuffix(".0") + " MB"
    if size >= 1024:
        return f"{max(1, round(size / 1024))} KB"
    return f"{size} bytes"


def is_accepted(path: Path | str) -> bool:
    """True when Scribe takes this kind of file (by its extension)."""
    return Path(path).suffix.lower() in ACCEPTED_EXTENSIONS


def web_page_sentence(name: str) -> str:
    return f"{name}: {PRODUCT_NAME} does not take web pages. Save it as Word or PDF first."


def not_a_document_sentence(name: str) -> str:
    """QUILL-SCRIBE-NOTDOC (PRD 11), also for the server's ``not_a_document``."""
    return (
        f"{PRODUCT_NAME} cannot convert {name}: it takes PDF, pictures, Office, "
        "OpenDocument, text, EPUB and MOBI files, not web pages."
    )


def too_big_sentence(name: str, size: int) -> str:
    """QUILL-SCRIBE-TOOBIG (PRD 11): said before upload; nothing is sent."""
    return f"{name} is {size_words(size)}. {PRODUCT_NAME} takes files up to 500 MB."


def refusal(path: Path) -> tuple[str, str]:
    """``(code, sentence)`` when *path* cannot go to Scribe, else ``("", "")``."""
    from quill.core.scribe.errors import ScribeNotDocumentError, ScribeTooBigError

    suffix = path.suffix.lower()
    if suffix in WEB_PAGE_EXTENSIONS:
        return ScribeNotDocumentError.code, web_page_sentence(path.name)
    if suffix not in ACCEPTED_EXTENSIONS:
        return ScribeNotDocumentError.code, not_a_document_sentence(path.name)
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    if size > MAX_UPLOAD_BYTES:
        return ScribeTooBigError.code, too_big_sentence(path.name, size)
    return "", ""


def url_refusal(url: str) -> str:
    """The sentence when a link plainly names a web page, else ``""``.

    A link with no telling extension may still be a file, so only Scribe can
    say; its ``not_a_document`` is mapped to the same sentence.
    """
    path = urlsplit(url).path
    name = path.rsplit("/", 1)[-1] or url
    if Path(path).suffix.lower() in WEB_PAGE_EXTENSIONS:
        return web_page_sentence(name)
    return ""


def check(path: Path) -> None:
    """Raise the coded error when *path* cannot go to Scribe (the runner's guard)."""
    from quill.core.scribe.errors import ScribeNotDocumentError, ScribeTooBigError

    code, sentence = refusal(path)
    if code == ScribeTooBigError.code:
        raise ScribeTooBigError(sentence, reason="checked_before_upload")
    if code:
        raise ScribeNotDocumentError(sentence, reason="checked_before_upload")


def input_wildcard() -> str:
    """The file picker's filter: every type Scribe takes, then each family."""
    every = ";".join(f"*{ext}" for ext in sorted(ACCEPTED_EXTENSIONS))
    groups = (
        ("PDF", (".pdf",)),
        ("Pictures", tuple(ext for _name, exts in ACCEPTED_TYPES[1:10] for ext in exts)),
        ("Text documents", (".doc", ".docx", ".rtf", ".odt", ".txt")),
        ("Spreadsheets", (".xls", ".xlsx", ".ods")),
        ("Presentations", (".ppt", ".pptx", ".odp")),
        ("Ebooks", (".epub", ".mobi")),
    )
    # Labels without the long pattern lists: a screen reader reads the label.
    parts = [f"Every file {PRODUCT_NAME} takes|{every}"]
    for label, exts in groups:
        parts.append(f"{label}|" + ";".join(f"*{ext}" for ext in exts))
    return "|".join(parts)


__all__ = [
    "ACCEPTED_EXTENSIONS",
    "ACCEPTED_TYPES",
    "MAX_UPLOAD_BYTES",
    "WEB_PAGE_EXTENSIONS",
    "check",
    "input_wildcard",
    "is_accepted",
    "not_a_document_sentence",
    "refusal",
    "size_words",
    "too_big_sentence",
    "url_refusal",
    "web_page_sentence",
]
