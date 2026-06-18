"""Validation tests for the ``quill.extension/1`` manifest contract.

These exercise :mod:`quill.core.quillins.validation`, the hand-rolled validator
that is the authority the loader enforces (no ``jsonschema`` dependency ships).
"""

from __future__ import annotations

import pytest

from quill.core.quillins.model import ExtensionManifest, ManifestError
from quill.core.quillins.validation import parse_manifest, validate_manifest


def _snippet_manifest() -> dict[str, object]:
    """A minimal, valid Layer 1 (snippet-only) manifest."""

    return {
        "schema": "quill.extension/1",
        "id": "com.example.fence",
        "name": "Code Fence",
        "version": "1.0.0",
        "contributes": {
            "commands": [
                {
                    "id": "ext.fence.wrap",
                    "title": "Wrap In Code Fence",
                    "run": {"snippet": "```\n${selection}\n```\n${cursor}"},
                }
            ],
            "context_menu": [{"when": "editor.hasSelection", "command": "ext.fence.wrap"}],
            "hotkeys": [{"command": "ext.fence.wrap", "binding": "Ctrl+Shift+Grave, F"}],
        },
    }


def _handler_manifest() -> dict[str, object]:
    """A minimal, valid Layer 2 (Python handler) manifest."""

    return {
        "schema": "quill.extension/1",
        "id": "com.example.titlecase",
        "name": "Title Case",
        "version": "1.0.0",
        "capabilities": ["editor.read", "editor.write", "ui.announce", "ui.command"],
        "main": "extension.py",
        "contributes": {
            "commands": [
                {
                    "id": "ext.titlecase.run",
                    "title": "Title Case Selection",
                    "run": {"handler": "title_case"},
                }
            ],
            "menus": [{"parent": "Format", "command": "ext.titlecase.run"}],
        },
    }


def test_valid_snippet_manifest_has_no_errors() -> None:
    assert validate_manifest(_snippet_manifest()) == []


def test_valid_handler_manifest_has_no_errors() -> None:
    assert validate_manifest(_handler_manifest()) == []


def test_parse_builds_immutable_model() -> None:
    manifest = parse_manifest(_handler_manifest())
    assert isinstance(manifest, ExtensionManifest)
    assert manifest.id == "com.example.titlecase"
    assert manifest.is_layer_two
    assert manifest.has_capability("ui.command")
    command = manifest.contributes.commands[0]
    assert command.is_handler and command.handler == "title_case"


def test_parse_snippet_is_layer_one() -> None:
    manifest = parse_manifest(_snippet_manifest())
    assert not manifest.is_layer_two
    assert manifest.contributes.commands[0].is_snippet


def test_non_object_manifest_is_rejected() -> None:
    assert validate_manifest(["not", "an", "object"]) == ["manifest must be a JSON object"]


def test_wrong_schema_is_rejected() -> None:
    raw = _snippet_manifest()
    raw["schema"] = "quill.extension/2"
    errors = validate_manifest(raw)
    assert any("schema must be" in error for error in errors)


def test_unknown_top_level_property_is_rejected() -> None:
    raw = _snippet_manifest()
    raw["surprise"] = True
    errors = validate_manifest(raw)
    assert any("unknown property 'surprise'" in error for error in errors)


@pytest.mark.parametrize("bad_id", ["Com.Example", "ab", "a..b", "ext space"])
def test_invalid_id_is_rejected(bad_id: str) -> None:
    raw = _snippet_manifest()
    raw["id"] = bad_id
    assert validate_manifest(raw) != []


@pytest.mark.parametrize("bad_version", ["1.0", "v1.0.0", "1.0.0.0", "1.0.x"])
def test_invalid_version_is_rejected(bad_version: str) -> None:
    raw = _snippet_manifest()
    raw["version"] = bad_version
    assert any("MAJOR.MINOR.PATCH" in error for error in validate_manifest(raw))


def test_command_id_must_be_ext_namespaced() -> None:
    raw = _snippet_manifest()
    raw["contributes"]["commands"][0]["id"] = "wrap"  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("must match 'ext." in error for error in errors)


