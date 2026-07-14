"""BRF sidecar persistence (BR-015, #238).

A *sidecar* stores per-file braille-workflow state — last reading position,
proofing progress, user-confirmed page anchors, and per-page notes — alongside a
braille file as ``<brf_path>.quill.json`` (e.g. ``notes.brf.quill.json``). The
braille file itself is never modified. Writes are atomic via
:func:`quill.core.storage.write_json_atomic` (temp file + ``os.replace``), so an
interrupted write leaves the previous sidecar intact.

This module is pure and wx-free. It is the foundation for restore-on-open
(BR-016, #239) and the Proofing submenu (BR-017, #240).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic

SCHEMA_VERSION = 1
SIDECAR_SUFFIX = ".quill.json"
DOCUMENT_TYPE = "brf"


class BRFSidecarError(ValueError):
    """Raised when a sidecar file exists but cannot be parsed or validated."""


def sidecar_path(brf_path: Path) -> Path:
    """Return the sidecar path for ``brf_path`` (``<name>.quill.json``)."""
    return brf_path.with_name(brf_path.name + SIDECAR_SUFFIX)


def _as_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BRFSidecarError(f"{label} must be an integer")
    return value


def _as_str(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise BRFSidecarError(f"{label} must be a string")
    return value


def _as_int_list(value: Any, label: str) -> list[int]:
    if not isinstance(value, list):
        raise BRFSidecarError(f"{label} must be a list")
    return [_as_int(item, f"{label} item") for item in value]


@dataclass(slots=True)
class SidecarPosition:
    """Last caret position, resolved to braille page/line/cell and print page."""

    last_offset: int = 0
    braille_page: int = 0
    line: int = 0
    cell: int = 0
    print_page: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_offset": self.last_offset,
            "braille_page": self.braille_page,
            "line": self.line,
            "cell": self.cell,
            "print_page": self.print_page,
        }

    @classmethod
    def from_dict(cls, data: Any) -> SidecarPosition:
        if not isinstance(data, dict):
            raise BRFSidecarError("position must be an object")
        return cls(
            last_offset=_as_int(data.get("last_offset", 0), "position.last_offset"),
            braille_page=_as_int(data.get("braille_page", 0), "position.braille_page"),
            line=_as_int(data.get("line", 0), "position.line"),
            cell=_as_int(data.get("cell", 0), "position.cell"),
            print_page=_as_str(data.get("print_page", ""), "position.print_page"),
        )


@dataclass(slots=True)
class SidecarProofing:
    """Proofing progress for the document."""

    last_proofed_braille_page: int = 0
    proofed_pages: list[int] = field(default_factory=list)
    pages_needing_review: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_proofed_braille_page": self.last_proofed_braille_page,
            "proofed_pages": list(self.proofed_pages),
            "pages_needing_review": list(self.pages_needing_review),
        }

    @classmethod
    def from_dict(cls, data: Any) -> SidecarProofing:
        if not isinstance(data, dict):
            raise BRFSidecarError("proofing must be an object")
        return cls(
            last_proofed_braille_page=_as_int(
                data.get("last_proofed_braille_page", 0),
                "proofing.last_proofed_braille_page",
            ),
            proofed_pages=_as_int_list(data.get("proofed_pages", []), "proofing.proofed_pages"),
            pages_needing_review=_as_int_list(
                data.get("pages_needing_review", []), "proofing.pages_needing_review"
            ),
        )


@dataclass(slots=True)
class SidecarAnchor:
    """A user-confirmed braille-page to print-page anchor with confidence."""

    braille_page: int = 0
    print_page: str = ""
    offset: int = 0
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "braille_page": self.braille_page,
            "print_page": self.print_page,
            "offset": self.offset,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Any) -> SidecarAnchor:
        if not isinstance(data, dict):
            raise BRFSidecarError("anchor must be an object")
        confidence = data.get("confidence", 0.0)
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise BRFSidecarError("anchor.confidence must be a number")
        return cls(
            braille_page=_as_int(data.get("braille_page", 0), "anchor.braille_page"),
            print_page=_as_str(data.get("print_page", ""), "anchor.print_page"),
            offset=_as_int(data.get("offset", 0), "anchor.offset"),
            confidence=float(confidence),
        )


@dataclass(slots=True)
class SidecarNote:
    """A free-form note attached to a braille page."""

    braille_page: int = 0
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"braille_page": self.braille_page, "text": self.text}

    @classmethod
    def from_dict(cls, data: Any) -> SidecarNote:
        if not isinstance(data, dict):
            raise BRFSidecarError("note must be an object")
        return cls(
            braille_page=_as_int(data.get("braille_page", 0), "note.braille_page"),
            text=_as_str(data.get("text", ""), "note.text"),
        )


@dataclass(slots=True)
class BRFSidecar:
    """The full sidecar payload for one braille file."""

    document_type: str = DOCUMENT_TYPE
    schema_version: int = SCHEMA_VERSION
    profile: dict[str, Any] = field(default_factory=dict)
    position: SidecarPosition = field(default_factory=SidecarPosition)
    proofing: SidecarProofing = field(default_factory=SidecarProofing)
    anchors: list[SidecarAnchor] = field(default_factory=list)
    notes: list[SidecarNote] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "schema_version": self.schema_version,
            "profile": dict(self.profile),
            "position": self.position.to_dict(),
            "proofing": self.proofing.to_dict(),
            "anchors": [a.to_dict() for a in self.anchors],
            "notes": [n.to_dict() for n in self.notes],
        }

    @classmethod
    def from_dict(cls, data: Any) -> BRFSidecar:
        if not isinstance(data, dict):
            raise BRFSidecarError("sidecar root must be an object")
        profile = data.get("profile", {})
        if not isinstance(profile, dict):
            raise BRFSidecarError("profile must be an object")
        anchors = data.get("anchors", [])
        notes = data.get("notes", [])
        if not isinstance(anchors, list):
            raise BRFSidecarError("anchors must be a list")
        if not isinstance(notes, list):
            raise BRFSidecarError("notes must be a list")
        return cls(
            document_type=_as_str(data.get("document_type", DOCUMENT_TYPE), "document_type"),
            schema_version=_as_int(data.get("schema_version", SCHEMA_VERSION), "schema_version"),
            profile=dict(profile),
            position=SidecarPosition.from_dict(data.get("position", {})),
            proofing=SidecarProofing.from_dict(data.get("proofing", {})),
            anchors=[SidecarAnchor.from_dict(a) for a in anchors],
            notes=[SidecarNote.from_dict(n) for n in notes],
        )


def read_sidecar(brf_path: Path) -> BRFSidecar | None:
    """Read the sidecar for ``brf_path``.

    Returns ``None`` when no sidecar exists. Raises :class:`BRFSidecarError`
    when a sidecar exists but is not valid JSON or does not match the schema.
    """
    path = sidecar_path(brf_path)
    if not path.exists():
        return None
    try:
        raw = read_json(path, default=None)
    except JSONDecodeError as exc:
        raise BRFSidecarError(f"{path.name} is not valid JSON: {exc}") from exc
    return BRFSidecar.from_dict(raw)


def write_sidecar(brf_path: Path, sidecar: BRFSidecar) -> None:
    """Atomically write ``sidecar`` for ``brf_path``."""
    write_json_atomic(sidecar_path(brf_path), sidecar.to_dict())


def clear_sidecar(brf_path: Path) -> None:
    """Remove the sidecar for ``brf_path`` if present (no error if missing)."""
    path = sidecar_path(brf_path)
    if path.exists():
        path.unlink()
