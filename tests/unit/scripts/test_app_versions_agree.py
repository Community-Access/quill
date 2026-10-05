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

Since build numbers (2026-10) it compares the build too: the app's build
constant (``_BUILD`` / ``APP_BUILD``) is the installer's fallback ``AppBuild``,
the Windows file version is ``X.Y.Z.B``, and every installer that writes the
version marker writes the build beside it.
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


def _module_build(module: str, constant: str = "_BUILD") -> int:
    return int(_one(rf"^{constant} = (\d+)\b", _read(module), module))


def _assert_inno_build(path: str, version: str, build: int) -> None:
    """The installer's build, file version and marker agree with the app's."""
    text = _read(path)
    assert _one(r'#define AppBuild "([^"]+)"', text, path) == str(build), path
    assert _one(r'#define AppFileVersion "([^"]+)"', text, path) == f"{version}.{build}", path
    assert "VersionInfoVersion={#AppFileVersion}" in text, path
    if 'Key: "version"' in text:
        assert 'Key: "version_build"; String: "{#AppVersion}+{#AppBuild}"' in text, path


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
    _assert_inno_build(
        "standalone/radio/installer/quill-radio.iss", expected, _module_build("quill/apps/radio.py")
    )


def test_cast_says_one_version_everywhere() -> None:
    # Cast keeps its constant in the menu mixin (podcasts.py re-exports it),
    # and ships two shared-runtime installers, both of which write the
    # quill-app-version.ini marker Check for Updates reads (release-channels
    # plan, Phase 0).
    expected = _pyproject_version("cast")
    assert (
        _one(r'^APP_VERSION = "([^"]+)"', _read("quill/apps/podcasts_menu.py"), "podcasts_menu.py")
        == expected
    )
    assert _release_script_version("cast") == expected
    assert _readme_version("cast") == expected
    for iss in ("quill-cast-shared.iss", "quill-cast-lite.iss", "quill-cast.iss"):
        assert _inno_version(f"standalone/cast/installer/{iss}") == expected, iss
    for iss in ("quill-cast-shared.iss", "quill-cast-lite.iss"):
        text = _read(f"standalone/cast/installer/{iss}")
        assert "quill-app-version.ini" in text, f"{iss} does not write the version marker"
    build = _module_build("quill/apps/podcasts_menu.py", "APP_BUILD")
    for iss in ("quill-cast-shared.iss", "quill-cast-lite.iss", "quill-cast.iss"):
        _assert_inno_build(f"standalone/cast/installer/{iss}", expected, build)


def test_quill_lite_says_one_build_everywhere() -> None:
    expected = _one(
        r'^APP_VERSION = "([^"]+)"', _read("quill/core/lite/__init__.py"), "lite/__init__.py"
    )
    assert _release_script_version("quilllite") == expected
    _assert_inno_build(
        "standalone/quilllite/installer/quilllite.iss",
        expected,
        _module_build("quill/core/lite/__init__.py", "APP_BUILD"),
    )


@pytest.mark.parametrize(
    ("app", "module"),
    [
        ("converter", "quill/apps/converter.py"),
        ("weather", "quill/apps/weather.py"),
        ("inkwell", "quill/apps/inkwell.py"),
    ],
)
def test_every_installer_carries_the_apps_build(app: str, module: str) -> None:
    version, build = _module_version(module), _module_build(module)
    for iss in sorted((_ROOT / "standalone" / app / "installer").glob("*.iss")):
        _assert_inno_build(str(iss.relative_to(_ROOT)), version, build)


def test_every_build_script_passes_the_build_to_the_installer() -> None:
    """A script that forgot /dAppBuild ships the fallback build forever."""
    for script in sorted((_ROOT / "standalone").glob("*/scripts/build_release.ps1")):
        text = script.read_text(encoding="utf-8")
        assert "Resolve-QuillReleaseBuild" in text, script
        assert text.count('"/dAppVersion=$version"') == text.count(
            '"/dAppVersion=$version" "/dAppBuild=$build" "/dAppFileVersion=$fileVersion"'
        ), script


def test_studio_says_one_version_everywhere() -> None:
    # Studio's constant was QUILL's own __version__ (1.0.0) while its installer
    # said 2.2.0, so About and Check for Updates described a different program.
    expected = _pyproject_version("studio")
    assert _module_version("quill/apps/studio.py") == expected
    assert _release_script_version("studio") == expected
    build = _module_build("quill/apps/studio.py")
    for iss in ("quill-audio-studio.iss", "quill-audio-studio-lite.iss"):
        path = f"standalone/studio/installer/{iss}"
        assert _inno_version(path) == expected, iss
        _assert_inno_build(path, expected, build)


def test_converter_says_one_version_everywhere() -> None:
    expected = _pyproject_version("converter")
    assert _module_version("quill/apps/converter.py") == expected
    assert _release_script_version("converter") == expected
