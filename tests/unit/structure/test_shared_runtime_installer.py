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

import re
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


# -- the media tools must not ride inside the runtime's install-if-newer gate --
#
# ffmpeg and libmpv are 306 MB, so they are contributed per app rather than
# built into the shared runtime (scripts\StageMediaTools.ps1). Until 2026-08-21
# they were nonetheless installed by the SAME [Files] line as the runtime, which
# is gated by RuntimeNeedsInstall -- so which tools a machine ended up with was
# decided by the order the apps happened to be installed in. Install Cast
# (ffmpeg only, newer runtime build) and then Radio (ffmpeg + mpv, older build)
# and Radio's payload was skipped whole: no libmpv, no Ogg/Opus/HLS stations, no
# output-device choice, no DVR -- and reinstalling hit the same skip, so the
# app's own repair advice ("reinstalling restores it") could not come true.

#: app id -> the tool defines its installer must set, mirroring the app module's
#: ``REQUIRED_COMPONENTS``. The apps that declare no media tools are absent on
#: purpose: they must set neither define and ship neither tool.
MEDIA_TOOL_DEFINES = {
    "standalone/radio/installer/quill-radio.iss": {"ToolFfmpeg", "ToolMpv"},
    "standalone/cast/installer/quill-cast-shared.iss": {"ToolFfmpeg"},
    "standalone/studio/installer/quill-audio-studio.iss": {"ToolFfmpeg", "ToolMpv"},
}

#: ``quill/apps/<module>.py`` for each of the above, so the two lists cannot
#: drift: the installer's tools are the app's declared components or the app
#: launches missing something it says it needs.
APP_MODULE_FOR_INSTALLER = {
    "standalone/radio/installer/quill-radio.iss": "radio",
    "standalone/cast/installer/quill-cast-shared.iss": "podcasts",
    "standalone/studio/installer/quill-audio-studio.iss": "studio",
}

_DEFINE_FOR_COMPONENT = {"ffmpeg": "ToolFfmpeg", "mpv": "ToolMpv"}


def _files_entry(source: str, starts_with: str) -> str:
    """One whole [Files] entry: its Source line plus every ``\\`` continuation.

    Read as a unit on purpose -- ``Check:`` and ``Excludes:`` both sit on
    continuation lines here, so a per-line assertion would pass while the entry
    said the opposite of what it was asserted to say.
    """
    lines = source.splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith(starts_with))
    entry = [lines[index]]
    while entry[-1].rstrip().endswith("\\"):
        index += 1
        entry.append(lines[index])
    return "\n".join(entry)


def test_the_tools_are_installed_unconditionally_not_behind_the_runtime_gate() -> None:
    """Each tool gets its own Check-less [Files] entry, or install order decides."""
    source = FRAGMENT.read_text(encoding="utf-8")
    for tool in ("ffmpeg", "mpv"):
        marker = rf'Source: "{{#RuntimeSourceDir}}\tools\{tool}\*"'
        assert marker in source, f"{tool} has no [Files] entry of its own"
        entry = _files_entry(source, marker)
        assert "Check:" not in entry, (
            f"the {tool} entry is gated by a Check, so a newer sibling runtime "
            f"can still skip it and install order decides who has {tool}"
        )
        assert rf'DestDir: "{{code:RuntimeDir}}\tools\{tool}"' in entry, (
            f"{tool} must land in the shared runtime's tools\\ dir, which is "
            f"where QUILL_APP_ROOT-based discovery looks for it"
        )


def test_the_runtime_wildcard_excludes_the_tools_it_no_longer_installs() -> None:
    """Without the exclude, every tool byte is packed twice (306 MB per app)."""
    source = FRAGMENT.read_text(encoding="utf-8")
    gated = _files_entry(source, r'Source: "{#RuntimeSourceDir}\*"')
    assert "Check: RuntimeNeedsInstall" in gated, "the runtime itself must stay gated"
    assert r'Excludes: "tools,tools\*"' in gated, (
        "the gated runtime wildcard must exclude tools\\, which is now installed "
        "by its own entries -- otherwise the payload carries them twice"
    )