def test_command_run_requires_exactly_one_of_snippet_or_handler() -> None:
    raw = _snippet_manifest()
    raw["contributes"]["commands"][0]["run"] = {  # type: ignore[index]
        "snippet": "x",
        "handler": "y",
    }
    errors = validate_manifest(raw)
    assert any("exactly one of snippet or handler" in error for error in errors)


def test_handler_command_requires_main_and_ui_command() -> None:
    raw = _handler_manifest()
    raw.pop("main")
    del raw["capabilities"]  # type: ignore[arg-type]
    errors = validate_manifest(raw)
    assert any("requires a top-level 'main' module" in error for error in errors)
    assert any("requires the 'ui.command' capability" in error for error in errors)


def test_unknown_capability_is_rejected() -> None:
    raw = _snippet_manifest()
    raw["capabilities"] = ["editor.read", "telepathy"]
    errors = validate_manifest(raw)
    assert any("not a known capability" in error for error in errors)


def test_duplicate_capability_is_rejected() -> None:
    raw = _snippet_manifest()
    raw["capabilities"] = ["editor.read", "editor.read"]
    errors = validate_manifest(raw)
    assert any("duplicate" in error for error in errors)


def test_duplicate_command_id_is_rejected() -> None:
    raw = _snippet_manifest()
    commands = raw["contributes"]["commands"]  # type: ignore[index]
    commands.append(dict(commands[0]))
    errors = validate_manifest(raw)
    assert any("duplicate" in error for error in errors)


def test_menu_parent_must_be_known() -> None:
    raw = _handler_manifest()
    raw["contributes"]["menus"][0]["parent"] = "Bogus"  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("parent must be one of" in error for error in errors)


def test_context_when_must_be_known() -> None:
    raw = _snippet_manifest()
    raw["contributes"]["context_menu"][0]["when"] = "editor.onMars"  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("when must be one of" in error for error in errors)


def test_menu_referencing_unknown_ext_command_is_rejected() -> None:
    raw = _snippet_manifest()
    raw["contributes"]["menus"] = [{"parent": "Tools", "command": "ext.nope.missing"}]  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("unknown contributed command 'ext.nope.missing'" in error for error in errors)


def test_builtin_command_reference_checked_when_set_supplied() -> None:
    raw = _snippet_manifest()
    raw["contributes"]["menus"] = [{"parent": "Tools", "command": "app.does_not_exist"}]  # type: ignore[index]
    errors = validate_manifest(raw, builtin_command_ids=frozenset({"app.real"}))
    assert any("unknown built-in command 'app.does_not_exist'" in error for error in errors)
    # Without the built-in set, a non-ext reference is accepted unchecked.
    assert not any("built-in" in error for error in validate_manifest(raw))


def test_parse_raises_manifest_error_with_problem_list() -> None:
    raw = _snippet_manifest()
    raw["version"] = "nope"
    with pytest.raises(ManifestError) as excinfo:
        parse_manifest(raw)
    assert excinfo.value.errors


# ---------------------------------------------------------------------------
# Abbreviation contribution tests
# ---------------------------------------------------------------------------


def _abbrev_manifest(*, use_handler: bool = False) -> dict[str, object]:
    base: dict[str, object] = {
        "schema": "quill.extension/1",
        "id": "com.example.abbrevs",
        "name": "Abbrevs",
        "version": "1.0.0",
        "contributes": {
            "abbreviations": [
                {
                    "trigger": "qtest",
                    "expansion": "Test expansion text.",
                    "description": "A test abbreviation.",
                }
            ]
        },
    }
    if use_handler:
        abbrevs = base["contributes"]["abbreviations"]  # type: ignore[index]
        abbrevs[0].pop("expansion")  # type: ignore[union-attr]
        abbrevs[0]["handler"] = "on_qtest"  # type: ignore[union-attr]
        base["capabilities"] = ["editor.write", "ui.command"]
        base["main"] = "extension.py"
    return base


def test_valid_declarative_abbreviation_has_no_errors() -> None:
    assert validate_manifest(_abbrev_manifest()) == []


def test_valid_handler_abbreviation_has_no_errors() -> None:
    assert validate_manifest(_abbrev_manifest(use_handler=True)) == []


