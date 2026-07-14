"""Build the portable distribution ZIP for a release.

The portable bundle is the runnable QUILL distribution with embedded
Python and all bundled tools (Pandoc, DECtalk, eSpeak-NG, Piper,
Kokoro). It is published as a release asset so users who don't want
the installer can extract the zip and run run-quill.cmd.

Usage::

    python scripts/build_portable_zip.py \\
        --source-dir windows-distribution/portable \\
        --output Quill-Portable-v0.7.0-beta.1.zip
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

# Build-only scratch that must never ship in the portable ZIP: the staging area
# where downloaded tool archives are unpacked before being copied into tools/
# (a duplicate ~376 MB), and Python bytecode caches. Matched against any path
# component so nested caches are excluded too.
_EXCLUDED_DIRS = frozenset({"_tool-download", "__pycache__"})


def _is_scratch(path: Path, root: Path) -> bool:
    return any(part in _EXCLUDED_DIRS for part in path.relative_to(root).parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("windows-distribution") / "portable",
        help="The portable bundle directory to zip.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="The output zip path (e.g. Quill-Portable-v0.7.0-beta.1.zip).",
    )
    args = parser.parse_args()

    if not args.source_dir.is_dir():
        print(f"ERROR: {args.source_dir} is not a directory", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    file_count = 0
    skipped = 0
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(args.source_dir.rglob("*")):
            if not path.is_file():
                continue
            if _is_scratch(path, args.source_dir):
                skipped += 1
                continue
            arcname = path.relative_to(args.source_dir.parent)
            zf.write(path, arcname)
            file_count += 1
    note = f" (skipped {skipped} build-scratch files)" if skipped else ""
    print(f"Wrote {args.output} ({file_count} files){note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
