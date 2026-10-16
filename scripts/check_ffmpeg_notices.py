"""Fail a build that ships ffmpeg.exe without FFmpeg's licence beside it.

The pinned FFmpeg is a GPLv3 build. Distributing it means distributing its
licence and where its source is, and for most of 2026 the family's bundles
carried the executables with neither: the files existed in the package, but a
staging step that guessed at a path (Quill Cast's onedir looked for a
``LICENSE`` next to the staging folder, which never existed) copied nothing and
said nothing. A silent omission is the failure this script exists to make loud.

It walks each directory it is given, finds every ``ffmpeg.exe`` in it, and
requires every file in
:data:`quill.core.speech.ffmpeg_install.FFMPEG_NOTICE_FILES` in the same
folder, byte-identical to the package copy (so a stale source offer naming the
wrong build is caught too). The build scripts run it over the portable folder
and the shared-runtime payload after staging, before anything is zipped or
compiled. It reads only local files and never touches the network.

Usage::

    python scripts/check_ffmpeg_notices.py <bundle dir> [<bundle dir> ...]

Exit status is 0 when every ffmpeg.exe found carries its notices (or none was
found), 1 otherwise, with one plain sentence per problem.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from quill.core.speech.ffmpeg_install import FFMPEG_NOTICE_FILES  # noqa: E402

NOTICES_DIR = _REPO_ROOT / "quill" / "data" / "notices" / "ffmpeg"


def problems_in(bundle: Path, notices_dir: Path = NOTICES_DIR) -> list[str]:
    """Every way *bundle* ships ffmpeg.exe without its notices, as sentences."""
    found: list[str] = []
    if not bundle.is_dir():
        return [f"{bundle} is not a folder, so it cannot be checked."]
    for exe in sorted(bundle.rglob("*")):
        if exe.name.lower() != "ffmpeg.exe" or not exe.is_file():
            continue
        folder = exe.parent
        for name in FFMPEG_NOTICE_FILES:
            shipped = folder / name
            if not shipped.is_file():
                found.append(f"{folder} ships ffmpeg.exe without {name}.")
            elif shipped.read_bytes() != (notices_dir / name).read_bytes():
                found.append(
                    f"{shipped} differs from quill/data/notices/ffmpeg/{name}; "
                    "restage it from the package."
                )
    return found


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("Usage: check_ffmpeg_notices.py <bundle dir> [<bundle dir> ...]", file=sys.stderr)
        return 2
    problems: list[str] = []
    for raw in args:
        problems.extend(problems_in(Path(raw)))
    for line in problems:
        print(f"ERROR: {line}", file=sys.stderr)
    if problems:
        return 1
    print(f"FFmpeg licence notices present in {len(args)} bundle folder(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
