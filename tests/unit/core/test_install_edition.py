"""An update offers back the edition you are actually running.

Two users reported the same thing a month apart -- "what was downloaded was
the portable version rather than the full installer" (#1100), and "whenever i
update it shows me the portable" (2026-08-16). #1100 was closed after fixing
the portable-versus-installed axis, and the complaint outlived the fix,
because the real fault was bigger than that axis:

* A release publishes FOUR assets and the updater chose between them by file
  extension. Windows prefers ``.exe``, so every installed listener got
  whichever ``.exe`` GitHub listed first -- the 2.6 MB thin installer, even
  for someone running the full 240 MB edition -- and a Companion listener was
  handed an ``.exe`` that cannot install their zip-based copy at all.
* The "am I installed?" test looked for the literal ``unins000``. Inno numbers
  its uninstallers, so a copy installed over an existing one carries
  ``unins001`` instead -- and read as portable, which is precisely the
  "it shows me the portable" report.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import install_edition as edition

ASSETS = [
    {"name": "Quill-Radio-Companion-3.0.0.zip", "browser_download_url": "u/companion"},
    {"name": "Quill-Radio-Lite-Setup-3.0.0.exe", "browser_download_url": "u/lite"},
    {"name": "Quill-Radio-Portable-3.0.0.zip", "browser_download_url": "u/portable"},
    {"name": "Quill-Radio-Setup-Shared-3.0.0.exe", "browser_download_url": "u/full"},
]


def _pick(edition_name: str) -> str:
    for asset in ASSETS:
        if edition.matches_asset(edition_name, asset["name"]):
            return asset["browser_download_url"]
    return ""


@pytest.mark.parametrize(
    ("edition_name", "expected"),
    [
        (edition.INSTALLER_FULL, "u/full"),
        (edition.INSTALLER_LITE, "u/lite"),
        (edition.PORTABLE, "u/portable"),
        (edition.COMPANION, "u/companion"),
    ],
)
def test_each_edition_is_offered_its_own_download(edition_name: str, expected: str) -> None:
    assert _pick(edition_name) == expected


def test_the_four_assets_are_never_confused_with_each_other() -> None:
    """Each asset matches exactly one edition -- the property that makes
    'first .exe wins' impossible to reintroduce."""
    for asset in ASSETS:
        matched = [
            name
            for name in (
                edition.INSTALLER_FULL,
                edition.INSTALLER_LITE,
                edition.PORTABLE,
                edition.COMPANION,
            )
            if edition.matches_asset(name, asset["name"])
        ]
        assert len(matched) == 1, f"{asset['name']} matched {matched}"


def test_a_marker_written_by_the_installer_is_believed(tmp_path: Path) -> None:
    (tmp_path / edition.MARKER_NAME).write_text(edition.INSTALLER_FULL, encoding="utf-8")
    # Even with folder evidence that would otherwise say otherwise: the thing
    # that installed the app knows which installer it was.
    (tmp_path / "unins000.exe").write_text("x", encoding="utf-8")
    assert edition.detect(tmp_path) == edition.INSTALLER_FULL


def test_a_junk_marker_falls_back_to_the_evidence(tmp_path: Path) -> None:
    (tmp_path / edition.MARKER_NAME).write_text("something-else", encoding="utf-8")
    (tmp_path / "data").mkdir()
    assert edition.detect(tmp_path) == edition.PORTABLE


@pytest.mark.parametrize("uninstaller", ["unins000.exe", "unins001.exe", "unins002.dat"])
def test_any_numbered_uninstaller_means_installed_not_portable(
    tmp_path: Path, uninstaller: str
) -> None:
    """The 'it shows me the portable' report: Inno's second uninstaller is
    unins001, and the old check only knew unins000."""
    (tmp_path / "data").mkdir()  # an installed copy may keep data beside it
    (tmp_path / uninstaller).write_text("x", encoding="utf-8")
    assert edition.detect(tmp_path) != edition.PORTABLE


def test_a_real_portable_bundle_is_still_portable(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    assert edition.detect(tmp_path) == edition.PORTABLE


def test_an_app_only_bundle_is_the_companion(tmp_path: Path) -> None:
    assert edition.detect(tmp_path) == edition.COMPANION


def test_running_portable_agrees_about_numbered_uninstallers(tmp_path, monkeypatch) -> None:
    from quill.core import storage_mode, updates

    monkeypatch.setattr(storage_mode, "portable_root_dir", lambda: tmp_path / "data")
    (tmp_path / "data").mkdir()
    assert updates.running_portable() is True
    (tmp_path / "unins001.exe").write_text("x", encoding="utf-8")
    assert updates.running_portable() is False


def test_the_installers_ship_their_edition_marker() -> None:
    """The wiring half: each installer stages a marker the updater can read."""
    repo = Path(__file__).resolve().parents[3]
    for name, expected in (
        ("quill-radio.iss", edition.INSTALLER_FULL),
        ("quill-radio-lite.iss", edition.INSTALLER_LITE),
    ):
        source = (repo / "standalone" / "radio" / "installer" / name).read_text(encoding="utf-8")
        assert f"edition-{expected}.txt" in source, name
        assert f'DestName: "{edition.MARKER_NAME}"' in source, name
        marker = repo / "standalone" / "radio" / "installer" / f"edition-{expected}.txt"
        assert marker.read_text(encoding="utf-8").strip() == expected


def test_no_thin_installer_looks_for_the_runtime_in_a_folder_that_never_exists() -> None:
    """The thin installer's whole promise is "nothing large to fetch if you
    already have the runtime". It looked under Runtime\\3.13\\ while the
    runtime installs to Runtime\\, so the check was always false and it
    re-downloaded 230 MB every single time."""
    repo = Path(__file__).resolve().parents[3]
    for path in repo.glob("standalone/*/installer/*-lite.iss"):
        source = path.read_text(encoding="utf-8")
        assert "Runtime\\3.13\\quillville-runtime.json" not in source, path.name
        assert "Runtime\\quillville-runtime.json" in source, path.name
