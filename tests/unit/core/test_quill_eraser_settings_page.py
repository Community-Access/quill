"""Quill Eraser's four settings are on a Settings page, where Find a setting reaches them.

The user guide sent people to Settings for them, and none of the four was on
any page: the only way to change one was to edit settings.json by hand.
"""

from __future__ import annotations

from quill.core import settings_registry as registry

_ERASER = (
    "hygiene_min_confidence",
    "hygiene_allow_double_space_after_period",
    "hygiene_max_blank_lines",
    "hygiene_rules_disabled",
)


def test_every_quill_eraser_setting_has_a_labelled_spec_on_the_spelling_page() -> None:
    specs = {spec.key: spec for spec in registry.specs_for_group("spelling")}
    for key in _ERASER:
        assert key in specs, key
        assert specs[key].label.startswith("Quill Eraser: ")
        assert specs[key].description


def test_the_choice_values_are_the_ones_settings_accepts() -> None:
    spec = next(s for s in registry.specs_for_group("spelling") if s.key == _ERASER[0])
    assert {value for value, _label in spec.choices} == {"high", "medium", "low"}
