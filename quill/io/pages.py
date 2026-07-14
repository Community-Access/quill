from __future__ import annotations

import subprocess
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.document import Document
from quill.io.markitdown_bridge import convert_with_markitdown

# Pages paragraph style names → Markdown heading prefix
_STYLE_HEADING_PREFIX: dict[str, str] = {
    "title": "# ",
    "heading": "## ",
    "heading 1": "## ",
    "heading 2": "### ",
    "heading 3": "#### ",
    "heading 4": "##### ",
    "heading 5": "###### ",
    "heading 6": "###### ",
}


def read_pages_document(path: Path) -> Document:
    """Import an Apple Pages document and extract text with heading structure.

    Uses Route A (pure Python IWA parsing) when available, falls back to Route B
    (LibreOffice + MarkItDown) for higher fidelity. If neither is available,
    returns a graceful error message.
    """
    try:
        return _read_pages_via_iwa(path)
    except Exception:  # noqa: BLE001 - fall through to the LibreOffice route
        pass

    try:
        return _read_pages_via_libreoffice(path)
    except Exception:  # noqa: BLE001 - fall through to the graceful error below
        pass

    return Document(
        text=(
            f"(Pages import not available for {path.name}.)\n\n"
            "To import Pages documents, either:\n"
            "1. Install keynote-parser: pip install keynote-parser\n"
            "2. Or install LibreOffice, and open Help > Download Optional "
            'Components and download "PDF and Office text extraction"\n'
        ),
        path=path,
        modified=False,
        encoding="utf-8",
        line_ending="\n",
        source_metadata={
            "source_kind": "pages",
            "engine": "unavailable",
            "quality_score": 0,
        },
    )


class _UnknownIWAMessage:
    """Stub returned for Pages-specific IWA message types keynote-parser doesn't know."""

    def __init__(self, type_id: int, data: bytes) -> None:
        self._type_id = type_id

    @classmethod
    def FromString(cls, data: bytes) -> _UnknownIWAMessage:
        return cls(0, data)

    def to_dict(self) -> dict:
        return {"_pbtype": f"UNKNOWN.Type{self._type_id}"}


def _patched_id_name_map() -> dict[int, Any]:
    """Return a wrapper around keynote-parser's ID_NAME_MAP that never raises KeyError."""
    import keynote_parser.codec as _codec

    class _FallbackMap(dict):
        def __missing__(self, type_id: int) -> type:
            class _Factory:
                _tid = type_id

                @classmethod
                def FromString(cls, data: bytes) -> _UnknownIWAMessage:
                    return _UnknownIWAMessage(cls._tid, data)

            return _Factory

    return _FallbackMap(_codec.ID_NAME_MAP)


def _parse_iwa_bundle(path: Path, zip_file_reader: Callable[..., Any]) -> dict[str, list[dict]]:
    """Walk a .pages bundle and return all decoded IWA objects keyed by archive ID."""
    from keynote_parser.codec import IWAFile

    archives_by_id: dict[str, list[dict]] = {}
    for filename, handle in zip_file_reader(str(path), progress=False):
        if ".iwa" not in filename:
            continue
        try:
            iwa = IWAFile.from_buffer(handle.read(), filename)
            for chunk in iwa.to_dict()["chunks"]:
                for archive in chunk["archives"]:
                    arch_id = str(archive.get("header", {}).get("identifier", ""))
                    objects = [o for o in archive.get("objects", []) if isinstance(o, dict)]
                    if arch_id and arch_id != "0":
                        archives_by_id[arch_id] = objects
        except Exception:
            continue
    return archives_by_id


def _read_pages_via_iwa(path: Path) -> Document:
    """Route A: Parse .pages IWA archives (requires keynote-parser).

    keynote-parser only ships Keynote proto definitions; Pages-specific message
    types (e.g. type 10000 = WP.DocumentArchive) are unknown to it.  We patch
    ID_NAME_MAP at call time so unknown types are silently skipped rather than
    crashing the entire parse.
    """
    try:
        import keynote_parser.codec as _codec
        from keynote_parser.file_utils import zip_file_reader
    except ImportError as e:
        raise ImportError("keynote-parser not available") from e

    # Temporarily replace ID_NAME_MAP with a fallback-safe version.
    # The lock serializes concurrent openers so they don't corrupt each other's map.
    _ID_NAME_MAP_LOCK = getattr(_codec, "_quill_id_name_map_lock", None)
    if _ID_NAME_MAP_LOCK is None:
        _ID_NAME_MAP_LOCK = threading.Lock()
        _codec._quill_id_name_map_lock = _ID_NAME_MAP_LOCK  # type: ignore[attr-defined]
    with _ID_NAME_MAP_LOCK:
        _original_map = _codec.ID_NAME_MAP
        _codec.ID_NAME_MAP = _patched_id_name_map()
        try:
            archives_by_id = _parse_iwa_bundle(path, zip_file_reader)
        finally:
            _codec.ID_NAME_MAP = _original_map

    if not archives_by_id:
        raise ValueError("No IWA archives found in Pages file")

    # Find TSWP.StorageArchive objects — the main text stores.
    # Prefer those flagged as in_document / inDocument; fall back to any with text.
    all_storage: list[dict] = []
    for objects in archives_by_id.values():
        for obj in objects:
            if obj.get("_pbtype") == "TSWP.StorageArchive":
                all_storage.append(obj)

    storages = [s for s in all_storage if s.get("inDocument") or s.get("in_document")]
    if not storages:
        storages = [s for s in all_storage if s.get("text", "").strip()]

    if not storages:
        raise ValueError("No text content found in Pages IWA archives")

    text_parts: list[str] = []
    for storage in storages:
        # text is a protobuf repeated string field → list in MessageToDict output
        raw_parts = storage.get("text")
        raw = "".join(raw_parts) if isinstance(raw_parts, list) else (raw_parts or "")
        if not raw.strip():
            continue
        text_parts.append(_storage_to_markdown(storage, archives_by_id))

    combined = "\n\n".join(t for t in text_parts if t.strip())
    if not combined.strip():
        raise ValueError("No text extracted from Pages via IWA")

    return Document(
        text=combined.strip() + "\n",
        path=path,
        modified=False,
        encoding="utf-8",
        line_ending="\n",
        source_metadata={
            "source_kind": "pages",
            "engine": "keynote-parser (IWA)",
            "quality_score": 75,
        },
    )


