"""Tests for the manifest ``targets`` field: loader filtering + validation.

``targets`` decides which app(s) a Quillin loads in. An omitted ``targets`` means
the editor only (``["quill"]``), so every pre-existing Quillin keeps loading in
the editor and never appears in a companion app unless it opts in.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.quillins.loader import (
    discover_bundled_extensions,
    discover_extensions,
    extensions_root,
)
from quill.core.quillins.validation import validate_manifest


class _Features:
    def __init__(self, *, third_party: bool = True, bundled: bool = True) -> None:
        self._third_party = third_party
        self._bundled = bundled

    def is_enabled(self, feature_id: str) -> bool:
        if feature_id == "core.third_party_plugins":
            return self._third_party
        if feature_id == "core.bundled_quillins":
            return self._bundled
        return False


def _manifest(extension_id: str, *, targets: list[str] | None = None) -> dict[str, object]:
    manifest: dict[str, object] = {
        "schema": "quill.extension/1",
        "id": extension_id,
        "name": extension_id,
        "version": "1.0.0",
        "contributes": {
            "commands": [{"id": "ext.x.wrap", "title": "Wrap", "run": {"snippet": "x"}}]
        },
    }
    if targets is not None:
        manifest["targets"] = targets
    return manifest


def _install(root: Path, extension_id: str, manifest: dict[str, object]) -> None:
    directory = extensions_root(root=root) / extension_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _install_bundled(root: Path, extension_id: str, manifest: dict[str, object]) -> None:
    directory = root / extension_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


# -- loader filtering (third-party path) ------------------------------------


def test_third_party_targets_filtering(tmp_path: Path) -> None:
    _install(tmp_path, "com.example.radio", _manifest("com.example.radio", targets=["radio"]))
    _install(tmp_path, "com.example.editor", _manifest("com.example.editor"))  # default quill
    _install(tmp_path, "com.example.both", _manifest("com.example.both", targets=["quill", "cast"]))
    features = _Features(third_party=True)

    def ids(app_id: str) -> set[str]:
        return {e.id for e in discover_extensions(features, root=tmp_path, app_id=app_id)}

    # Editor default: the targets-less one and the quill+cast one, never radio.
    assert ids("quill") == {"com.example.editor", "com.example.both"}
    assert ids("radio") == {"com.example.radio"}
    assert ids("cast") == {"com.example.both"}
    assert ids("weather") == set()


def test_editor_default_app_id_is_quill(tmp_path: Path) -> None:
    _install(tmp_path, "com.example.editor", _manifest("com.example.editor"))
    _install(tmp_path, "com.example.radio", _manifest("com.example.radio", targets=["radio"]))
    # No app_id -> the implicit editor id, so an editor caller is unaffected and
    # never picks up a radio-only Quillin.
    discovered = {e.id for e in discover_extensions(_Features(), root=tmp_path)}
    assert discovered == {"com.example.editor"}


# -- loader filtering (bundled path) ----------------------------------------


def test_bundled_targets_filtering(tmp_path: Path) -> None:
    _install_bundled(tmp_path, "editor-only", _manifest("com.example.editoronly"))
    _install_bundled(tmp_path, "cast-only", _manifest("com.example.castonly", targets=["cast"]))
    features = _Features(bundled=True)

    editor = {e.id for e in discover_bundled_extensions(features, root=tmp_path, app_id="quill")}
    cast = {e.id for e in discover_bundled_extensions(features, root=tmp_path, app_id="cast")}
    assert editor == {"com.example.editoronly"}
    assert cast == {"com.example.castonly"}


# -- validation --------------------------------------------------------------


def _valid_base(**extra: object) -> dict[str, object]:
    base: dict[str, object] = {
        "schema": "quill.extension/1",
        "id": "com.example.q",
        "name": "Q",
        "version": "1.0.0",
    }
    base.update(extra)
    return base


def test_valid_targets_accepted() -> None:
    assert validate_manifest(_valid_base(targets=["radio", "cast"])) == []


def test_unknown_target_rejected() -> None:
    errors = validate_manifest(_valid_base(targets=["nope"]))
    assert any("not a known app id" in e for e in errors)


def test_empty_targets_rejected() -> None:
    errors = validate_manifest(_valid_base(targets=[]))
    assert any("must not be empty" in e for e in errors)


def test_editor_only_capability_cannot_target_non_editor_app() -> None:
    manifest = _valid_base(
        targets=["radio"],
        capabilities=["editor.write"],
        main="ext.py",
        contributes={"commands": [{"id": "ext.q.go", "title": "Go", "run": {"handler": "go"}}]},
    )
    # ui.command is required for a handler command; add it so the ONLY failure is
    # the editor-only/target conflict.
    manifest["capabilities"] = ["editor.write", "ui.command"]
    errors = validate_manifest(manifest)
    assert any("editor-only capabilities" in e and "radio" in e for e in errors)


def test_editor_only_capability_ok_for_default_editor_target() -> None:
    manifest = _valid_base(
        capabilities=["editor.write", "ui.command"],
        main="ext.py",
        contributes={"commands": [{"id": "ext.q.go", "title": "Go", "run": {"handler": "go"}}]},
    )
    assert validate_manifest(manifest) == []


# -- feed_auth_providers contribution ---------------------------------------


def test_feed_auth_provider_requires_capability_and_main() -> None:
    manifest = _valid_base(
        targets=["cast"],
        contributes={
            "feed_auth_providers": [
                {
                    "id": "ext.q.provider",
                    "match_hosts": ["premium.example.com"],
                    "handler": "h",
                }
            ]
        },
    )
    errors = validate_manifest(manifest)
    assert any("podcast.feed.auth" in e for e in errors)
    assert any("main" in e for e in errors)


def test_feed_auth_provider_valid() -> None:
    manifest = _valid_base(
        targets=["cast"],
        capabilities=["podcast.feed.auth", "storage"],
        main="ext.py",
        contributes={
            "feed_auth_providers": [
                {
                    "id": "ext.q.provider",
                    "match_hosts": ["premium.example.com", "*.premium.example.com"],
                    "handler": "feed_auth_header",
                }
            ]
        },
    )
    assert validate_manifest(manifest) == []