def test_abbreviation_requires_expansion_or_handler() -> None:
    raw = _abbrev_manifest()
    raw["contributes"]["abbreviations"][0].pop("expansion")  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("exactly one of 'expansion' or 'handler'" in e for e in errors)


def test_abbreviation_cannot_have_both_expansion_and_handler() -> None:
    raw = _abbrev_manifest()
    raw["contributes"]["abbreviations"][0]["handler"] = "on_q"  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("exactly one of 'expansion' or 'handler'" in e for e in errors)


def test_duplicate_abbreviation_trigger_is_rejected() -> None:
    raw = _abbrev_manifest()
    dup = dict(raw["contributes"]["abbreviations"][0])  # type: ignore[index]
    raw["contributes"]["abbreviations"].append(dup)  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("duplicate" in e and "qtest" in e for e in errors)


def test_abbreviation_handler_requires_main_and_ui_command() -> None:
    raw = _abbrev_manifest(use_handler=True)
    raw.pop("main")
    del raw["capabilities"]  # type: ignore[arg-type]
    errors = validate_manifest(raw)
    assert any("requires a top-level 'main' module" in e for e in errors)
    assert any("requires the 'ui.command' capability" in e for e in errors)


def test_abbreviation_file_extensions_must_start_with_dot() -> None:
    raw = _abbrev_manifest()
    raw["contributes"]["abbreviations"][0]["file_extensions"] = ["txt", ".md"]  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("must start with '.'" in e and "txt" in e for e in errors)


def test_valid_abbreviation_parsed_into_contributions() -> None:
    m = parse_manifest(_abbrev_manifest())
    assert len(m.contributes.abbreviations) == 1
    entry = m.contributes.abbreviations[0]
    assert isinstance(entry, dict)
    assert entry["trigger"] == "qtest"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Smart trigger contribution tests
# ---------------------------------------------------------------------------


def _smart_trigger_manifest() -> dict[str, object]:
    return {
        "schema": "quill.extension/1",
        "id": "com.example.triggers",
        "name": "Triggers",
        "version": "1.0.0",
        "capabilities": ["editor.write", "ui.announce", "ui.command"],
        "main": "extension.py",
        "contributes": {
            "commands": [
                {
                    "id": "ext.triggers.insert",
                    "title": "Insert From Trigger",
                    "run": {"handler": "on_trigger"},
                }
            ],
            "smart_triggers": [
                {
                    "trigger": "randpara",
                    "command": "ext.triggers.insert",
                    "syntax": "=randpara(count)",
                    "description": "Inserts N random paragraphs.",
                }
            ],
        },
    }


def test_valid_smart_trigger_has_no_errors() -> None:
    assert validate_manifest(_smart_trigger_manifest()) == []


def test_smart_trigger_name_must_match_pattern() -> None:
    raw = _smart_trigger_manifest()
    raw["contributes"]["smart_triggers"][0]["trigger"] = "Bad-Name!"  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("must match" in e for e in errors)


def test_duplicate_smart_trigger_name_is_rejected() -> None:
    raw = _smart_trigger_manifest()
    dup = dict(raw["contributes"]["smart_triggers"][0])  # type: ignore[index]
    raw["contributes"]["smart_triggers"].append(dup)  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("duplicate" in e and "randpara" in e for e in errors)


def test_smart_trigger_min_args_must_not_exceed_max_args() -> None:
    raw = _smart_trigger_manifest()
    raw["contributes"]["smart_triggers"][0]["min_args"] = 5  # type: ignore[index]
    raw["contributes"]["smart_triggers"][0]["max_args"] = 2  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("min_args" in e and "max_args" in e for e in errors)


def test_smart_trigger_command_ref_is_validated() -> None:
    raw = _smart_trigger_manifest()
    raw["contributes"]["smart_triggers"][0]["command"] = "ext.no.such.cmd"  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("unknown contributed command 'ext.no.such.cmd'" in e for e in errors)


