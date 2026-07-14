from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core import paths
from quill.core.commands import CommandRegistry
from quill.core.features import (
    FEATURE_STATE_OFF,
    FEATURE_STATE_ON,
    FEATURE_STATE_QUIET,
    PROFILE_ACCESSIBILITY_PROFESSIONAL,
    PROFILE_DEFINITIONS,
    PROFILE_DEVELOPER_POWER_TEXT,
    PROFILE_ESSENTIAL,
    PROFILE_FULL_QUILL,
    FeatureManager,
    export_feature_profile_file,
    feature_for_command,
    find_feature,
    import_feature_profile_file,
)


@pytest.fixture(autouse=True)
def feature_data_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    data_dir = fake_home / "quill-data"
    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setenv("QUILL_DATA_DIR", str(data_dir))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE_ROOT", raising=False)
    return data_dir


def test_feature_mapping_infers_command_groups() -> None:
    assert feature_for_command("edit.find") == "core.search"
    assert feature_for_command("edit.replace") == "core.search"
    assert feature_for_command("edit.replace_all") == "core.search.regex"
    assert feature_for_command("tools.read_aloud_start_pause") == "core.read_aloud"
    assert feature_for_command("tools.watch_folder_toggle") == "core.watch_folder"
    assert feature_for_command("tools.watch_folder_settings") == "core.watch_folder"
    assert feature_for_command("tools.watch_folder_status") == "core.watch_folder"
    assert feature_for_command("whisperer.model_manager") == "core.bw_transcription"
    assert feature_for_command("whisperer.model_status") == "core.bw_transcription"
    assert feature_for_command("whisperer.model_recommend") == "core.bw_transcription"
    assert feature_for_command("whisperer.check_faster_whisper") == "core.bw_transcription"
    assert feature_for_command("whisperer.provider_center") == "core.bw_providers"
    assert feature_for_command("whisperer.provider_status") == "core.bw_providers"
    assert feature_for_command("whisperer.provider_recommend") == "core.bw_providers"
    assert feature_for_command("whisperer.provider_select") == "core.bw_providers"
    assert feature_for_command("whisperer.readiness_check") == "core.bw_insights"
    assert feature_for_command("whisperer.capability_matrix") == "core.bw_insights"
    assert feature_for_command("whisperer.download_queue") == "core.bw_insights"
    assert feature_for_command("tools.announcement_backend") == "core.accessibility"
    assert feature_for_command("tools.announcement_trace_toggle") == "core.accessibility"
    assert feature_for_command("format.insert_table") == "core.format"
    assert feature_for_command("edit.word_prediction") == "core.intellisense"
    assert feature_for_command("help.open_logs_folder") == "core.help"
    assert feature_for_command("help.open_diagnostics_folder") == "core.help"
    assert feature_for_command("tools.yaml_structure_editor") == "core.format"
    assert feature_for_command("tools.ai_assistant") == "future.ai"
    assert feature_for_command("tools.ai_rewrite_selection") == "future.ai"
    assert feature_for_command("tools.ai_summarize_selection") == "future.ai"
    assert feature_for_command("tools.ai_continue_writing") == "future.ai"
    assert feature_for_command("tools.ai_fix_grammar") == "future.ai"
    assert feature_for_command("tools.run_python") == "future.ai"


def test_feature_mapping_returns_nested_feature_id() -> None:
    """Regression for #346: feature_for_command must pass through the nested
    feature id that the COMMAND_FEATURE_MAP declares verbatim. Downstream
    consumers (find_feature / FeatureManager) match against the literal id
    in FEATURE_DEFINITIONS, so a nested id with an internal dot must
    survive the round-trip without truncation."""
    # The typescript-console command maps to a sub-feature of developer_console.
    nested = feature_for_command("tools.open_typescript_console")
    assert nested == "core.developer_console.typescript"

    # find_feature must resolve the nested id back to its own definition
    # (not the parent core.developer_console).
    feature = find_feature(nested)
    assert feature is not None
    assert feature.id == "core.developer_console.typescript"
    assert "typescript" in feature.name.lower()
    # The nested feature must declare its parent dependency so a state
    # change propagates correctly.
    assert "core.developer_console" in feature.dependencies


