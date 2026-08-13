"""Run the *real* OptiLab Core on a saved file, when it is available.

Attribution
-----------
OptiLab Core is by **Lanes Audio / dgl1984** --
https://github.com/dgl1984/optilab (author: https://github.com/dgl1984).
QUILL vendors its processing engine unmodified at **v1.4.0** under
``quill/native/optilab/upstream/``, licensed **Apache-2.0 with the Commons
Clause v1.0**; ``upstream/LICENSE`` and ``upstream/NOTICE`` ship beside it.
Upstream's NOTICE grants royalty-free commercial use of OptiLab Core as a tool
for producing, processing, broadcasting or streaming audio; the Commons Clause
withholds the right to sell the Software itself, which QUILL does not do.

What this is for
----------------
:mod:`quill.core.optilab` builds ffmpeg filter chains that *reproduce the shape*
of OptiLab's three modes. They are a faithful adaptation, not a port, and they
have one honest limitation the module has always documented: upstream reduces
its lift and withdraws bass assistance **while final limiting is running
heavy**, and an ffmpeg graph is feed-forward, so no stage can see how hard a
later one is working. That feedback loop cannot be expressed there at all.

This module closes that gap **for saved files only** -- recordings and
conversions -- by piping PCM through an adapter executable that links the real
engine. Those paths already shell out to ffmpeg, offline, with no live-preview
property to protect.

Live playback stays on the ffmpeg chain, permanently and by design. mpv applies
enhancement natively from a filter string and nothing in that path ever holds a
sample in Python; routing live audio through a subprocess would reintroduce a
relay everywhere and cost the live preview that path exists to provide.

**Entirely optional.** No adapter built -> ``available()`` is False and every
caller uses the ffmpeg chain exactly as before. A missing C++ toolchain must
never fail a build or a feature.

wx-free, strict-typed. This module only *locates and describes* the adapter and
builds its argv; running it belongs to the caller's existing ffmpeg pipeline.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: Our mode ids (quill.core.optilab.OPTILAB_MODES) -> the adapter's --mode.
#: "off" has no adapter form: it means do not run this at all.
_MODE_ARGS: dict[str, str] = {
    "podcast": "podcast",
    "stream": "stream",
    "limiter": "limiter",
}

#: The executable's basename, matching CMake's target name.
_EXE_STEM = "quill-optilab"

#: Upstream identity, surfaced by the About box, the compliance report and the
#: Compare Engines explanation so attribution travels with the feature rather
#: than living only in a source comment.
UPSTREAM_NAME = "OptiLab Core"
UPSTREAM_AUTHOR = "Lanes Audio / dgl1984"
UPSTREAM_URL = "https://github.com/dgl1984/optilab"
UPSTREAM_AUTHOR_URL = "https://github.com/dgl1984"
UPSTREAM_VERSION = "1.4.0"
UPSTREAM_LICENSE = "Apache-2.0 WITH Commons-Clause"


def attribution() -> str:
    """One speakable sentence of credit, for anywhere this is surfaced."""
    return (
        f"{UPSTREAM_NAME} {UPSTREAM_VERSION} by {UPSTREAM_AUTHOR}, "
        f"{UPSTREAM_URL}, {UPSTREAM_LICENSE}."
    )


def _exe_name() -> str:
    return f"{_EXE_STEM}.exe" if sys.platform.startswith("win") else _EXE_STEM


def find_adapter() -> Path | None:
    """The adapter executable, or None when this build does not include it.

    Looked for beside the app first (where a shipped build stages it), then in
    the source tree's build output, then on PATH -- the same order and the same
    permissiveness as :func:`quill.core.speech.ffmpeg.find_ffmpeg`, so a
    developer who has built it once gets it without configuration.
    """
    name = _exe_name()
    candidates: list[Path] = []

    override = os.environ.get("QUILL_OPTILAB_ADAPTER", "").strip()
    if override:
        candidates.append(Path(override))

    root = Path(__file__).resolve().parent.parent
    candidates.append(root / "native" / "optilab" / name)
    for build_dir in ("build", "build/Release", "build/Debug"):
        candidates.append(root / "native" / "optilab" / build_dir / name)
    candidates.append(Path(sys.prefix) / name)
    candidates.append(Path(sys.executable).parent / name)

    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:  # noqa: PERF203 - an unreadable path is simply not it
            continue

    from shutil import which

    found = which(name)
    return Path(found) if found else None


def available() -> bool:
    """Whether exact processing can run at all on this machine."""
    return find_adapter() is not None


def unavailable_reason() -> str:
    """Why the exact option is disabled, in words a listener can act on.

    Never returns an empty string: an option that is greyed out with no
    explanation is worse than one that is absent.
    """
    if available():
        return ""
    return (
        "Exact OptiLab processing needs the OptiLab component, which this "
        "build does not include. The built-in sound enhancements are unaffected."
    )


def adapter_command(
    adapter: Path,
    *,
    mode: str,
    sample_rate: int,
    channels: int = 2,
    input_db: float = 0.0,
    auto_adapt: int = 0,
) -> list[str]:
    """The argv for one offline pass. Raises ValueError on an unusable mode.

    An argv **list**, never a string: this is handed to
    ``stability.safe_subprocess``, and a shell would be a place for a filename
    to become an instruction.
    """
    flag = _MODE_ARGS.get(mode)
    if flag is None:
        raise ValueError(f"{mode!r} is not an OptiLab processing mode")
    if not 8000 <= int(sample_rate) <= 384_000:
        raise ValueError(f"{sample_rate!r} is not a usable sample rate")
    if int(channels) not in (1, 2):
        raise ValueError("OptiLab Core processes mono or stereo only")
    return [
        str(adapter),
        "--mode",
        flag,
        "--rate",
        str(int(sample_rate)),
        "--channels",
        str(int(channels)),
        "--input-db",
        f"{float(input_db):.2f}",
        "--adapt",
        str(max(0, min(100, int(auto_adapt)))),
    ]


#: What differs between the two chains, for Compare Engines and the user guide.
#: Three rows because there are exactly three honest differences -- reach, live
#: preview, and the feedback loop. Anything more would be marketing.
ENGINE_DIFFERENCES: tuple[tuple[str, str, str], ...] = (
    (
        "Where it runs",
        "Everywhere: live radio, podcasts, recordings and conversion",
        "Saved files only -- recordings and conversion",
    ),
    (
        "Live preview while you adjust",
        "Yes",
        "No, because it is not on the live path",
    ),
    (
        "Limiter feedback loop",
        "Absent: a feed-forward graph cannot ease the lift while limiting runs heavy",
        "Present",
    ),
)


__all__ = [
    "ENGINE_DIFFERENCES",
    "UPSTREAM_AUTHOR",
    "UPSTREAM_AUTHOR_URL",
    "UPSTREAM_LICENSE",
    "UPSTREAM_NAME",
    "UPSTREAM_URL",
    "UPSTREAM_VERSION",
    "adapter_command",
    "attribution",
    "available",
    "find_adapter",
    "unavailable_reason",
]
