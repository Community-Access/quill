"""The installed version comes from the installer's marker, not the runtime's code."""

from __future__ import annotations

import sys

from quill.core import app_version


def _marker(root, text: str) -> None:
    (root / app_version.MARKER_NAME).write_text(text, encoding="utf-8")


def test_no_marker_means_the_code_version(tmp_path) -> None:
    assert app_version.installed_version("1.1.1", tmp_path) == "1.1.1"
    assert app_version.describe_version("1.1.1", tmp_path) == "1.1.1"
    assert app_version.read_marker(None) == ""


def test_the_marker_wins_over_a_runtime_that_ran_ahead(tmp_path) -> None:
    """The 2026-09-29 case: installer 1.0.0, a sibling's runtime saying 1.1.0."""
    _marker(tmp_path, "[app]\nversion = 1.0.0\n")
    assert app_version.installed_version("1.1.0", tmp_path) == "1.0.0"
    assert app_version.describe_version("1.1.0", tmp_path) == (
        "1.0.0 (running shared runtime code 1.1.0)"
    )


def test_a_matching_marker_reads_plainly(tmp_path) -> None:
    _marker(tmp_path, "[app]\nversion=3.0.4\n")
    assert app_version.describe_version("3.0.4", tmp_path) == "3.0.4"


def test_a_damaged_marker_is_ignored(tmp_path) -> None:
    for text in ("not an ini", "[app]\nversion = banana\n", "[other]\nversion = 1.0.0\n", ""):
        _marker(tmp_path, text)
        assert app_version.installed_version("1.1.1", tmp_path) == "1.1.1", text


def test_every_installer_writes_the_marker() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    for iss in (
        "standalone/quilllite/installer/quilllite.iss",
        "standalone/radio/installer/quill-radio.iss",
    ):
        text = (root / iss).read_text(encoding="utf-8")
        assert (
            'Filename: "{app}\\quill-app-version.ini"; Section: "app"; '
            'Key: "version"; String: "{#AppVersion}"' in text
        ), iss
        # ...and the app's own launcher goes into that same {app}, which is
        # the whole reason the marker can be found: the launcher exports its
        # folder as QUILL_LAUNCHER_DIR and marker_roots() looks there first.
        # Split the two and every installed copy silently reads the shared
        # runtime's version again, which is the defect this file exists for
        # (2026-09-30).
        assert '.exe"; DestDir: "{app}"' in text, iss


def test_the_marker_is_found_beside_the_launcher_not_in_the_runtime(tmp_path, monkeypatch) -> None:
    """The 2026-09-30 case: the fix for the version bug had the same bug in it.

    The installer writes the marker into ``{app}`` -- beside ``QuillRadio.exe``
    -- but ``QUILL_APP_ROOT`` on a shared-runtime install is the *runtime's*
    folder, which holds no marker. Looking only there meant every installed
    copy still reported the runtime's constant, which is the whole defect.
    """
    app = tmp_path / "Program Files" / "Quill Radio"
    runtime = tmp_path / "QuillVille" / "Runtime" / "3.13"
    app.mkdir(parents=True)
    runtime.mkdir(parents=True)
    _marker(app, "[app]\nversion = 3.1.1\n")

    monkeypatch.setenv("QUILL_LAUNCHER_DIR", str(app))
    monkeypatch.setenv("QUILL_APP_ROOT", str(runtime))
    monkeypatch.setattr(sys, "executable", str(runtime / "QuillVilleRuntime.exe"))

    assert app in app_version.marker_roots()
    assert app_version.installed_version("3.0.5") == "3.1.1"
    assert app_version.describe_version("3.0.5") == "3.1.1 (running shared runtime code 3.0.5)"


def test_no_marker_anywhere_still_means_the_code_version(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_LAUNCHER_DIR", str(tmp_path))
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path))
    assert app_version.installed_version("3.1.1") == "3.1.1"
