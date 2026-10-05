"""Global hotkeys: the allowlist boundary and the browser's note filter --
pure logic, no wx construction."""

from __future__ import annotations

import ast
import functools
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


# -- every app's keys against every key the family registers system-wide ---- #
#
# The test above covers the editors and QUILL's key. The family runs side by
# side, though, and a key registered with RegisterHotKey reaches its owner
# before any window sees it, so a menu key in one app equal to another app's
# system-wide key never fires while that other app runs. QUILL Cast's Mark as
# Played and Next sat on QUILL's Ctrl+Alt+Shift+Q until 2026-10-04 for exactly
# that reason, and nineteen more were found when this gate arrived. On
# 2026-10-05 Weather, Converter, Media Player and Inkwell gave up their default
# show/hide keys and Radio's four claimants moved; the same day Inkwell gave up
# Quick Insert (Ctrl+Alt+Shift+K) and Expand Word (Ctrl+Alt+Shift+X, Quill
# Radio's Export My Setup), and the gate widened from show/hide keys to EVERY
# key any family app registers system-wide by default. There is no allowance:
# one collision fails.

_APPS_DIR = Path(__file__).resolve().parents[3] / "quill" / "apps"
_QUILL_DIR = _APPS_DIR.parent

#: Empty, and it stays empty: a new key takes a chord nobody in the family
#: registers system-wide. (It held nineteen entries from 2026-10-04 to -05.)
_GRANDFATHERED: frozenset[str] = frozenset()

#: Every place under quill/ that names RegisterHotKey, and what it registers out
#: of the box. A new one fails test_every_register_hotkey_site_is_accounted_for
#: until its default keys are in family_chords.default_system_wide_keys() (or it
#: is shown to register nothing by default) and it is added here.
_REGISTER_HOTKEY_SITES: dict[str, str] = {
    # The hardware media keys (no modifier: not a shortcut anywhere), and the
    # show/hide key from SHOW_HIDE_DEFAULTS or the listener's choice.
    "ui/app_shell.py": "media keys; show/hide key",
    # QUILL's Global Hotkeys table: Settings().global_hotkeys plus the default
    # show/hide fallback, both in default_system_wide_keys().
    "ui/main_frame_hotkeys.py": "Settings.global_hotkeys",
    # Inkwell's Quick Insert and Expand Word keys: InkwellSettings defaults.
    "apps/inkwell_keys.py": "InkwellSettings quick_insert_hotkey, expand_now_hotkey",
    # A momentary probe of who owns a key the listener asked about; registers
    # nothing that stays.
    "platform/windows/hotkey_owner.py": "probe only",
}


def _family_show_hide_keys() -> dict[str, str]:
    """``{chord identity: owner}`` for every family app's default show/hide key."""
    from quill.core.family_chords import show_hide_owners

    return show_hide_owners()


def _system_wide_owners() -> dict[str, list[str]]:
    """``{chord identity: [owner app id, ...]}`` for every key any family app
    registers system-wide by default."""
    from quill.core.family_chords import default_system_wide_keys
    from quill.core.lite.keymap import chord_identity

    owners: dict[str, list[str]] = {}
    for key in default_system_wide_keys():
        owners.setdefault(chord_identity(key.chord), []).append(key.app_id)
    return owners


@functools.cache
def _scan() -> tuple:
    """The menus scanned from the source now -- once a run, since the scan
    parses every module under quill/."""
    from quill.core.family_chords import scan_menu_chords

    return tuple(scan_menu_chords())


def _fresh_rows() -> list:
    """Every default key: the tables plus the fresh scan."""
    from quill.core.family_chords import every_default_chord

    return every_default_chord(list(_scan()))


def _every_default_chord() -> list[tuple[str, str]]:
    """``(where, chord)`` for every default key any app in the family ships."""
    return [(row.where, row.chord) for row in _fresh_rows()]


def _show_hide_collisions() -> set[str]:
    """Every family key that equals a key some family app registers
    system-wide by default (the name is older than the widening)."""
    from quill.core.app_launcher import app_name
    from quill.core.lite.keymap import chord_identity

    keys = _system_wide_owners()
    found = set()
    for where, chord in _every_default_chord():
        for owner in keys.get(chord_identity(chord), []):
            # The owner's own QuillVille row is meant to be its key: opening
            # Cast and bringing Cast up are one intent (app_keymaps.py).
            if where == f"QuillVille launcher: Open {app_name(owner)}":
                continue
            found.add(f"{owner}: {where}")
    return found