def test_smart_trigger_builtin_command_checked_when_set_supplied() -> None:
    raw = _smart_trigger_manifest()
    raw["contributes"]["smart_triggers"][0]["command"] = "app.does_not_exist"  # type: ignore[index]
    errors = validate_manifest(raw, builtin_command_ids=frozenset({"app.real"}))
    assert any("unknown built-in command 'app.does_not_exist'" in e for e in errors)


def test_smart_trigger_file_extensions_must_start_with_dot() -> None:
    raw = _smart_trigger_manifest()
    raw["contributes"]["smart_triggers"][0]["file_extensions"] = ["md", ".txt"]  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("must start with '.'" in e and "md" in e for e in errors)


def test_valid_smart_trigger_parsed_into_contributions() -> None:
    m = parse_manifest(_smart_trigger_manifest())
    assert len(m.contributes.smart_triggers) == 1


# ---------------------------------------------------------------------------
# Preferences contribution tests
# ---------------------------------------------------------------------------


def _prefs_manifest() -> dict[str, object]:
    return {
        "schema": "quill.extension/1",
        "id": "com.example.prefs",
        "name": "Prefs",
        "version": "1.0.0",
        "capabilities": ["settings.own.read", "settings.own.write"],
        "contributes": {
            "preferences": [
                {
                    "id": "main",
                    "title": "Example Settings",
                    "description": "Settings for the example Quillin.",
                    "settings": [
                        {
                            "key": "enabled",
                            "label": "Enable feature",
                            "type": "boolean",
                            "default": True,
                            "description": "Toggle the feature on or off.",
                        }
                    ],
                }
            ]
        },
    }


def test_valid_preferences_has_no_errors() -> None:
    assert validate_manifest(_prefs_manifest()) == []


def test_preferences_requires_settings_capability() -> None:
    raw = _prefs_manifest()
    del raw["capabilities"]  # type: ignore[arg-type]
    errors = validate_manifest(raw)
    assert any("settings.own.read" in e or "settings.own.write" in e for e in errors)


def test_preferences_setting_type_must_be_known() -> None:
    raw = _prefs_manifest()
    raw["contributes"]["preferences"][0]["settings"][0]["type"] = "telepathy"  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("type" in e and "telepathy" in e for e in errors)


def test_preferences_setting_requires_all_mandatory_fields() -> None:
    raw = _prefs_manifest()
    del raw["contributes"]["preferences"][0]["settings"][0]["description"]  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("description" in e for e in errors)


def test_preferences_condition_requires_setting_and_equals() -> None:
    raw = _prefs_manifest()
    raw["contributes"]["preferences"][0]["settings"][0]["visible_when"] = {  # type: ignore[index]
        "setting": "enabled"
        # missing "equals"
    }
    errors = validate_manifest(raw)
    assert any("'equals'" in e for e in errors)


def test_preferences_tab_missing_order_is_rejected() -> None:
    raw = _prefs_manifest()
    raw["contributes"]["preferences"][0]["tabs"] = [  # type: ignore[index]
        {
            "id": "general",
            "title": "General",
            "description": "General settings.",
            # missing "order"
        }
    ]
    errors = validate_manifest(raw)
    assert any("order" in e for e in errors)


def test_valid_preferences_parsed_into_contributions() -> None:
    m = parse_manifest(_prefs_manifest())
    assert len(m.contributes.preferences) == 1


# ---------------------------------------------------------------------------
# Document event contribution tests
# ---------------------------------------------------------------------------


def _doc_events_manifest() -> dict[str, object]:
    return {
        "schema": "quill.extension/1",
        "id": "com.example.eventer",
        "name": "Eventer",
        "version": "1.0.0",
        "capabilities": ["document.events", "editor.write", "ui.announce"],
        "main": "extension.py",
        "contributes": {
            "document_events": [
                {
                    "event": "document.opened",
                    "handler": "on_opened",
                    "title": "On Opened",
                    "description": "Runs when a document is opened from disk.",
                }
            ]
        },
    }


def test_valid_document_event_has_no_errors() -> None:
    assert validate_manifest(_doc_events_manifest()) == []


def test_unknown_document_event_name_is_rejected() -> None:
    raw = _doc_events_manifest()
    raw["contributes"]["document_events"][0]["event"] = "document.hacked"  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("not a recognized event" in e for e in errors)


