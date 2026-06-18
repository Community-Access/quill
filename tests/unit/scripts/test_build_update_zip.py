"""Unit tests for scripts/build_update_zip.py."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.build_update_zip import (
    _find_latest_base_version,
    build_update_zip,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_bootstrapper(bootstrapper_dir: Path, name: str = "bootstrap.exe") -> Path:
    dest = bootstrapper_dir / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"stub-bootstrapper")
    return dest


def _make_source_tree(source_root: Path, files: dict[str, bytes]) -> list[dict[str, object]]:
    """Write files under source_root and return manifest entries."""
    entries: list[dict[str, object]] = []
    prefix = "python/Lib/site-packages"
    for rel, content in files.items():
        dest = source_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        entries.append({
            "path": rel,
            "install_path": f"{prefix}/{rel}",
            "sha256": _sha256(content),
            "size": len(content),
        })
    return entries


def _make_manifest_file(manifest_dir: Path, version: str, entries: list[dict]) -> Path:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / f"manifest-{version}.json"
    path.write_text(
        json.dumps({"version": version, "files": entries}) + "\n",
        encoding="utf-8",
    )
    return path


def _run_build(
    *,
    tmp_path: Path,
    mode: str,
    source_entries: list[dict],
    base_entries: list[dict] | None = None,
    base_version: str | None = None,
    platform: str = "windows",
    bootstrapper_name: str = "bootstrap.exe",
) -> Path:
    """Drive build_update_zip with mocked scan_files, return output ZIP path."""
    bs_dir = tmp_path / "bootstrappers"
    _make_bootstrapper(bs_dir, bootstrapper_name)

    manifest_dir = tmp_path / "manifests"
    if base_entries is not None and base_version:
        _make_manifest_file(manifest_dir, base_version, base_entries)

    output = tmp_path / "out" / "update.zip"

    # Source root just needs to exist so zipfile.write() can find files
    source_root = tmp_path / "src"

    with patch("scripts.build_update_zip.scan_files", return_value=source_entries):
        rc = build_update_zip(
            version="0.5.0",
            mode=mode,
            base_version=base_version,
            platform=platform,
            bootstrapper_dir=bs_dir,
            source_root=source_root,
            output=output,
            install_prefix="python/Lib/site-packages",
            manifest_dir=manifest_dir,
        )

    assert rc == 0, f"build_update_zip returned {rc}"
    return output


def _zip_names(zip_path: Path) -> set[str]:
    with zipfile.ZipFile(zip_path) as zf:
        return set(zf.namelist())


def _read_update_manifest(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        return json.loads(zf.read("UPDATE_MANIFEST.json"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_delta_includes_only_changed_files(tmp_path: Path) -> None:
    shared_hash = _sha256(b"unchanged")
    changed_hash_old = _sha256(b"old content")
    changed_hash_new = _sha256(b"new content")

    base_entries = [
        {
            "path": "quill/unchanged.py",
            "install_path": "python/Lib/site-packages/quill/unchanged.py",
            "sha256": shared_hash,
            "size": 9,
        },
        {
            "path": "quill/changed.py",
            "install_path": "python/Lib/site-packages/quill/changed.py",
            "sha256": changed_hash_old,
            "size": 11,
        },
    ]
    new_entries = [
        {
            "path": "quill/unchanged.py",
            "install_path": "python/Lib/site-packages/quill/unchanged.py",
            "sha256": shared_hash,
            "size": 9,
        },
        {
            "path": "quill/changed.py",
            "install_path": "python/Lib/site-packages/quill/changed.py",
            "sha256": changed_hash_new,
            "size": 11,
        },
    ]

    # Write the actual source file so zipfile can include it
    src = tmp_path / "src"
    (src / "quill").mkdir(parents=True, exist_ok=True)
    (src / "quill" / "changed.py").write_bytes(b"new content")

    bs_dir = tmp_path / "bootstrappers"
    _make_bootstrapper(bs_dir)
    manifest_dir = tmp_path / "manifests"
    _make_manifest_file(manifest_dir, "0.4.0", base_entries)
    output = tmp_path / "out" / "update.zip"

    with patch("scripts.build_update_zip.scan_files", return_value=new_entries):
        rc = build_update_zip(
            version="0.5.0",
            mode="delta",
            base_version="0.4.0",
            platform="windows",
            bootstrapper_dir=bs_dir,
            source_root=src,
            output=output,
            install_prefix="python/Lib/site-packages",
            manifest_dir=manifest_dir,
        )

    assert rc == 0
    names = _zip_names(output)
    assert "python/Lib/site-packages/quill/changed.py" in names
    assert "python/Lib/site-packages/quill/unchanged.py" not in names


def test_full_mode_includes_all_files(tmp_path: Path) -> None:
    src = tmp_path / "src"
    entries = _make_source_tree(
        src,
        {
            "quill/__init__.py": b"",
            "quill/core/settings.py": b"x=1",
        },
    )

    output = _run_build(tmp_path=tmp_path, mode="full", source_entries=entries)
    names = _zip_names(output)
    assert "python/Lib/site-packages/quill/__init__.py" in names
    assert "python/Lib/site-packages/quill/core/settings.py" in names


def test_bootstrapper_always_at_zip_root(tmp_path: Path) -> None:
    src = tmp_path / "src"
    entries = _make_source_tree(src, {"quill/__init__.py": b""})
    output = _run_build(tmp_path=tmp_path, mode="full", source_entries=entries)
    assert "bootstrap.exe" in _zip_names(output)


def test_update_manifest_json_included_in_zip(tmp_path: Path) -> None:
    src = tmp_path / "src"
    entries = _make_source_tree(src, {"quill/__init__.py": b""})
    output = _run_build(tmp_path=tmp_path, mode="full", source_entries=entries)
    assert "UPDATE_MANIFEST.json" in _zip_names(output)
    meta = _read_update_manifest(output)
    assert meta["version"] == "0.5.0"
    assert meta["mode"] == "full"


def test_delta_with_no_changes_still_includes_bootstrapper(tmp_path: Path) -> None:
    shared_hash = _sha256(b"same")
    entries = [
        {
            "path": "quill/__init__.py",
            "install_path": "python/Lib/site-packages/quill/__init__.py",
            "sha256": shared_hash,
            "size": 4,
        }
    ]

    bs_dir = tmp_path / "bootstrappers"
    _make_bootstrapper(bs_dir)
    manifest_dir = tmp_path / "manifests"
    _make_manifest_file(manifest_dir, "0.4.0", entries)
    output = tmp_path / "out" / "update.zip"
    src = tmp_path / "src"
    src.mkdir()

    with patch("scripts.build_update_zip.scan_files", return_value=entries):
        rc = build_update_zip(
            version="0.5.0",
            mode="delta",
            base_version="0.4.0",
            platform="windows",
            bootstrapper_dir=bs_dir,
            source_root=src,
            output=output,
            install_prefix="python/Lib/site-packages",
            manifest_dir=manifest_dir,
        )

    assert rc == 0
    names = _zip_names(output)
    assert "bootstrap.exe" in names
    assert "UPDATE_MANIFEST.json" in names
    # No changed files
    assert "python/Lib/site-packages/quill/__init__.py" not in names


def test_auto_detects_base_version_from_manifests(tmp_path: Path) -> None:
    src = tmp_path / "src"
    new_entries = _make_source_tree(src, {"quill/__init__.py": b"new"})
    old_entries = [
        {
            "path": "quill/__init__.py",
            "install_path": "python/Lib/site-packages/quill/__init__.py",
            "sha256": _sha256(b"old"),
            "size": 3,
        }
    ]

    bs_dir = tmp_path / "bootstrappers"
    _make_bootstrapper(bs_dir)
    manifest_dir = tmp_path / "manifests"
    # Two available base manifests; 0.4.0 should be selected as highest < 0.5.0
    _make_manifest_file(manifest_dir, "0.3.0", old_entries)
    _make_manifest_file(manifest_dir, "0.4.0", old_entries)
    output = tmp_path / "out" / "update.zip"

    with patch("scripts.build_update_zip.scan_files", return_value=new_entries):
        rc = build_update_zip(
            version="0.5.0",
            mode="delta",
            base_version=None,  # must auto-detect
            platform="windows",
            bootstrapper_dir=bs_dir,
            source_root=src,
            output=output,
            install_prefix="python/Lib/site-packages",
            manifest_dir=manifest_dir,
        )

    assert rc == 0
    meta = _read_update_manifest(output)
    assert meta["base_version"] == "0.4.0"


def test_deleted_files_recorded_in_update_manifest(tmp_path: Path) -> None:
    src = tmp_path / "src"
    new_entries = _make_source_tree(src, {"quill/__init__.py": b"x"})

    old_entries = [
        {
            "path": "quill/__init__.py",
            "install_path": "python/Lib/site-packages/quill/__init__.py",
            "sha256": _sha256(b"x"),
            "size": 1,
        },
        {
            "path": "quill/removed_module.py",
            "install_path": "python/Lib/site-packages/quill/removed_module.py",
            "sha256": _sha256(b"old"),
            "size": 3,
        },
    ]

    bs_dir = tmp_path / "bootstrappers"
    _make_bootstrapper(bs_dir)
    manifest_dir = tmp_path / "manifests"
    _make_manifest_file(manifest_dir, "0.4.0", old_entries)
    output = tmp_path / "out" / "update.zip"

    with patch("scripts.build_update_zip.scan_files", return_value=new_entries):
        rc = build_update_zip(
            version="0.5.0",
            mode="delta",
            base_version="0.4.0",
            platform="windows",
            bootstrapper_dir=bs_dir,
            source_root=src,
            output=output,
            install_prefix="python/Lib/site-packages",
            manifest_dir=manifest_dir,
        )

    assert rc == 0
    meta = _read_update_manifest(output)
    deleted = meta["deleted"]
    assert any("removed_module.py" in d for d in deleted)


# ---------------------------------------------------------------------------
# _find_latest_base_version
# ---------------------------------------------------------------------------


def test_find_latest_base_version_picks_highest_below_current(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    for v in ["0.3.0", "0.4.0", "0.4.1"]:
        (manifest_dir / f"manifest-{v}.json").write_text("{}", encoding="utf-8")
    result = _find_latest_base_version("0.5.0", manifest_dir)
    assert result == "0.4.1"


def test_find_latest_base_version_ignores_versions_above_current(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    (manifest_dir / "manifest-0.6.0.json").write_text("{}", encoding="utf-8")
    result = _find_latest_base_version("0.5.0", manifest_dir)
    assert result is None
