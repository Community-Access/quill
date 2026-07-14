"""Tests for the verbosity templates library (§19)."""

from __future__ import annotations

import pytest

from quill.core.verbosity.library import (
    TemplateLibrary,
    TemplateSource,
    apply_template_to_verb,
)
from quill.core.verbosity.registry import default_registry


def _verb(verb_id: str):
    verb = default_registry().get(verb_id)
    assert verb is not None
    return verb


def test_library_starts_with_builtins() -> None:
    library = TemplateLibrary()
    names = [tpl.name for tpl in library.all()]
    assert "Default line" in names
    entries = library.all()
    assert all(a.name <= b.name for a, b in zip(entries, entries[1:], strict=False))


def test_save_creates_user_template() -> None:
    library = TemplateLibrary()
    entry = library.save("My nav", "Line {line} of {total}")
    assert entry.source == TemplateSource.USER
    assert entry.editable
    assert library.get("My nav") is not None


def test_cannot_overwrite_builtin() -> None:
    library = TemplateLibrary()
    with pytest.raises(ValueError):
        library.save("Default line", "hacked")


def test_rename_user_template() -> None:
    library = TemplateLibrary()
    library.save("Old", "Line {line}")
    library.rename("Old", "New")
    assert library.get("Old") is None
    assert library.get("New") is not None


def test_rename_conflict_raises() -> None:
    library = TemplateLibrary()
    library.save("A", "{line}")
    library.save("B", "{total}")
    with pytest.raises(ValueError):
        library.rename("A", "B")


def test_delete_user_template() -> None:
    library = TemplateLibrary()
    library.save("Temp", "{line}")
    library.delete("Temp")
    assert library.get("Temp") is None


def test_delete_builtin_refused() -> None:
    library = TemplateLibrary()
    with pytest.raises(ValueError):
        library.delete("Default line")


def test_install_from_pack_is_read_only() -> None:
    library = TemplateLibrary()
    entry = library.install_from_pack("Kelly concise", "L{line}", pack="Concise Nav")
    assert entry.source == TemplateSource.QVP
    assert not entry.editable
    with pytest.raises(ValueError):
        library.delete("Kelly concise")


def test_apply_strips_unsupported_tokens_and_reports() -> None:
    # doc.save supports {name} only; {line} and {column} are not tracked.
    result = apply_template_to_verb("Saved {name} at {line}:{column}", _verb("doc.save"))
    assert "line" in result.removed_tokens
    assert "column" in result.removed_tokens
    assert "{line}" not in result.template
    assert "Removed 2 tokens" in result.message
    assert "line, column" in result.message


def test_apply_no_removal_clean_message() -> None:
    result = apply_template_to_verb("Saved {name}", _verb("doc.save"))
    assert result.removed_tokens == ()
    assert result.message == "Applied template."


def test_library_apply_by_name() -> None:
    library = TemplateLibrary()
    library.save("Tight", "Line {line} col {column}")
    result = library.apply("Tight", _verb("nav.next_word"))  # supports word, column
    assert "line" in result.removed_tokens
    assert "column" not in result.removed_tokens
