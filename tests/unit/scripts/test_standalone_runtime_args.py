"""The shared runtime must not carry media tools; the apps that need them do.

``standalone/runtime/build_runtime.ps1`` used to stage ffmpeg, ffprobe and
libmpv into the runtime it builds. That put 304 MB -- 41% of the runtime -- into
*every* app that installs it, including the four that never call any of them:
``Quill-Weather-Setup-Shared-2.2.0.exe`` was 191.5 MB for an app that reads out
a forecast. It also created an ordering dependency nothing documented, because
the runtime build hard-failed without a vetted directory for each, so a Weather
build only worked if some other app had already produced the runtime.

The rule now (the 2026-07-20 runtime/component plan, S2): the media tools live
beside the runtime, and staging is **opt-in**. Each app's own build_release.ps1
stages exactly what that app declares in ``REQUIRED_COMPONENTS``, through
``scripts/StageMediaTools.ps1``. An app that declares nothing calls nothing --
so there is no per-app exclusion list to keep in step, and the failure mode is a
missing tool in one app rather than 304 MB in all of them.

These tests hold that shape in place from both ends: the runtime build must not
stage, and each app must stage if and only if it declares.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_STANDALONE = Path("standalone")
_BUILD_RUNTIME = _STANDALONE / "runtime" / "build_runtime.ps1"
_STAGER = Path("scripts") / "StageMediaTools.ps1"
_STAGE_CALL = "Stage-QuillMediaTools"

#: App build script -> whether that app declares any media component.
#: Radio declares ("ffmpeg", "mpv"); Cast and Studio declare ("ffmpeg",) -- and
#: Studio also stages libmpv for its player preview, which its build has always
#: shipped. Weather, Inkwell, Beacon, Social, Converter and Player declare none.
_DECLARES_MEDIA: dict[str, bool] = {
    "radio": True,
    "studio": True,
    "weather": False,
    "inkwell": False,
}


def _apps_building_the_runtime() -> list[Path]:
    return sorted(
        path
        for path in _STANDALONE.glob("*/scripts/build_release.ps1")
        if "build_runtime.ps1" in path.read_text(encoding="utf-8", errors="replace")
    )


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _runtime_invocation(body: str) -> str:
    """The single ``build_runtime.ps1`` call line, backtick continuations joined.

    Reading a fixed window of characters after the call would now also swallow
    the ``Stage-QuillMediaTools`` line that legitimately follows it -- which does
    pass ``-FfmpegDir``, to the stager rather than to the runtime build.
    """
    lines = body.splitlines()
    index = max(i for i, line in enumerate(lines) if "build_runtime.ps1" in line)
    call = [lines[index]]
    while call[-1].rstrip().endswith("`") and index + len(call) < len(lines):
        call.append(lines[index + len(call)])
    return "\n".join(call)


def test_at_least_one_app_builds_the_shared_runtime() -> None:
    """Guard the guard: a bad glob would make every assertion below vacuous."""
    assert _apps_building_the_runtime()


def test_the_stager_exists() -> None:
    assert _STAGER.is_file(), f"{_STAGER} is the one place media staging is implemented"
    assert _STAGE_CALL in _text(_STAGER)


@pytest.mark.parametrize("switch", ["-FfmpegDir", "-LibmpvDir"])
def test_the_runtime_build_takes_no_media_directories(switch: str) -> None:
    """A parameter it no longer needs is a parameter that will start staging again."""
    body = _text(_BUILD_RUNTIME)
    param_block = body.split("param(", 1)[1].split(")", 1)[0]
    assert switch.lstrip("-") not in param_block, (
        f"{_BUILD_RUNTIME} still declares {switch}; the shared runtime must not "
        "stage media tools -- see scripts/StageMediaTools.ps1"
    )


@pytest.mark.parametrize("tool", ["ffmpeg.exe", "libmpv-2.dll", "ffprobe.exe"])
def test_the_runtime_build_copies_no_media_tools(tool: str) -> None:
    body = _text(_BUILD_RUNTIME)
    copying = [
        line for line in body.splitlines() if tool in line and line.strip().startswith("Copy-Item")
    ]
    assert not copying, f"{_BUILD_RUNTIME} still copies {tool} into the runtime: {copying}"


@pytest.mark.parametrize("app", sorted(_DECLARES_MEDIA))
def test_apps_stage_exactly_what_they_declare(app: str) -> None:
    """Declaring media means staging it; declaring none means staging none."""
    script = _STANDALONE / app / "scripts" / "build_release.ps1"
    if not script.is_file():  # pragma: no cover - an app was renamed or removed
        pytest.skip(f"{script} does not exist")
    body = _text(script)
    stages = _STAGE_CALL in body
    if _DECLARES_MEDIA[app]:
        assert stages, (
            f"{app} declares media components but never calls {_STAGE_CALL}; its "
            "installer would ship without ffmpeg and break offline on first launch"
        )
        assert "StageMediaTools.ps1" in body, f"{app} calls {_STAGE_CALL} without sourcing it"
    else:
        assert not stages, (
            f"{app} declares no media components but stages them anyway -- that is "
            "the 304 MB this change exists to remove"
        )


@pytest.mark.parametrize("app", sorted(_DECLARES_MEDIA))
def test_no_app_passes_media_directories_to_the_runtime_build(app: str) -> None:
    script = _STANDALONE / app / "scripts" / "build_release.ps1"
    if not script.is_file():  # pragma: no cover
        pytest.skip(f"{script} does not exist")
    invocation = _runtime_invocation(_text(script))
    for switch in ("-FfmpegDir", "-LibmpvDir"):
        assert switch not in invocation, (
            f"{app} still passes {switch} to build_runtime.ps1, which no longer "
            f"accepts it (PowerShell would swallow it into $args): {invocation!r}"
        )
