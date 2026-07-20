"""Tests for accessibility settings model and persistence (PRD 29)."""

from quill.apps.beacon import a11y
from quill.apps.beacon.a11y import A11ySettings


def test_defaults():
    s = A11ySettings()
    assert s.verbosity == "normal"
    assert s.high_contrast is False
    assert s.text_scale == 1.0
    assert s.reduced_motion is False


def test_text_scale_steps():
    s = A11ySettings(scale_index=0)
    assert s.text_scale == a11y.SCALE_STEPS[0]
    s = A11ySettings(scale_index=len(a11y.SCALE_STEPS) - 1)
    assert s.text_scale == a11y.SCALE_STEPS[-1]


def test_persistence_roundtrip(tmp_path):
    s = A11ySettings(verbosity="verbose", high_contrast=True, scale_index=4, reduced_motion=True)
    a11y.save(tmp_path, s)
    loaded = a11y.load(tmp_path)
    assert loaded.verbosity == "verbose"
    assert loaded.high_contrast is True
    assert loaded.scale_index == 4
    assert loaded.reduced_motion is True
    assert loaded.text_scale == a11y.SCALE_STEPS[4]


def test_load_missing_file_returns_defaults(tmp_path):
    assert a11y.load(tmp_path) == A11ySettings()


def test_from_dict_sanitizes_bad_values():
    s = A11ySettings.from_dict({"verbosity": "loud", "scale_index": 99, "high_contrast": "yes"})
    assert s.verbosity == "normal"
    assert s.scale_index == a11y.DEFAULT_SCALE_INDEX
    assert s.high_contrast is True  # truthy string -> True


def test_from_dict_handles_garbage_scale():
    s = A11ySettings.from_dict({"scale_index": "big"})
    assert s.scale_index == a11y.DEFAULT_SCALE_INDEX


def test_corrupt_file_falls_back(tmp_path):
    (tmp_path / a11y.SETTINGS_NAME).write_text("not json", encoding="utf-8")
    assert a11y.load(tmp_path) == A11ySettings()