def test_each_media_installer_declares_exactly_the_tools_its_app_requires() -> None:
    """The installer's defines and the app's REQUIRED_COMPONENTS are one list."""
    for relative, expected in MEDIA_TOOL_DEFINES.items():
        source = (REPO / relative).read_text(encoding="utf-8")
        declared = {define for define in ("ToolFfmpeg", "ToolMpv") if f"#define {define}" in source}
        assert declared == expected, f"{relative} declares {declared}, expected {expected}"

        module = REPO / "quill" / "apps" / f"{APP_MODULE_FOR_INSTALLER[relative]}.py"
        text = module.read_text(encoding="utf-8")
        line = next(raw for raw in text.splitlines() if raw.startswith("REQUIRED_COMPONENTS"))
        required = {component for component in _DEFINE_FOR_COMPONENT if f'"{component}"' in line}
        assert {_DEFINE_FOR_COMPONENT[c] for c in required} == expected, (
            f"{module.name} requires {sorted(required)} but {relative} stages "
            f"{sorted(expected)} -- the app would launch without a tool it declares"
        )


def test_apps_with_no_media_components_stage_no_tools() -> None:
    """Weather must not ship 306 MB another app's build left in the shared dist."""
    for relative in SHARED_RUNTIME_INSTALLERS - set(MEDIA_TOOL_DEFINES):
        source = (REPO / relative).read_text(encoding="utf-8")
        assert "#define ToolFfmpeg" not in source, relative
        assert "#define ToolMpv" not in source, relative


# -- every {#Macro} an installer uses must be defined somewhere it can see -----
#
# QUILL Cast's 2.0 work added the quill-cast:// URI handler to all three of its
# installers, but only quill-cast.iss defined the AppExeName it interpolates --
# and quill-cast.iss is the one build_release.ps1 no longer compiles. So the two
# installers that ARE built could not compile at all ("Undeclared identifier:
# AppExeName. Compile aborted."), and nothing noticed for as long as nobody cut
# a release. ISCC catches this instantly; the gap was that nothing ran ISCC.
# This is the cheap half of that check, and it runs on every commit.

#: Macros ISPP/Inno provide or that the build supplies on the command line
#: (ISCC /d...), so an installer is right not to define them itself.
_EXTERNALLY_DEFINED = frozenset({
    "AppVersion",  # passed as /dAppVersion=<version> by every build script
    "SetupSetting",  # ISPP built-in
    "Sign",  # /DSign, and only ever tested with #ifdef
})

_MACRO_USE = re.compile(r"\{#\s*([A-Za-z_][A-Za-z0-9_]*)")
_MACRO_DEF = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)
_INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.MULTILINE)


def _defined_names(path: Path, *, seen: set[Path] | None = None) -> set[str]:
    """Every macro name visible in *path*, following #include one level or more."""
    seen = seen if seen is not None else set()
    resolved = path.resolve()
    if resolved in seen or not resolved.is_file():
        return set()
    seen.add(resolved)
    text = resolved.read_text(encoding="utf-8")
    names = set(_MACRO_DEF.findall(text))
    for relative in _INCLUDE.findall(text):
        names |= _defined_names(resolved.parent / relative, seen=seen)
    return names


def _used_names(path: Path, *, seen: set[Path] | None = None) -> set[str]:
    seen = seen if seen is not None else set()
    resolved = path.resolve()
    if resolved in seen or not resolved.is_file():
        return set()
    seen.add(resolved)
    text = resolved.read_text(encoding="utf-8")
    names = set(_MACRO_USE.findall(text))
    for relative in _INCLUDE.findall(text):
        names |= _used_names(resolved.parent / relative, seen=seen)
    return names


def test_every_installer_defines_the_macros_it_interpolates() -> None:
    problems: list[str] = []
    for path in sorted(REPO.glob("standalone/*/installer/*.iss")):
        undefined = _used_names(path) - _defined_names(path) - _EXTERNALLY_DEFINED
        if undefined:
            problems.append(f"{path.relative_to(REPO).as_posix()}: {sorted(undefined)}")
    assert not problems, (
        "these installers interpolate a macro nothing defines, so ISCC aborts on "
        f"the first build that compiles them: {problems}"
    )
