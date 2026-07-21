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
    assert k.command_for("Ctrl+Z") is None


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
    k.rebind("compose", "Ctrl+Shift+N")
    assert k.command_for("Ctrl+Shift+N") == "compose"


def test_persistence_roundtrip(tmp_path):
    k = Keymap()
    k.rebind("compose", "Ctrl+Shift+N")
    km_mod.save(tmp_path, k)
    loaded = km_mod.load(tmp_path)
    assert loaded.chord_for("compose") == "Ctrl+Shift+N"
    # unrelated defaults still present
    assert loaded.chord_for("reply") == "Ctrl+R"


def test_load_missing_returns_defaults(tmp_path):
    assert km_mod.load(tmp_path).chord_for("compose") == "Ctrl+N"
