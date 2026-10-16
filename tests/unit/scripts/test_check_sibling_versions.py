"""GATE-SIBVER: no app may ship a sibling's unreleased version number."""

from __future__ import annotations

import importlib.util
import re
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


# -- the table knows every app that ships (2026-10-15) ---------------------------
#
# SITES lacked Beacon, Social and Audio Studio, so ``build-quill-apps.ps1 all``
# -- which names every app it builds -- stopped at "unknown app(s)" and no app's
# version was checked by any joint build. These hold the table against every
# other list of the apps that ship, so the next app added to one of them fails
# here with its name rather than turning the gate off.


def _site_apps(gate) -> set[str]:
    return {site.app for site in gate.SITES}


def _build_scripts() -> dict[str, Path]:
    """Every standalone installer build script, keyed by its folder (= app key)."""
    return {
        path.parents[1].name: path
        for path in sorted((_REPO / "standalone").glob("*/scripts/build_release.ps1"))
    }


def test_every_app_with_a_build_constant_has_a_row(gate) -> None:
    spec = importlib.util.spec_from_file_location(
        "release_build_number", _REPO / "scripts" / "release_build_number.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    constants = {app: where for app, where in module.BUILD_CONSTANTS.items() if app != "quill"}
    missing = sorted(set(constants) - _site_apps(gate))
    assert not missing, (
        f"GATE-SIBVER has no row for {missing}: add an AppVersionSite to SITES in "
        "scripts/check_sibling_versions.py, or every build that releases it stops the check."
    )
    assert _site_apps(gate) == set(constants), "SITES names an app release_build_number does not"
    for site in gate.SITES:
        assert (site.source, site.build_constant) == constants[site.app], site.app


def test_every_app_build_quill_apps_can_build_has_a_row(gate) -> None:
    script = (_REPO / "build-quill-apps.ps1").read_text(encoding="utf-8-sig")
    ids = set(re.findall(r'Id = "([a-z]+)"', script)) - {"quill"}
    assert ids, "the build-quill-apps.ps1 catalogue was not found"
    missing = sorted(ids - _site_apps(gate))
    assert not missing, (
        f"build-quill-apps.ps1 can release {missing}, which GATE-SIBVER has no row for; "
        "a joint build naming it would stop before checking any version."
    )
    assert gate.unknown_apps_problem(sorted(ids)) == ""


def test_every_installer_build_runs_the_gate_for_its_own_app(gate) -> None:
    scripts = _build_scripts()
    assert scripts, "no standalone build scripts found"
    for app, path in scripts.items():
        assert app in _site_apps(gate), f"{path} builds {app}, which GATE-SIBVER has no row for"
        text = path.read_text(encoding="utf-8-sig")
        assert re.search(
            rf'Assert-QuillSiblingVersions\b[^\n]*-Releasing @\("{app}"\)'
            r"[^\n]*-Skip:\$SkipPublishedCheck",
            text,
        ), f"{path} never runs GATE-SIBVER for {app}"
        assert "[switch]$SkipPublishedCheck" in text, path


def test_tag_prefixes_are_the_ones_releases_are_tagged_with(gate) -> None:
    from quill.core.release_tags import release_tag

    for site in gate.SITES:
        assert release_tag(site.app, "1.0.0") == f"{site.tag_prefix}1.0.0", site.app


def test_an_app_missing_from_the_table_fails_loudly_and_says_so(gate, monkeypatch, capsys) -> None:
    def no_network(**_kwargs):
        raise AssertionError("an unknown app must be refused before releases are read")

    monkeypatch.setattr(gate, "_published_tags", no_network)
    assert gate.main(["--releasing", "radio", "--releasing", "nosuchapp"]) == 2
    err = capsys.readouterr().err
    assert "GATE-SIBVER cannot run" in err
    assert "releases nosuchapp, which" in err
    assert "AppVersionSite" in err
    assert "no app's version was checked" in err


def test_beacon_social_and_studio_are_in_the_gate(gate) -> None:
    assert {"beacon", "social", "studio"} <= _site_apps(gate)
    assert gate.unknown_apps_problem(["beacon", "social", "studio"]) == ""
