"""What a returned file is, what structure QUILL relies on in it, and whether it opens.

These are the facts the comparison reads (:mod:`.compare`) and
``validation.json`` holds, under the names Pneuma's corpus used where the
fact is the same (``max_cells``, ``form_feeds``, ``headings``, ``seconds``...),
so the replay tests' ``corpus.validation()`` reads a live run as it reads
their corpus.

They describe the **shape** of what came back, never its quality: no OCR
accuracy, no braille translation, no epubcheck. ``opens`` is whether QUILL's
own reader for that format reads the file (``None`` when this computer
cannot tell, for example without the PDF extraction pack).

Files are only read: XML through :mod:`quill.core.safe_xml`, zips listed and
read in memory, a DAISY book unpacked into a temporary folder. wx-free, no
network.
"""

from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

_HTML_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


def sniff(path: Path) -> str:
    """The kind of file by its first bytes: zip, html, pdf, mp3, mobi, text or other."""
    try:
        with path.open("rb") as handle:
            head = handle.read(80)
    except OSError:
        return "missing"
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    if head.startswith(b"%PDF"):
        return "pdf"
    if head[60:68] == b"BOOKMOBI":
        return "mobi"
    if head.startswith(b"ID3") or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xe3"):
        return "mp3"
    lowered = head.lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if lowered.startswith((b"<!doctype html", b"<html", b"<?xml", b"<head", b"<meta")):
        return "html"
    if all(byte in b"\t\r\n\x0c" or 32 <= byte < 127 for byte in head) and head:
        return "text"
    return "other"


def html_facts(text: str) -> dict[str, Any]:
    """Pneuma's HTML checks, by pattern (the same counts their README gives)."""
    images = _HTML_IMG.findall(text)
    lang = re.search(r"<html\b[^>]*\blang=\"([^\"]*)\"", text, re.IGNORECASE)
    title = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    doctype = re.match(r"\s*(<!DOCTYPE[^>]*>)", text, re.IGNORECASE)
    return {
        "doctype": doctype.group(1) if doctype else "",
        "imgs": len(images),
        "data_uri_imgs": sum(1 for i in images if re.search(r"src=\"data:", i)),
        "external_img_refs": sum(
            1 for i in images if re.search(r"src=\"(?!data:|https?:)[^\"]+\"", i, re.IGNORECASE)
        ),
        "imgs_without_alt": sum(1 for i in images if not re.search(r"\balt=\"[^\"]+", i)),
        "headings": len(re.findall(r"<h[1-6]\b", text, re.IGNORECASE)),
        "tables": len(re.findall(r"<table\b", text, re.IGNORECASE)),
        "th": len(re.findall(r"<th\b", text, re.IGNORECASE)),
        "lists": len(re.findall(r"<(?:ul|ol)\b", text, re.IGNORECASE)),
        "links": len(re.findall(r"<a\b[^>]*href", text, re.IGNORECASE)),
        "mathml": len(re.findall(r"<math\b", text, re.IGNORECASE)),
        "lang": lang.group(1) if lang else "",
        "title": " ".join(title.group(1).split()) if title else "",
        "scripts": len(re.findall(r"<script\b", text, re.IGNORECASE)),
    }


def brf_facts(raw: bytes) -> dict[str, Any]:
    """The page shape QUILL's braille view relies on: cells, lines, form feeds."""
    pages = raw.split(b"\x0c")
    lines = raw.replace(b"\x0c", b"").split(b"\r\n" if b"\r\n" in raw else b"\n")
    per_page = [len(p.strip(b"\r\n").split(b"\r\n")) for p in pages if p.strip(b"\r\n \t")]
    return {
        "ascii_only": all(b < 128 for b in raw),
        "form_feeds": raw.count(b"\x0c"),
        "crlf": b"\r\n" in raw,
        "max_cells": max((len(line.rstrip(b"\r")) for line in lines), default=0),
        "lines": len(lines),
        "max_lines_per_page": max(per_page, default=0),
        "tabs": raw.count(b"\t"),
        "non_ascii_bytes": sum(1 for b in raw if b >= 128),
    }


def _zip_names(path: Path) -> list[str] | None:
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    except (OSError, zipfile.BadZipFile):
        return None


def _read_member(path: Path, name: str) -> bytes:
    with zipfile.ZipFile(path) as archive:
        return archive.read(name)


