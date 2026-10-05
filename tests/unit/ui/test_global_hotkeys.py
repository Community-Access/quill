"""Global hotkeys: the allowlist boundary and the browser's note filter --
pure logic, no wx construction."""

from __future__ import annotations

import ast
from pathlib import Path

from quill.core.sticky_notes import StickyNote
from quill.ui.main_frame_hotkeys import GLOBAL_HOTKEY_SAFE_COMMANDS, GlobalHotkeysMixin
from quill.ui.sticky_notes_browser import filter_notes


def _note(body: str, updated: str) -> StickyNote:
    base = StickyNote.create(body)
    return StickyNote(
        id=base.id, title=base.title, body=base.body, created_at=updated, updated_at=updated
    )


def test_filter_notes_empty_query_returns_all_newest_first() -> None:
    notes = [_note("older note", "2026-01-01T00:00:00"), _note("newer note", "2026-06-01T00:00:00")]
    result = filter_notes(notes, "")
    assert [n.body for n in result] == ["newer note", "older note"]


def test_filter_notes_matches_title_and_body_case_insensitive() -> None:
    notes = [
        _note("Groceries\nmilk and eggs", "2026-01-02T00:00:00"),
        _note("Meeting\ncall with MILK vendor", "2026-01-03T00:00:00"),
        _note("Unrelated\nnothing here", "2026-01-04T00:00:00"),
    ]
    result = filter_notes(notes, "milk")
    assert len(result) == 2
    assert all("milk" in (n.title + n.body).casefold() for n in result)


def test_filter_notes_no_match() -> None:
    assert filter_notes([_note("a", "2026-01-01T00:00:00")], "zzz") == []


class _Host(GlobalHotkeysMixin):
    """Just enough host protocol to exercise _global_hotkey_bindings."""

    def __init__(self, configured: dict[str, str], legacy: str | None = None) -> None:
        self.settings = type("S", (), {"global_hotkeys": configured})()
        self._legacy = legacy

    def _binding_for(self, command_id: str) -> str | None:
        return self._legacy if command_id == "tools.sticky_note_capture" else None

    def _parse_keybinding(self, binding: str | None):
        return (1, 65) if binding else None


def test_allowlist_is_the_boundary() -> None:
    host = _Host({
        "radio.play_pause": "Ctrl+Alt+P",
        "file.save": "Ctrl+Alt+S",  # NOT on the allowlist: must be dropped
        "edit.select_all": "Ctrl+Alt+A",  # ditto
    })
    bindings = host._global_hotkey_bindings()
    assert bindings["radio.play_pause"] == "Ctrl+Alt+P"
    assert "file.save" not in bindings
    assert "edit.select_all" not in bindings


def test_blank_bindings_are_dropped() -> None:
    host = _Host({"radio.play_pause": "   "})
    assert "radio.play_pause" not in host._global_hotkey_bindings()


def test_legacy_sticky_binding_survives_unless_overridden() -> None:
    host = _Host({}, legacy="Ctrl+Alt+N")
    assert host._global_hotkey_bindings()["tools.sticky_note_capture"] == "Ctrl+Alt+N"
    host = _Host({"tools.sticky_note_capture": "Ctrl+Alt+M"}, legacy="Ctrl+Alt+N")
    assert host._global_hotkey_bindings()["tools.sticky_note_capture"] == "Ctrl+Alt+M"


class _GatedHost(_Host):
    """A host whose Podcasts feature is off (the public-build shape)."""

    def __init__(self, configured: dict[str, str]) -> None:
        super().__init__(configured)
        from quill.core.commands import CommandRegistry

        self.commands = CommandRegistry()
        self.commands.register(
            "podcasts.play_pause", "Podcasts: Play/Pause", lambda: None, feature_id="core.podcasts"
        )
        self.commands.register(
            "podcasts.stop", "Podcasts: Stop", lambda: None, feature_id="core.podcasts"
        )
        self.commands.register(
            "radio.play_pause", "Radio: Play/Pause", lambda: None, feature_id="core.radio"
        )

    def _feature_enabled(self, feature_id: str) -> bool:
        return feature_id != "core.podcasts"


