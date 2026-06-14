from __future__ import annotations

from pathlib import Path

from quill.core.keymap_packs import (
    KEYBOARD_PACK_CUSTOM,
    KEYBOARD_PACK_DEFAULT,
    KEYBOARD_PACKS,
    KeyboardPack,
    keyboard_pack_description,
    keyboard_pack_names,
    keyboard_pack_preview,
)
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

__all__ = [
    "DEFAULT_KEYMAP",
    "KEYBOARD_PACK_CUSTOM",
    "KEYBOARD_PACK_DEFAULT",
    "KEYBOARD_PACKS",
    "KeyboardPack",
    "KQP_EXTENSION",
    "build_keymap_for_pack",
    "export_keyboard_pack",
    "export_keymap",
    "find_keymap_conflict",
    "import_keyboard_pack",
    "import_keymap",
    "keyboard_pack_description",
    "keyboard_pack_names",
    "keyboard_pack_preview",
    "keymap_path",
    "list_keymap_profiles",
    "load_keymap",
    "load_keymap_profile",
    "merge_keymaps",
    "reset_keymap",
    "save_keymap",
]

DEFAULT_KEYMAP: dict[str, str] = {
    "file.new": "Ctrl+N",
    "file.open": "Ctrl+O",
    "file.save": "Ctrl+S",
    "file.save_as": "Ctrl+Shift+S",
    "file.open_from_remote": "Ctrl+Shift+Grave, Shift+O",  # QUILL-key chord (R taken by read-aloud)
    "file.save_to_remote": "Ctrl+Shift+Grave, W",  # QUILL-key chord
    "file.manage_remote_sites": "Ctrl+Shift+Grave, Shift+M",  # QUILL-key chord
    "file.close_document": "Ctrl+W",
    "file.print": "Ctrl+P",
    "window.next_document": "Ctrl+Tab",
    "window.previous_document": "Ctrl+Shift+Tab",
    "navigate.speak_window_title": "Ctrl+Shift+Grave, F",
    "navigate.speak_full_path": "Ctrl+Shift+Grave, P",
    "navigate.speak_status_summary": "Ctrl+Shift+Grave, Q",
    "view.send_to_tray": "Ctrl+Shift+Grave, T",
    "view.toggle_soft_wrap": "Alt+Z",
    "view.toggle_tab_control": "Ctrl+Shift+Grave, Shift+T",
    "app.command_palette": "Ctrl+Shift+P",
    "app.preferences": "Ctrl+,",
    "app.exit": "Alt+F4",
    "navigate.go_to_line": "Ctrl+G",
    "navigate.go_to_page": "Ctrl+Shift+G",
    "navigate.next_region": "F6",
    "navigate.previous_region": "Shift+F6",
    "navigate.back_location": "Alt+Left",
    "navigate.forward_location": "Alt+Right",
    "navigate.outline_navigator": "Ctrl+Shift+O",
    "navigate.match_bracket": "Ctrl+Shift+\\",
    "navigate.next_structure": "Alt+Down",
    "navigate.previous_structure": "Alt+Up",
    "navigate.heading_organizer": "Ctrl+Shift+Grave, O",
    "navigate.list_bookmarks": "Alt+Shift+B",
    "tools.ask_quill_chat": "Alt+Q",
    "tools.word_count": "Ctrl+Shift+W",
    "tools.spell_check_dialog": "F7",
    "tools.next_misspelling": "Alt+F7",
    "tools.previous_misspelling": "Shift+Alt+F7",
    "tools.misspelling_list": "Alt+Shift+L",
    "tools.thesaurus": "Shift+F7",
    "tools.read_aloud_start_pause": "Ctrl+Shift+Grave, R",  # §10.8.2: P→R
    "tools.read_aloud_stop": "Ctrl+Shift+Grave, Shift+R",  # §10.8.2: Shift+P→Shift+R
    "tools.dictation_toggle": "Ctrl+Shift+Grave, D",
    "tools.describe_image": "Ctrl+Shift+Grave, I",
    "tools.document_intake_report": "Ctrl+Shift+I",
    "help.switch_feature_profile": "Alt+Shift+P",
    "edit.copy_with_source": "Ctrl+Shift+C",
    "edit.copy_selection_for_email": "Ctrl+Shift+Grave, C",
    "edit.undo": "Ctrl+Z",
    "edit.redo": "Ctrl+Y",
    "edit.toggle_extend_selection_mode": "",  # no default binding; assign via keymap editor
    "edit.start_selection": "F8",
    "edit.complete_selection": "Shift+F8",
    "edit.reselect": "Ctrl+Shift+F8",
    "edit.go_to_start_of_selection": "Alt+Shift+F8",
    "edit.copy_all": "Ctrl+F8",
    "edit.unselect_all": "Ctrl+Shift+A",
    "edit.say_selected": "",  # Shift+Space — conditional intercept in _on_editor_key_down
    "edit.read_all": "Alt+F8",
    "edit.find": "Ctrl+F",
    "edit.find_next": "F3",
    "edit.find_previous": "Shift+F3",
    "edit.find_all_matches": "Alt+F3",
    "edit.replace": "Ctrl+H",
    "tools.search_in_files": "Ctrl+Shift+F",
    "tools.replace_in_files": "Ctrl+Shift+R",
    "tools.sticky_note_capture": "Ctrl+Shift+Grave, N",
    "edit.replace_all": "Ctrl+Shift+H",
    "edit.insert_link": "Ctrl+K",
    "edit.follow_link": "Ctrl+Enter",
    "edit.word_prediction": "Ctrl+.",  # freed Ctrl+Space for select_chunk (§4.22)
    "edit.select_chunk": "Ctrl+Space",  # §4.22 EdSharp parity
    "view.preview": "Ctrl+Shift+V",
    "view.browser_preview": "Ctrl+Shift+Grave, V",  # §10.8.2: QUILL-key chord
    "view.split_preview": "Ctrl+Shift+Backslash",
    "view.focus_preview": "Ctrl+F6",
    "view.switch_editing_lens": "Ctrl+Shift+Grave, K",
    "edit.set_mark": "Ctrl+Shift+M",
    "edit.pop_mark": "Ctrl+M",
    "edit.exchange_point_mark": "Ctrl+Shift+X",
    "edit.list_marks": "Alt+M",
    "edit.select_paragraph": "",  # Ctrl+Alt+P removed (§10.8 screen-reader-hostile)
    "edit.select_block": "Ctrl+Shift+B",
    "edit.expand_selection": "Alt+Shift+Up",
    "edit.shrink_selection": "Alt+Shift+Down",
    "edit.set_named_mark": "",
    "edit.jump_to_named_mark": "",
    "edit.open_review_buffer": "",
    "edit.select_to_start_of_line": "Shift+Home",
    "edit.select_to_end_of_line": "Shift+End",
    "edit.select_to_start_of_document": "Ctrl+Shift+Home",
    "edit.select_to_end_of_document": "Ctrl+Shift+End",
    "edit.quote_lines": "Ctrl+Q",  # §4.22 EdSharp parity
    "edit.unquote_lines": "Ctrl+Shift+Q",  # §4.22 EdSharp parity
    "edit.duplicate_selection": "",  # §4.17; no default key to avoid Ctrl+D clash
    "edit.reverse_lines": "Alt+Shift+Z",  # §4.22 EdSharp parity
    "format.toggle_line_comment": "Ctrl+/",
    "format.toggle_block_comment": "Shift+Alt+A",
    "format.indent": "Ctrl+]",
    "format.outdent": "Ctrl+[",
    "format.list_manager": "Ctrl+Shift+Grave, L",
    "format.bold": "Ctrl+B",
    "format.italic": "Ctrl+I",
    "format.heading_1": "Ctrl+Shift+Grave, 1",
    "format.heading_2": "Ctrl+Shift+Grave, 2",
    "format.heading_3": "Ctrl+Shift+Grave, 3",
    "format.heading_4": "Ctrl+Shift+Grave, 4",
    "format.heading_5": "Ctrl+Shift+Grave, 5",
    "format.heading_6": "Ctrl+Shift+Grave, 6",
    "format.decrease_heading_level": "Alt+Shift+Left",
    "format.increase_heading_level": "Alt+Shift+Right",
    "format.insert_html_tag": "Ctrl+Shift+Grave, H",
    "format.insert_markdown_tag": "Ctrl+Shift+Grave, M",
    "format.insert_snippet": "Ctrl+Shift+Grave, S",
    "format.manage_snippets": "Ctrl+Shift+Grave, Shift+S",
    "format.expand_abbreviation": "Ctrl+Shift+Grave, A",
    "format.manage_abbreviations": "Ctrl+Shift+Grave, Shift+A",
    "format.toggle_abbreviation_expansion": "Ctrl+Shift+Grave, E",
    "power.insert_special_character": "F2",  # §4.22 EdSharp parity
    "power.number_lines": "Alt+Shift+N",  # §4.22 Number Items parity
    "power.trim_blank_lines": "Ctrl+Shift+Enter",  # §4.22 Trim Blanks parity
    "power.keep_unique_lines": "Alt+Shift+K",  # §4.22 Keep Unique parity
    "quill.quick_nav.heading": "H",
    "quill.quick_nav.link": "A",
    "quill.quick_nav.list": "L",
    "quill.quick_nav.list_item": "I",
    "quill.quick_nav.table": "T",
    "quill.quick_nav.block_quote": "Q",
    "quill.quick_nav.bookmark": "B",
    "quill.quick_nav.code_block": "'",
    "quill.quick_nav.table_of_contents": "C",
    "quill.quick_nav.paragraph": "P",
    "quill.quick_nav.sentence": "S",
    "quill.quick_nav.block": "TAB",
    "quill.quick_nav.skip_forward": "]",
    "quill.quick_nav.skip_backward": "[",
    # §8.1 — context help for current mode and doc summary (Alt+I).
    # Alt+H is reserved for the Help menu mnemonic; Ctrl+Shift+H is edit.replace_all;
    # Ctrl+Alt+ is banned by §10.8 (screen-reader-hostile). Use the QUILL-key chord.
    "help.context_help": "Ctrl+Shift+Grave, Shift+H",
    "document.summary": "Alt+I",
    # §8.2 — universal "Go to anything" palette (Quill+G).
    "navigate.go_to_anything": "Ctrl+Shift+Grave, G",
    # §8.1 — QUILL-key cheatsheet overlay (Alt+?).
    "help.key_cheatsheet": "Alt+Shift+/",
    # §8.1 — live contrast check announcement.
    "view.announce_contrast": "Ctrl+Shift+Grave, Shift+C",
    # §8.2 — explain why the focused item is unavailable ("Why don't I see…?").
    "help.why_unavailable": "Alt+F1",
    # §10.8 — magic paste moves to QUILL key, V (handled in QuillKeyMixin prefix
    # state machine).  Ctrl+Alt+V removed — screen readers eat Ctrl+Alt+ chords.
    "edit.magic_paste": "",
    # §CopyTray — Copy Tray slot access (12 slots).
    # Paste: Ctrl+Shift+N for N=1-9, Ctrl+Shift+0 for slot 10,
    #        Ctrl+Shift+- for slot 11, Ctrl+Shift+= for slot 12.
    # Copy:  QUILL+Shift+N for same key positions (Shift+digit/symbol).
    # QUILL+1-6 (bare) are heading shortcuts; Shift variants are distinct.
    # Open tray dialog: QUILL+X.
    "edit.open_copy_tray": "Ctrl+Shift+Grave, X",
    "edit.clear_all_tray_slots": "",
    "edit.copy_to_next_slot": "",
    "edit.search_tray_slots": "",
    "edit.copy_to_tray_1": "Ctrl+Shift+Grave, Shift+1",
    "edit.copy_to_tray_2": "Ctrl+Shift+Grave, Shift+2",
    "edit.copy_to_tray_3": "Ctrl+Shift+Grave, Shift+3",
    "edit.copy_to_tray_4": "Ctrl+Shift+Grave, Shift+4",
    "edit.copy_to_tray_5": "Ctrl+Shift+Grave, Shift+5",
    "edit.copy_to_tray_6": "Ctrl+Shift+Grave, Shift+6",
    "edit.copy_to_tray_7": "Ctrl+Shift+Grave, Shift+7",
    "edit.copy_to_tray_8": "Ctrl+Shift+Grave, Shift+8",
    "edit.copy_to_tray_9": "Ctrl+Shift+Grave, Shift+9",
    "edit.copy_to_tray_10": "Ctrl+Shift+Grave, Shift+0",
    "edit.copy_to_tray_11": "Ctrl+Shift+Grave, Shift+-",
    "edit.copy_to_tray_12": "Ctrl+Shift+Grave, Shift+=",
    "edit.paste_from_tray_1": "Ctrl+Shift+1",
    "edit.paste_from_tray_2": "Ctrl+Shift+2",
    "edit.paste_from_tray_3": "Ctrl+Shift+3",
    "edit.paste_from_tray_4": "Ctrl+Shift+4",
    "edit.paste_from_tray_5": "Ctrl+Shift+5",
    "edit.paste_from_tray_6": "Ctrl+Shift+6",
    "edit.paste_from_tray_7": "Ctrl+Shift+7",
    "edit.paste_from_tray_8": "Ctrl+Shift+8",
    "edit.paste_from_tray_9": "Ctrl+Shift+9",
    "edit.paste_from_tray_10": "Ctrl+Shift+0",
    "edit.paste_from_tray_11": "Ctrl+Shift+-",
    "edit.paste_from_tray_12": "Ctrl+Shift+=",
}