def test_feature_manager_respects_profile_state() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_ESSENTIAL)
    assert manager.state_for("core.file") == FEATURE_STATE_ON
    assert manager.state_for("core.search.regex") == FEATURE_STATE_OFF
    assert manager.state_for("future.ai") == FEATURE_STATE_QUIET
    # future.publishing is locked_off (publishing-providers-framework branch
    # under review), which overrides any profile's quiet/on state.
    assert manager.state_for("future.publishing") == FEATURE_STATE_OFF


def test_casual_writer_is_a_focused_just_write_profile() -> None:
    """#890: Casual Writer turns off power/AI/review/remote/developer surfaces
    (an unlisted feature defaults to ON, so each must be named), while keeping
    the write/format/print/send core -- and all screen-reader I/O -- available."""
    from quill.core.features import PROFILE_WRITER

    manager = FeatureManager(active_profile_id=PROFILE_WRITER)

    # Explicitly off: not part of "write, format, print, send".
    for off_feature in (
        "future.ai",
        "future.ai_menu_top_level",
        "core.glow",
        "core.remote",
        "core.github_remote",
        "core.developer_console",
        "core.emmet",
        "core.watch_folder",
        "core.analysis",
        "core.notebook",
    ):
        assert manager.state_for(off_feature) == FEATURE_STATE_OFF, off_feature

    # Core writing stays on.
    assert manager.state_for("core.editor") == FEATURE_STATE_ON
    assert manager.state_for("core.file") == FEATURE_STATE_ON
    assert manager.state_for("core.format") == FEATURE_STATE_ON

    # "Just write" must not mean "less accessible": screen-reader I/O stays.
    assert manager.state_for("core.voice_commands") == FEATURE_STATE_ON
    assert manager.state_for("core.braille") == FEATURE_STATE_ON  # ON by default, not stripped
    assert manager.state_for("core.read_aloud") != FEATURE_STATE_OFF
    assert manager.state_for("core.dictation") != FEATURE_STATE_OFF


def test_feature_manager_can_switch_profiles() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_ESSENTIAL)
    preview = manager.change_profile_preview(PROFILE_DEVELOPER_POWER_TEXT)
    assert "Developer and Power Text" in preview
    comparison = manager.compare_profiles(PROFILE_ESSENTIAL, PROFILE_DEVELOPER_POWER_TEXT)
    assert "Comparing Essential to Developer and Power Text" in comparison
    manager.switch_profile(PROFILE_DEVELOPER_POWER_TEXT)
    assert manager.active_profile_id == PROFILE_DEVELOPER_POWER_TEXT


def test_change_profile_preview_reports_same_profile() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_ESSENTIAL)

    preview = manager.change_profile_preview(PROFILE_ESSENTIAL)

    assert preview.startswith("Essential is already active.")
    assert "No switch was made because this profile is already in use." in preview


def test_feature_manager_undo_and_reset_profile() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_ESSENTIAL)
    manager.switch_profile(PROFILE_DEVELOPER_POWER_TEXT)
    assert manager.undo_last_profile_change() is True
    assert manager.active_profile_id == PROFILE_ESSENTIAL
    manager.reset_to_essential_profile()
    assert manager.active_profile_id == PROFILE_ESSENTIAL


def test_feature_manager_finds_feature_by_alias() -> None:
    feature = find_feature("regex")
    assert feature is not None
    assert feature.id == "core.search.regex"


def test_feature_registry_includes_shipped_profiles() -> None:
    assert PROFILE_ESSENTIAL in PROFILE_DEFINITIONS
    assert PROFILE_DEVELOPER_POWER_TEXT in PROFILE_DEFINITIONS
    assert PROFILE_ACCESSIBILITY_PROFESSIONAL in PROFILE_DEFINITIONS
    assert PROFILE_FULL_QUILL in PROFILE_DEFINITIONS
    assert "reader_and_student" in PROFILE_DEFINITIONS
    assert "office_and_admin" in PROFILE_DEFINITIONS
    assert "low_vision" in PROFILE_DEFINITIONS
    assert "braille_screen_reader_power_user" in PROFILE_DEFINITIONS


