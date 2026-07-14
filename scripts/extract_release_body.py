"""Extract a single version's section from CHANGELOG.md for the release pipeline.

Reuses :func:`quill.core.release_notes.extract_version_section` so the GitHub
release body, the signed update-feed ``notes`` field, and the in-app
What's New / Check-for-Updates dialogs all show the same abbreviated text.

Usage::

    python scripts/extract_release_body.py --version v0.8.0-beta1 \
        --output release-body.md --fallback-full

Pure stdlib + the wx-free ``quill.core`` helpers, so it runs in CI without a
full editable install (``PYTHONPATH=.`` is enough).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quill.core.release_notes import extract_version_section


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract a release's CHANGELOG section.")
    parser.add_argument("--version", required=True, help="Release version or git tag.")
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the section here (default: print to stdout).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=0,
        help="Truncate to this many characters (0 = no limit).",
    )
    parser.add_argument(
        "--fallback-full",
        action="store_true",
        help="When no matching section is found, emit the whole changelog "
        "instead of an empty string (keeps a release body from being blank).",
    )
    args = parser.parse_args()

    text = args.changelog.read_text(encoding="utf-8")
    section = extract_version_section(text, args.version)
    if not section and args.fallback_full:
        section = text.strip()
    if args.max_chars > 0:
        section = section[: args.max_chars]

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(section + "\n", encoding="utf-8")
    else:
        sys.stdout.write(section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