_PROFILES_DIR = Path(__file__).resolve().parent / "keymap"


def keymap_path() -> Path:
    return app_data_dir() / "keymap.json"


def load_keymap() -> dict[str, str]:
    raw = read_json(keymap_path(), default={})
    return merge_keymaps(raw)


def load_keymap_profile(name: str) -> dict[str, str]:
    """Return the merged keymap for a named JSON profile in quill/core/keymap/.

    Falls back to DEFAULT_KEYMAP if the profile file is not found.
    Profile names map to ``profile_<name>.json``; spaces are replaced with
    underscores and the string is lower-cased.  Example: ``"Minimal"``
    loads ``profile_minimal.json``.
    """
    slug = name.lower().replace(" ", "_")
    profile_path = _PROFILES_DIR / f"profile_{slug}.json"
    data = read_json(profile_path, default={})
    if not isinstance(data, dict):
        return DEFAULT_KEYMAP.copy()
    bindings = data.get("bindings", {})
    if not isinstance(bindings, dict):
        return DEFAULT_KEYMAP.copy()
    merged = DEFAULT_KEYMAP.copy()
    merged.update({k: v for k, v in bindings.items() if isinstance(v, str)})
    return merged


def list_keymap_profiles() -> list[str]:
    """Return the display names of available JSON profiles."""
    profiles: list[str] = []
    if not _PROFILES_DIR.is_dir():
        return profiles
    for path in sorted(_PROFILES_DIR.glob("profile_*.json")):
        data = read_json(path, default={})
        if isinstance(data, dict) and "_name" in data:
            profiles.append(str(data["_name"]))
    return profiles


