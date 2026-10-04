"""GATE-SIBVER: no app may ship a sibling's unreleased version number."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def gate():
    spec = importlib.util.spec_from_file_location(
        "check_sibling_versions", _REPO / "scripts" / "check_sibling_versions.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    import sys

    sys.modules[spec.name] = module  # dataclasses resolve their module by name
    spec.loader.exec_module(module)
    return module


def test_versions_parse_and_prereleases_sort_below_the_number(gate) -> None:
    assert gate.parse_version("3.1.0") == gate.parse_version("v3.1.0")
    assert gate.parse_version("3.3.0-beta.1") < gate.parse_version("3.3.0-beta.2")
    assert gate.parse_version("3.3.0-dev.20261003.2") < gate.parse_version("3.3.0-beta.1")
    assert gate.parse_version("3.1.0") > gate.parse_version("3.0.4")
    assert gate.parse_version("1.1.0") < gate.parse_version("1.1.1")
    assert gate.parse_version("0.9.0-beta.2") < gate.parse_version("0.9.0")
    assert gate.parse_version("nonsense") == ()


def test_newest_published_picks_by_version_not_by_string(gate) -> None:
    tags = ["quill-lite-v1.0.0", "quill-lite-v1.0.1", "quill-lite-v1.1.0", "quill-radio-v3.0.4"]
    assert gate.newest_published(tags, "quill-lite-v") == "1.1.0"
    assert gate.newest_published(tags, "quill-radio-v") == "3.0.4"
    assert gate.newest_published(tags, "quill-weather-v") is None


def test_the_2026_09_29_failure_is_caught(gate) -> None:
    """Lite said 1.1.0 in source while 1.0.1 was the release, and a Radio build
    was about to freeze it into every Radio user's runtime."""
    problems = gate.disagreements(
        {"radio": "3.0.4", "quilllite": "1.1.0"},
        {"radio": "3.0.3", "quilllite": "1.0.1"},
        releasing={"radio"},
    )
    assert len(problems) == 1
    assert problems[0].startswith("quilllite: source says 1.1.0")
    assert "--releasing quilllite" in problems[0]


def test_releasing_the_app_that_is_ahead_is_the_normal_case(gate) -> None:
    assert (
        gate.disagreements(
            {"radio": "3.0.4", "quilllite": "1.1.1"},
            {"radio": "3.0.4", "quilllite": "1.1.0"},
            releasing={"quilllite"},
        )
        == []
    )


def test_a_checkout_behind_the_release_fails_and_so_does_a_release_without_a_bump(gate) -> None:
    behind = gate.disagreements({"radio": "3.0.3"}, {"radio": "3.0.4"}, releasing=set())
    assert behind and "already published" in behind[0]
    no_bump = gate.disagreements({"radio": "3.0.4"}, {"radio": "3.0.4"}, releasing={"radio"})
    assert no_bump and "Bump the version in the release commit" in no_bump[0]


def test_an_app_never_released_is_skipped(gate) -> None:
    assert gate.disagreements({"weather": "2.2.0"}, {"weather": None}, releasing=set()) == []


def test_cast_is_in_the_gate(gate) -> None:
    sites = {site.app: site for site in gate.SITES}
    assert sites["cast"].tag_prefix == "quill-cast-v"
    assert sites["cast"].source == "quill/apps/podcasts_menu.py"


def test_every_site_names_a_real_constant(gate) -> None:
    for site in gate.SITES:
        version = gate.source_version(site)
        assert gate.parse_version(version), (site.app, version)
