"""Open a Kindle (MOBI) book as a document, in QUILL and in QUILL Lite.

The one place both editors' open paths call (``quill.io.open_read`` for QUILL,
``quill.core.lite.open_prepare`` for QUILL Lite), so the two read a Kindle book
the same way and say the same thing about it.

The book's text becomes Markdown (:mod:`quill.io.mobi_html`): its inferred
headings are ``#`` lines that heading navigation walks, and its pictures are
``![Picture 1](...)`` links to files saved from the book. The pictures go in a
folder beside the book named ``<book>_pictures``, the way a saved web page
keeps its pictures in ``<page>_files``, so the links are short and still work
when the document is previewed or exported. When that folder cannot be written
(a read-only share, a CD), they go under QUILL's own data folder instead.
Nothing is written when the book has no pictures.

Like an EPUB or a PDF, the book is never written back: Save goes to Save As
(``quill.io.export.EXPORT_ONLY_SUFFIXES``).

wx-free; strict-typed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import quote

from quill.core.document import Document
from quill.core.epub import book_language
from quill.io.mobi_html import HEADINGS_INFERRED_NOTE, kindle_html_to_markdown
from quill.io.mobi_read import MobiBook, MobiPicture, read_mobi

__all__ = ["MOBI_SUFFIXES", "is_mobi_path", "mobi_metadata", "read_mobi_document"]

#: A ``.prc`` from a Kindle source is the same Palm database (``BOOKMOBI``).
#: ``.azw3`` is not: it is KF8, which this reader refuses.
MOBI_SUFFIXES: frozenset[str] = frozenset({".mobi", ".prc"})


def is_mobi_path(path: Path | str) -> bool:
    return Path(path).suffix.lower() in MOBI_SUFFIXES


def read_mobi_document(path: Path, *, pictures_root: Path | None = None) -> Document:
    """*path* as a document. Raises ``MobiReadError`` (a sentence) or ``OSError``.

    *pictures_root* is where pictures go when the folder beside the book cannot
    be written; QUILL's data folder when not given.
    """
    book = read_mobi(path)
    saver = _PictureSaver(path, book, pictures_root)
    text, headings = kindle_html_to_markdown(book.html, saver.link)
    return Document(
        text=text,
        path=path,
        modified=False,
        encoding="utf-8",
        line_ending="\n",
        source_metadata=mobi_metadata(book, headings=headings, pictures=saver.saved),
    )


def mobi_metadata(book: MobiBook, *, headings: int, pictures: int) -> dict[str, object]:
    """The open flow's ``source_metadata`` for a Kindle book."""
    metadata: dict[str, object] = {
        "source_kind": "mobi",
        "engine": "mobi",
        "quality_score": 100,
        "title": book.title,
        "headings_inferred": headings,
        "picture_count": pictures,
    }
    language = book_language(book.language, [])  # never a POSIX "C" (F5)
    if language:
        metadata["language"] = language
    if headings:
        metadata["open_note"] = HEADINGS_INFERRED_NOTE
    return metadata


class _PictureSaver:
    """Writes each picture the text points at, once, and returns its link."""

    def __init__(self, path: Path, book: MobiBook, fallback_root: Path | None) -> None:
        self._path = path
        self._book = book
        self._fallback_root = fallback_root
        self._folder: Path | None = None
        self._relative = True
        self._links: dict[int, str] = {}
        self.saved = 0

    def link(self, index: int) -> str | None:
        if index in self._links:
            return self._links[index]
        picture = self._book.pictures.get(index)
        if picture is None:
            return None
        target = self._write(picture)
        if target is None:
            return None
        if self._relative:
            link = quote(f"{target.parent.name}/{target.name}")
        else:
            link = target.as_uri()
        self._links[index] = link
        self.saved += 1
        return link

    def _write(self, picture: MobiPicture) -> Path | None:
        name = f"picture-{picture.index}{picture.extension}"
        for folder, relative in self._folders():
            target = folder / name
            try:
                folder.mkdir(parents=True, exist_ok=True)
                if not (target.is_file() and target.stat().st_size == len(picture.data)):
                    target.write_bytes(picture.data)
            except OSError:
                continue
            self._folder, self._relative = folder, relative
            return target
        return None

    def _folders(self) -> list[tuple[Path, bool]]:
        if self._folder is not None:
            return [(self._folder, self._relative)]
        beside = self._path.parent / f"{self._path.stem}_pictures"
        digest = hashlib.sha256(str(self._path.resolve()).encode("utf-8")).hexdigest()[:16]
        root = self._fallback_root
        if root is None:
            from quill.core.paths import app_data_dir

            root = app_data_dir() / "mobi-pictures"
        return [(beside, True), (root / digest, False)]
