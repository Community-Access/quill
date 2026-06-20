from pathlib import Path

from quill.core.document import Document


def test_document_name_defaults_to_untitled() -> None:
    document = Document()
    assert document.name == "Untitled"


def test_document_name_uses_file_name() -> None:
    document = Document(path=Path("C:\\tmp\\story.md"))
    assert document.name == "story.md"


def test_set_text_marks_document_modified_and_increments_revision() -> None:
    document = Document(text="one")
    document.set_text("two")
    assert document.modified is True
    assert document.revision == 1


def test_set_text_no_op_does_not_bump_revision() -> None:
    """Regression for #341: no-op writes must not advance the revision
    counter. The contract is that revision reflects distinct textual
    changes only."""
    document = Document(text="one")
    baseline = document.revision
    document.set_text("one")
    assert document.revision == baseline
    document.set_text("two")
    assert document.revision == baseline + 1
    document.set_text("two")
    assert document.revision == baseline + 1


def test_mark_saved_does_not_bump_revision() -> None:
    """Regression for #341: path / modified / encoding / line-ending
    mutations are state changes but not textual edits, so revision stays
    put when only those change."""
    document = Document(text="one")
    document.set_text("two")
    revision_after_edit = document.revision
    document.mark_saved(Path("C:\\tmp\\doc.txt"))
    assert document.revision == revision_after_edit


def test_revision_can_be_seeded_via_private_field_for_tests() -> None:
    """Regression for #341: tests that need a deterministic revision value
    can construct a Document with the private _revision dataclass field
    (Document.revision is a read-only property with no public setter)."""
    document = Document(text="x", _revision=42)
    assert document.revision == 42