def test_intellisense_feature_is_in_registry() -> None:
    assert "core.intellisense" in PROFILE_DEFINITIONS[PROFILE_FULL_QUILL].states


def test_publishing_feature_is_in_registry() -> None:
    assert "future.publishing" in PROFILE_DEFINITIONS[PROFILE_FULL_QUILL].states


def test_feature_profile_import_and_export_roundtrip() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_DEVELOPER_POWER_TEXT)
    payload = manager.export_profile_data()
    payload["overrides"] = {"future.cleanup": "quiet", "core.profile": "off"}
    payload["schema_version"] = 1

    warnings = manager.import_profile_data(json.loads(json.dumps(payload)))

    assert warnings == []
    assert manager.active_profile_id == PROFILE_DEVELOPER_POWER_TEXT
    assert manager.state_for("future.cleanup") == FEATURE_STATE_QUIET
    assert manager.state_for("core.profile") == FEATURE_STATE_ON


def test_feature_profile_file_export_import_roundtrip(tmp_path: Path) -> None:
    source = FeatureManager(active_profile_id=PROFILE_DEVELOPER_POWER_TEXT)
    source.overrides = {"future.cleanup": "quiet"}
    path = tmp_path / "team.qpf"

    export_feature_profile_file(source, path)
    assert path.exists()

    target = FeatureManager()
    warnings = import_feature_profile_file(target, path)

    assert warnings == []
    assert target.active_profile_id == PROFILE_DEVELOPER_POWER_TEXT
    assert target.state_for("future.cleanup") == FEATURE_STATE_QUIET


def test_feature_profile_file_import_rejects_garbage(tmp_path: Path) -> None:
    path = tmp_path / "broken.qpf"
    path.write_text("not a profile", encoding="utf-8")

    target = FeatureManager()
    with pytest.raises(ValueError):
        import_feature_profile_file(target, path)


def test_feature_dependency_enforcement_turns_on_required_features() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_ESSENTIAL)
    manager.overrides["core.search"] = FEATURE_STATE_OFF
    affected = manager.enable_feature("core.search.regex")

    assert "core.search" in affected
    assert manager.state_for("core.search") == FEATURE_STATE_ON
    assert manager.state_for("core.search.regex") == FEATURE_STATE_ON


def test_feature_dependency_enforcement_turns_off_dependents() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_FULL_QUILL)
    affected = manager.disable_feature("core.search")

    assert "core.search" in affected
    assert "core.search.regex" in affected
    assert manager.state_for("core.search") == FEATURE_STATE_OFF
    assert manager.state_for("core.search.regex") == FEATURE_STATE_OFF


def test_set_feature_enabled_toggles_and_announces() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_ESSENTIAL)
    manager.overrides["core.search"] = FEATURE_STATE_OFF

    affected = manager.set_feature_enabled("core.search.regex", True)
    assert "core.search" in affected
    assert manager.is_enabled("core.search.regex") is True
    announcement = manager.describe_feature_toggle("core.search.regex", True, affected)
    assert announcement.startswith("Turned on")
    assert "it needs" in announcement

    affected_off = manager.set_feature_enabled("core.search", False)
    assert "core.search" in affected_off
    assert "core.search.regex" in affected_off
    assert manager.is_enabled("core.search.regex") is False
    off_announcement = manager.describe_feature_toggle("core.search", False, affected_off)
    assert off_announcement.startswith("Turned off")
    assert "that need it" in off_announcement


def test_describe_feature_toggle_handles_no_change_and_solo() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_FULL_QUILL)

    # Enabling an already-on feature reports no change.
    affected = manager.set_feature_enabled("core.search", True)
    assert affected == []
    assert manager.describe_feature_toggle("core.search", True, affected).endswith("is already on.")

    # A toggle that affects only the feature itself omits the dependency clause.
    solo = manager.describe_feature_toggle("core.search.regex", True, ["core.search.regex"])
    assert "(" not in solo
    assert solo.startswith("Turned on")


