"""Tests for the Quillins manifest data model and error hierarchy."""

from __future__ import annotations

import pytest

from quill.core.quillins.model import (
    API_VERSION,
    CAP_SCHEDULE,
    CAPABILITIES,
    CONSENT_GATED_CAPABILITIES,
    SCHEMA_ID,
    ApiVersionError,
    CapabilityError,
    ConflictError,
    ConsentDeniedError,
    Contributions,
    ExtensionCommand,
    ExtensionManifest,
    FileTypeContribution,
    ManifestError,
    QuillinError,
    ScheduleContribution,
    SnippetGalleryEntry,
    SnippetParam,
)


def test_schema_and_api_version_are_stable_identifiers() -> None:
    assert SCHEMA_ID == "quill.extension/1"
    assert API_VERSION == 1


def test_consent_gated_caps_are_the_fs_net_and_core_settings_write() -> None:
    # settings.core.write requires explicit user confirmation per change,
    # making it as privileged as file/network access.
    assert CONSENT_GATED_CAPABILITIES == frozenset({
        "fs.read",
        "fs.write",
        "net",
        "settings.core.write",
    })
    assert CONSENT_GATED_CAPABILITIES <= CAPABILITIES


def test_command_is_snippet_or_handler() -> None:
    snippet = ExtensionCommand(id="ext.a.s", title="S", snippet="x")
    handler = ExtensionCommand(id="ext.a.h", title="H", handler="run")
    assert snippet.is_snippet and not snippet.is_handler
    assert handler.is_handler and not handler.is_snippet


def test_manifest_layer_detection() -> None:
    layer1 = ExtensionManifest(id="com.a", name="A", version="1.0.0")
    layer2 = ExtensionManifest(id="com.b", name="B", version="1.0.0", main="extension.py")
    assert not layer1.is_layer_two
    assert layer2.is_layer_two


def test_manifest_has_capability() -> None:
    manifest = ExtensionManifest(
        id="com.a", name="A", version="1.0.0", capabilities=("editor.read",)
    )
    assert manifest.has_capability("editor.read")
    assert not manifest.has_capability("net")


def test_manifest_defaults_are_empty_contributions() -> None:
    manifest = ExtensionManifest(id="com.a", name="A", version="1.0.0")
    assert isinstance(manifest.contributes, Contributions)
    assert manifest.contributes.commands == ()


def test_error_hierarchy_descends_from_quillin_error() -> None:
    for error_type in (
        ManifestError,
        CapabilityError,
        ConsentDeniedError,
        ConflictError,
        ApiVersionError,
    ):
        assert issubclass(error_type, QuillinError)


def test_manifest_error_carries_problem_list() -> None:
    error = ManifestError(["a is bad", "b is bad"])
    assert error.errors == ["a is bad", "b is bad"]
    assert "a is bad" in str(error)


def test_capability_error_names_the_capability() -> None:
    error = CapabilityError("net", detail="fetch(url)")
    assert error.capability == "net"
    assert "net" in str(error)


def test_document_events_catalogue_has_fourteen_entries() -> None:
    from quill.core.quillins.model import DOCUMENT_EVENTS

    expected = {
        "document.opened",
        "document.activated",
        "document.before_save",
        "document.after_save",
        "document.before_close",
        "document.after_close",
        "document.created",
        "document.loaded_from_session",
        "smart_trigger.entered",
        "abbreviation.expanded",
        "quillin.enabled",
        "quillin.disabled",
        "quill.shutdown",
        "settings.changed",
    }
    assert DOCUMENT_EVENTS == expected


def test_contributions_carries_new_contribution_fields() -> None:
    c = Contributions()
    assert c.abbreviations == ()
    assert c.smart_triggers == ()
    assert c.preferences == ()
    assert c.document_events == ()
    assert c.status_bar == ()
    assert c.schedule == ()
    assert c.file_types == ()
    assert c.snippet_gallery == ()


def test_schedule_capability_is_registered() -> None:
    assert CAP_SCHEDULE == "schedule"
    assert CAP_SCHEDULE in CAPABILITIES


def test_schedule_contribution_defaults() -> None:
    sched = ScheduleContribution(id="refresh", interval_seconds=300, handler="on_tick")
    assert sched.description == ""
    assert sched.interval_seconds == 300


def test_file_type_contribution_is_frozen() -> None:
    import dataclasses

    ft = FileTypeContribution(extensions=(".csv",), handler="on_open")
    assert ft.description == ""
    with pytest.raises(dataclasses.FrozenInstanceError):
        ft.handler = "x"  # type: ignore[misc]


def test_snippet_gallery_entry_with_params() -> None:
    entry = SnippetGalleryEntry(
        id="hdr",
        name="Header",
        body="# {title}",
        params=(SnippetParam(name="title", label="Title", default="Untitled"),),
    )
    assert entry.category == ""
    assert entry.params[0].default == "Untitled"
    assert entry.params[0].name == "title"
