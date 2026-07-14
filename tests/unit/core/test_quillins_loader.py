"""Tests for Quillin discovery, enable/disable state, and the SEC-8 gate.

The loader must return nothing unless the ``core.third_party_plugins`` feature is
enabled (locked off for 1.0). All tests pin discovery to a temporary ``root`` so
they never touch real app data.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from quill.core.quillins.loader import (
    _parse_semver,
    discover_extensions,
    extensions_root,
    grant_capabilities,
    is_event_enabled,
    load_enabled_manifests,
    load_state,
    remove_extension,
    set_enabled,
    set_event_enabled,
)


class _Features:
    """Minimal stand-in for the feature registry's ``is_enabled`` surface."""

    def __init__(self, third_party: bool) -> None:
        self._third_party = third_party

    def is_enabled(self, feature_id: str) -> bool:
        if feature_id == "core.third_party_plugins":
            return self._third_party
        return False


def _install(root: Path, extension_id: str, manifest: dict[str, object] | None) -> Path:
    directory = extensions_root(root=root) / extension_id
    directory.mkdir(parents=True, exist_ok=True)
    if manifest is not None:
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


def _snippet_manifest(extension_id: str = "com.example.fence") -> dict[str, object]:
    return {
        "schema": "quill.extension/1",
        "id": extension_id,
        "name": "Code Fence",
        "version": "1.0.0",
        "contributes": {
            "commands": [{"id": "ext.fence.wrap", "title": "Wrap", "run": {"snippet": "x"}}]
        },
    }


def test_discovery_is_empty_when_flag_off(tmp_path: Path) -> None:
    _install(tmp_path, "com.example.fence", _snippet_manifest())
    assert discover_extensions(_Features(third_party=False), root=tmp_path) == []


def test_discovery_finds_installed_when_flag_on(tmp_path: Path) -> None:
    _install(tmp_path, "com.example.fence", _snippet_manifest())
    discovered = discover_extensions(_Features(third_party=True), root=tmp_path)
    assert len(discovered) == 1
    assert discovered[0].id == "com.example.fence"
    assert discovered[0].is_valid
    assert not discovered[0].enabled  # default disabled


def test_invalid_manifest_is_surfaced_not_silently_dropped(tmp_path: Path) -> None:
    bad = _snippet_manifest("com.example.bad")
    bad["version"] = "nope"
    _install(tmp_path, "com.example.bad", bad)
    discovered = discover_extensions(_Features(third_party=True), root=tmp_path)
    assert len(discovered) == 1
    assert not discovered[0].is_valid
    assert discovered[0].errors


def test_missing_manifest_is_reported(tmp_path: Path) -> None:
    _install(tmp_path, "no-manifest", manifest=None)
    discovered = discover_extensions(_Features(third_party=True), root=tmp_path)
    assert len(discovered) == 1
    assert not discovered[0].is_valid
    assert any("missing manifest.json" in error for error in discovered[0].errors)


def test_enable_disable_round_trips_through_state(tmp_path: Path) -> None:
    _install(tmp_path, "com.example.fence", _snippet_manifest())
    set_enabled("com.example.fence", True, root=tmp_path)
    state = load_state(root=tmp_path)
    assert state.entry("com.example.fence").enabled is True
    set_enabled("com.example.fence", False, root=tmp_path)
    assert load_state(root=tmp_path).entry("com.example.fence").enabled is False


def test_load_enabled_manifests_only_returns_enabled_valid(tmp_path: Path) -> None:
    _install(tmp_path, "com.example.fence", _snippet_manifest())
    features = _Features(third_party=True)
    assert load_enabled_manifests(features, root=tmp_path) == []
    set_enabled("com.example.fence", True, root=tmp_path)
    manifests = load_enabled_manifests(features, root=tmp_path)
    assert [m.id for m in manifests] == ["com.example.fence"]


def test_enabled_but_disabled_flag_still_blocks_loading(tmp_path: Path) -> None:
    _install(tmp_path, "com.example.fence", _snippet_manifest())
    set_enabled("com.example.fence", True, root=tmp_path)
    # Flag off => SEC-8 returns nothing even though state says enabled.
    assert load_enabled_manifests(_Features(third_party=False), root=tmp_path) == []


def test_grant_capabilities_dedupes_and_persists(tmp_path: Path) -> None:
    grant_capabilities(
        "com.example.fence", ("editor.read", "editor.read", "editor.write"), root=tmp_path
    )
    granted = load_state(root=tmp_path).entry("com.example.fence").granted_capabilities
    assert granted == ("editor.read", "editor.write")


def test_remove_extension_deletes_directory_and_state(tmp_path: Path) -> None:
    _install(tmp_path, "com.example.fence", _snippet_manifest())
    set_enabled("com.example.fence", True, root=tmp_path)
    assert remove_extension("com.example.fence", root=tmp_path) is True
    assert not (extensions_root(root=tmp_path) / "com.example.fence").exists()
    assert "com.example.fence" not in load_state(root=tmp_path).entries


