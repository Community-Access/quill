from __future__ import annotations

from dataclasses import fields

from quill.core.settings import Settings
from quill.core.settings_registry import (
    SETTING_GROUPS,
    SETTING_SPECS,
    default_value,
    export_settings,
    find_spec,
    groups,
    import_settings,
    reset_all,
    reset_setting,
    search_specs,
    set_value,
    specs_for_group,
)


def test_every_spec_maps_to_a_real_settings_field() -> None:
    field_names = {field.name for field in fields(Settings)}
    for spec in SETTING_SPECS:
        assert spec.key in field_names, f"{spec.key} is not a Settings field"


def test_every_spec_belongs_to_a_declared_group() -> None:
    group_ids = {group.id for group in SETTING_GROUPS}
    for spec in SETTING_SPECS:
        assert spec.group in group_ids, f"{spec.key} -> unknown group {spec.group}"


def test_spec_keys_are_unique() -> None:
    keys = [spec.key for spec in SETTING_SPECS]
    assert len(keys) == len(set(keys))


def test_previously_unsurfaced_fields_are_registered() -> None:
    keys = {spec.key for spec in SETTING_SPECS}
    for key in ("auto_side_preview", "csv_open_mode", "word_open_mode"):
        assert key in keys, f"{key} should be surfaced in the Settings registry"


def test_integration_group_and_shell_verb_specs_registered() -> None:
    group_ids = {group.id for group in SETTING_GROUPS}
    assert "integration" in group_ids
    keys = {spec.key for spec in SETTING_SPECS}
    for key in (
        "shell_integration_enabled",
        "shell_file_types",
        "shell_verb_open",
        "shell_verb_ocr",
        "shell_verb_ocr_structured",
        "shell_verb_read",
    ):
        assert key in keys, f"{key} should be surfaced in the Settings registry"


def test_set2_set3_set4_fields_are_registered() -> None:
    keys = {spec.key for spec in SETTING_SPECS}
    for key in (
        # SET-2 timing and pacing
        "autosave_interval_seconds",
        "quick_nav_debounce_ms",
        "quick_nav_min_chars",
        "announcement_throttle_ms",
        "read_aloud_sentence_pause_ms",
        # SET-3 verbosity and announcements
        "announcement_verbosity",
        "announce_wrap",
        "announce_counts",
        "announce_mode_changes",
        "announce_spelling",
        "announce_punctuation_level",
        # SET-4 behavior toggles
        "browse_mode_sticky",
        "confirm_destructive_actions",
        "default_export_preset",
        "default_new_document_format",
        "autoformat_smart_quotes",
        "autoformat_dashes",
        "quick_nav_include_headings",
        "quick_nav_include_links",
        "quick_nav_include_lists",
    ):
        assert key in keys, f"{key} should be surfaced in the Settings registry"


def test_feat19_external_change_fields_are_registered() -> None:
    keys = {spec.key for spec in SETTING_SPECS}
    for key in (
        "external_change_watch_enabled",
        "external_change_auto_reload_when_clean",
        "external_change_prompt_on_conflict",
        "external_change_debounce_ms",
    ):
        assert key in keys, f"{key} should be surfaced in the Settings registry"


def test_specs_for_group_filters() -> None:
    for group in groups():
        for spec in specs_for_group(group.id):
            assert spec.group == group.id


def test_choice_values_are_accepted_by_settings() -> None:
    base = Settings()
    for spec in SETTING_SPECS:
        if spec.kind != "choice":
            continue
        for stored_value, _label in spec.choices:
            updated = set_value(base, spec.key, stored_value)
            assert getattr(updated, spec.key) == stored_value


def test_search_matches_label_keyword_and_description() -> None:
    assert any(spec.key == "theme" for spec in search_specs("dark mode"))
    assert any(spec.key == "soft_wrap" for spec in search_specs("wrap"))
    assert search_specs("") == list(SETTING_SPECS)
    assert search_specs("zzzz-no-match") == []


def test_reset_setting_restores_default() -> None:
    spec = find_spec("recent_files_limit")
    assert spec is not None
    changed = set_value(Settings(), "recent_files_limit", 3)
    assert changed.recent_files_limit == 3
    restored = reset_setting(changed, "recent_files_limit")
    assert restored.recent_files_limit == default_value("recent_files_limit")


def test_reset_all_returns_defaults() -> None:
    assert reset_all() == Settings()


def test_set_value_clamps_out_of_range() -> None:
    clamped = set_value(Settings(), "recent_files_limit", 9999)
    assert clamped.recent_files_limit <= 50


def test_export_import_round_trip() -> None:
    original = set_value(Settings(), "theme", "dark")
    original = set_value(original, "recent_files_limit", 12)
    exported = export_settings(original)
    assert exported["schema_version"] == 1
    restored = import_settings(exported)
    assert restored == original


def test_import_accepts_bare_mapping_and_ignores_unknown() -> None:
    restored = import_settings({"theme": "light", "not_a_real_key": 1})
    assert restored.theme == "light"


def test_import_garbage_returns_defaults() -> None:
    assert import_settings(None) == Settings()
    assert import_settings([1, 2, 3]) == Settings()


def test_browse_mode_followon_timeout_default_is_unlimited() -> None:
    # #265 follow-up: the accesswatch comment asked for browse mode to
    # just wait for keys and not time out. The new default is
    # 'unlimited' so QUILL key + N never expires by default.
    assert Settings().browse_mode_followon_timeout == "unlimited"


def test_import_unknown_browse_mode_followon_token_falls_back_to_unlimited() -> None:
    # #265 follow-up: a stale settings.json with an unknown token
    # should fall back to 'unlimited' rather than crash.
    restored = import_settings({"browse_mode_followon_timeout": "garbage"})
    assert restored.browse_mode_followon_timeout == "unlimited"


def test_import_browse_mode_followon_custom_ms_clamps_to_window() -> None:
    # #265 follow-up: custom-ms clamps to [0, 60000].
    too_low = import_settings({"browse_mode_followon_custom_ms": -50})
    assert too_low.browse_mode_followon_custom_ms == 0
    too_high = import_settings({"browse_mode_followon_custom_ms": 99999})
    assert too_high.browse_mode_followon_custom_ms == 60000
    middle = import_settings({"browse_mode_followon_custom_ms": 2500})
    assert middle.browse_mode_followon_custom_ms == 2500


def test_export_import_browse_mode_followon_round_trip() -> None:
    # #265 follow-up: the two new fields round-trip through the loader.
    original = set_value(Settings(), "browse_mode_followon_timeout", "custom")
    original = set_value(original, "browse_mode_followon_custom_ms", 2500)
    exported = export_settings(original)
    restored = import_settings(exported)
    assert restored.browse_mode_followon_timeout == "custom"
    assert restored.browse_mode_followon_custom_ms == 2500