def test_document_events_requires_document_events_capability() -> None:
    raw = _doc_events_manifest()
    raw["capabilities"] = ["editor.write", "ui.announce"]
    errors = validate_manifest(raw)
    assert any("'document.events' capability" in e for e in errors)


def test_document_events_requires_main_module() -> None:
    raw = _doc_events_manifest()
    raw.pop("main")
    errors = validate_manifest(raw)
    assert any("requires a top-level 'main' module" in e for e in errors)


def test_duplicate_document_event_handler_pair_is_rejected() -> None:
    raw = _doc_events_manifest()
    dup = dict(raw["contributes"]["document_events"][0])  # type: ignore[index]
    raw["contributes"]["document_events"].append(dup)  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("duplicate" in e and "document.opened" in e for e in errors)


def test_same_event_different_handlers_is_allowed() -> None:
    raw = _doc_events_manifest()
    second = {
        "event": "document.opened",
        "handler": "on_opened_also",
        "title": "Also On Opened",
        "description": "Another handler for the same event.",
    }
    raw["contributes"]["document_events"].append(second)  # type: ignore[index]
    assert validate_manifest(raw) == []


def test_document_event_filter_extensions_must_start_with_dot() -> None:
    raw = _doc_events_manifest()
    raw["contributes"]["document_events"][0]["filter_extensions"] = ["log", ".txt"]  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("must start with '.'" in e and "log" in e for e in errors)


def test_document_event_conditions_unknown_key_is_rejected() -> None:
    raw = _doc_events_manifest()
    raw["contributes"]["document_events"][0]["conditions"] = {  # type: ignore[index]
        "file_extension": ".txt",
        "surprise_field": "value",
    }
    errors = validate_manifest(raw)
    assert any("surprise_field" in e for e in errors)


def test_valid_document_events_parsed_into_contributions() -> None:
    m = parse_manifest(_doc_events_manifest())
    assert len(m.contributes.document_events) == 1
    entry = m.contributes.document_events[0]
    assert isinstance(entry, dict)
    assert entry["event"] == "document.opened"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Lifecycle events (quillin.enabled, quillin.disabled, quill.shutdown, settings.changed)
# ---------------------------------------------------------------------------


def test_lifecycle_events_are_valid_document_events() -> None:
    for event in ("quillin.enabled", "quillin.disabled", "quill.shutdown", "settings.changed"):
        raw = _doc_events_manifest()
        raw["contributes"]["document_events"][0]["event"] = event  # type: ignore[index]
        errors = validate_manifest(raw)
        assert not errors, f"Expected no errors for event {event!r}: {errors}"


# ---------------------------------------------------------------------------
# Command description
# ---------------------------------------------------------------------------


def test_command_description_is_optional() -> None:
    raw = _handler_manifest()
    raw["contributes"]["commands"][0]["description"] = "Makes selected text title case."  # type: ignore[index]
    errors = validate_manifest(raw)
    assert not errors


def test_command_description_is_parsed() -> None:
    raw = _handler_manifest()
    raw["contributes"]["commands"][0]["description"] = "My description."  # type: ignore[index]
    m = parse_manifest(raw)
    assert m.contributes.commands[0].description == "My description."


def test_command_description_too_long_is_rejected() -> None:
    raw = _handler_manifest()
    raw["contributes"]["commands"][0]["description"] = "x" * 401  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("description" in e for e in errors)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


def _categories_manifest() -> dict[str, object]:
    raw = _snippet_manifest()
    raw["categories"] = ["writing", "productivity"]
    return raw


def test_valid_categories_has_no_errors() -> None:
    assert not validate_manifest(_categories_manifest())


def test_categories_parsed_into_manifest() -> None:
    m = parse_manifest(_categories_manifest())
    assert "writing" in m.categories
    assert "productivity" in m.categories


def test_unknown_category_is_rejected() -> None:
    raw = _categories_manifest()
    raw["categories"] = ["writing", "games"]
    errors = validate_manifest(raw)
    assert any("games" in e for e in errors)