def docx_facts(path: Path) -> dict[str, Any]:
    names = _zip_names(path)
    if names is None or "word/document.xml" not in names:
        return {"zip": names is not None, "word_document": False}
    body = _read_member(path, "word/document.xml").decode("utf-8", errors="replace")
    styles = ""
    if "word/styles.xml" in names:
        styles = _read_member(path, "word/styles.xml").decode("utf-8", errors="replace")
    heading_ids = set(
        re.findall(
            r"<w:style\b[^>]*w:styleId=\"([^\"]+)\"[^>]*>(?:(?!</w:style>).)*?"
            r"<w:name w:val=\"(?:heading|Heading) \d\"",
            styles,
            re.DOTALL,
        )
    )
    used = re.findall(r"<w:pStyle w:val=\"([^\"]+)\"", body)
    lang = re.search(r"<w:lang\b[^>]*w:val=\"([^\"]+)\"", styles or body)
    return {
        "zip": True,
        "word_document": True,
        "paragraphs": len(re.findall(r"<w:p[ >]", body)),
        "tables": len(re.findall(r"<w:tbl>", body)),
        "headings": sum(1 for style in used if style in heading_ids or "eading" in style),
        "images": len(re.findall(r"<wp:docPr\b", body)),
        "math_omml": len(re.findall(r"<m:oMath\b", body)),
        "language": lang.group(1) if lang else "",
    }


def epub_facts(path: Path) -> dict[str, Any]:
    names = _zip_names(path)
    if names is None:
        return {"zip": False}
    facts: dict[str, Any] = {"zip": True, "mimetype_first": bool(names) and names[0] == "mimetype"}
    opf_name = next((n for n in names if n.endswith(".opf")), "")
    if opf_name:
        opf = _read_member(path, opf_name).decode("utf-8", errors="replace")
        version = re.search(r"<package\b[^>]*\bversion=\"([^\"]+)\"", opf)
        language = re.search(r"<dc:language[^>]*>([^<]*)</dc:language>", opf)
        facts["epub_version"] = version.group(1) if version else ""
        facts["language"] = language.group(1).strip() if language else ""
        facts["spine_items"] = len(re.findall(r"<itemref\b", opf))
    facts["mathml_items"] = sum(
        1
        for n in names
        if n.endswith((".xhtml", ".html", ".htm")) and b"<math" in _read_member(path, n)
    )
    return facts


def mobi_facts(raw: bytes) -> dict[str, Any]:
    if len(raw) < 78 or raw[60:68] != b"BOOKMOBI":
        return {"palmdb_type": raw[60:68].decode("latin-1") if len(raw) >= 68 else ""}
    records = int.from_bytes(raw[76:78], "big")
    first = int.from_bytes(raw[78:82], "big") if records else 0
    header = raw[first : first + 16 + 232]
    magic = header[16:20].decode("latin-1")
    return {
        "palmdb_type": "BOOKMOBI",
        "records": records,
        "mobi_magic": magic,
        "mobi_version": int.from_bytes(header[36:40], "big") if magic == "MOBI" else 0,
        "compression": int.from_bytes(header[0:2], "big"),
        "exth": b"EXTH" in raw[first : first + 2048],
    }


def pdf_facts(path: Path) -> dict[str, Any]:
    try:
        import pypdf  # optional: not every computer has it
    except ImportError:
        return {}
    try:
        reader = pypdf.PdfReader(str(path))
        root = reader.trailer["/Root"]
        return {
            "pages": len(reader.pages),
            "tagged": "/StructTreeRoot" in root,
            "lang": str(root.get("/Lang", "")),
            "encrypted": bool(reader.is_encrypted),
        }
    except Exception as error:  # noqa: BLE001 - a fact, not a failure
        return {"pdf_error": type(error).__name__}


