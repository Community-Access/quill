from __future__ import annotations

from pathlib import Path

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"
EDITOR = (_UI / "keymap_editor.py").read_text(encoding="utf-8")
MAIN = (_UI / "main_frame.py").read_text(encoding="utf-8")


def test_editor_is_a_mixin_wired_into_main_frame() -> None:
    # The editor now lives in its own mixin to keep main_frame lean; MainFrame
    # must still inherit it so open_keymap_editor resolves.
    assert "class KeymapEditorMixin" in EDITOR
    assert "KeymapEditorMixin," in MAIN
    assert "from quill.ui.keymap_editor import KeymapEditorMixin" in MAIN
    # The old inline copies must be gone (no duplicate definitions).
    assert "def open_keymap_editor" not in MAIN
    assert "def _apply_keymap_binding" not in MAIN


def test_editor_has_persistent_dialog_with_search_and_inline_bindings() -> None:
    start = EDITOR.index("def open_keymap_editor")
    end = EDITOR.index("def _apply_keymap_binding")
    body = EDITOR[start:end]

    assert 'wx.Dialog(self.frame, title="Keymap Editor"' in body
    assert "wx.ListBox(dialog" in body
    assert "or 'Unassigned'" in body
    assert "self._binding_for(command_id)" in body
    # A live search field that filters as you type.
    assert "wx.TextCtrl(dialog" in body
    assert "wx.EVT_TEXT" in body
    # Keystroke-aware search: typing a shortcut reverse-looks-up the command.
    assert "bindings_equivalent(" in body
    assert "is assigned to:" in body
    assert "is unassigned and available." in body
    # Record Keys and Diagnostics buttons, plus inline Edit.
    assert 'wx.Button(dialog, label="&Record Keys...")' in body
    assert 'wx.Button(dialog, label="&Edit Keybinding...")' in body
    assert 'wx.Button(dialog, label="Run &Diagnostics...")' in body
    assert "def edit_selected" in body
    assert "EVT_LISTBOX_DCLICK, edit_selected" in body
    assert "self._apply_keymap_binding(command_id, new_binding" in body
    assert "refresh_list(keep=selected)" in body


def test_apply_binding_normalises_validates_resolves_conflicts_and_persists() -> None:
    start = EDITOR.index("def _apply_keymap_binding")
    end = EDITOR.index("def _event_to_binding_string")
    body = EDITOR[start:end]

    assert "if not new_binding:" in body
    # Alias/any-order tolerant parse, then a dispatchability gate so no inert key
    # is ever assigned.
    assert "parse_binding(new_binding, quill_key_prefix=prefix)" in body
    assert "self._binding_is_dispatchable(canonical)" in body
    # Canonical, all-conflicts detection with a friendly reassign offer.
    assert "find_keymap_conflicts(" in body
    assert "wx.YES_NO" in body
    assert "will become unassigned" in body
    # Stores the normalised (canonical) form and persists.
    assert "self.keymap[command_id] = canonical" in body
    assert "save_keymap(self.keymap)" in body
    assert "self._reload_shortcuts_from_keymap()" in body


def test_diagnostics_and_self_heal_present() -> None:
    assert "def _run_keymap_diagnostics" in EDITOR
    assert "diagnose_keymap(" in EDITOR
    assert "def _heal_keymap" in EDITOR
    # Heal removes bad entries and re-applies the keymap.
    heal = EDITOR[EDITOR.index("def _heal_keymap") :]
    assert "del self.keymap[command_id]" in heal
    assert "self._reload_shortcuts_from_keymap()" in heal


def test_keyboard_reference_opens_html_in_browser() -> None:
    start = MAIN.index("def open_keyboard_reference")
    end = MAIN.index("def open_user_guide")
    body = MAIN[start:end]

    assert "build_keyboard_shortcut_html(self.commands.list(), self.features)" in body
    assert "keyboard-shortcuts" in body
    assert "os.replace(temp_path, target_path)" in body
    assert "webbrowser.open(target_path.as_uri())" in body