def test_duplicate_category_is_rejected() -> None:
    raw = _categories_manifest()
    raw["categories"] = ["writing", "writing"]
    errors = validate_manifest(raw)
    assert any("duplicate" in e for e in errors)


def test_categories_must_be_array() -> None:
    raw = _categories_manifest()
    raw["categories"] = "writing"
    errors = validate_manifest(raw)
    assert any("categories" in e for e in errors)


# ---------------------------------------------------------------------------
# Requires
# ---------------------------------------------------------------------------


def _requires_manifest() -> dict[str, object]:
    raw = _snippet_manifest()
    raw["requires"] = [{"id": "com.quill.journalstamp", "min_version": "1.0.0"}]
    return raw


def test_valid_requires_has_no_errors() -> None:
    assert not validate_manifest(_requires_manifest())


def test_requires_parsed_into_manifest() -> None:
    m = parse_manifest(_requires_manifest())
    assert len(m.requires) == 1
    dep = m.requires[0]
    assert dep.id == "com.quill.journalstamp"
    assert dep.min_version == "1.0.0"


def test_requires_min_version_is_optional() -> None:
    raw = _requires_manifest()
    raw["requires"] = [{"id": "com.quill.journalstamp"}]
    errors = validate_manifest(raw)
    assert not errors


def test_requires_bad_version_is_rejected() -> None:
    raw = _requires_manifest()
    raw["requires"] = [{"id": "com.quill.journalstamp", "min_version": "1.0"}]
    errors = validate_manifest(raw)
    assert any("min_version" in e for e in errors)


def test_requires_bad_id_is_rejected() -> None:
    raw = _requires_manifest()
    raw["requires"] = [{"id": "Not A Valid ID"}]
    errors = validate_manifest(raw)
    assert any("id" in e for e in errors)


def test_requires_duplicate_id_is_rejected() -> None:
    raw = _requires_manifest()
    raw["requires"] = [
        {"id": "com.quill.journalstamp"},
        {"id": "com.quill.journalstamp"},
    ]
    errors = validate_manifest(raw)
    assert any("duplicate" in e for e in errors)


# ---------------------------------------------------------------------------
# net_allowed_hosts
# ---------------------------------------------------------------------------


def _net_manifest() -> dict[str, object]:
    raw = {
        "schema": "quill.extension/1",
        "id": "com.example.weather",
        "name": "Weather Sidebar",
        "version": "1.0.0",
        "capabilities": ["net", "ui.announce", "ui.command"],
        "main": "extension.py",
        "net_allowed_hosts": ["api.openweathermap.org"],
    }
    return raw


def test_valid_net_allowed_hosts_has_no_errors() -> None:
    assert not validate_manifest(_net_manifest())


def test_net_allowed_hosts_parsed_into_manifest() -> None:
    m = parse_manifest(_net_manifest())
    assert "api.openweathermap.org" in m.net_allowed_hosts


def test_net_allowed_hosts_without_net_cap_is_rejected() -> None:
    raw = _net_manifest()
    raw["capabilities"] = ["ui.announce", "ui.command"]
    errors = validate_manifest(raw)
    assert any("net" in e for e in errors)


def test_net_allowed_hosts_wildcard_is_valid() -> None:
    raw = _net_manifest()
    raw["net_allowed_hosts"] = ["*.openweathermap.org"]
    assert not validate_manifest(raw)


def test_net_allowed_hosts_bad_pattern_is_rejected() -> None:
    raw = _net_manifest()
    raw["net_allowed_hosts"] = ["not a hostname!"]
    errors = validate_manifest(raw)
    assert any("net_allowed_hosts" in e for e in errors)


def test_net_allowed_hosts_duplicate_is_rejected() -> None:
    raw = _net_manifest()
    raw["net_allowed_hosts"] = ["api.openweathermap.org", "api.openweathermap.org"]
    errors = validate_manifest(raw)
    assert any("duplicate" in e for e in errors)


# ---------------------------------------------------------------------------
# Status bar
# ---------------------------------------------------------------------------


