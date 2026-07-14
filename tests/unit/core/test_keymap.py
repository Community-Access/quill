from __future__ import annotations

import sys
from pathlib import Path

import pytest

import quill.core.keymap as keymap_module
from quill.core.keymap import (
    DEFAULT_KEYMAP,
    KEYBOARD_PACK_DEFAULT,
    KEYBOARD_PACKS,
    build_keymap_for_pack,
    export_keymap,
    find_keymap_conflict,
    import_keymap,
    keyboard_pack_names,
    keyboard_pack_preview,
    load_keymap,
    reset_keymap,
    save_keymap,
)


def _duplicates(mapping: dict[str, str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for command_id, binding in mapping.items():
        normalized = binding.strip().upper()
        if not normalized:
            continue
        grouped.setdefault(normalized, []).append(command_id)
    return {binding: commands for binding, commands in grouped.items() if len(commands) > 1}


def test_load_keymap_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    keymap = load_keymap()
    assert keymap == DEFAULT_KEYMAP
    assert _duplicates(keymap) == {}


def test_load_keymap_merges_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    save_keymap({"file.save": "Ctrl+Alt+Shift+Y"})
    keymap = load_keymap()
    assert keymap["file.save"] == "Ctrl+Alt+Shift+Y"
    assert keymap["file.open"] == DEFAULT_KEYMAP["file.open"]


def test_merge_keymaps_ignores_conflicting_bindings() -> None:
    merged = keymap_module.merge_keymaps({
        "app.command_palette": "Ctrl+Shift+P",
        "view.preview": "Ctrl+Shift+P",
    })
    assert merged["app.command_palette"] == "Ctrl+Shift+P"
    assert merged["view.preview"] == DEFAULT_KEYMAP["view.preview"]
    assert _duplicates(merged) == {}


def test_import_keymap_saves_merged_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store_path = tmp_path / "keymap-store.json"
    source_path = tmp_path / "incoming.json"
    export_keymap(source_path, {"edit.find": "Ctrl+Alt+F"})
    monkeypatch.setattr(keymap_module, "keymap_path", lambda: store_path)

    merged = import_keymap(source_path)

    assert merged["edit.find"] == "Ctrl+Alt+F"
    saved = load_keymap()
    assert saved["edit.find"] == "Ctrl+Alt+F"
    assert saved["file.save"] == DEFAULT_KEYMAP["file.save"]


def test_reset_keymap_restores_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store_path = tmp_path / "keymap-store.json"
    monkeypatch.setattr(keymap_module, "keymap_path", lambda: store_path)
    save_keymap({"file.new": "Ctrl+Alt+N"})

    reset = reset_keymap()

    assert reset == DEFAULT_KEYMAP
    assert load_keymap() == DEFAULT_KEYMAP


def test_load_keymap_drops_unknown_command_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A saved binding for a command id that no longer exists is dropped."""
    store_path = tmp_path / "keymap-store.json"
    monkeypatch.setattr(keymap_module, "keymap_path", lambda: store_path)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    save_keymap({"definitely.not.a.command": "Ctrl+Alt+Z"})

    loaded = load_keymap()

    assert "definitely.not.a.command" not in loaded
    assert loaded == DEFAULT_KEYMAP


def test_load_keymap_drops_empty_binding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A saved binding that is whitespace-only is treated as 'use default'."""
    store_path = tmp_path / "keymap-store.json"
    monkeypatch.setattr(keymap_module, "keymap_path", lambda: store_path)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    save_keymap({"file.save": "   "})

    loaded = load_keymap()

    assert loaded["file.save"] == DEFAULT_KEYMAP["file.save"]


def test_load_keymap_persists_cleaned_map(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When the saved file contains entries that get dropped, the surviving
    subset is written back to disk so the user sees the cleanup on next open.

    Valid entries survive untouched; invalid entries (unknown command id,
    conflicting chord, whitespace-only binding) are removed. The on-disk
    file keeps only the user's surviving delta — not the full
    DEFAULT_KEYMAP — so a small override file stays small.
    """
    store_path = tmp_path / "keymap-store.json"
    monkeypatch.setattr(keymap_module, "keymap_path", lambda: store_path)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    # Mix: one valid override, one orphan command id, one conflict.
    save_keymap({
        "file.save": "Ctrl+Alt+Shift+Y",  # valid override, must survive
        "definitely.removed.command": "Ctrl+Alt+X",  # unknown id, must be dropped
        "app.command_palette": "Ctrl+S",  # collides with file.save default
    })

    loaded = load_keymap()

    # Cleaned map in memory.
    assert loaded["file.save"] == "Ctrl+Alt+Shift+Y"
    assert "definitely.removed.command" not in loaded
    assert loaded["app.command_palette"] == DEFAULT_KEYMAP["app.command_palette"]

    # Surviving user overrides persisted to disk for the next launch, as a
    # delta plus the epoch stamp. Only the keys the user had on disk and that
    # survived the merge are kept.
    on_disk = keymap_module.read_json(store_path, default={})
    assert on_disk == {
        "file.save": "Ctrl+Alt+Shift+Y",
        "_defaults_epoch": keymap_module.KEYMAP_DEFAULTS_EPOCH,
    }
    assert "definitely.removed.command" not in on_disk
    assert "app.command_palette" not in on_disk


def test_load_keymap_leaves_clean_file_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the saved file is already valid, load_keymap does not rewrite it.

    A clean file should not trigger a disk write on every launch — only
    files that need cleanup do.
    """
    store_path = tmp_path / "keymap-store.json"
    monkeypatch.setattr(keymap_module, "keymap_path", lambda: store_path)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    save_keymap({"file.save": "Ctrl+Alt+Shift+Y"})
    mtime_before = store_path.stat().st_mtime_ns

    load_keymap()

    assert store_path.stat().st_mtime_ns == mtime_before


def test_find_keymap_conflict_matches_existing_command() -> None:
    keymap = {"file.save": "Ctrl+S", "edit.find": "Ctrl+F"}
    conflict = find_keymap_conflict(keymap, "file.open", "Ctrl+S")
    assert conflict == "file.save"


def test_keyboard_pack_names_include_default() -> None:
    names = keyboard_pack_names()
    assert names[0] == KEYBOARD_PACK_DEFAULT
    assert "Windows Notepad" in names
    assert "VS Code" in names


def test_build_keymap_for_pack_applies_overlay() -> None:
    keymap = build_keymap_for_pack("VS Code")
    assert keymap["file.open"] == "Ctrl+P"
    assert keymap["format.duplicate_line"] == "Shift+Alt+Down"
    assert keymap["file.save"] == DEFAULT_KEYMAP["file.save"]


def test_previous_misspelling_shortcut_is_available() -> None:
    assert DEFAULT_KEYMAP["tools.previous_misspelling"] == "Ctrl+Shift+F7"


def test_replace_shortcut_is_available() -> None:
    assert DEFAULT_KEYMAP["edit.replace"] == "Ctrl+H"


def test_snippet_shortcuts_are_available() -> None:
    # word_prediction moved to Ctrl+. (§4.22); Ctrl+Space freed for select_chunk
    assert DEFAULT_KEYMAP["edit.word_prediction"] == "Ctrl+."
    assert DEFAULT_KEYMAP["edit.select_chunk"] == "Ctrl+Space"
    assert DEFAULT_KEYMAP["format.insert_snippet"] == "Ctrl+Shift+Grave, S"
    assert DEFAULT_KEYMAP["format.manage_snippets"] == "Ctrl+Shift+Grave, Shift+S"


def test_sticky_note_shortcut_is_available() -> None:
    assert DEFAULT_KEYMAP["tools.sticky_note_capture"] == "Ctrl+Shift+Grave, Shift+N"


def test_indent_shortcuts_are_available() -> None:
    assert DEFAULT_KEYMAP["format.indent"] == "Ctrl+]"
    assert DEFAULT_KEYMAP["format.outdent"] == "Ctrl+["
    assert DEFAULT_KEYMAP["format.list_manager"] == "Ctrl+Shift+Grave, L"


def test_browser_preview_shortcut_is_available() -> None:
    assert DEFAULT_KEYMAP["view.preview"] == "Ctrl+Shift+V"
    assert DEFAULT_KEYMAP["view.browser_preview"] == "Ctrl+Shift+Grave, V"


def test_legacy_preview_conflict_migrates_to_in_app_preview() -> None:
    merged = keymap_module.merge_keymaps({
        "view.preview": "Ctrl+Shift+P",
        "view.browser_preview": "Ctrl+Shift+V",
    })
    assert merged["view.preview"] == "Ctrl+Shift+V"
    assert merged["view.browser_preview"] == "Ctrl+Shift+Grave, V"


def test_find_defaults_to_ctrl_f() -> None:
    assert DEFAULT_KEYMAP["edit.find"] == "Ctrl+F"


def test_legacy_find_grave_binding_migrates_to_ctrl_f() -> None:
    # A saved keymap that still has Find on the QUILL-key prefix is rewritten to
    # the conventional Ctrl+F on load.
    merged = keymap_module.merge_keymaps({"edit.find": "Ctrl+Shift+Grave, F"})
    assert merged["edit.find"] == "Ctrl+F"


def test_legacy_find_grave_z_binding_migrates_to_ctrl_f() -> None:
    # A pre-release beta also shipped Find on the QUILL-key prefix + Z. The
    # 0.8.0 beta force rewrites it to Ctrl+F on load so upgraders get the
    # conventional Find shortcut back.
    merged = keymap_module.merge_keymaps({"edit.find": "Ctrl+Shift+Grave, Z"})
    assert merged["edit.find"] == "Ctrl+F"


def test_beta_forces_any_quill_leader_find_to_ctrl_f() -> None:
    # The beta force overwrites *any* saved Find binding on the QUILL-key
    # leader chord, not just the specific letters earlier betas shipped, so
    # no upgrader is left with Find unreachable on a leader chord.
    for stale in ("Ctrl+Shift+Grave, K", "CTRL+SHIFT+GRAVE, Shift+F", "Ctrl+Shift+Grave"):
        merged = keymap_module.merge_keymaps({"edit.find": stale})
        assert merged["edit.find"] == "Ctrl+F", stale


def test_non_leader_custom_find_binding_is_preserved() -> None:
    # A user who deliberately rebinds Find to a non-leader chord keeps it; the
    # beta force only reclaims leader-chord Find bindings.
    merged = keymap_module.merge_keymaps({"edit.find": "Ctrl+Alt+F"})
    assert merged["edit.find"] == "Ctrl+Alt+F"


# ---------------------------------------------------------------------------
# Delta storage + defaults epoch (forward-compat for default changes)
# ---------------------------------------------------------------------------


def test_save_keymap_persists_only_the_override_delta_plus_epoch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Passing the full merged map must still persist only the entries that
    # differ from the default -- that delta is what lets a later default
    # change reach the user automatically.
    store_path = tmp_path / "keymap-store.json"
    monkeypatch.setattr(keymap_module, "keymap_path", lambda: store_path)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))

    full = DEFAULT_KEYMAP.copy()
    full["file.save"] = "Ctrl+Alt+Shift+Y"
    save_keymap(full)

    on_disk = keymap_module.read_json(store_path, default={})
    assert on_disk == {
        "file.save": "Ctrl+Alt+Shift+Y",
        "_defaults_epoch": keymap_module.KEYMAP_DEFAULTS_EPOCH,
    }


def test_non_overridden_command_tracks_the_current_default() -> None:
    # The crux of the forward-compat design: a command absent from the saved
    # delta resolves to whatever DEFAULT_KEYMAP says today -- so a changed or
    # newly added default reaches existing users with no migration entry.
    saved = {
        "file.save": "Ctrl+Alt+Shift+Y",
        "_defaults_epoch": keymap_module.KEYMAP_DEFAULTS_EPOCH,
    }
    merged = keymap_module.merge_keymaps(saved)
    assert merged["file.save"] == "Ctrl+Alt+Shift+Y"
    assert merged["edit.find"] == DEFAULT_KEYMAP["edit.find"]


def test_legacy_full_snapshot_is_converted_to_a_stamped_delta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An old full-snapshot file (no epoch, every command pinned to its value
    # at save time) is cleaned up and rewritten as a delta + epoch on load:
    # default-valued entries drop out, the stale leader-chord Find is forced
    # back to Ctrl+F, and only genuine overrides remain.
    store_path = tmp_path / "keymap-store.json"
    monkeypatch.setattr(keymap_module, "keymap_path", lambda: store_path)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    keymap_module.write_json_atomic(
        store_path,
        {
            "file.save": DEFAULT_KEYMAP["file.save"],  # equals default -> dropped
            "edit.find": "Ctrl+Shift+Grave, Z",  # stale leader chord -> Ctrl+F
            "format.bold": "Ctrl+Shift+Alt+B",  # genuine override -> kept
        },
    )

    loaded = load_keymap()
    assert loaded["edit.find"] == DEFAULT_KEYMAP["edit.find"]
    assert loaded["format.bold"] == "Ctrl+Shift+Alt+B"

    on_disk = keymap_module.read_json(store_path, default={})
    assert on_disk == {
        "format.bold": "Ctrl+Shift+Alt+B",
        "_defaults_epoch": keymap_module.KEYMAP_DEFAULTS_EPOCH,
    }


def test_post_epoch_file_respects_a_deliberate_leader_chord_find() -> None:
    # Once a file is on the current epoch (a delta of deliberate choices), the
    # one-time legacy clean-up no longer runs: a Find the user chose to put on
    # the QUILL-key leader chord after upgrading is left alone.
    saved = {
        "edit.find": "Ctrl+Shift+Grave, Z",
        "_defaults_epoch": keymap_module.KEYMAP_DEFAULTS_EPOCH,
    }
    merged = keymap_module.merge_keymaps(saved)
    assert merged["edit.find"] == "Ctrl+Shift+Grave, Z"


def test_epoch_metadata_key_is_not_treated_as_a_binding() -> None:
    merged = keymap_module.merge_keymaps({"_defaults_epoch": 1, "edit.find": "Alt+F"})
    assert "_defaults_epoch" not in merged
    assert merged["edit.find"] == "Alt+F"


def test_quote_lines_default_is_ctrl_shift_q() -> None:
    # #608: Quote Lines moved from Ctrl+Q to Ctrl+Shift+Q so Ctrl+Q is
    # free for the system Quit shortcut on macOS (Cmd+Q in wxPython).
    assert DEFAULT_KEYMAP["edit.quote_lines"] == "Ctrl+Shift+Q"
    # Unquote Lines moves from Ctrl+Shift+Q to Ctrl+Shift+K to keep
    # the pair on the home row (Q -> K) and free Ctrl+Q entirely.
    assert DEFAULT_KEYMAP["edit.unquote_lines"] == "Ctrl+Shift+K"


def test_app_exit_default_is_ctrl_q_for_macos_quit() -> None:
    # #608: app.exit is bound to Ctrl+Q so wx maps it to Cmd+Q on
    # macOS (the conventional Quit shortcut). Alt+F4 still works via
    # the wx ID_EXIT stock accelerator on the File menu.
    assert DEFAULT_KEYMAP["app.exit"] == "Ctrl+Q"


def test_legacy_quote_lines_ctrl_q_migrates_to_ctrl_shift_q() -> None:
    # #608: A user who saved Ctrl+Q on edit.quote_lines (the prior default)
    # has their saved entry rewritten to Ctrl+Shift+Q on load, so they
    # don't keep the macOS-quit collision after upgrading.
    merged = keymap_module.merge_keymaps({"edit.quote_lines": "Ctrl+Q"})
    assert merged["edit.quote_lines"] == "Ctrl+Shift+Q"


def test_legacy_unquote_lines_ctrl_shift_q_migrates_to_ctrl_shift_k() -> None:
    # #608 mirror: A user who saved Ctrl+Shift+Q on edit.unquote_lines
    # (the prior default) has it rewritten to Ctrl+Shift+K on load.
    merged = keymap_module.merge_keymaps({"edit.unquote_lines": "Ctrl+Shift+Q"})
    assert merged["edit.unquote_lines"] == "Ctrl+Shift+K"


# ---------------------------------------------------------------------------
# #609: macOS Option+Left/Right no longer hijacked by Back/Forward Location.
# ---------------------------------------------------------------------------


def test_default_keymap_uses_alt_left_on_windows() -> None:
    """#609: the Windows default for back/forward location stays
    Alt+Left / Alt+Right (the conventional Windows chord)."""
    if sys.platform == "darwin":
        # Skip on macOS so the assertion is unambiguous.
        return
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["navigate.back_location"] == "Alt+Left"
    assert DEFAULT_KEYMAP["navigate.forward_location"] == "Alt+Right"


def test_default_keymap_uses_cmd_brackets_on_macos() -> None:
    """#609: the macOS default for back/forward location is Cmd+[ /
    Cmd+], the conventional macOS chord, so the Alt+Left / Alt+Right
    slot is free for the system word-by-word movement."""
    if sys.platform != "darwin":
        return
    from quill.core.keymap import DEFAULT_KEYMAP

    assert DEFAULT_KEYMAP["navigate.back_location"] == "Cmd+["
    assert DEFAULT_KEYMAP["navigate.forward_location"] == "Cmd+]"


def test_legacy_macos_alt_left_back_location_rewritten_to_cmd_open_bracket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#609: a pre-#609 macOS user who saved Alt+Left for back location
    has it rewritten to Cmd+[ on first load."""
    monkeypatch.setattr(sys, "platform", "darwin")
    merged = keymap_module.merge_keymaps({"navigate.back_location": "Alt+Left"})
    assert merged["navigate.back_location"] == "Cmd+["


def test_legacy_macos_alt_right_forward_location_rewritten_to_cmd_close_bracket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#609: a pre-#609 macOS user who saved Alt+Right for forward
    location has it rewritten to Cmd+] on first load."""
    monkeypatch.setattr(sys, "platform", "darwin")
    merged = keymap_module.merge_keymaps({"navigate.forward_location": "Alt+Right"})
    assert merged["navigate.forward_location"] == "Cmd+]"


def test_default_keymap_has_no_ctrl_q_collision() -> None:
    # #608 pin: no two commands in the default keymap may share Ctrl+Q,
    # because that chord is now reserved for app.exit (which maps to
    # Cmd+Q on macOS).
    collisions = {
        chord: commands
        for chord, commands in _duplicates(DEFAULT_KEYMAP).items()
        if chord == "CTRL+Q"
    }
    assert collisions == {}


def test_profile_picker_shortcut_is_available() -> None:
    assert DEFAULT_KEYMAP["help.switch_feature_profile"] == "Alt+Shift+P"


def test_keyboard_pack_preview_mentions_highlights() -> None:
    preview = keyboard_pack_preview("Quill Review")
    assert "Highlights:" in preview
    assert "Copy With Source" in preview


def test_keyboard_packs_are_known() -> None:
    assert KEYBOARD_PACK_DEFAULT in KEYBOARD_PACKS
    assert "Quill Writer" in KEYBOARD_PACKS


def test_corrupt_keymap_file_is_quarantined_then_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store_path = tmp_path / "keymap-store.json"
    monkeypatch.setattr(keymap_module, "keymap_path", lambda: store_path)
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    store_path.write_text("not json at all", encoding="utf-8")

    loaded = load_keymap()

    assert loaded == DEFAULT_KEYMAP
    backups = list((tmp_path / "migration-backups").glob("keymap-corrupt-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "not json at all"
