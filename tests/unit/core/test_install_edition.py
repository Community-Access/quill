"""An update offers back the edition you are actually running.

Two users reported the same thing a month apart -- "what was downloaded was
the portable version rather than the full installer" (#1100), and "whenever i
update it shows me the portable" (2026-08-16). Two faults sat behind it:

* The updater chose between a release's assets by file extension, so every
  installed listener got whichever ``.exe`` GitHub listed first.
* The "am I installed?" test looked for the literal ``unins000``. Inno numbers
  its uninstallers, so a copy installed over an existing one carries
  ``unins001`` instead -- and read as portable, which is precisely the
  "it shows me the portable" report.

Since 2026-10-11 every app ships exactly two downloads, the installer and the
portable zip. The thin "Lite" installer and the Companion zip are retired, and
the guards at the bottom of this file keep them from coming back.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from quill.core import install_edition as edition

REPO = Path(__file__).resolve().parents[3]

#: An old release, which still carries the two retired assets.
ASSETS = [
    {"name": "Quill-Radio-Companion-3.0.0.zip", "browser_download_url": "u/companion"},
    {"name": "Quill-Radio-Lite-Setup-3.0.0.exe", "browser_download_url": "u/lite"},
    {"name": "Quill-Radio-Portable-3.0.0.zip", "browser_download_url": "u/portable"},
    {"name": "Quill-Radio-Setup-Shared-3.0.0.exe", "browser_download_url": "u/full"},
]


def test_there_are_exactly_two_editions() -> None:
    assert edition.EDITIONS == (edition.PORTABLE, edition.INSTALLER_FULL)
    assert not hasattr(edition, "INSTALLER_LITE")
    assert not hasattr(edition, "COMPANION")


@pytest.mark.parametrize(
    ("edition_name", "expected"),
    [(edition.INSTALLER_FULL, ["u/full"]), (edition.PORTABLE, ["u/portable"])],
)
def test_each_edition_is_offered_its_own_download(edition_name: str, expected: list) -> None:
    found = [
        asset["browser_download_url"]
        for asset in ASSETS
        if edition.matches_asset(edition_name, asset["name"])
    ]
    assert found == expected


def test_the_retired_assets_match_no_edition() -> None:
    """The thin installer and the Companion zip of an old release are never
    offered, so going back to that release cannot hand one out."""
    for name in ("Quill-Radio-Companion-3.0.0.zip", "Quill-Radio-Lite-Setup-3.0.0.exe"):
        assert not any(edition.matches_asset(e, name) for e in edition.EDITIONS), name


def test_an_unknown_edition_matches_nothing() -> None:
    for asset in ASSETS:
        assert not edition.matches_asset("installer-lite", asset["name"])
        assert not edition.matches_asset("companion", asset["name"])


def test_a_marker_written_by_the_installer_is_believed(tmp_path: Path) -> None:
    (tmp_path / edition.MARKER_NAME).write_text(edition.INSTALLER_FULL, encoding="utf-8")
    # Even with folder evidence that would otherwise say otherwise: the thing
    # that installed the app knows which installer it was.
    (tmp_path / "data").mkdir()
    assert edition.detect(tmp_path) == edition.INSTALLER_FULL


@pytest.mark.parametrize(
    ("old_marker", "expected"),
    [("installer-lite", edition.INSTALLER_FULL), ("companion", edition.PORTABLE)],
)
def test_a_marker_from_a_retired_edition_maps_to_its_replacement(
    tmp_path: Path, old_marker: str, expected: str
) -> None:
    """A copy installed from a retired download updates to the nearest one
    that still ships, rather than to nothing."""
    (tmp_path / edition.MARKER_NAME).write_text(old_marker, encoding="utf-8")
    assert edition.detect(tmp_path) == expected


def test_a_junk_marker_falls_back_to_the_evidence(tmp_path: Path) -> None:
    (tmp_path / edition.MARKER_NAME).write_text("something-else", encoding="utf-8")
    (tmp_path / "data").mkdir()
    assert edition.detect(tmp_path) == edition.PORTABLE


@pytest.mark.parametrize("uninstaller", ["unins000.exe", "unins001.exe", "unins002.dat"])
def test_any_numbered_uninstaller_means_the_installer(tmp_path: Path, uninstaller: str) -> None:
    """The 'it shows me the portable' report: Inno's second uninstaller is
    unins001, and the old check only knew unins000."""
    (tmp_path / "data").mkdir()  # an installed copy may keep data beside it
    (tmp_path / uninstaller).write_text("x", encoding="utf-8")
    assert edition.detect(tmp_path) == edition.INSTALLER_FULL


def test_a_real_portable_bundle_is_still_portable(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    assert edition.detect(tmp_path) == edition.PORTABLE


def test_a_folder_with_no_data_and_no_uninstaller_is_the_installer(tmp_path: Path) -> None:
    """An installed app's QUILL_APP_ROOT can be the shared runtime's folder,
    which has neither. That used to read as a Companion copy; it is installed."""
    assert edition.detect(tmp_path) == edition.INSTALLER_FULL


def test_running_portable_agrees_about_numbered_uninstallers(tmp_path, monkeypatch) -> None:
    from quill.core import storage_mode, updates

    monkeypatch.setattr(storage_mode, "portable_root_dir", lambda: tmp_path / "data")
    (tmp_path / "data").mkdir()
    assert updates.running_portable() is True
    (tmp_path / "unins001.exe").write_text("x", encoding="utf-8")
    assert updates.running_portable() is False


def test_the_installers_ship_their_edition_marker() -> None:
    """The wiring half: each installer that stages a marker stages the
    installer one, and the marker file says so."""
    for app, name in (
        ("radio", "quill-radio.iss"),
        ("converter", "quill-converter.iss"),
        ("cast", "quill-cast-shared.iss"),
        ("quilllite", "quilllite.iss"),
        ("beacon", "quill-beacon-shared.iss"),
        ("social", "quill-social-shared.iss"),
    ):
        installer_dir = REPO / "standalone" / app / "installer"
        source = (installer_dir / name).read_text(encoding="utf-8")
        assert f"edition-{edition.INSTALLER_FULL}.txt" in source, name
        assert f'DestName: "{edition.MARKER_NAME}"' in source, name
        marker = installer_dir / f"edition-{edition.INSTALLER_FULL}.txt"
        assert marker.read_text(encoding="utf-8").strip() == edition.INSTALLER_FULL


def test_quill_radio_ships_two_downloads_not_four() -> None:
    """Radio 3.0.0 publishes an installer and a portable zip, like QUILL Lite.

    The thin installer and the Companion zip were retired for the same reasons
    QUILL Lite retired them (standalone/radio/scripts/build_release.ps1). A
    thin .iss left behind is one somebody compiles by hand and publishes.
    """
    installer_dir = REPO / "standalone" / "radio" / "installer"
    assert not (installer_dir / "quill-radio-lite.iss").exists()
    assert not (installer_dir / "edition-installer-lite.txt").exists()
    script = (REPO / "standalone" / "radio" / "scripts" / "build_release.ps1").read_text(
        encoding="utf-8"
    )
    assert "--no-runtime" not in script
    assert "quill-radio-lite.iss" not in script


# -- the family-wide guard (2026-10-11) -----------------------------------------
#
# Every app ships the portable build and the installer, nothing else. These keep
# the thin installer and the runtime-less Companion build from creeping back.
# quilllite.iss is QUILL Lite's own (full) installer: the product is named Lite.


def test_no_app_ships_a_thin_installer() -> None:
    thin = sorted(
        p.relative_to(REPO).as_posix()
        for p in (REPO / "standalone").glob("*/installer/*-lite.iss")
        if p.name != "quilllite.iss"
    )
    assert thin == [], f"retired thin installers came back: {thin}"
    markers = sorted(
        p.relative_to(REPO).as_posix()
        for p in (REPO / "standalone").glob("*/installer/edition-installer-lite.txt")
    )
    assert markers == [], f"retired thin-installer markers came back: {markers}"


#: ``--no-runtime`` exactly; ``--no-runtime-download`` is the portable
#: launcher's switch and stays.
_NO_RUNTIME_FLAG = re.compile(r"--no-runtime(?![-\w])")


def test_no_build_script_offers_the_runtime_less_companion_build() -> None:
    scripts = [
        *(REPO / "standalone").glob("*/scripts/*.py"),
        *(REPO / "standalone").glob("*/scripts/*.ps1"),
        *(REPO / "scripts").glob("*.py"),
        *(REPO / "scripts").glob("*.ps1"),
        REPO / "build.ps1",
    ]
    offenders = sorted(
        p.relative_to(REPO).as_posix()
        for p in scripts
        if p.is_file() and _NO_RUNTIME_FLAG.search(p.read_text(encoding="utf-8", errors="replace"))
    )
    assert offenders == [], f"a --no-runtime Companion path came back: {offenders}"


CONVERTER_ASSETS = [
    {"name": "Quill-Converter-Portable-1.0.0.zip", "browser_download_url": "u/portable"},
    {"name": "Quill-Converter-Setup-Shared-1.0.0.exe", "browser_download_url": "u/full"},
]


@pytest.mark.parametrize(
    ("edition_name", "expected"),
    [(edition.INSTALLER_FULL, "u/full"), (edition.PORTABLE, "u/portable")],
)
def test_quill_converter_two_downloads_are_told_apart(edition_name: str, expected: str) -> None:
    """Converter publishes Radio's two downloads (2026-09-26): each edition finds its own."""
    found = [
        asset["browser_download_url"]
        for asset in CONVERTER_ASSETS
        if edition.matches_asset(edition_name, asset["name"])
    ]
    assert found == [expected]


