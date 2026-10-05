"""Build numbers: the same release number shipped more than once (2026-10).

A rebuild of Quill Radio 3.2.0 with a fix is 3.2.0 build 2. It must be offered
to everyone on build 1, said where a person needs it ("3.2.0 (build 2)"),
tagged so installed copies can read it, and recorded by the installer beside
the version. GATE-VERSORT (test_release_versioning.py) holds the order; this
file holds everything that carries a build from the order to a person.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

from quill.core import app_version
from quill.core.release_tags import next_build, parse_release_tag, release_tag
from quill.core.updates import _app_version_from_tag, is_newer_version, select_latest

_REPO = Path(__file__).resolve().parents[3]


def _script(name: str):
    spec = importlib.util.spec_from_file_location(name, _REPO / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# -- tags --------------------------------------------------------------------------


def test_a_build_is_tagged_the_way_installed_copies_read() -> None:
    assert release_tag("radio", "3.2.0+2") == "quill-radio-v3.2.0-build.2"
    assert release_tag("quilllite", "1.2.0+1") == "quill-lite-v1.2.0-build.1"
    assert release_tag("quill", "1.1.0-beta.1+3") == "v1.1.0-beta.1.build.3"
    assert release_tag("radio", "3.2.0+g1a2b3c4") == "quill-radio-v3.2.0"
    assert release_tag("radio", "3.2.0") == "quill-radio-v3.2.0"  # build-less tags stay


def test_both_tag_spellings_read_back() -> None:
    assert parse_release_tag("quill-radio-v3.2.0-build.2") == ("radio", "3.2.0-build.2")
    assert parse_release_tag("quill-radio-v3.2.0+2") == ("radio", "3.2.0+2")
    assert parse_release_tag("v1.0.0-build.1") == ("quill", "1.0.0-build.1")
    assert _app_version_from_tag("quill-radio-v3.2.0-build.12") == "3.2.0-build.12"
    assert _app_version_from_tag("quill-cast-v2.0.0+3") == "2.0.0+3"


def test_next_build_counts_this_number_only() -> None:
    tags = [
        "quill-radio-v3.1.1",
        "quill-radio-v3.2.0-build.1",
        "quill-radio-v3.2.0+3",
        "quill-lite-v3.2.0-build.9",
        "v3.2.0-build.7",
    ]
    assert next_build(tags, "radio", "3.2.0") == 4
    assert next_build(tags, "radio", "3.1.1") == 1  # a build-less release is build 0
    assert next_build(tags, "radio", "3.3.0") == 1
    assert next_build(tags, "quilllite", "3.2.0") == 10
    assert next_build(tags, "quill", "3.2.0+1") == 8


# -- update offers -------------------------------------------------------------------


def test_a_newer_build_of_the_same_version_is_offered_and_the_same_build_is_not() -> None:
    assert is_newer_version("3.2.0+1", "3.2.0-build.2")
    assert not is_newer_version("3.2.0+2", "3.2.0-build.2")
    assert not is_newer_version("3.2.0+2", "3.2.0-build.1")
    # A copy installed before build numbers (marker says 3.2.0) takes build 1.
    assert is_newer_version("3.2.0", "3.2.0-build.1")


def test_the_newest_build_is_the_offer_and_up_to_date_names_the_build() -> None:
    from quill.core.updater import check
    from quill.core.updater.channels import ChannelState

    releases = [
        SimpleNamespace(version="3.2.0-build.1", prerelease=False, has_platform_asset=True),
        SimpleNamespace(version="3.2.0-build.2", prerelease=False, has_platform_asset=True),
    ]
    assert select_latest(releases).version == "3.2.0-build.2"  # type: ignore[arg-type,union-attr]
    up_to_date = check.up_to_date_text("3.2.0+2", ChannelState())
    assert up_to_date.startswith("You are up to date (3.2.0 (build 2)).")


# -- the installer's marker -----------------------------------------------------------


def _marker(root: Path, text: str) -> None:
    (root / app_version.MARKER_NAME).write_text(text, encoding="utf-8")


def test_the_marker_carries_the_build_beside_the_version(tmp_path: Path) -> None:
    _marker(tmp_path, "[app]\nversion=3.2.0\nversion_build=3.2.0+2\n")
    assert app_version.read_marker(tmp_path) == "3.2.0+2"
    assert app_version.installed_version("3.2.0", tmp_path, build=1) == "3.2.0+2"
    assert app_version.describe_version("3.2.0", tmp_path, build=2) == "3.2.0 (build 2)"
    assert app_version.describe_version("3.2.0", tmp_path, build=1) == (
        "3.2.0 (build 2) (running shared runtime code 3.2.0 (build 1))"
    )


def test_a_stale_build_from_a_newer_install_is_ignored(tmp_path: Path) -> None:
    """Inno never deletes a key an older installer does not write."""
    _marker(tmp_path, "[app]\nversion=3.1.1\nversion_build=3.2.0+2\n")
    assert app_version.read_marker(tmp_path) == "3.1.1"


def test_a_marker_from_before_builds_is_build_zero_not_the_codes(tmp_path: Path) -> None:
    _marker(tmp_path, "[app]\nversion=1.0.0\n")
    assert app_version.installed_version("1.0.0", tmp_path, build=1) == "1.0.0"
    # Same release, older marker: not a mismatch worth a sentence.
    assert app_version.describe_version("1.0.0", tmp_path, build=1) == "1.0.0"


def test_no_marker_means_the_code_version_and_build(tmp_path: Path) -> None:
    assert app_version.installed_version("3.2.0", tmp_path, build=1) == "3.2.0+1"
    assert app_version.describe_version("3.2.0", tmp_path, build=1) == "3.2.0 (build 1)"
    assert app_version.full_version("3.2.0", 0) == "3.2.0"


def test_the_pending_releases_are_build_one() -> None:
    from quill import __build__
    from quill.apps import podcasts_menu, radio
    from quill.core import lite

    assert (radio._VERSION, radio._BUILD) == ("3.2.0", 1)
    assert (podcasts_menu.APP_VERSION, podcasts_menu.APP_BUILD) == ("2.0.0", 1)
    assert (lite.APP_VERSION, lite.APP_BUILD) == ("1.2.0", 1)
    assert __build__ == 1


# -- what people see ------------------------------------------------------------------


def test_the_update_notice_says_both_builds() -> None:
    from quill.ui import update_notice

    header = update_notice.update_header("Quill Radio", "3.2.0+1", "3.2.0-build.2")
    assert "Update available: Quill Radio 3.2.0 (build 2)" in header
    assert "Current version: 3.2.0 (build 1)" in header


def test_update_history_says_the_build() -> None:
    from quill.core.updater.history import UpdateEvent
    from quill.ui.updates.update_history_dialog import details_text

    event = UpdateEvent(
        at="2026-10-04T12:00:00Z",
        app="radio",
        kind="installed",
        from_version="3.2.0+1",
        to_version="3.2.0+2",
    )
    text = details_text(event)
    assert "From version: 3.2.0 (build 1)" in text
    assert "To version: 3.2.0 (build 2)" in text


def test_quill_reports_its_build() -> None:
    from quill import __build__, build_info

    assert build_info.release_build() >= 0
    assert build_info.feed_version().endswith(f"+{__build__}") or build_info.release_build() == 0


def test_release_notes_find_the_release_for_any_build() -> None:
    from quill.core.release_notes import extract_version_section

    changelog = "# Changelog\n\n## 1.1.0 Beta 1\n\n- one\n\n## 1.0.0\n\n- zero\n"
    assert extract_version_section(changelog, "v1.0.0-build.2") == "- zero"
    assert extract_version_section(changelog, "1.0.0+3") == "- zero"


def test_the_health_check_waits_for_the_exact_build(tmp_path: Path) -> None:
    from quill.core.updater.apply import started_marker

    assert started_marker(tmp_path, "3.2.0+2") != started_marker(tmp_path, "3.2.0+1")
    assert started_marker(tmp_path, "3.2.0+2") == started_marker(tmp_path, "3.2.0-build.2")
    assert started_marker(tmp_path, "1.1.0 Beta 1") == started_marker(tmp_path, "1.1.0-beta.1")


# -- downloads --------------------------------------------------------------------------


class _Response:
    def __init__(self, body: bytes, status: int) -> None:
        self._body, self.status = body, status

    def read(self, size: int = -1) -> bytes:
        chunk, self._body = self._body[:size], self._body[size:]
        return chunk

    def close(self) -> None:
        return None


def test_half_of_one_build_is_never_finished_with_another(tmp_path: Path) -> None:
    """Every build of a version ships under one file name."""
    from quill.core.updater.download import download_verified

    build_one, build_two = b"1" * 80_000, b"2" * 80_000
    dest = tmp_path / "Quill-Radio-Setup-Shared-3.2.0.exe"
    partial = tmp_path / (dest.name + ".partial")
    partial.write_bytes(build_one[:30_000])
    (tmp_path / (dest.name + ".partial.sha256")).write_text(
        hashlib.sha256(build_one).hexdigest(), encoding="ascii"
    )
    starts: list[int] = []

    def opener(_url: str, start: int) -> _Response:
        starts.append(start)
        return _Response(build_two[start:], 206 if start else 200)

    got = download_verified(
        "u",
        dest,
        sha256=hashlib.sha256(build_two).hexdigest(),
        size=len(build_two),
        open_range=opener,
        free_space=lambda _p: 10**12,
    )
    assert got.read_bytes() == build_two
    assert starts == [0]
    assert not (tmp_path / (dest.name + ".partial.sha256")).exists()


# -- installers and file versions -------------------------------------------------------


def test_quills_installer_file_version_carries_the_build() -> None:
    dist = _script("build_windows_distribution")
    assert dist._iss_numeric_version("1.0.0", "stable", 0, 2) == "1.0.0.2"
    assert dist._iss_numeric_version("1.1.0", "beta", 1, 3) == "1.1.0.3"
    assert dist._iss_numeric_version("1.1.0", "beta", 1) == "1.1.0.1"  # no build: as before
    assert dist._release_build_from_init_py(_REPO) >= 1


def test_the_launcher_file_version_carries_the_build() -> None:
    launcher = _script("build_native_launcher")
    assert launcher.product_file_version(launcher.PRODUCTS["radio"]) == "3.2.0.1"
    for product in launcher.PRODUCTS.values():
        parts = launcher.product_file_version(product).split(".")
        assert len(parts) == 4 and all(p.isdigit() for p in parts)


def test_gate_vc_reads_the_file_version_fallback(tmp_path: Path) -> None:
    from quill.tools.check_version_consistency import _iss_version_errors

    iss = tmp_path / "x.iss"
    iss.write_text(
        '#define AppVersion "2.0.0"\n#define AppFileVersion "1.0.1.1"\n'
        "VersionInfoVersion={#AppFileVersion}\n",
        encoding="utf-8",
    )
    assert any("VersionInfoVersion" in e for e in _iss_version_errors(iss, "2.0.0", "x"))
    iss.write_text(
        '#define AppVersion "2.0.0"\n#define AppFileVersion "2.0.0.3"\n'
        "VersionInfoVersion={#AppFileVersion}\n",
        encoding="utf-8",
    )
    assert _iss_version_errors(iss, "2.0.0", "x") == []


# -- the release build number script -----------------------------------------------------


def test_the_release_script_takes_the_next_build_and_checks_the_source() -> None:
    script = _script("release_build_number")
    assert script.source_build("radio") == 1  # the pending 3.2.0 is build 1
    # Nothing published for 3.2.0 yet: build 1, which is what source says.
    assert script.resolve("radio", "3.2.0", tags=lambda: ["quill-radio-v3.1.1"]) == (
        1,
        "3.2.0.1",
        "",
    )
    # Build 1 is out: the next is build 2, and source must say so first.
    tags = ["quill-radio-v3.1.1", "quill-radio-v3.2.0-build.1"]
    build, file_version, problem = script.resolve("radio", "3.2.0", tags=lambda: tags)
    assert build == 2 and file_version == "" and "_BUILD = 2" in problem


def test_the_release_script_refuses_a_published_build() -> None:
    script = _script("release_build_number")
    tags = ["quill-radio-v3.2.0-build.1"]
    build, file_version, problem = script.resolve("radio", "3.2.0", build=1, tags=lambda: tags)
    assert build == 1 and not file_version and "already published" in problem


def test_the_release_script_offline_and_dev_paths() -> None:
    script = _script("release_build_number")

    def offline() -> list[str]:
        raise OSError("no network")

    assert script.resolve("radio", "3.3.0-dev.20261004.1", dev=True, tags=offline) == (
        0,
        "3.3.0.0",
        "",
    )
    build, _fv, problem = script.resolve("radio", "3.2.0", tags=offline)
    assert build == 0 and "does not guess" in problem
    build, file_version, problem = script.resolve("radio", "3.2.0", offline_ok=True, tags=offline)
    assert problem == "" and file_version == f"3.2.0.{build}"


def test_every_app_has_a_build_constant() -> None:
    script = _script("release_build_number")
    for app in script.BUILD_CONSTANTS:
        assert script.source_build(app) >= 1, app


# -- GATE-SIBVER with builds ------------------------------------------------------------


def test_sibver_compares_builds_only_where_both_sides_carry_one() -> None:
    gate = _script("check_sibling_versions")
    # A release tagged before build numbers says nothing about builds.
    assert gate.disagreements({"radio": "3.0.4+1"}, {"radio": "3.0.4"}, set()) == []
    # A sibling carrying a build nobody can download.
    ahead = gate.disagreements({"radio": "3.2.0+2"}, {"radio": "3.2.0-build.1"}, set())
    assert ahead and "nobody can download" in ahead[0]
    # Releasing a rebuild without bumping the build.
    same = gate.disagreements({"radio": "3.2.0+1"}, {"radio": "3.2.0-build.1"}, {"radio"})
    assert same and "its build number" in same[0]
    # Releasing the rebuild with the build bumped.
    assert gate.disagreements({"radio": "3.2.0+2"}, {"radio": "3.2.0-build.1"}, {"radio"}) == []
    # A checkout behind the published build.
    behind = gate.disagreements({"radio": "3.2.0+1"}, {"radio": "3.2.0-build.2"}, set())
    assert behind and "behind" in behind[0]


def test_sibver_reads_the_build_constants() -> None:
    gate = _script("check_sibling_versions")
    for site in gate.SITES:
        assert site.build_constant, site.app
        assert "+" in gate.source_version(site), site.app
    assert (
        gate.newest_published(
            ["quill-radio-v3.2.0-build.1", "quill-radio-v3.2.0-build.2", "quill-radio-v3.1.1"],
            "quill-radio-v",
        )
        == "3.2.0-build.2"
    )
