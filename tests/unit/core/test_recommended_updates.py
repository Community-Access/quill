from __future__ import annotations

from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.recommended_updates import (
    RECOMMENDED_KEYMAP_UPDATES,
    apply_recommended_keymap_updates,
)

_FIND = next(u for u in RECOMMENDED_KEYMAP_UPDATES if u.command_id == "edit.find")


def test_apply_forces_the_binding_and_reports_the_id_when_enabled() -> None:
    keymap = dict(DEFAULT_KEYMAP)
    keymap["edit.find"] = "Ctrl+Shift+Grave, Z"  # a stale override to overwrite
    updated, newly = apply_recommended_keymap_updates(keymap, [], enabled=True)
    assert updated["edit.find"] == _FIND.binding == "Ctrl+F"
    assert _FIND.id in newly
    # Input is not mutated.
    assert keymap["edit.find"] == "Ctrl+Shift+Grave, Z"


def test_already_applied_update_does_not_fire_again() -> None:
    keymap = dict(DEFAULT_KEYMAP)
    keymap["edit.find"] = "Ctrl+Alt+F"  # user rebound it after the update applied
    updated, newly = apply_recommended_keymap_updates(keymap, [_FIND.id], enabled=True)
    assert newly == set()
    assert updated["edit.find"] == "Ctrl+Alt+F"  # their choice is respected


def test_disabled_changes_nothing_and_marks_nothing() -> None:
    keymap = dict(DEFAULT_KEYMAP)
    keymap["edit.find"] = "Ctrl+Shift+Grave, Z"
    updated, newly = apply_recommended_keymap_updates(keymap, [], enabled=False)
    assert newly == set()
    assert updated["edit.find"] == "Ctrl+Shift+Grave, Z"


def test_update_for_unknown_command_is_skipped() -> None:
    # A stale registry entry referencing a dropped command must not inject it.
    keymap = dict(DEFAULT_KEYMAP)
    _, newly = apply_recommended_keymap_updates(
        keymap, [], enabled=True, valid_command_ids=frozenset()
    )
    assert newly == set()


# ---------------------------------------------------------------------------
# Recommended settings updates (the settings analog)
# ---------------------------------------------------------------------------

from quill.core import recommended_updates as ru  # noqa: E402
from quill.core.recommended_updates import (  # noqa: E402
    RecommendedSettingsUpdate,
    apply_recommended_settings_updates,
)


def _set(applied, *, enabled, registry):
    """Run apply_recommended_settings_updates against a synthetic registry."""
    captured: dict[str, object] = {}
    import unittest.mock as mock

    with mock.patch.object(ru, "RECOMMENDED_SETTINGS_UPDATES", registry):
        newly = apply_recommended_settings_updates(
            lambda field, value: captured.__setitem__(field, value),
            applied,
            enabled=enabled,
            valid_fields=frozenset({"theme", "sound_enabled"}),
        )
    return captured, newly


_REG = (RecommendedSettingsUpdate(id="theme-dark-x", field="theme", value="dark", reason="r"),)


def test_settings_update_fires_once_when_enabled() -> None:
    captured, newly = _set([], enabled=True, registry=_REG)
    assert captured == {"theme": "dark"}
    assert newly == {"theme-dark-x"}


def test_settings_update_skipped_when_already_applied() -> None:
    captured, newly = _set(["theme-dark-x"], enabled=True, registry=_REG)
    assert captured == {}
    assert newly == set()


def test_settings_update_noop_when_disabled() -> None:
    captured, newly = _set([], enabled=False, registry=_REG)
    assert captured == {} and newly == set()


def test_settings_update_skips_unknown_field() -> None:
    reg = (RecommendedSettingsUpdate(id="x", field="removed_field", value=1, reason="r"),)
    captured, newly = _set([], enabled=True, registry=reg)
    assert captured == {} and newly == set()
