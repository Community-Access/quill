"""Tests for GATE-VC: version consistency gate."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from quill.tools.check_version_consistency import (
    _authoritative_version,
    _check_changelog,
    _check_iss,
    _check_pyproject,
    _check_standalone_apps,
    main,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_authoritative_version_reads_init_py() -> None:
    version = _authoritative_version(_REPO_ROOT)
    assert re.match(r"^\d+\.\d+", version), f"unexpected version format: {version!r}"


@pytest.mark.skipif(
    not (_REPO_ROOT / "build" / "version.toml").exists(),
    reason=(
        "build/version.toml is the local-only (gitignored) canonical display-version "
        "source. Without it GATE-VC falls back to the PEP 440 base in quill/__init__.py, "
        "which cannot match a prerelease display string ('0.7.0 Beta 1') in the iss and "
        "CHANGELOG, so the live-tree check is only meaningful where that source is present."
    ),
)
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


# -- the standalone apps ------------------------------------------------------
#
# Added 2026-08-25, readying Quill Radio 3.0.0. GATE-VC had only ever looked at
# the main QUILL app, and an audit by hand found three siblings shipping a wrong
# number: Cast stamped VersionInfoVersion 1.0.1.0 onto a 2.0.0 release, Audio
# Studio's full installer said 1.0.0 for 2.2.0, and Inkwell's said 2.2.0 for
# 1.0.0. Every one of them was invisible, because nothing looked.


def _app(root: Path, name: str, version: str) -> Path:
    app = root / "standalone" / name
    (app / "installer").mkdir(parents=True)
    (app / "scripts").mkdir(parents=True)
    (app / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n', encoding="utf-8"
    )
    return app


def test_each_app_is_checked_against_its_own_version_not_quills(tmp_path: Path) -> None:
    """They release independently, so there is no repo-wide number to agree on."""
    _app(tmp_path, "radio", "3.0.0")
    _app(tmp_path, "cast", "2.0.0")

    assert _check_standalone_apps(tmp_path) == []


def test_a_stale_versioninfo_is_caught(tmp_path: Path) -> None:
    """Cast's real bug: Windows would have shown 1.0.1 for a 2.0.0 release, and
    used it to decide whether an upgrade was an upgrade."""
    app = _app(tmp_path, "cast", "2.0.0")
    (app / "installer" / "quill-cast.iss").write_text(
        '#define AppVersion "2.0.0"\nVersionInfoVersion=1.0.1.0\n', encoding="utf-8"
    )

    errors = _check_standalone_apps(tmp_path)

    assert any("VersionInfoVersion" in e for e in errors), errors


def test_a_stale_appversion_is_caught(tmp_path: Path) -> None:
    app = _app(tmp_path, "studio", "2.2.0")
    (app / "installer" / "quill-audio-studio.iss").write_text(
        '#define AppVersion "1.0.0"\n', encoding="utf-8"
    )

    assert any("AppVersion" in e for e in _check_standalone_apps(tmp_path)), "not caught"


def test_the_build_script_version_is_checked_too(tmp_path: Path) -> None:
    """It is the number the installer is actually compiled with."""
    app = _app(tmp_path, "radio", "3.0.0")
    (app / "scripts" / "build_release.ps1").write_text('$version = "2.9.0"\n', encoding="utf-8")

    assert any("build_release.ps1" in e for e in _check_standalone_apps(tmp_path)), "not caught"


def test_two_changelogs_may_not_name_two_different_days(tmp_path: Path) -> None:
    """Quill Radio's real bug: its two changelogs dated 3.0.0 to 15 and 17 August."""
    app = _app(tmp_path, "radio", "3.0.0")
    (app / "docs").mkdir()
    (app / "CHANGELOG.md").write_text("## [3.0.0] - 2026-08-15\n", encoding="utf-8")
    (app / "docs" / "CHANGELOG.md").write_text("## [3.0.0] - 2026-08-17\n", encoding="utf-8")

    errors = _check_standalone_apps(tmp_path)

    assert any("release date" in e for e in errors), errors


def test_prose_after_the_dash_is_not_mistaken_for_a_date(tmp_path: Path) -> None:
    """Quill Weather's heading reads "## 2.2.0 -- first release"; a looser
    pattern read "first" as the day it shipped and reported a disagreement."""
    app = _app(tmp_path, "weather", "2.2.0")
    (app / "docs").mkdir()
    (app / "CHANGELOG.md").write_text("## 2.2.0 -- first release\n", encoding="utf-8")
    (app / "docs" / "CHANGELOG.md").write_text("## [2.2.0] - 2026-08-12\n", encoding="utf-8")

    assert _check_standalone_apps(tmp_path) == []


def test_the_shared_runtime_is_not_an_app(tmp_path: Path) -> None:
    """standalone/runtime's AppVersion is CPython's 3.13, not a release number."""
    runtime = tmp_path / "standalone" / "runtime" / "installer"
    runtime.mkdir(parents=True)
    (runtime / "quillville-runtime.iss").write_text('#define AppVersion "3.13"\n', encoding="utf-8")

    assert _check_standalone_apps(tmp_path) == []