def test_the_show_hide_keys_come_from_the_one_table() -> None:
    """No app registers a literal: every show/hide key is in family_chords, so
    the gate cannot miss one. Weather, Converter, Media Player and Inkwell
    register the listener's choice and nothing by default."""
    from quill.core.family_chords import SHOW_HIDE_DEFAULTS
    from quill.core.lite.keymap import chord_identity

    literals = []
    for path in sorted(_APPS_DIR.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_register_tray_hotkey"
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                literals.append(f"{path.name}: {node.args[0].value}")
    assert literals == []
    assert {app for app, key in SHOW_HIDE_DEFAULTS.items() if key} == {"quill", "radio", "cast"}
    assert {app for app, key in SHOW_HIDE_DEFAULTS.items() if not key} == {
        "weather",
        "converter",
        "player",
        "inkwell",
    }
    owners = _family_show_hide_keys()
    assert owners[chord_identity("Ctrl+Alt+Shift+R")] == "radio"
    assert owners[chord_identity("Ctrl+Alt+Shift+Q")] == "quill"
    assert owners[chord_identity("Ctrl+Alt+Shift+F12")] == "cast"


def test_the_scan_reaches_launchers_runtime_menus_and_numbered_rows() -> None:
    """The places a key hides from a plain table walk: the QuillVille launchers,
    menus built from row tables at runtime (Local Media), QUILL's own Weather
    menu, and the numbered Alt+Shift+1..9 recent rows."""
    rows = _every_default_chord()
    where = " | ".join(place for place, _chord in rows)
    chords = {(place.split(" ")[0], chord) for place, chord in rows}
    assert "QuillVille launcher row 1" in where
    assert "QuillVille launcher: Open Quill Cast" in where
    assert any(place.startswith("ui/radio/local_media_window_menu.py") for place, _ in rows)
    assert any(place.startswith("ui/main_frame_weather.py") for place, _ in rows)
    assert ("core/recent_documents.py", "Alt+Shift+9") in chords
    assert ("ui/main_frame_radio.py", "Alt+Shift+1") in chords


def test_no_app_key_is_a_family_show_hide_key() -> None:
    new = sorted(_show_hide_collisions() - _GRANDFATHERED)
    assert new == [], "keys another app takes system-wide: " + "; ".join(new)


def test_nothing_is_grandfathered() -> None:
    assert _GRANDFATHERED == frozenset()


def test_every_register_hotkey_site_is_accounted_for() -> None:
    """A new RegisterHotKey anywhere in quill/ is a new system-wide key the
    gate cannot see until somebody adds its defaults to the inventory."""
    found = set()
    for path in sorted(_QUILL_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(
            isinstance(node, ast.Attribute) and node.attr == "RegisterHotKey"
            for node in ast.walk(tree)
        ):
            found.add(path.relative_to(_QUILL_DIR).as_posix())
    assert found == set(_REGISTER_HOTKEY_SITES)


def test_no_two_system_wide_keys_are_the_same_key() -> None:
    clashes = {chord: owners for chord, owners in _system_wide_owners().items() if len(owners) > 1}
    assert clashes == {}


def test_every_system_wide_key_holds_ctrl_or_alt() -> None:
    """Anything else takes the key away from every program the listener types in."""
    from quill.core.family_chords import default_system_wide_keys
    from quill.core.lite.keymap import normalise_chord

    bare = [
        f"{key.app_id} {key.purpose}: {key.chord}"
        for key in default_system_wide_keys()
        if not {part.lower() for part in normalise_chord(key.chord).split("+")[:-1]}
        & {"ctrl", "alt"}
    ]
    assert bare == []


def test_inkwell_registers_nothing_until_chosen() -> None:
    from quill.core.expansion.settings import InkwellSettings
    from quill.core.family_chords import default_system_wide_keys

    settings = InkwellSettings()
    assert (settings.tray_hotkey, settings.quick_insert_hotkey, settings.expand_now_hotkey) == (
        "",
        "",
        "",
    )
    assert [key for key in default_system_wide_keys() if key.app_id == "inkwell"] == []


def test_the_media_keys_are_only_the_hardware_media_keys() -> None:
    """The one default registration left out of the inventory: Play/Pause, Stop,
    Next and Previous, with no modifier -- keys no app uses as a shortcut."""
    from quill.ui.app_shell import AppShellFrame

    assert set(AppShellFrame._MEDIA_KEY_CODES.values()) <= {0xB0, 0xB1, 0xB2, 0xB3}
    source = (_QUILL_DIR / "ui" / "app_shell.py").read_text(encoding="utf-8")
    assert "RegisterHotKey(hotkey_id, 0, keycode)" in source


class _DefaultsHost(GlobalHotkeysMixin):
    """QUILL's Global Hotkeys mixin on a fresh profile: default settings and
    the default keymap, nothing chosen."""

    def __init__(self, *, own_show_hide: bool) -> None:
        from quill.core.settings import Settings

        self.settings = Settings()
        self._tray_hotkey_registered = own_show_hide

    def _binding_for(self, command_id: str) -> str | None:
        from quill.core.keymap import DEFAULT_KEYMAP

        return DEFAULT_KEYMAP.get(command_id)

    def _parse_keybinding(self, binding: str | None):
        from quill.core.lite.keymap import normalise_chord

        if not binding or "," in binding:
            return None  # a two-step chord cannot be a system-wide key
        return (1, 65) if normalise_chord(binding) else None


def test_quills_default_global_hotkeys_are_in_the_inventory() -> None:
    """What QUILL, Radio and Cast actually hand RegisterHotKey on a fresh
    profile is exactly what default_system_wide_keys() says."""
    from quill.core.family_chords import default_system_wide_keys
    from quill.core.lite.keymap import chord_identity

    known = {chord_identity(key.chord) for key in default_system_wide_keys()}
    for own in (False, True):
        host = _DefaultsHost(own_show_hide=own)
        registered = [
            chord
            for chord in host._global_hotkey_bindings().values()
            if host._parse_keybinding(chord) is not None
        ]
        assert [chord for chord in registered if chord_identity(chord) not in known] == []


def test_the_committed_menu_scan_matches_the_source() -> None:
    """An installed build has no source to scan, so the picker reads the copy.
    Regenerate with ``python -m quill.tools.family_chords_snapshot --write``."""
    from quill.core.family_chords import SNAPSHOT_PATH
    from quill.tools.family_chords_snapshot import rendered

    assert SNAPSHOT_PATH.read_bytes().decode("utf-8") == rendered(list(_scan())), (
        "stale: python -m quill.tools.family_chords_snapshot --write"
    )


# -- the four moved commands (Radio's Ctrl+Alt+Shift+R, 2026-10-05) ----------- #


def test_radios_show_hide_key_is_nobody_elses_command() -> None:
    from quill.core.app_keymaps import APP_KEYMAPS
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    lite = {row[3]: row[2] for row in COMMANDS if row[3]}
    assert APP_KEYMAPS["cast"]["app.restore"] == "Ctrl+Alt+F12"
    assert DEFAULT_KEYMAP["tools.keymap_editor"] == "Ctrl+Alt+Shift+Space"
    # Rule 2: the Keyboard Manager is one key in both editors.
    assert lite["cmd_keyboard_manager"] == DEFAULT_KEYMAP["tools.keymap_editor"]
    studio = (_APPS_DIR / "studio.py").read_text(encoding="utf-8")
    assert "Resume Last Book on La&unch\\tCtrl+Alt+F10" in studio
    assert "\\tCtrl+Alt+Shift+R" not in studio


def test_casts_restore_is_the_editors_restore_key() -> None:
    """Rule 2: one verb, one key -- Restore Settings is Ctrl+Alt+F12 in both editors."""
    from quill.core.app_keymaps import APP_KEYMAPS
    from quill.core.keymap import DEFAULT_KEYMAP

    assert APP_KEYMAPS["cast"]["app.restore"] == DEFAULT_KEYMAP["tools.share_import"]