def test_a_disabled_features_command_is_never_registered_as_a_global_hotkey() -> None:
    # A feature this build does not offer (Podcasts is not released for 1.0.0)
    # must not get a system-wide key, whatever the saved settings say.
    host = _GatedHost({"podcasts.play_pause": "Ctrl+Alt+8", "radio.play_pause": "Ctrl+Alt+P"})
    bindings = host._global_hotkey_bindings()
    assert "podcasts.play_pause" not in bindings
    assert bindings["radio.play_pause"] == "Ctrl+Alt+P"


def test_a_disabled_features_command_is_not_listed_in_the_manager() -> None:
    host = _GatedHost({})
    listed = {command_id for command_id, _label, _needs in host._global_hotkey_safe_commands()}
    assert "podcasts.play_pause" not in listed
    assert "podcasts.stop" not in listed
    assert "radio.play_pause" in listed


def test_every_allowlisted_command_is_low_risk_by_construction() -> None:
    """Meta-guard: the allowlist stays media/notes/compose/window-visibility
    only. Anything document-editing or destructive being added here should fail
    review AND this test."""
    allowed_prefixes = (
        "radio.",
        "podcasts.",
        "notes.",
        "tools.sticky",
        "tools.post_to_mastodon",
        "view.toggle_window_to_tray",  # shows/hides the window; touches no document
    )
    for command_id, _label, _needs in GLOBAL_HOTKEY_SAFE_COMMANDS:
        assert command_id.startswith(allowed_prefixes), command_id


def test_no_editor_chord_is_the_global_show_hide_key() -> None:
    # A registered system-wide hotkey reaches its owner before any window sees
    # the key, so an editor command bound to the same chord can never fire --
    # in QUILL, and in QUILL Lite whenever QUILL is running. Unquote Lines sat
    # on Ctrl+Alt+Shift+Q in both editors until 2026-10-03.
    from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS
    from quill.core.lite.keymap import chord_identity
    from quill.core.lite.keymap import default_aliases as lite_aliases
    from quill.ui.main_frame_hotkeys import DEFAULT_SHOW_HIDE_HOTKEY

    hotkey = chord_identity(DEFAULT_SHOW_HIDE_HOTKEY)
    claimants = [
        f"QUILL {command_id}"
        for table in (DEFAULT_KEYMAP, DEFAULT_ALIASES)
        for command_id, chord in table.items()
        if chord and chord_identity(chord) == hotkey
    ]
    claimants += [
        f"QUILL Lite {row[3]}" for row in COMMANDS if row[2] and chord_identity(row[2]) == hotkey
    ]
    claimants += [
        f"QUILL Lite alias {handler}"
        for handler, chord in lite_aliases().items()
        if chord and chord_identity(chord) == hotkey
    ]
    assert claimants == []


# -- every app's keys against every family app's show/hide key -------------- #
#
# The test above covers the editors and QUILL's key. The family runs side by
# side, though, and every app registers a show/hide key of its own, so a menu
# key in one app equal to another app's show/hide key never fires while that
# other app runs. QUILL Cast's Mark as Played and Next sat on QUILL's
# Ctrl+Alt+Shift+Q until 2026-10-04 for exactly that reason.

_APPS_DIR = Path(__file__).resolve().parents[3] / "quill" / "apps"

#: Collisions with another app's show/hide key that were already there when this
#: gate arrived (2026-10-04), as ``"<owner>: <claimant>"``. Each one is real: the
#: key goes to the owner while the owner runs. Shrink this, never grow it -- a
#: new key takes a chord nobody in the family registers system-wide. QUILL's and
#: Cast's show/hide keys may never appear here.
_GRANDFATHERED: frozenset[str] = frozenset({
    "converter: QUILL Lite cmd_clear_collected",
    "converter: podcasts_menu.py Choose Columns...",
    "converter: radio_settings_menu.py Choose Columns...",
    "inkwell: QUILL Lite cmd_toggle_tab_mode",
    "inkwell: QUILL format.toggle_tab_insert_mode",
    "inkwell: podcasts_menu.py Podcast Index Credentials...",
    "inkwell: radio radio.recording_settings",
    "player: QUILL Lite cmd_print_preview",
    "player: cast app.recent_problems",
    "player: radio app.recent_problems",
    "player: weather weather.monitor_pause",
    "radio: QUILL Lite cmd_keyboard_manager",
    "radio: QUILL tools.keymap_editor",
    "radio: cast app.restore",
    "radio: studio.py Resume Last Book on Launch",
    "weather: QUILL Lite cmd_toggle_overwrite",
    "weather: QUILL view.toggle_overwrite_mode",
    "weather: podcasts_menu.py Keyboard Shortcuts...",
    "weather: radio_menu_bar.py Restore from Backup...",
})


