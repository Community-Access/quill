"""Every app that builds the shared runtime must pass it a vetted ffmpeg/libmpv.

``standalone/runtime/build_runtime.ps1`` bundles ffmpeg and libmpv into the
shared QuillVille Runtime and deliberately refuses PATH / %APPDATA%
auto-discovery for both, so it hard-fails unless the caller passes ``-FfmpegDir``
and ``-LibmpvDir``.

Quill Weather passed only ``-Python``. Because its own payload ships neither
binary, the omission looked deliberate -- but the runtime it builds ships both,
so every Weather build failed unless some other app had already produced the
runtime. That was an undocumented ordering dependency, and the ``-FfmpegDir``
the caller reached for was silently swallowed into ``$args`` (the script has no
``[CmdletBinding()]``), which made the real error impossible to read.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_STANDALONE = Path("standalone")
# The invocation may be split across lines with a backtick continuation, so read
# a window after the call rather than trying to regex PowerShell line joining.
_ARG_WINDOW = 300


def _build_scripts_invoking_the_runtime() -> list[Path]:
    return sorted(
        path
        for path in _STANDALONE.glob("*/scripts/build_release.ps1")
        if "build_runtime.ps1" in path.read_text(encoding="utf-8", errors="replace")
    )


def test_at_least_one_app_builds_the_shared_runtime() -> None:
    """Guard the guard: a bad glob would make every assertion below vacuous."""
    assert _build_scripts_invoking_the_runtime()


@pytest.mark.parametrize("switch", ["-FfmpegDir", "-LibmpvDir"])
def test_runtime_invocation_forwards_the_vetted_directories(switch: str) -> None:
    offenders: list[str] = []
    for script in _build_scripts_invoking_the_runtime():
        text = script.read_text(encoding="utf-8", errors="replace")
        # The last mention is the invocation; earlier ones are comments/paths.
        start = text.rindex("build_runtime.ps1")
        if switch not in text[start : start + _ARG_WINDOW]:
            offenders.append(script.as_posix())
    assert not offenders, f"{switch} not forwarded to build_runtime.ps1 by: {offenders}"


@pytest.mark.parametrize("switch", ["FfmpegDir", "LibmpvDir"])
def test_the_directories_are_declared_parameters(switch: str) -> None:
    """A switch that is not declared is absorbed into $args and silently ignored."""
    offenders = [
        script.as_posix()
        for script in _build_scripts_invoking_the_runtime()
        if f"${switch}"
        not in script.read_text(encoding="utf-8", errors="replace").split("param(")[1].split(")")[0]
    ]
    assert not offenders, f"${switch} is not a declared parameter of: {offenders}"