def test_remove_rejects_path_escape(tmp_path: Path) -> None:
    # A crafted id must never delete outside the extensions root.
    assert remove_extension("..", root=tmp_path) is False


# -- semver parsing ----------------------------------------------------------


def test_parse_semver_valid() -> None:
    assert _parse_semver("1.2.3") == (1, 2, 3)
    assert _parse_semver("0.6.0") == (0, 6, 0)


def test_parse_semver_invalid_returns_none() -> None:
    assert _parse_semver("nope") is None
    assert _parse_semver("") is None


# -- min_quill_version enforcement -------------------------------------------


def test_min_quill_version_below_current_is_accepted(tmp_path: Path) -> None:
    manifest = _snippet_manifest()
    manifest["min_quill_version"] = "0.1.0"
    _install(tmp_path, "com.example.fence", manifest)
    with patch("quill.core.quillins.loader._running_quill_version", return_value="0.6.0"):
        discovered = discover_extensions(_Features(third_party=True), root=tmp_path)
    assert discovered[0].is_valid


def test_min_quill_version_above_current_is_rejected(tmp_path: Path) -> None:
    manifest = _snippet_manifest()
    manifest["min_quill_version"] = "99.0.0"
    _install(tmp_path, "com.example.fence", manifest)
    with patch("quill.core.quillins.loader._running_quill_version", return_value="0.6.0"):
        discovered = discover_extensions(_Features(third_party=True), root=tmp_path)
    assert not discovered[0].is_valid
    assert any("requires QUILL" in e for e in discovered[0].errors)


# -- requires enforcement ----------------------------------------------------


def _requires_manifest(
    extension_id: str = "com.example.child",
    dep_id: str = "com.example.dep",
    min_version: str = "",
) -> dict[str, object]:
    requires_entry: dict[str, object] = {"id": dep_id}
    if min_version:
        requires_entry["min_version"] = min_version
    return {
        "schema": "quill.extension/1",
        "id": extension_id,
        "name": "Child",
        "version": "1.0.0",
        "requires": [requires_entry],
        "contributes": {
            "commands": [{"id": "ext.child.run", "title": "Run", "run": {"snippet": "x"}}]
        },
    }


def test_requires_met_when_dependency_is_installed(tmp_path: Path) -> None:
    _install(tmp_path, "com.example.dep", _snippet_manifest("com.example.dep"))
    _install(tmp_path, "com.example.child", _requires_manifest())
    discovered = {
        item.id: item for item in discover_extensions(_Features(third_party=True), root=tmp_path)
    }
    assert discovered["com.example.child"].is_valid


def test_requires_error_when_dependency_missing(tmp_path: Path) -> None:
    _install(tmp_path, "com.example.child", _requires_manifest())
    discovered = discover_extensions(_Features(third_party=True), root=tmp_path)
    assert not discovered[0].is_valid
    assert any("not installed" in e for e in discovered[0].errors)


def test_requires_error_when_version_too_low(tmp_path: Path) -> None:
    dep = _snippet_manifest("com.example.dep")
    dep["version"] = "0.1.0"
    _install(tmp_path, "com.example.dep", dep)
    _install(tmp_path, "com.example.child", _requires_manifest(min_version="1.0.0"))
    discovered = {
        item.id: item for item in discover_extensions(_Features(third_party=True), root=tmp_path)
    }
    assert not discovered["com.example.child"].is_valid
    assert any(">=" in e for e in discovered["com.example.child"].errors)


# -- per-event toggle --------------------------------------------------------


def test_event_is_enabled_by_default(tmp_path: Path) -> None:
    assert is_event_enabled("com.example.fence", "after_save", root=tmp_path) is True


def test_set_event_disabled_persists(tmp_path: Path) -> None:
    set_event_enabled("com.example.fence", "after_save", False, root=tmp_path)
    assert is_event_enabled("com.example.fence", "after_save", root=tmp_path) is False


def test_re_enabling_event_removes_it_from_disabled_set(tmp_path: Path) -> None:
    set_event_enabled("com.example.fence", "after_save", False, root=tmp_path)
    set_event_enabled("com.example.fence", "after_save", True, root=tmp_path)
    assert is_event_enabled("com.example.fence", "after_save", root=tmp_path) is True


def test_disabled_events_survive_state_round_trip(tmp_path: Path) -> None:
    set_event_enabled("com.example.fence", "after_save", False, root=tmp_path)
    set_event_enabled("com.example.fence", "before_save", False, root=tmp_path)
    state = load_state(root=tmp_path)
    entry = state.entry("com.example.fence")
    assert "after_save" in entry.disabled_events
    assert "before_save" in entry.disabled_events
    assert "activated" not in entry.disabled_events
