"""Tests for the remappable keyboard model (PRD 10.1)."""

import pytest

from quill_social import keymap as km_mod
from quill_social.keymap import Keymap, normalize_chord


def test_normalize_orders_modifiers():
    assert normalize_chord("shift+ctrl+r") == "Ctrl+Shift+R"
    assert normalize_chord("Ctrl+Shift+R") == "Ctrl+Shift+R"
    assert normalize_chord("alt+b") == "Alt+B"


def test_defaults_match_prd():
    k = Keymap()
    assert k.chord_for("compose") == "Ctrl+N"
    assert k.chord_for("command_center") == "Ctrl+Shift+C"
    assert k.chord_for("where_am_i") == "Ctrl+Shift+I"


def test_command_for_chord_is_reverse_lookup():
    k = Keymap()
    assert k.command_for("ctrl+n") == "compose"
    assert k.command_for("F6") == "next_pane"
    assert k.command_for("Ctrl+Alt+Shift+Z") is None


def test_rebind_detects_conflict():
    k = Keymap()
    with pytest.raises(ValueError):
        k.rebind("reply", "Ctrl+N")  # already compose


def test_rebind_force_steals():
    k = Keymap()
    k.rebind("reply", "Ctrl+N", force=True)
    assert k.command_for("Ctrl+N") == "reply"
    assert k.chord_for("compose") == ""


def test_rebind_to_new_chord():
    k = Keymap()
    k.rebind("compose", "Ctrl+Shift+J")
    assert k.command_for("Ctrl+Shift+J") == "compose"


def test_persistence_roundtrip(tmp_path):
    k = Keymap()
    k.rebind("compose", "Ctrl+Shift+J")
    km_mod.save(tmp_path, k)
    loaded = km_mod.load(tmp_path)
    assert loaded.chord_for("compose") == "Ctrl+Shift+J"
    # unrelated defaults still present
    assert loaded.chord_for("reply") == "Ctrl+R"


def test_load_missing_returns_defaults(tmp_path):
    assert km_mod.load(tmp_path).chord_for("compose") == "Ctrl+N"


def test_no_two_default_commands_share_a_chord():
    """Two commands on one chord means the menu shows a key one of them never gets."""
    chords = [normalize_chord(c) for c in km_mod.DEFAULT_BINDINGS.values()]
    assert sorted({c for c in chords if chords.count(c) > 1}) == []


def test_every_menu_command_has_a_default_chord():
    """Family rule 8: every command has a key. The menu rows read these."""
    for command_id in (
        "flag",
        "accessibility_check",
        "send_to_quill",
        "new_folder",
        "new_smart_folder",
        "edit_smart_folder",
        "delete_smart_folder",
        "import_opml",
        "export_opml",
        "unsubscribe",
        "listen_toggle",
        "listen_next",
        "listen_prev",
        "listen_stop",
        "drafts",
        "agenda",
        "queue_schedule",
        "approvals",
        "catchup",
        "analytics",
        "safety_center",
        "notification_policies",
        "plugins",
        "outbox",
        "summarize_feed",
        "user_guide",
        "keyboard_reference",
        "product_requirements",
        "about",
        "preferences",
    ):
        assert Keymap().chord_for(command_id), command_id


def test_a_new_default_yields_to_a_chord_the_listener_already_chose(tmp_path):
    """A keymap.json saved before a default existed keeps its own key; the
    newcomer is left without one rather than sharing it."""
    (tmp_path / km_mod.BINDINGS_NAME).write_text('{"compose": "Ctrl+Shift+D"}', encoding="utf-8")
    loaded = km_mod.load(tmp_path)
    assert loaded.command_for("Ctrl+Shift+D") == "compose"
    assert loaded.chord_for("drafts") == ""
    assert loaded.chord_for("agenda") == "Ctrl+Shift+Y"
