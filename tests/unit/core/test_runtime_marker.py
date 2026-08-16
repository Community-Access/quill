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


def test_installed_build_reads_the_build_field(tmp_path: Path) -> None:
    assert m.installed_build(tmp_path) is None  # no marker
    m.write_marker(tmp_path, python_version="3.13.1", build_id="2026-07-24")
    assert m.installed_build(tmp_path) == "2026-07-24"


def test_installed_build_none_when_build_predates_tracking(tmp_path: Path) -> None:
    # A marker written before build tracking has an empty build field.
    m.write_marker(tmp_path, python_version="3.13.1", build_id="")
    assert m.installed_version(tmp_path) == "3.13.1"
    assert m.installed_build(tmp_path) is None


def test_needs_install_refreshes_a_stale_same_python_build(tmp_path: Path) -> None:
    # #1217: same CPython, but the bundled app code/data is older than the
    # payload -> must refresh (the version-only gate wrongly skipped this).
    m.write_marker(tmp_path, python_version="3.13.1", build_id="2026-07-01")
    assert m.needs_install(tmp_path, "3.13.1", required_build="2026-07-24") is True


def test_needs_install_skips_when_build_is_current_or_newer(tmp_path: Path) -> None:
    m.write_marker(tmp_path, python_version="3.13.1", build_id="2026-07-24")
    # Same build -> skip.
    assert m.needs_install(tmp_path, "3.13.1", required_build="2026-07-24") is False
    # Installed is NEWER than the incoming payload (older sibling app) -> never
    # downgrade the shared runtime.
    assert m.needs_install(tmp_path, "3.13.1", required_build="2026-07-01") is False


def test_needs_install_refreshes_when_installed_marker_predates_build_tracking(
    tmp_path: Path,
) -> None:
    m.write_marker(tmp_path, python_version="3.13.1", build_id="")
    assert m.needs_install(tmp_path, "3.13.1", required_build="2026-07-24") is True


def test_needs_install_without_required_build_is_version_only(tmp_path: Path) -> None:
    # Back-compat: callers that don't pass a build keep the old version-only gate.
    m.write_marker(tmp_path, python_version="3.13.1", build_id="2026-07-24")
    assert m.needs_install(tmp_path, "3.13.1") is False
    assert m.needs_install(tmp_path, "3.14.0") is True


def test_two_builds_on_one_day_are_distinguishable(tmp_path: Path) -> None:
    """The 2026-08-16 fault: build ids were bare dates, so the morning's
    runtime and the afternoon's compared equal and an update installed over
    the old one was skipped -- the app kept running the earlier code while
    the installer reported success. Stamps carry the time now."""
    m.write_marker(tmp_path, python_version="3.13.14", build_id="2026-08-16T08:30:00Z")
    assert m.needs_install(tmp_path, "3.13.14", required_build="2026-08-16T11:12:00Z") is True
    # ...and the reverse is still a no-op, so an older sibling never downgrades.
    m.write_marker(tmp_path, python_version="3.13.14", build_id="2026-08-16T11:12:00Z")
    assert m.needs_install(tmp_path, "3.13.14", required_build="2026-08-16T08:30:00Z") is False


def test_a_date_only_marker_is_older_than_any_stamp_from_the_same_day(tmp_path: Path) -> None:
    """Upgrading from a pre-fix install: "2026-08-16" < "2026-08-16T..." by
    plain string compare, so the first fixed installer refreshes it."""
    m.write_marker(tmp_path, python_version="3.13.14", build_id="2026-08-16")
    assert m.needs_install(tmp_path, "3.13.14", required_build="2026-08-16T00:01:00Z") is True
