"""Multi-vintage shared-store safety for the keymap store.

Like ``settings.json``, ``%APPDATA%\\Quill\\keymap.json`` is read and rewritten
by several apps of possibly different vintages. A binding for a command this
build does not ship (because a newer sibling app added the command) must not be
dropped on this build's rewrite, and a keymap stamped with a newer epoch must
not be downgraded. See ``quill.core.keymap.merge_keymaps`` /
``_keymap_overrides`` / ``load_keymap``.
"""

from __future__ import annotations

import json

from quill.core import keymap as km
from quill.core.keymap import (
    DEFAULT_KEYMAP,
    KEYMAP_DEFAULTS_EPOCH,
    _keymap_overrides,
    _persisted_keymap_document,
    merge_keymaps,
)

# A command id this build does not ship, bound to a chord no default uses.
_FOREIGN = "audio_studio.a_future_command_this_build_lacks"
_FOREIGN_CHORD = "Ctrl+Alt+Shift+F12"


def _doc(epoch: int, **bindings) -> dict:
    return {**bindings, "_defaults_epoch": epoch}


# --- pure merge / delta behavior --------------------------------------------


def test_merge_preserves_unknown_command_binding():
    merged = merge_keymaps(_doc(KEYMAP_DEFAULTS_EPOCH, **{_FOREIGN: _FOREIGN_CHORD}))
    assert merged.get(_FOREIGN) == _FOREIGN_CHORD


def test_overrides_include_unknown_command():
    merged = merge_keymaps(_doc(KEYMAP_DEFAULTS_EPOCH, **{_FOREIGN: _FOREIGN_CHORD}))
    assert _keymap_overrides(merged).get(_FOREIGN) == _FOREIGN_CHORD


def test_persisted_document_round_trips_unknown_command():
    merged = merge_keymaps(_doc(KEYMAP_DEFAULTS_EPOCH, **{_FOREIGN: _FOREIGN_CHORD}))
    doc = _persisted_keymap_document(merged)
    assert doc[_FOREIGN] == _FOREIGN_CHORD
    assert doc["_defaults_epoch"] == KEYMAP_DEFAULTS_EPOCH
    # Stable across a second merge (no drift on repeated rewrites).
    assert merge_keymaps(doc).get(_FOREIGN) == _FOREIGN_CHORD


def test_default_bindings_still_omitted_from_delta():
    # No regression: a pristine map serializes to just the epoch stamp.
    merged = merge_keymaps(_doc(KEYMAP_DEFAULTS_EPOCH))
    assert _keymap_overrides(merged) == {}


def test_known_override_still_persisted():
    # Pick any real default command and rebind it to an unused chord.
    command = next(iter(DEFAULT_KEYMAP))
    merged = merge_keymaps(_doc(KEYMAP_DEFAULTS_EPOCH, **{command: _FOREIGN_CHORD}))
    assert _keymap_overrides(merged).get(command) == _FOREIGN_CHORD


# --- end-to-end through load_keymap -----------------------------------------


def _patch_path(monkeypatch, tmp_path):
    path = tmp_path / "keymap.json"
    monkeypatch.setattr(km, "keymap_path", lambda: path)
    return path


def test_load_preserves_unknown_binding_through_a_rewrite(monkeypatch, tmp_path):
    path = _patch_path(monkeypatch, tmp_path)
    # A pre-epoch (0) file forces a rewrite (epoch gets bumped); the foreign
    # binding must survive it.
    path.write_text(json.dumps(_doc(0, **{_FOREIGN: _FOREIGN_CHORD})), encoding="utf-8")
    km.load_keymap()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk.get("_defaults_epoch") == KEYMAP_DEFAULTS_EPOCH  # rewrite happened
    assert on_disk.get(_FOREIGN) == _FOREIGN_CHORD  # and it was preserved


def test_future_epoch_file_not_rewritten(monkeypatch, tmp_path):
    path = _patch_path(monkeypatch, tmp_path)
    doc = _doc(
        KEYMAP_DEFAULTS_EPOCH + 5,
        **{_FOREIGN: _FOREIGN_CHORD, "another.future_command": "Ctrl+Alt+Shift+F11"},
    )
    path.write_text(json.dumps(doc), encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    km.load_keymap()
    after = path.read_text(encoding="utf-8")
    assert before == after  # an older build must never downgrade a newer keymap