def _family_show_hide_keys() -> dict[str, str]:
    """``{chord identity: owner}`` for every family app's system-wide show/hide key.

    Read from the source, not listed by hand: each app passes its chord to
    ``_register_tray_hotkey`` as a literal or a module constant, so a new app
    is covered the day it registers one. Inkwell's comes from a setting, whose
    default is read here directly.
    """
    from quill.core.expansion.settings import InkwellSettings
    from quill.core.lite.keymap import chord_identity
    from quill.ui.main_frame_hotkeys import DEFAULT_SHOW_HIDE_HOTKEY

    keys = {
        chord_identity(DEFAULT_SHOW_HIDE_HOTKEY): "QUILL",
        chord_identity(InkwellSettings().tray_hotkey): "inkwell",
    }
    for path in sorted(_APPS_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        constants = {
            target.id: node.value.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_register_tray_hotkey"
                and node.args
            ):
                continue
            arg = node.args[0]
            chord = arg.value if isinstance(arg, ast.Constant) else None
            if isinstance(arg, ast.Name):
                chord = constants.get(arg.id)
            if isinstance(chord, str):
                keys[chord_identity(chord)] = path.stem
    return keys


def _every_default_chord() -> list[tuple[str, str]]:
    """``(where, chord)`` for every default key any app in the family ships."""
    from quill.core.app_keymaps import APP_KEYMAPS
    from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS
    from quill.core.lite.keymap import default_aliases as lite_aliases

    found = [(f"QUILL {cid}", chord) for cid, chord in DEFAULT_KEYMAP.items()]
    found += [(f"QUILL alias {cid}", chord) for cid, chord in DEFAULT_ALIASES.items()]
    found += [(f"QUILL Lite {row[3]}", row[2]) for row in COMMANDS]
    found += [(f"QUILL Lite alias {name}", chord) for name, chord in lite_aliases().items()]
    for app_id, table in APP_KEYMAPS.items():
        found += [(f"{app_id} {cid}", chord) for cid, chord in table.items()]
    # Menu labels with the key written in ("Name\tKey"), in every app module:
    # Cast and Radio still write most of theirs that way.
    for path in sorted(_APPS_DIR.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and "\t" in node.value
            ):
                label, _tab, chord = node.value.partition("\t")
                where = f"{path.relative_to(_APPS_DIR).as_posix()} {label.replace('&', '')}"
                found.append((where, chord.strip()))
    return [(where, chord) for where, chord in found if chord]


def _show_hide_collisions() -> set[str]:
    from quill.core.lite.keymap import chord_identity

    keys = _family_show_hide_keys()
    return {
        f"{keys[chord_identity(chord)]}: {where}"
        for where, chord in _every_default_chord()
        if chord_identity(chord) in keys
    }


def test_the_show_hide_scan_finds_every_app_that_registers_one() -> None:
    from quill.core.lite.keymap import chord_identity

    owners = set(_family_show_hide_keys().values())
    assert {"QUILL", "radio", "weather", "converter", "player", "inkwell"} <= owners
    assert chord_identity("Ctrl+Alt+Shift+F12") in _family_show_hide_keys()


def test_no_app_key_is_a_family_show_hide_key() -> None:
    new = sorted(_show_hide_collisions() - _GRANDFATHERED)
    assert new == [], "keys another app takes system-wide: " + "; ".join(new)


def test_the_grandfathered_collisions_only_shrink() -> None:
    fixed = sorted(_GRANDFATHERED - _show_hide_collisions())
    assert fixed == [], "fixed -- remove from _GRANDFATHERED: " + "; ".join(fixed)
    assert not [
        entry for entry in _GRANDFATHERED if entry.startswith(("QUILL:", "podcasts_routes:"))
    ]
