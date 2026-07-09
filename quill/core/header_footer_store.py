"""Per-document Header/Footer spec storage (#892).

Stored as document metadata (part of the document's identity, keyed by its
normalized path, surviving save/reload) rather than a one-off print-time
setting -- the same ``key_for``-by-path shape :class:`~quill.core.bookmarks.DocumentMemory`
already uses, so an untitled (unsaved) document simply isn't persisted.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from quill.core.bookmarks import DocumentMemory
from quill.core.header_footer import HeaderFooterSpec, PageNumberStyle
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = ["HeaderFooterStore"]

_FILENAME = "header_footer.json"

key_for = DocumentMemory.key_for


@dataclass(slots=True)
class HeaderFooterStore:
    path: Path = field(default_factory=lambda: app_data_dir() / _FILENAME)
    documents: dict[str, HeaderFooterSpec] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> HeaderFooterStore:
        target = path if path is not None else app_data_dir() / _FILENAME
        try:
            raw = read_json(target, default={})
        except (OSError, ValueError):
            raw = {}
        documents: dict[str, HeaderFooterSpec] = {}
        if isinstance(raw, dict):
            for key, entry in raw.items():
                if not isinstance(key, str) or not isinstance(entry, dict):
                    continue
                try:
                    documents[key] = HeaderFooterSpec(
                        header_left=str(entry.get("header_left", "")),
                        header_center=str(entry.get("header_center", "")),
                        header_right=str(entry.get("header_right", "")),
                        footer_left=str(entry.get("footer_left", "")),
                        footer_center=str(entry.get("footer_center", "")),
                        footer_right=str(entry.get("footer_right", "")),
                        first_page_different=bool(entry.get("first_page_different", False)),
                        first_page_header_left=str(entry.get("first_page_header_left", "")),
                        first_page_header_center=str(entry.get("first_page_header_center", "")),
                        first_page_header_right=str(entry.get("first_page_header_right", "")),
                        first_page_footer_left=str(entry.get("first_page_footer_left", "")),
                        first_page_footer_center=str(entry.get("first_page_footer_center", "")),
                        first_page_footer_right=str(entry.get("first_page_footer_right", "")),
                        page_number_style=(
                            PageNumberStyle.ROMAN
                            if entry.get("page_number_style") == PageNumberStyle.ROMAN
                            else PageNumberStyle.ARABIC
                        ),
                        start_page_number=max(1, int(entry.get("start_page_number", 1))),
                    )
                except (TypeError, ValueError):
                    continue
        return cls(path=target, documents=documents)

    def save(self) -> None:
        ordered = {key: asdict(self.documents[key]) for key in sorted(self.documents)}
        write_json_atomic(self.path, ordered)

    def get(self, key: str | None) -> HeaderFooterSpec | None:
        if not key:
            return None
        return self.documents.get(key)

    def set(self, key: str | None, spec: HeaderFooterSpec) -> None:
        if not key:
            return
        self.documents[key] = spec
        self.save()

    def clear(self, key: str | None) -> None:
        if not key:
            return
        self.documents.pop(key, None)
        self.save()