def test_feature_health_report_includes_coverage() -> None:
    registry = CommandRegistry()
    registry.register("edit.find", "Find", lambda: None)
    registry.register("tools.read_aloud_start_pause", "Read Aloud", lambda: None)

    report = FeatureManager(active_profile_id=PROFILE_ACCESSIBILITY_PROFESSIONAL).health_report(
        registry.list()
    )

    assert "Feature profile health check" in report
    assert "No coverage problems found." in report or "Commands without a feature mapping" in report


def test_feature_with_off_dependency_stays_off_even_if_self_on() -> None:
    # FLAG-1: a dependent feature is effectively off when any feature in its
    # dependency chain is off, regardless of how the dependency was disabled.
    manager = FeatureManager(active_profile_id=PROFILE_FULL_QUILL)
    # core.bw_providers -> core.bw_transcription -> core.dictation -> core.editor
    manager.overrides["core.dictation"] = FEATURE_STATE_OFF

    assert manager.state_for("core.bw_providers") == FEATURE_STATE_ON
    assert manager.is_enabled("core.bw_providers") is False
    assert manager.is_visible("core.bw_providers") is False
    assert manager.is_enabled("core.bw_transcription") is False


def test_visible_commands_hide_features_with_unmet_dependencies() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_FULL_QUILL)
    registry = CommandRegistry()
    registry.register("tools.dictation_start", "Dictate", lambda: None, feature_id="core.dictation")
    registry.register(
        "whisperer.model_manager", "Models", lambda: None, feature_id="core.bw_transcription"
    )
    registry.register("edit.find", "Find", lambda: None, feature_id="core.search")

    manager.overrides["core.dictation"] = FEATURE_STATE_OFF
    visible_ids = {command.id for command in manager.visible_commands(registry.list())}

    assert "edit.find" in visible_ids
    assert "tools.dictation_start" not in visible_ids
    assert "whisperer.model_manager" not in visible_ids


def test_enabled_feature_with_all_dependencies_on_is_visible() -> None:
    manager = FeatureManager(active_profile_id=PROFILE_FULL_QUILL)

    assert manager.is_enabled("core.navigate") is True
    assert manager.is_visible("core.navigate") is True


def test_voice_commands_is_unlocked_and_visible() -> None:
    # Hey QUILL Phase 1: core.voice_commands is surfaced (push-to-talk over the
    # offline speech stack). The runtime double-gate lives in
    # voice_commands_available (off by default via settings, off in Safe Mode).
    manager = FeatureManager(active_profile_id=PROFILE_FULL_QUILL)

    assert manager.is_enabled("core.voice_commands") is True
    assert manager.is_visible("core.voice_commands") is True


def test_bits_whisperer_master_flag_is_locked_off() -> None:
    # BITS Whisperer is deferred to QUILL 2.0; the master `core.bw_whisperer`
    # flag is locked off for 1.0, which hard-disables it and every bw_* feature
    # that depends on it, regardless of the active profile or any override.
    manager = FeatureManager(active_profile_id=PROFILE_FULL_QUILL)

    assert manager.state_for("core.bw_whisperer") == FEATURE_STATE_OFF
    assert manager.is_enabled("core.bw_whisperer") is False
    assert manager.is_enabled("core.bw_transcription") is False
    assert manager.is_enabled("core.bw_providers") is False
    assert manager.is_visible("core.bw_transcription") is False

    # A locked-off flag cannot be turned on by a user override either.
    manager.overrides["core.bw_whisperer"] = FEATURE_STATE_ON
    assert manager.is_enabled("core.bw_whisperer") is False


def test_every_feature_id_referenced_in_main_frame_is_defined() -> None:
    # FLAG-2: every feature_id wired to a command surface must be a registered
    # FeatureDefinition, so no command is left orphaned to an unknown feature.
    import re
    from pathlib import Path

    from quill.core.features import FEATURE_DEFINITIONS

    source = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")
    referenced = set(re.findall(r'feature_id="([^"]+)"', source))

    assert referenced, "expected main_frame to wire feature ids to commands"
    missing = sorted(fid for fid in referenced if fid not in FEATURE_DEFINITIONS)
    assert missing == [], f"command feature ids missing from FEATURE_DEFINITIONS: {missing}"
