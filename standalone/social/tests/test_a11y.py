"""Tests for accessibility settings (PRD 28)."""

from quill_social import a11y
from quill_social.a11y import A11ySettings


def test_defaults():
    s = A11ySettings()
    assert s.verbosity == "normal"
    assert s.high_contrast is False
    assert s.text_scale == 1.0
    assert s.speak_network_prefix is True
    assert s.speak_engagement is False


def test_text_scale_steps():
    assert A11ySettings(scale_index=0).text_scale == a11y.SCALE_STEPS[0]
    assert A11ySettings(scale_index=len(a11y.SCALE_STEPS) - 1).text_scale \
        == a11y.SCALE_STEPS[-1]


def test_persistence_roundtrip(tmp_path):
    s = A11ySettings(verbosity="verbose", high_contrast=True, scale_index=4,
                     speak_engagement=True)
    a11y.save(tmp_path, s)
    loaded = a11y.load(tmp_path)
    assert loaded.verbosity == "verbose"
    assert loaded.high_contrast is True
    assert loaded.scale_index == 4
    assert loaded.speak_engagement is True


def test_from_dict_sanitizes():
    s = A11ySettings.from_dict({"verbosity": "loud", "scale_index": 99})
    assert s.verbosity == "normal"
    assert s.scale_index == a11y.DEFAULT_SCALE_INDEX


def test_corrupt_file_falls_back(tmp_path):
    (tmp_path / a11y.SETTINGS_NAME).write_text("not json", encoding="utf-8")
    assert a11y.load(tmp_path) == A11ySettings()