def _storage_to_markdown(storage: dict, archives_by_id: dict[str, list[dict]]) -> str:
    """Convert a TSWP.StorageArchive dict to Markdown, applying heading prefixes."""
    raw_parts = storage.get("text")
    raw_text = "".join(raw_parts) if isinstance(raw_parts, list) else (raw_parts or "")

    # Build char-position → style-name map from tableParaStyle entries.
    # Each entry: {characterIndex: N, object: {identifier: M}}
    # The referenced archive contains a TSWP.ParagraphStyleArchive whose
    # inline TSS.StyleArchive has a human-readable "name" field.
    para_style: dict[int, str] = {}
    table = storage.get("tableParaStyle", {})
    for entry in table.get("entries", []):
        char_idx = entry.get("characterIndex")
        if char_idx is None:
            continue
        ref = entry.get("object", {})
        ref_id = str(ref.get("identifier", ""))
        if not ref_id or ref_id not in archives_by_id:
            continue
        name = _resolve_style_name(archives_by_id[ref_id], archives_by_id)
        if name:
            para_style[int(char_idx)] = name

    if not para_style:
        return raw_text.rstrip("\n")

    # Walk paragraphs (split on \n) and prefix headings.
    lines: list[str] = []
    char_pos = 0
    for para in raw_text.split("\n"):
        style_name = _para_style_at(para_style, char_pos)
        prefix = _STYLE_HEADING_PREFIX.get(style_name.lower().strip(), "")
        lines.append(f"{prefix}{para}" if prefix and para.strip() else para)
        char_pos += len(para) + 1  # +1 for the \n separator

    return "\n".join(lines).rstrip("\n")


def _resolve_style_name(
    objects: list[dict],
    archives_by_id: dict[str, list[dict]] | None = None,
    _depth: int = 0,
) -> str:
    """Return the style name from a ParagraphStyleArchive archive's objects.

    Pages stores base styles with super.name set directly; variation styles only
    carry super.parent (a reference to the base style).  We follow that chain up
    to 5 levels deep to find the authoritative name.
    """
    if _depth > 5:
        return ""
    for obj in objects:
        if obj.get("_pbtype") != "TSWP.ParagraphStyleArchive":
            continue
        super_style = obj.get("super", {})
        if not isinstance(super_style, dict):
            continue
        name = super_style.get("name", "")
        if name:
            return str(name)
        # Variation style — follow parent reference
        if archives_by_id:
            parent_id = str((super_style.get("parent") or {}).get("identifier", ""))
            if parent_id and parent_id in archives_by_id:
                name = _resolve_style_name(archives_by_id[parent_id], archives_by_id, _depth + 1)
                if name:
                    return name
    return ""


def _para_style_at(para_style: dict[int, str], char_pos: int) -> str:
    """Return the style name in effect at char_pos (closest entry ≤ char_pos)."""
    if char_pos in para_style:
        return para_style[char_pos]
    best_pos = -1
    best_name = ""
    for pos, name in para_style.items():
        if pos <= char_pos and pos > best_pos:
            best_pos = pos
            best_name = name
    return best_name


def _read_pages_via_libreoffice(path: Path) -> Document:
    """Route B: Convert .pages to DOCX via LibreOffice, then MarkItDown.

    Requires LibreOffice (soffice) and the markitdown Python package.
    """
    from quill.core.external_tools import libreoffice_executable

    soffice = libreoffice_executable()
    if soffice is None:
        raise ImportError(
            "LibreOffice (soffice) was not found. On macOS install it from "
            "libreoffice.org or with `brew install --cask libreoffice`."
        )
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        docx_path = tmpdir_path / "converted.docx"

        try:
            subprocess.run(
                [
                    soffice,
                    "--headless",
                    "--convert-to",
                    "docx",
                    "--outdir",
                    str(tmpdir_path),
                    str(path),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )
        except FileNotFoundError as e:
            raise ImportError("LibreOffice (soffice) not found in PATH") from e
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"LibreOffice conversion failed: {stderr}") from e

        if not docx_path.exists():
            raise RuntimeError("LibreOffice did not produce a DOCX file")

        text = convert_with_markitdown(docx_path)

        return Document(
            text=text.strip() + "\n",
            path=path,
            modified=False,
            encoding="utf-8",
            line_ending="\n",
            source_metadata={
                "source_kind": "pages",
                "engine": "libreoffice + markitdown",
                "quality_score": 85,
            },
        )


def outline_pages_document(document: Document) -> list[tuple[int, str]]:
    """Extract heading outline from a Pages-imported document.

    Returns list of (level, heading_text) tuples.
    Expects document text to be Markdown with # headings.
    """
    import re

    headings: list[tuple[int, str]] = []
    for line in document.text.split("\n"):
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            headings.append((len(match.group(1)), match.group(2).strip()))
    return headings