def _status_bar_manifest() -> dict[str, object]:
    return {
        "schema": "quill.extension/1",
        "id": "com.example.statusdemo",
        "name": "Status Demo",
        "version": "1.0.0",
        "capabilities": ["ui.status", "ui.command"],
        "main": "extension.py",
        "contributes": {
            "status_bar": [
                {
                    "id": "wordcount",
                    "label": "Words: --",
                    "handler": "get_word_count",
                    "tooltip": "Current document word count",
                    "width": 12,
                }
            ]
        },
    }


def test_valid_status_bar_has_no_errors() -> None:
    assert not validate_manifest(_status_bar_manifest())


def test_status_bar_parsed_into_contributions() -> None:
    from quill.core.quillins.model import StatusBarContribution

    m = parse_manifest(_status_bar_manifest())
    assert len(m.contributes.status_bar) == 1
    cell = m.contributes.status_bar[0]
    assert isinstance(cell, StatusBarContribution)
    assert cell.id == "wordcount"
    assert cell.handler == "get_word_count"
    assert cell.width == 12


def test_status_bar_requires_ui_status_capability() -> None:
    raw = _status_bar_manifest()
    raw["capabilities"] = ["ui.command"]
    errors = validate_manifest(raw)
    assert any("ui.status" in e for e in errors)


def test_status_bar_requires_main_module() -> None:
    raw = _status_bar_manifest()
    del raw["main"]
    raw["capabilities"] = ["ui.status", "ui.command"]
    errors = validate_manifest(raw)
    assert any("main" in e for e in errors)


def test_status_bar_duplicate_cell_id_is_rejected() -> None:
    raw = _status_bar_manifest()
    raw["contributes"]["status_bar"].append(  # type: ignore[index]
        {"id": "wordcount", "label": "Words: --", "handler": "other_handler"}
    )
    errors = validate_manifest(raw)
    assert any("duplicate" in e for e in errors)


def test_status_bar_width_out_of_range_is_rejected() -> None:
    raw = _status_bar_manifest()
    raw["contributes"]["status_bar"][0]["width"] = 99  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("width" in e for e in errors)


# ---------------------------------------------------------------------------
# Preferences search_keywords
# ---------------------------------------------------------------------------


def test_pref_setting_search_keywords_valid() -> None:
    raw = _prefs_manifest()
    raw["contributes"]["preferences"][0]["settings"][0]["search_keywords"] = [
        "date",
        "header",
        "journal",
    ]  # type: ignore[index]
    errors = validate_manifest(raw)
    assert not errors


def test_pref_setting_search_keywords_must_be_array() -> None:
    raw = _prefs_manifest()
    raw["contributes"]["preferences"][0]["settings"][0]["search_keywords"] = "date"  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("search_keywords" in e for e in errors)


def test_pref_setting_search_keyword_too_long_is_rejected() -> None:
    raw = _prefs_manifest()
    raw["contributes"]["preferences"][0]["settings"][0]["search_keywords"] = ["x" * 65]  # type: ignore[index]
    errors = validate_manifest(raw)
    assert any("search_keywords" in e for e in errors)


# -- schedule (Part 1) -------------------------------------------------------


def _schedule_manifest(interval_seconds: int = 60) -> dict[str, object]:
    return {
        "schema": "quill.extension/1",
        "id": "com.example.timer",
        "name": "Timer",
        "version": "1.0.0",
        "capabilities": ["schedule"],
        "main": "extension.py",
        "contributes": {
            "schedule": [{"id": "tick", "interval_seconds": interval_seconds, "handler": "on_tick"}]
        },
    }


def test_schedule_valid() -> None:
    assert validate_manifest(_schedule_manifest(60)) == []


def test_schedule_too_short() -> None:
    errors = validate_manifest(_schedule_manifest(59))
    assert any("interval_seconds" in e for e in errors)


def test_schedule_too_long() -> None:
    errors = validate_manifest(_schedule_manifest(86401))
    assert any("interval_seconds" in e for e in errors)


def test_schedule_requires_capability() -> None:
    raw = _schedule_manifest(60)
    raw["capabilities"] = []
    errors = validate_manifest(raw)
    assert any("schedule" in e and "capability" in e for e in errors)


