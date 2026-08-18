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


#: The installers that ship the shared QuillVille Runtime, and must therefore
#: carry the fragment. Adding or removing one is a deliberate edit here.
#:
#: Not every installer is on this list, and that is correct: the ``-lite``
#: variants download the runtime rather than shipping it. Beacon, Cast and
#: Social joined on 2026-08-18, when the last three self-contained apps were
#: promoted to the shared-runtime layout (their ``-shared`` installers
#: supersede the old onedir ones under the same AppIds).
SHARED_RUNTIME_INSTALLERS = {
    "standalone/beacon/installer/quill-beacon-shared.iss",
    "standalone/cast/installer/quill-cast-shared.iss",
    "standalone/inkwell/installer/quill-inkwell.iss",
    "standalone/radio/installer/quill-radio.iss",
    "standalone/social/installer/quill-social-shared.iss",
    "standalone/studio/installer/quill-audio-studio.iss",
    "standalone/weather/installer/quill-weather.iss",
}


def test_every_app_that_includes_the_fragment_gets_the_fix() -> None:
    """One fragment, one named installer per app: the fix cannot be half-applied.

    This used to assert ``len(including) >= 5`` over a glob. It counted *files*,
    and the fifth was ``quill-radio-shared.iss`` -- a validation-only prototype,
    superseded on 2026-07-24, that included the fragment for the same app as
    ``quill-radio.iss``. So Radio was counted twice and the floor was met by a
    duplicate rather than by coverage; deleting the dead file broke a test that
    had been green for the wrong reason. Four apps ship the shared runtime, and
    naming them means a *removal* fails loudly instead of being absorbed by
    whatever else happens to match the glob.
    """
    including = {
        path.relative_to(REPO).as_posix()
        for path in REPO.glob("standalone/*/installer/*.iss")
        if "shared-runtime.iss" in path.read_text(encoding="utf-8")
    }
    missing = SHARED_RUNTIME_INSTALLERS - including
    assert not missing, f"these ship the shared runtime but omit the fragment: {sorted(missing)}"
    unexpected = including - SHARED_RUNTIME_INSTALLERS
    assert not unexpected, (
        "these include the fragment but are not declared above -- add them to "
        f"SHARED_RUNTIME_INSTALLERS if that is intended: {sorted(unexpected)}"
    )


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