def mp3_facts(path: Path) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    try:
        from mutagen.mp3 import MP3

        audio = MP3(str(path))
        facts.update({
            "seconds": round(float(audio.info.length), 1),
            "bitrate_kbps": int(audio.info.bitrate // 1000),
            "sample_rate": int(audio.info.sample_rate),
            "channels": int(audio.info.channels),
            "id3": audio.tags is not None,
        })
    except Exception:  # noqa: BLE001 - mutagen missing or the file is not an MP3
        pass
    return facts


def daisy_facts(path: Path) -> dict[str, Any]:
    """The book QUILL's Media Player opens: its navigation file and chapters."""
    names = _zip_names(path)
    if names is None:
        return {"zip": False}
    from quill.core import safe_xml

    facts: dict[str, Any] = {
        "zip": True,
        "files": len([n for n in names if not n.endswith("/")]),
        "mp3s": len([n for n in names if n.lower().endswith(".mp3")]),
        "smils": len([n for n in names if n.lower().endswith(".smil")]),
        "ncx": any(n.lower().endswith(".ncx") for n in names),
    }
    well_formed = True
    for name in names:
        if name.lower().endswith((".xml", ".opf", ".ncx", ".smil")):
            try:
                safe_xml.fromstring(_read_member(path, name))
            except Exception:  # noqa: BLE001 - malformed XML is the fact
                well_formed = False
    facts["xml"] = "all well-formed" if well_formed else "some not well-formed"
    opf_name = next((n for n in names if n.lower().endswith(".opf")), "")
    if opf_name:
        opf = _read_member(path, opf_name).decode("utf-8", errors="replace")
        found = re.search(r"<dc:Format>([^<]*)</dc:Format>", opf)
        facts["dc_format"] = found.group(1) if found else ""
    book = next((n for n in names if n.lower().endswith("dtbook.xml")), "")
    if book:
        text = _read_member(path, book).decode("utf-8", errors="replace")
        images = re.findall(r"<img\b[^>]*\bsrc=\"([^\"]+)\"", text)
        folder = book.rsplit("/", 1)[0] + "/" if "/" in book else ""
        facts["dtbook_images"] = len(images)
        facts["dtbook_images_missing_from_zip"] = sum(
            1 for src in images if folder + src not in names
        )
    return facts


def _opens(format_id: str, path: Path) -> tuple[bool | None, str, dict[str, Any]]:
    """Whether QUILL's own reader for *format_id* reads *path*, and what it found."""
    found: dict[str, Any] = {}
    try:
        if format_id in ("html", "offline_html", "docx", "epub", "brf", "pdf"):
            from quill.io.open_read import read_open_document

            if format_id == "offline_html" and zipfile.is_zipfile(path):
                names = _zip_names(path) or []
                ok = any(n.lower().endswith((".html", ".htm")) for n in names)
                return ok, "" if ok else "the zip holds no web page", found
            doc, _book = read_open_document(path, path.suffix.lower())
            meta = getattr(doc, "source_metadata", {}) or {}
            if format_id == "pdf" and meta.get("extraction_pack_missing"):
                return None, "the PDF extraction pack is not installed", found
            if format_id == "brf":
                found["brf_cell_width"] = meta.get("brf_cell_width")
                found["brf_form_feed_count"] = meta.get("brf_form_feed_count")
            if format_id == "epub":
                found["chapters"] = len(getattr(_book, "chapters", []) or [])
            text = getattr(doc, "text", "")
            return bool(text.strip()), "" if text.strip() else "it opened empty", found
        if format_id == "mp3":
            from quill.core.speech.book_file import read_book

            book = read_book(path)
            return book.total_ms > 0, "", found
        if format_id == "daisy":
            return _daisy_opens(path, found)
        if format_id == "mobi":
            ok = sniff(path) == "mobi"
            return ok, "" if ok else "it is not a MOBI book", found
    except Exception as error:  # noqa: BLE001 - not opening is the finding
        return False, f"{type(error).__name__}: {str(error)[:160]}", found
    return None, "", found


def _daisy_opens(path: Path, found: dict[str, Any]) -> tuple[bool | None, str, dict[str, Any]]:
    from quill.core.media.daisy import parse_ncx
    from quill.core.scribe.results import daisy_entry

    work = Path(tempfile.mkdtemp(prefix="scribe-live-daisy-"))
    try:
        copy = work / "book.zip"
        shutil.copyfile(path, copy)
        entry = daisy_entry(copy)
        if entry is None:
            return False, "no navigation file (dtb.ncx or ncc.html) in the book", found
        if entry.suffix.lower() != ".ncx":  # the Media Player opens DAISY 3, from dtb.ncx
            return False, "no dtb.ncx in the book", found
        found["chapters"] = len(parse_ncx(entry.read_bytes()))
        ok = found["chapters"] > 0
        return ok, "" if ok else "its dtb.ncx lists no chapters", found
    finally:
        shutil.rmtree(work, ignore_errors=True)


def facts_for(format_id: str, path: Path, *, check_opens: bool = True) -> dict[str, Any]:
    """Every fact about one returned file."""
    try:
        raw = path.read_bytes()
    except OSError as error:
        return {"bytes": 0, "type": "missing", "opens": False, "open_error": str(error)}
    facts: dict[str, Any] = {"bytes": len(raw), "type": sniff(path)}
    if format_id in ("html", "offline_html") and facts["type"] != "zip":
        facts.update(html_facts(raw.decode("utf-8", errors="replace")))
    elif format_id == "offline_html":
        facts["zip"] = True
        facts["files"] = len(_zip_names(path) or [])
    elif format_id == "docx":
        facts.update(docx_facts(path))
    elif format_id == "epub":
        facts.update(epub_facts(path))
    elif format_id == "mobi":
        facts.update(mobi_facts(raw))
    elif format_id == "brf":
        facts.update(brf_facts(raw))
    elif format_id == "pdf":
        facts.update(pdf_facts(path))
    elif format_id == "mp3":
        facts.update(mp3_facts(path))
    elif format_id == "daisy":
        facts.update(daisy_facts(path))
    if check_opens:
        opens, error, found = _opens(format_id, path)
        facts["opens"] = opens
        if error:
            facts["open_error"] = error
        facts.update(found)
    return facts


__all__ = [
    "brf_facts",
    "daisy_facts",
    "docx_facts",
    "epub_facts",
    "facts_for",
    "html_facts",
    "mobi_facts",
    "mp3_facts",
    "pdf_facts",
    "sniff",
]
