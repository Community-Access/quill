"""The shared Python runtime's version marker (skip-if-present for installers)."""

from __future__ import annotations

from pathlib import Path

from quill.core import runtime_marker as m


def test_runtime_version_is_dotted(tmp_path: Path) -> None:
    v = m.runtime_version()
    parts = v.split(".")
    assert len(parts) >= 2 and all(p.isdigit() for p in parts[:2])


def test_marker_round_trips(tmp_path: Path) -> None:
    m.write_marker(tmp_path, python_version="3.13.1", build_id="2026-07-21")
    assert m.read_marker(tmp_path) == {"python": "3.13.1", "build": "2026-07-21"}
    assert m.installed_version(tmp_path) == "3.13.1"


def test_absent_marker_reads_none(tmp_path: Path) -> None:
    assert m.read_marker(tmp_path) is None
    assert m.installed_version(tmp_path) is None


def test_needs_install_matches_exact_version(tmp_path: Path) -> None:
    # Nothing installed yet -> needs install.
    assert m.needs_install(tmp_path, "3.13.1") is True
    m.write_marker(tmp_path, python_version="3.13.1", build_id="b1")
    # Exact match -> skip.
    assert m.needs_install(tmp_path, "3.13.1") is False
    # A different version keyed to the same folder -> needs install (upgrade).
    assert m.needs_install(tmp_path, "3.14.0") is True
