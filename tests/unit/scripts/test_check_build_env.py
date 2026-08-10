"""The build-environment preflight for the shared QuillVille Runtime.

``quillville-runtime.spec`` builds with ``collect_all("quill")``, so PyInstaller
bundles whatever is importable in the builder's virtualenv. Two silent failures
came from that -- wxPython drifting below the ``==4.3.1`` pin in ``[ui]``, and
``vosk``/``soundfile``/``hf_xet`` going missing so the runtime shipped without
offline dictation. Both builds exited 0. These cover the check that now runs
before the build so a drift fails loudly instead.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from scripts.check_build_env import _expand, check

_PYPROJECT = Path("pyproject.toml")
_BUILD_RUNTIME = Path("standalone/runtime/build_runtime.ps1")


def _optional() -> dict[str, list[str]]:
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]["optional-dependencies"]


def test_runtime_group_exists_and_only_names_real_extras() -> None:
    """A typo here would silently check nothing."""
    optional = _optional()
    assert "runtime" in optional, "pyproject has no [runtime] group"
    for spec in optional["runtime"]:
        extra = spec.split("[", 1)[1].rstrip("]")
        assert extra in optional, f"[runtime] references unknown extra: {extra}"


def test_expand_follows_extra_references() -> None:
    optional = {
        "runtime": ["quill[ui]", "quill[audio]"],
        "ui": ["wxPython==4.3.1"],
        "audio": ["sound_lib>=0.83"],
    }
    names = sorted(r.name for r in _expand("runtime", optional, set()))
    assert names == ["sound_lib", "wxPython"]


def test_expand_survives_a_reference_cycle() -> None:
    """A self-referential group must not hang the build."""
    optional = {"a": ["quill[b]"], "b": ["quill[a]", "certifi>=2026.1.1"]}
    names = [r.name for r in _expand("a", optional, set())]
    assert names == ["certifi"]


def test_a_missing_package_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scripts.check_build_env._installed", lambda python: {})
    problems = check(["runtime"], None)
    assert problems, "an empty environment must not pass"
    assert any("MISSING" in p for p in problems)


def test_a_version_below_the_pin_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """The exact drift that shipped wxWidgets 3.2.9 instead of 3.3.3."""
    from scripts.check_build_env import _installed

    drifted = {**_installed(None), "wxpython": "4.2.5"}
    monkeypatch.setattr("scripts.check_build_env._installed", lambda python: drifted)
    problems = check(["runtime"], None)
    assert any("wxPython" in p and "4.2.5" in p for p in problems), problems


def test_a_satisfied_environment_reports_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    optional = _optional()
    requirements = _expand("runtime", optional, set())
    satisfying = {}
    for requirement in requirements:
        pinned = [s for s in requirement.specifier if s.operator in ("==", ">=")]
        version = pinned[0].version if pinned else "99.0.0"
        satisfying[requirement.name.lower().replace("_", "-")] = version
    monkeypatch.setattr("scripts.check_build_env._installed", lambda python: satisfying)
    assert check(["runtime"], None) == []


def test_an_unknown_group_is_an_error() -> None:
    with pytest.raises(SystemExit, match="No such dependency group"):
        check(["not-a-real-group"], None)


def test_the_runtime_build_runs_the_check() -> None:
    """The preflight is worthless if the build does not call it."""
    script = _BUILD_RUNTIME.read_text(encoding="utf-8")
    assert "check_build_env.py" in script, "build_runtime.ps1 does not run the preflight"
    assert "--groups runtime" in script, "the preflight is not checking the runtime group"