#: QUILL Lite is the case the word-matching above cannot survive on its own: the
#: product NAME contains "lite", so without the prefix its installer reads as a
#: retired thin one and ``INSTALLER_FULL`` matches nothing it ever publishes.
LITE_ASSETS = [
    {"name": "QuillLite-Companion-1.0.0.zip", "browser_download_url": "u/companion"},
    {"name": "QuillLite-Lite-Setup-1.0.0.exe", "browser_download_url": "u/lite"},
    {"name": "QuillLite-Portable-1.0.0.zip", "browser_download_url": "u/portable"},
    {"name": "QuillLite-Setup-Shared-1.0.0.exe", "browser_download_url": "u/full"},
]


@pytest.mark.parametrize(
    ("edition_name", "expected"),
    [(edition.INSTALLER_FULL, "u/full"), (edition.PORTABLE, "u/portable")],
)
def test_an_app_whose_name_contains_lite(edition_name: str, expected: str) -> None:
    picked = [
        asset["browser_download_url"]
        for asset in LITE_ASSETS
        if edition.matches_asset(edition_name, asset["name"], app_prefix="QuillLite")
    ]
    assert picked == [expected]


def test_without_the_prefix_quilllite_cannot_be_told_apart() -> None:
    """The bug the prefix exists to stop, pinned so it cannot come back
    silently: without it, no QUILL Lite .exe reads as the installer."""
    assert not [
        asset["name"]
        for asset in LITE_ASSETS
        if edition.matches_asset(edition.INSTALLER_FULL, asset["name"])
    ]


def test_a_prefix_that_does_not_match_is_simply_ignored() -> None:
    assert edition.matches_asset(
        edition.PORTABLE, "Quill-Radio-Portable-3.0.0.zip", app_prefix="QuillLite"
    )
