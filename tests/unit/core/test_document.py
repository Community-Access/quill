from __future__ import annotations

from pathlib import Path

from quill.core.document import Document


def test_document_name_prefers_path_when_present(tmp_path: Path) -> None:
    document = Document(
        path=tmp_path / "local.txt",
        source_metadata={"display_name": "Remote Title"},
    )

    assert document.name == "local.txt"


def test_document_name_uses_metadata_display_name_without_path() -> None:
    document = Document(source_metadata={"display_name": "  Remote\nItem\tTitle  "})

    assert document.name == "Remote Item Title"


def test_document_name_defaults_to_untitled_without_path_or_display_name() -> None:
    assert Document().name == "Untitled"
