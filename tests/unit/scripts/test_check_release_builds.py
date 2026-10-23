"""check_release_builds.py: every app in a joint release checked against its
published builds in one pass, from the build its source declares."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def _module():
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    return importlib.import_module("check_release_builds")


def test_each_app_is_checked_with_the_build_its_source_declares(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    seen: list[list[str]] = []

    def fake_run(argv, **_kw):
        seen.append(argv)
        refused = "radio" in argv
        return SimpleNamespace(
            returncode=1 if refused else 0,
            stdout="" if refused else "5 1.2.0.5\n",
            stderr="Build number: radio 3.2.0 build 4 is already published.\n" if refused else "",
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(
        module.check_sibling_versions,
        "source_version",
        lambda site: {"quilllite": "1.2.0+5", "radio": "3.2.0+4"}[site.app],
    )
    problems = module.check(["quilllite", "radio"])
    assert [argv[argv.index("--build") + 1] for argv in seen] == ["5", "4"]
    assert problems == [
        "radio 3.2.0 build 4: Build number: radio 3.2.0 build 4 is already published."
    ]


def test_an_unknown_app_is_named_rather_than_skipped() -> None:
    assert _module().check(["nonesuch"]) == ["nonesuch: no version site is known for it"]
