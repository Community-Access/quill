"""The installed version comes from the installer's marker, not the runtime's code."""

from __future__ import annotations

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
