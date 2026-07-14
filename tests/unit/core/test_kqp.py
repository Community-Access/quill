"""Tests for the .kqp (Keyboard Quill Pack) format."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.keymap import (
    DEFAULT_KEYMAP,
    KQP_EXTENSION,
    export_keyboard_pack,
    import_keyboard_pack,
)
from quill.tools.kqp_validator import validate_file


def _write_kqp(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


# ---------------------------------------------------------------------------
# export_keyboard_pack
# ---------------------------------------------------------------------------


def test_export_creates_file(tmp_path: pytest.TempPathFactory) -> None:
    target = tmp_path / "my-pack.kqp"
    export_keyboard_pack(target, DEFAULT_KEYMAP.copy(), name="Test Pack", description="")
    assert target.exists()


def test_export_schema(tmp_path: pytest.TempPathFactory) -> None:
    target = tmp_path / "pack.kqp"
    export_keyboard_pack(
        target,
        DEFAULT_KEYMAP.copy(),
        name="Test",
        description="A test pack",
        author="Jane",
        version="2.0",
    )
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["kqp_version"] == 1
    assert data["name"] == "Test"
    assert data["description"] == "A test pack"
    assert data["author"] == "Jane"
    assert data["version"] == "2.0"
    assert isinstance(data["bindings"], dict)


def test_export_only_stores_delta(tmp_path: pytest.TempPathFactory) -> None:
    keymap = DEFAULT_KEYMAP.copy()
    keymap["edit.find"] = "Alt+F"  # override one binding
    target = tmp_path / "delta.kqp"
    export_keyboard_pack(target, keymap, name="Delta", description="")
    data = json.loads(target.read_text(encoding="utf-8"))
    # Only the override should appear in bindings; defaults are omitted.
    assert "edit.find" in data["bindings"]
    assert data["bindings"]["edit.find"] == "Alt+F"
    # A default binding that was not changed should NOT appear.
    assert "edit.undo" not in data["bindings"]


def test_export_extension_is_kqp() -> None:
    assert KQP_EXTENSION == ".kqp"


# ---------------------------------------------------------------------------
# import_keyboard_pack
# ---------------------------------------------------------------------------


def test_import_returns_name_and_description(tmp_path: pytest.TempPathFactory) -> None:
    path = tmp_path / "pack.kqp"
    _write_kqp(
        path,
        {
            "kqp_version": 1,
            "name": "My Pack",
            "description": "Optimised for writers.",
            "bindings": {},
        },
    )
    name, description, _ = import_keyboard_pack(path)
    assert name == "My Pack"
    assert description == "Optimised for writers."


def test_import_merges_bindings_with_defaults(tmp_path: pytest.TempPathFactory) -> None:
    path = tmp_path / "pack.kqp"
    _write_kqp(
        path,
        {
            "kqp_version": 1,
            "name": "Override Pack",
            "description": "",
            "bindings": {"edit.find": "Alt+F"},
        },
    )
    _, _, merged = import_keyboard_pack(path)
    assert merged["edit.find"] == "Alt+F"
    # Defaults are filled in.
    assert "edit.undo" in merged


def test_import_empty_bindings_gives_defaults(tmp_path: pytest.TempPathFactory) -> None:
    path = tmp_path / "empty.kqp"
    _write_kqp(path, {"kqp_version": 1, "name": "Empty", "description": "", "bindings": {}})
    _, _, merged = import_keyboard_pack(path)
    assert merged == DEFAULT_KEYMAP


def test_import_rejects_non_object(tmp_path: pytest.TempPathFactory) -> None:
    path = tmp_path / "bad.kqp"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="valid Keyboard Quill Pack"):
        import_keyboard_pack(path)


def test_import_rejects_wrong_version(tmp_path: pytest.TempPathFactory) -> None:
    path = tmp_path / "v99.kqp"
    _write_kqp(path, {"kqp_version": 99, "name": "Future", "bindings": {}})
    with pytest.raises(ValueError, match="kqp_version"):
        import_keyboard_pack(path)


def test_import_rejects_bindings_non_object(tmp_path: pytest.TempPathFactory) -> None:
    path = tmp_path / "bad_bindings.kqp"
    _write_kqp(path, {"kqp_version": 1, "name": "Bad", "description": "", "bindings": ["nope"]})
    with pytest.raises(ValueError, match="bindings"):
        import_keyboard_pack(path)


def test_import_runs_validator_before_merge(tmp_path: Path) -> None:
    """Finding #42: bad pack files must be rejected at import, not merged in.

    The kqp validator already knows what is allowed (parseable chord, known
    command id, non-empty name).  ``import_keyboard_pack`` must call it
    *before* ``save_keymap`` so a malformed file does not silently overwrite
    the user's bindings.
    """
    path = tmp_path / "no_name.kqp"
    # Missing 'name' field: validator reports it, importer must propagate.
    _write_kqp(
        path,
        {
            "kqp_version": 1,
            "description": "Anonymous pack",
            "bindings": {"edit.find": "Alt+F"},
        },
    )
    expected = validate_file(path, strict=False)
    assert expected, "validator should report at least one error for this fixture"
    with pytest.raises(ValueError) as excinfo:
        import_keyboard_pack(path)
    # Every validator error should be in the raised message so the user can
    # see the full list at once instead of fix-once-and-retry.
    for err in expected:
        assert err in str(excinfo.value), f"missing validator error: {err!r}"


# ---------------------------------------------------------------------------
# round-trip
# ---------------------------------------------------------------------------


def test_round_trip(tmp_path: pytest.TempPathFactory) -> None:
    keymap = DEFAULT_KEYMAP.copy()
    # Use key sequences not assigned to any other command in DEFAULT_KEYMAP and
    # not subject to a legacy rebinding or the beta Find force (which rewrites
    # any "Ctrl+Shift+Grave, *" edit.find binding to Ctrl+F).
    keymap["edit.find_next"] = "Ctrl+Shift+Grave, Z"
    keymap["tools.thesaurus"] = "Ctrl+Shift+Grave, Shift+Y"
    target = tmp_path / "trip.kqp"
    export_keyboard_pack(target, keymap, name="Trip Pack", description="Round trip test")
    name, description, merged = import_keyboard_pack(target)
    assert name == "Trip Pack"
    assert description == "Round trip test"
    assert merged["edit.find_next"] == "Ctrl+Shift+Grave, Z"
    assert merged["tools.thesaurus"] == "Ctrl+Shift+Grave, Shift+Y"
    # Untouched defaults survive.
    assert merged["file.save"] == DEFAULT_KEYMAP["file.save"]
