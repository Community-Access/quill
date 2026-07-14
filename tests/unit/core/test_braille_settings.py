"""Tests for BR-008: Braille Mode settings fields."""

from __future__ import annotations

from quill.core.settings import Settings
from quill.core.settings_migration import from_versioned, to_versioned
from quill.core.settings_registry import SETTING_SPECS, find_spec


def _braille_specs() -> list:
    return [s for s in SETTING_SPECS if s.key.startswith("braille_")]


def test_all_braille_settings_have_a_registry_spec() -> None:
    """Every ``braille_*`` field on :class:`Settings` has a spec."""
    spec_keys = {s.key for s in _braille_specs()}
    field_names = {name for name in Settings.__dataclass_fields__ if name.startswith("braille_")}
    missing_spec = field_names - spec_keys
    missing_field = spec_keys - field_names
    assert not missing_spec, f"Settings has braille_* field with no spec: {missing_spec}"
    assert not missing_field, f"Spec registered for missing Settings field: {missing_field}"


def test_braille_settings_have_expected_defaults() -> None:
    defaults = {
        "braille_cells_per_line": 40,
        "braille_lines_per_page": 25,
        "braille_use_form_feeds": True,
        "braille_calculate_pages": True,
        "braille_save_sidecar": True,
        "braille_status_verbosity": "normal",
        "braille_auto_announce_page_changes": False,
        "braille_auto_announce_print_page_changes": False,
        "braille_auto_announce_line_overflow": False,
        "braille_include_proofing_status": True,
        "braille_include_running_head": False,
        "braille_include_continuation": True,
    }
    settings = Settings()
    for key, value in defaults.items():
        assert getattr(settings, key) == value, (
            f"{key} default drifted to {getattr(settings, key)!r}"
        )


def test_braille_cells_per_line_is_clamped_into_range() -> None:
    settings = Settings.from_dict({"braille_cells_per_line": 10})
    assert settings.braille_cells_per_line == 28
    settings = Settings.from_dict({"braille_cells_per_line": 99})
    assert settings.braille_cells_per_line == 42


def test_braille_lines_per_page_is_clamped_into_range() -> None:
    settings = Settings.from_dict({"braille_lines_per_page": 5})
    assert settings.braille_lines_per_page == 20
    settings = Settings.from_dict({"braille_lines_per_page": 999})
    assert settings.braille_lines_per_page == 30


def test_braille_status_verbosity_rejects_unknown_values() -> None:
    settings = Settings.from_dict({"braille_status_verbosity": "loud"})
    assert settings.braille_status_verbosity == "normal"


def test_braille_settings_round_trip_through_migration() -> None:
    """A profile with non-default values survives a save/load cycle."""
    original = Settings.from_dict({
        "braille_cells_per_line": 39,
        "braille_lines_per_page": 28,
        "braille_use_form_feeds": False,
        "braille_calculate_pages": True,
        "braille_save_sidecar": False,
        "braille_status_verbosity": "detailed",
        "braille_auto_announce_page_changes": True,
        "braille_auto_announce_print_page_changes": True,
        "braille_auto_announce_line_overflow": True,
        "braille_include_proofing_status": False,
        "braille_include_running_head": True,
        "braille_include_continuation": False,
    })
    document = to_versioned(original)
    restored = from_versioned(document)
    for key in [
        "braille_cells_per_line",
        "braille_lines_per_page",
        "braille_use_form_feeds",
        "braille_calculate_pages",
        "braille_save_sidecar",
        "braille_status_verbosity",
        "braille_auto_announce_page_changes",
        "braille_auto_announce_print_page_changes",
        "braille_auto_announce_line_overflow",
        "braille_include_proofing_status",
        "braille_include_running_head",
        "braille_include_continuation",
    ]:
        assert getattr(restored, key) == getattr(original, key), key


def test_braille_settings_appear_in_braille_group() -> None:
    group_ids = {
        find_spec(key).group
        for key in (
            "braille_cells_per_line",
            "braille_lines_per_page",
            "braille_use_form_feeds",
            "braille_calculate_pages",
            "braille_save_sidecar",
            "braille_status_verbosity",
            "braille_auto_announce_page_changes",
            "braille_auto_announce_print_page_changes",
            "braille_auto_announce_line_overflow",
            "braille_include_proofing_status",
            "braille_include_running_head",
            "braille_include_continuation",
        )
    }
    assert group_ids == {"braille"}


def test_braille_int_specs_carry_min_and_max() -> None:
    cells_spec = find_spec("braille_cells_per_line")
    lines_spec = find_spec("braille_lines_per_page")
    assert cells_spec is not None and cells_spec.minimum == 28 and cells_spec.maximum == 42
    assert lines_spec is not None and lines_spec.minimum == 20 and lines_spec.maximum == 30


def test_braille_choice_spec_has_three_verbosities() -> None:
    spec = find_spec("braille_status_verbosity")
    assert spec is not None
    assert spec.kind == "choice"
    values = tuple(value for value, _label in spec.choices)
    assert values == ("brief", "normal", "detailed")