def test_schedule_requires_main() -> None:
    raw = _schedule_manifest(60)
    del raw["main"]
    errors = validate_manifest(raw)
    assert any("schedule" in e and "main" in e for e in errors)


def test_schedule_duplicate_id_is_rejected() -> None:
    raw = _schedule_manifest(60)
    raw["contributes"]["schedule"].append(  # type: ignore[index,union-attr]
        {"id": "tick", "interval_seconds": 120, "handler": "on_tick2"}
    )
    errors = validate_manifest(raw)
    assert any("duplicate" in e for e in errors)


def test_parse_schedule_builds_model() -> None:
    manifest = parse_manifest(_schedule_manifest(300))
    assert manifest.contributes.schedule[0].id == "tick"
    assert manifest.contributes.schedule[0].interval_seconds == 300
    assert manifest.contributes.schedule[0].handler == "on_tick"


# -- file_types (Part 2) -----------------------------------------------------


def _file_types_manifest(extensions: object = (".csv",)) -> dict[str, object]:
    return {
        "schema": "quill.extension/1",
        "id": "com.example.ftype",
        "name": "FileType",
        "version": "1.0.0",
        "capabilities": ["document.events"],
        "main": "extension.py",
        "contributes": {"file_types": [{"extensions": list(extensions), "handler": "on_open"}]},
    }


def test_file_types_valid() -> None:
    assert validate_manifest(_file_types_manifest([".csv"])) == []


def test_file_types_bad_extension() -> None:
    errors = validate_manifest(_file_types_manifest(["csv"]))
    assert any("must start with '.'" in e for e in errors)


def test_file_types_requires_document_events_capability() -> None:
    raw = _file_types_manifest([".csv"])
    raw["capabilities"] = []
    errors = validate_manifest(raw)
    assert any("file_types" in e and "document.events" in e for e in errors)


def test_file_types_requires_main() -> None:
    raw = _file_types_manifest([".csv"])
    del raw["main"]
    errors = validate_manifest(raw)
    assert any("file_types" in e and "main" in e for e in errors)


def test_parse_file_types_builds_model() -> None:
    manifest = parse_manifest(_file_types_manifest([".brf", ".brl"]))
    ft = manifest.contributes.file_types[0]
    assert ft.extensions == (".brf", ".brl")
    assert ft.handler == "on_open"


# -- snippet_gallery (Part 3) ------------------------------------------------


def _gallery_manifest(
    body: str = "Hello {name}", params: object | None = None
) -> dict[str, object]:
    entry: dict[str, object] = {"id": "greet", "name": "Greeting", "body": body}
    if params is not None:
        entry["params"] = params
    return {
        "schema": "quill.extension/1",
        "id": "com.example.gallery",
        "name": "Gallery",
        "version": "1.0.0",
        "contributes": {"snippet_gallery": [entry]},
    }


def test_snippet_gallery_valid() -> None:
    raw = _gallery_manifest("Hello {name}", [{"name": "name", "label": "Name"}])
    assert validate_manifest(raw) == []


def test_snippet_gallery_param_not_in_body() -> None:
    raw = _gallery_manifest("Hello there", [{"name": "name", "label": "Name"}])
    errors = validate_manifest(raw)
    assert any("placeholder" in e for e in errors)


def test_snippet_gallery_duplicate_id() -> None:
    raw = _gallery_manifest("Hi")
    raw["contributes"]["snippet_gallery"].append(  # type: ignore[index,union-attr]
        {"id": "greet", "name": "Other", "body": "Bye"}
    )
    errors = validate_manifest(raw)
    assert any("duplicate" in e for e in errors)


def test_snippet_gallery_needs_no_capability() -> None:
    # Pure snippets run no code, so the gallery requires no capability or main.
    assert validate_manifest(_gallery_manifest("just text")) == []


def test_parse_snippet_gallery_builds_model() -> None:
    raw = _gallery_manifest("Hello {name}", [{"name": "name", "label": "Name", "default": "x"}])
    manifest = parse_manifest(raw)
    entry = manifest.contributes.snippet_gallery[0]
    assert entry.id == "greet"
    assert entry.params[0].name == "name"
    assert entry.params[0].default == "x"
