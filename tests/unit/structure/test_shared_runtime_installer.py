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


def test_the_installer_lays_the_runtime_where_the_launcher_looks_for_it() -> None:
    """The two halves of "where does the runtime live" must agree.

    They did not. The C launcher probes
    ``%LOCALAPPDATA%/QuillVille/Runtime/<major>/quillville-runtime.json`` --
    versioned, because the design keys runtimes by major so a future Python
    lands *alongside* rather than on top of the current one -- while
    ``shared-runtime.iss`` installed to the UNVERSIONED ``Runtime/``. A fresh
    install therefore laid the runtime somewhere the launcher never looks, and
    the app answered "Quill Radio could not find a Python runtime" and exited.
    Found by running the installed copy rather than by reading either file
    (2026-08-16); each side looked perfectly reasonable alone.

    Pinned as *agreement between files*, because either side moving on its own
    is the bug.
    """
    resolver = (REPO / "quill" / "native" / "launcher" / "runtime_resolve.c").read_text(
        encoding="utf-8"
    )
    fragment = FRAGMENT.read_text(encoding="utf-8")
    assert '"%s\\\\QuillVille\\\\Runtime", local' in resolver, "the launcher's base folder moved"
    assert 'path_join(runtime_dir, sizeof(runtime_dir), base, "3.13")' in resolver, (
        "the launcher no longer appends the major -- change the installer in lockstep"
    )
    assert "RuntimeMajor()" in fragment, (
        "shared-runtime.iss installs to the unversioned folder again"
    )
    assert (
        "ExpandConstant('{localappdata}\\QuillVille\\Runtime') + '\\' + RuntimeMajor()" in fragment
    )


def test_every_thin_installer_probes_that_same_versioned_path() -> None:
    """A thin installer probing the wrong folder either re-downloads the
    230 MB runtime on every install (a path that never exists) or skips one
    that is genuinely absent."""
    thin = list(REPO.glob("standalone/*/installer/*-lite.iss"))
    assert thin, "expected to find the thin installers"
    for path in thin:
        assert "Runtime\\3.13\\quillville-runtime.json" in path.read_text(encoding="utf-8"), (
            path.name
        )