def save_keymap(keymap: dict[str, str]) -> None:
    write_json_atomic(keymap_path(), keymap)


def build_keymap_for_pack(name: str) -> dict[str, str]:
    pack = KEYBOARD_PACKS.get(name)
    merged = DEFAULT_KEYMAP.copy()
    if pack is None:
        return merged
    merged.update(pack.bindings)
    return merged


def merge_keymaps(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return DEFAULT_KEYMAP.copy()
    merged = DEFAULT_KEYMAP.copy()
    legacy_rebindings = {
        # Find returns to the conventional Ctrl+F. It had briefly defaulted to the
        # QUILL-key prefix; rewrite that stale saved binding on load.
        "edit.find": ("CTRL+SHIFT+GRAVE, F", "Ctrl+F"),
        # window.next_document / previous_document: Ctrl+Tab restored as default
        # in #190; no legacy rebinding needed.
        "view.send_to_tray": ("CTRL+ALT+T", "Ctrl+Shift+Grave, T"),
        "view.toggle_tab_control": ("CTRL+ALT+SHIFT+T", "Ctrl+Shift+Grave, Shift+T"),
        "navigate.heading_organizer": ("CTRL+ALT+SHIFT+H", "Ctrl+Shift+Grave, O"),
        "tools.read_aloud_start_pause": ("CTRL+ALT+P", "Ctrl+Shift+Grave, R"),
        "tools.read_aloud_stop": ("CTRL+ALT+S", "Ctrl+Shift+Grave, Shift+R"),
        "tools.dictation_toggle": ("CTRL+ALT+V", "Ctrl+Shift+Grave, D"),
        "edit.toggle_extend_selection_mode": ("F8", ""),
        "edit.copy_selection_for_email": ("CTRL+ALT+C", "Ctrl+Shift+Grave, C"),
        "tools.sticky_note_capture": ("CTRL+ALT+SHIFT+N", "Ctrl+Shift+Grave, N"),
        "view.browser_preview": ("CTRL+ALT+SHIFT+V", "Ctrl+Shift+Grave, V"),
        "format.list_manager": ("CTRL+ALT+L", "Ctrl+Shift+Grave, L"),
        "format.heading_1": ("CTRL+ALT+1", "Ctrl+Shift+Grave, 1"),
        "format.heading_2": ("CTRL+ALT+2", "Ctrl+Shift+Grave, 2"),
        "format.heading_3": ("CTRL+ALT+3", "Ctrl+Shift+Grave, 3"),
        "format.heading_4": ("CTRL+ALT+4", "Ctrl+Shift+Grave, 4"),
        "format.heading_5": ("CTRL+ALT+5", "Ctrl+Shift+Grave, 5"),
        "format.heading_6": ("CTRL+ALT+6", "Ctrl+Shift+Grave, 6"),
        "format.insert_html_tag": ("CTRL+ALT+H", "Ctrl+Shift+Grave, H"),
        "format.insert_markdown_tag": ("CTRL+ALT+M", "Ctrl+Shift+Grave, M"),
        "format.insert_snippet": ("CTRL+ALT+SPACE", "Ctrl+Shift+Grave, S"),
        "format.manage_snippets": ("CTRL+ALT+SHIFT+SPACE", "Ctrl+Shift+Grave, Shift+S"),
        "format.expand_abbreviation": ("", "Ctrl+Shift+Grave, A"),
        "format.manage_abbreviations": ("", "Ctrl+Shift+Grave, Shift+A"),
        "format.toggle_abbreviation_expansion": ("", "Ctrl+Shift+Grave, E"),
    }
    legacy_preview_conflict = (
        str(raw.get("view.preview", "")).strip().upper() == "CTRL+SHIFT+P"
        and str(raw.get("view.browser_preview", "")).strip().upper() == "CTRL+SHIFT+V"
    )
    for command_id, binding in raw.items():
        if isinstance(command_id, str) and isinstance(binding, str):
            normalized = binding
            if legacy_preview_conflict and command_id == "view.preview":
                normalized = "Ctrl+Shift+V"
            elif legacy_preview_conflict and command_id == "view.browser_preview":
                normalized = "Ctrl+Alt+Shift+V"
            legacy_binding = legacy_rebindings.get(command_id)
            if legacy_binding is not None and normalized.strip().upper() == legacy_binding[0]:
                normalized = legacy_binding[1]
            if not normalized.strip():
                merged[command_id] = ""
                continue
            conflict = find_keymap_conflict(merged, command_id, normalized)
            if conflict is None:
                merged[command_id] = normalized
    return merged


def export_keymap(target: Path, keymap: dict[str, str]) -> None:
    write_json_atomic(target, keymap)


def import_keymap(source: Path) -> dict[str, str]:
    raw = read_json(source, default={})
    merged = merge_keymaps(raw)
    save_keymap(merged)
    return merged


KQP_EXTENSION = ".kqp"
_KQP_VERSION = 1


def export_keyboard_pack(
    target: Path,
    keymap: dict[str, str],
    name: str,
    description: str,
    author: str = "",
    version: str = "1.0",
) -> None:
    """Write a .kqp (Keyboard Quill Pack) file.

    Only bindings that differ from DEFAULT_KEYMAP are stored so the file
    captures intent rather than a snapshot of defaults that may change.
    """
    delta: dict[str, str] = {k: v for k, v in keymap.items() if v != DEFAULT_KEYMAP.get(k)}
    payload: dict[str, object] = {
        "kqp_version": _KQP_VERSION,
        "name": name.strip(),
        "description": description.strip(),
        "author": author.strip(),
        "version": version.strip(),
        "bindings": delta,
    }
    write_json_atomic(target, payload)


def import_keyboard_pack(source: Path) -> tuple[str, str, dict[str, str]]:
    """Read a .kqp file. Return (name, description, merged_keymap).

    Raises ValueError if the file is missing, malformed, uses an unsupported
    kqp_version, or fails the kqp validator.  The merged keymap is persisted
    via save_keymap *only* after validation succeeds (finding #42: a bad
    pack must never silently overwrite the user's bindings).
    """
    raw = read_json(source, default=None)
    if not isinstance(raw, dict):
        raise ValueError(f"{source.name} is not a valid Keyboard Quill Pack (expected JSON object)")
    file_version = raw.get("kqp_version")
    if file_version != _KQP_VERSION:
        raise ValueError(
            f"{source.name}: unsupported kqp_version {file_version!r} "
            f"(this build supports version {_KQP_VERSION})"
        )
    name = str(raw.get("name", source.stem)) or source.stem
    description = str(raw.get("description", ""))
    bindings = raw.get("bindings", {})
    if not isinstance(bindings, dict):
        raise ValueError(f"{source.name}: 'bindings' must be a JSON object")
    # Re-write the parsed payload to a temp buffer and run the same validator
    # the standalone ``quill.tools.kqp_validator`` runs, so the import path
    # uses the same rules as the CLI.
    from quill.tools.kqp_validator import _validate_file  # local import: avoid cycles

    issues = _validate_file(source, strict=False)
    if issues:
        joined = "; ".join(issues)
        raise ValueError(f"{source.name} failed keyboard pack validation: {joined}")
    merged = merge_keymaps(bindings)
    save_keymap(merged)
    return name, description, merged


def reset_keymap() -> dict[str, str]:
    defaults = DEFAULT_KEYMAP.copy()
    save_keymap(defaults)
    return defaults


def find_keymap_conflict(
    keymap: dict[str, str],
    command_id: str,
    binding: str,
) -> str | None:
    candidate = binding.strip().upper()
    if not candidate:
        return None
    for existing_command, existing_binding in keymap.items():
        if existing_command == command_id:
            continue
        if existing_binding.strip().upper() == candidate:
            return existing_command
    return None
