"""Tests for GATE-VC: version consistency gate."""

from __future__ import annotations

import re
from pathlib import Path

from quill.tools.check_version_consistency import (
    _authoritative_version,
    _check_changelog,
    _check_iss,
    _check_pyproject,
    main,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_authoritative_version_reads_init_py() -> None:
    version = _authoritative_version(_REPO_ROOT)
    assert re.match(r"^\d+\.\d+", version), f"unexpected version format: {version!r}"


def test_live_tree_is_consistent() -> None:
    """The checked-in tree must have no version skew."""
    result = main()
    assert result == 0, "GATE-VC found version inconsistencies in the live tree"


def test_pyproject_static_version_is_flagged(tmp_path: Path) -> None:
    init_py = tmp_path / "quill" / "__init__.py"
    init_py.parent.mkdir()
    init_py.write_text('__version__ = "1.2.3"\n')

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_bytes(
        b'[project]\nname = "quill"\nversion = "1.2.3"\n'
        b'[tool.hatch.version]\npath = "quill/__init__.py"\n'
    )
    errors = _check_pyproject(tmp_path, "1.2.3")
    assert any("static" in e for e in errors), errors


def test_pyproject_missing_dynamic_is_flagged(tmp_path: Path) -> None:
    init_py = tmp_path / "quill" / "__init__.py"
    init_py.parent.mkdir()
    init_py.write_text('__version__ = "1.2.3"\n')

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_bytes(
        b'[project]\nname = "quill"\n[tool.hatch.version]\npath = "quill/__init__.py"\n'
    )
    errors = _check_pyproject(tmp_path, "1.2.3")
    assert any("dynamic" in e for e in errors), errors


def test_pyproject_wrong_hatch_path_is_flagged(tmp_path: Path) -> None:
    init_py = tmp_path / "quill" / "__init__.py"
    init_py.parent.mkdir()
    init_py.write_text('__version__ = "1.2.3"\n')

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_bytes(
        b'[project]\nname = "quill"\ndynamic = ["version"]\n'
        b'[tool.hatch.version]\npath = "src/__init__.py"\n'
    )
    errors = _check_pyproject(tmp_path, "1.2.3")
    assert any("hatch" in e.lower() or "path" in e for e in errors), errors


def test_iss_wrong_version_is_flagged(tmp_path: Path) -> None:
    installer = tmp_path / "installer"
    installer.mkdir()
    (installer / "quill.iss").write_text(
        '#define AppVersion "0.9.9"\nOutputBaseFilename=Quill-for-All-Setup-0.9.9\n'
    )
    errors = _check_iss(tmp_path, "1.2.3")
    assert any("AppVersion" in e for e in errors), errors


def test_iss_ok_returns_no_errors(tmp_path: Path) -> None:
    installer = tmp_path / "installer"
    installer.mkdir()
    (installer / "quill.iss").write_text(
        '#define AppVersion "1.2.3"\nOutputBaseFilename=Quill-for-All-Setup-1.2.3\n'
    )
    errors = _check_iss(tmp_path, "1.2.3")
    assert errors == []


def test_changelog_wrong_top_version_is_flagged(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text("## 0.9.9 (2026-01-01)\n\nsome content\n")
    errors = _check_changelog(tmp_path, "1.2.3")
    assert any("CHANGELOG" in e for e in errors), errors


def test_changelog_matching_version_ok(tmp_path: Path) -> None:
    (tmp_path / "CHANGELOG.md").write_text("## 1.2.3 (2026-01-01)\n\nsome content\n")
    errors = _check_changelog(tmp_path, "1.2.3")
    assert errors == []
