"""Tests for the verb catalog and registry (§15) and schema constants."""

from __future__ import annotations

import pytest

from quill.core.verbosity.parser import validate
from quill.core.verbosity.registry import (
    DuplicateVerbError,
    VerbRegistry,
    default_registry,
)
from quill.core.verbosity.schema import SCHEMAS, schema_for
from quill.core.verbosity.verbs import BUILTIN_VERBS, Severity

# The §15 prose says "44" but enumerates 34; the catalog is the source of truth.
_EXPECTED_IDS = {
    "nav.next_line",
    "nav.previous_line",
    "nav.next_word",
    "nav.previous_word",
    "nav.next_character",
    "nav.previous_character",
    "nav.document_start",
    "nav.document_end",
    "nav.next_print_page",
    "nav.previous_print_page",
    "edit.insert_text",
    "edit.delete_character",
    "edit.delete_word",
    "edit.select_word_right",
    "edit.select_line",
    "edit.unquote_lines",
    "doc.open",
    "doc.save",
    "doc.save_as",
    "doc.modified",
    "doc.read_only",
    "doc.encoding_changed",
    "search.find",
    "search.find_next",
    "search.find_previous",
    "search.no_results",
    "search.replace",
    "search.replace_all",
    "system.error",
    "system.warning",
    "system.info",
    "system.progress",
    "system.operation_complete",
    "_legacy",
}


def test_default_registry_has_full_catalog() -> None:
    registry = default_registry()
    assert {verb.id for verb in registry.all()} == _EXPECTED_IDS
    assert len(registry) == len(_EXPECTED_IDS)


def test_catalog_ids_unique() -> None:
    ids = [verb.id for verb in BUILTIN_VERBS]
    assert len(ids) == len(set(ids))


def test_all_returns_sorted_by_id() -> None:
    registry = default_registry()
    ids = [verb.id for verb in registry.all()]
    assert ids == sorted(ids)


def test_get_returns_registered_verb() -> None:
    registry = default_registry()
    verb = registry.get("doc.save")
    assert verb is not None
    assert verb.human_name == "Save document"
    assert registry.get("nope") is None


def test_contains() -> None:
    registry = default_registry()
    assert "doc.save" in registry
    assert "doc.nope" not in registry


def test_duplicate_registration_raises_structured_error() -> None:
    registry = default_registry()
    with pytest.raises(DuplicateVerbError) as excinfo:
        registry.register(BUILTIN_VERBS[0])
    assert excinfo.value.verb_id == BUILTIN_VERBS[0].id


def test_empty_registry_register_and_get() -> None:
    registry = VerbRegistry()
    assert len(registry) == 0
    registry.register(BUILTIN_VERBS[0])
    assert len(registry) == 1


def test_namespace_matches_id_prefix() -> None:
    for verb in BUILTIN_VERBS:
        expected = verb.id.split(".", 1)[0]
        assert verb.namespace == expected


def test_every_default_template_validates_against_its_tokens() -> None:
    # A verb's own default template must satisfy its own §13 contract.
    for verb in BUILTIN_VERBS:
        report = validate(verb.default_template, verb)
        assert report.ok, f"{verb.id}: {[i.message for i in report.errors]}"


def test_severities_are_valid() -> None:
    for verb in BUILTIN_VERBS:
        assert isinstance(verb.severity, Severity)


def test_schema_registry_complete() -> None:
    assert set(SCHEMAS) == {"settings", "custom_profile", "qvp", "profile_io"}
    # The QVP schema is the canonical .qvp.json (§20): nested pack metadata.
    required = schema_for("qvp")["required"]
    assert "pack" in required and "templates" in required
    assert "name" in schema_for("qvp")["properties"]["pack"]["required"]


def test_qvp_schema_forbids_unknown_fields() -> None:
    # Data-only contract: no room for an executable/code field to sneak in.
    assert schema_for("qvp")["additionalProperties"] is False
    assert schema_for("qvp")["properties"]["kind"]["const"] == "quill-verbosity-pack"
