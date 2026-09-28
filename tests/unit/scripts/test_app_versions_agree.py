"""Every place an app's version is written says the same thing (GATE-APPVER).

Quill Radio 3.0.4 shipped on 2026-09-28 with the installer, the zip, the
README and every document saying 3.0.4 -- and Help > About saying 3.0.3,
because the app's own constant in ``quill/apps/radio.py`` was not bumped.
That constant is also what Check for Updates compares against the release
tag, so a 3.0.4 install would have offered itself 3.0.4 as an update. The
build had to be redone and both releases' assets replaced.

This gate reads each source of truth as text (no imports, no wx) and fails
on the first disagreement, naming the file. Add an app here the day it gets
an installer.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (_ROOT / path).read_text(encoding="utf-8", errors="replace")


def _one(pattern: str, text: str, where: str) -> str:
    found = re.search(pattern, text, re.MULTILINE)
    assert found, f"{where}: no match for {pattern!r}"
    return found.group(1)


def _module_version(module: str) -> str:
    return _one(r'^_VERSION = "([^"]+)"', _read(module), module)


def _pyproject_version(app: str) -> str:
    return _one(r'^version = "([^"]+)"', _read(f"standalone/{app}/pyproject.toml"), app)


def _release_script_version(app: str) -> str:
    return _one(
        r'^\$version = "([^"]+)"', _read(f"standalone/{app}/scripts/build_release.ps1"), app
    )


def _inno_version(path: str) -> str:
    return _one(r'#define AppVersion "([^"]+)"', _read(path), path)


def _readme_version(app: str) -> str:
    return _one(r"^Version ([0-9][^,\s]*), released", _read(f"standalone/{app}/README.md"), app)


@pytest.mark.parametrize(
    ("app", "module"),
    [
        ("radio", "quill/apps/radio.py"),
        ("converter", "quill/apps/converter.py"),
        ("weather", "quill/apps/weather.py"),
        ("inkwell", "quill/apps/inkwell.py"),
    ],
)
def test_the_app_constant_matches_its_package(app: str, module: str) -> None:
    assert _module_version(module) == _pyproject_version(app), (
        f"{module} _VERSION and standalone/{app}/pyproject.toml disagree"
    )


def test_radio_says_one_version_everywhere() -> None:
    expected = _pyproject_version("radio")
    assert _module_version("quill/apps/radio.py") == expected
    assert _release_script_version("radio") == expected
    assert _inno_version("standalone/radio/installer/quill-radio.iss") == expected
    assert _readme_version("radio") == expected
    iss = _read("standalone/radio/installer/quill-radio.iss")
    assert f"VersionInfoVersion={expected}.0" in iss


def test_converter_says_one_version_everywhere() -> None:
    expected = _pyproject_version("converter")
    assert _module_version("quill/apps/converter.py") == expected
    assert _release_script_version("converter") == expected
