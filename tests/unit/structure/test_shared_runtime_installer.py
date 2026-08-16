"""The shared-runtime installer fragment must compare *builds*, not just Python.

The QuillVille Runtime carries the whole ``quill`` package -- every app's real
code -- so "same CPython" never means "same payload". On 2026-08-16 a Quill
Radio update installed cleanly over a runtime built four hours earlier and the
app kept running the older code: the fragment's skip test compared only the
CPython version, and the build id it could have compared was a bare date that
two builds on one day shared.

These are source-level guards. The decision logic itself is unit-tested in
``quill.core.runtime_marker`` (:func:`needs_install`); what is pinned here is
that the installer -- the thing that actually decides -- keeps asking the
question at all, for every app that ships the shared runtime.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FRAGMENT = REPO / "installer" / "shared-runtime.iss"


def test_the_skip_test_compares_the_payload_build_against_the_installed_one() -> None:
    source = FRAGMENT.read_text(encoding="utf-8")
    # It must read the build from BOTH sides: the marker already installed,
    # and the one this setup carries (extracted to {tmp} before any copy).
    assert "ExtractTemporaryFile('quillville-runtime.json')" in source
    assert "'build'" in source, "the build id is never read"
    assert "InstalledBuild >= PayloadBuild" in source, (
        "an installed build that is older than the payload must trigger a reinstall"
    )
    # The payload marker has to be shipped as a dontcopy file or the extract
    # above fails at install time.
    assert "quillville-runtime.json" in source and "dontcopy" in source


def test_every_app_that_includes_the_fragment_gets_the_fix() -> None:
    """One fragment, five installers: the fix cannot be half-applied."""
    including = sorted(
        path.relative_to(REPO).as_posix()
        for path in REPO.glob("standalone/*/installer/*.iss")
        if "shared-runtime.iss" in path.read_text(encoding="utf-8")
    )
    assert len(including) >= 5, f"expected every app's installer to include it, found {including}"


def test_the_runtime_build_id_carries_a_time_not_just_a_date() -> None:
    """Two builds on one day must not look identical to the installer."""
    build_script = (REPO / "standalone" / "runtime" / "build_runtime.ps1").read_text(
        encoding="utf-8"
    )
    assert "yyyy-MM-ddTHH:mm:ssZ" in build_script
    assert 'Get-Date -Format "yyyy-MM-dd"' not in build_script
