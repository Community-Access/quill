"""The braille editor control-type setting (rich2 / rich / plain)."""

from __future__ import annotations

from quill.core.settings import Settings


def test_editor_control_kind_round_trips() -> None:
    loaded = Settings.from_dict({"editor_control_kind": "plain"})
    assert loaded.editor_control_kind == "plain"
    assert Settings().editor_control_kind == "rich2"  # default


def test_editor_control_kind_validates_and_is_back_compatible() -> None:
    # Unknown values fall back to the default.
    assert Settings.from_dict({"editor_control_kind": "bogus"}).editor_control_kind == "rich2"
    # The retired editor_use_legacy_richedit bool maps to "rich".
    assert Settings.from_dict({"editor_use_legacy_richedit": True}).editor_control_kind == "rich"
    assert Settings.from_dict({"editor_use_legacy_richedit": False}).editor_control_kind == "rich2"
