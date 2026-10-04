"""Roll the Beta notes up into one Stable section (plan 4.5).

    python scripts/rollup_release_notes.py --app radio --from 3.2.0 --to 3.3.0
    python scripts/rollup_release_notes.py --app radio --to 3.3.0 --out notes.md
    python scripts/rollup_release_notes.py --app radio --from 3.2.0 --to 3.3.0 --summary

Reads the app's changelog and merges every section after ``--from`` up to and
including ``--to`` into "What's new since <from>": one heading per kind of
change, oldest Beta first; lines marked ``[beta-only]`` dropped, with what is
indented under them; each Beta's "Known rough edges" dropped. When a data
format moved between the two builds (their entries in the signed feed, or
``quill/core/data_formats.py`` for a build not listed yet) it starts with
"Before you update".

``--from`` defaults to the app's current Stable build in the feed.
``--summary`` prints the feed's plain-text ``notes_summary`` instead, made from
the same text. ``promote_release.py`` runs this at every promotion to Stable,
and its ``--dry-run`` prints the result.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quill.core.updater.notes_rollup import notes_summary  # noqa: E402
from quill.tools import release_feed as rf  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app", required=True, choices=sorted(rf.APPS))
    parser.add_argument("--from", dest="from_version", default="")
    parser.add_argument("--to", dest="to_version", required=True)
    parser.add_argument("--out", type=Path, help="write the markdown here as well")
    parser.add_argument("--summary", action="store_true", help="print the feed summary")
    return parser


def run(
    argv: list[str] | None = None,
    *,
    root: Path = rf.REPO_ROOT,
    out: Callable[[str], None] = print,
) -> int:
    args = build_parser().parse_args(argv)
    result, notes = rf.rolled_up_notes(
        args.app, args.to_version, from_version=args.from_version, root=root
    )
    for note in notes:
        out(f"Note: {note}")
    if not result.merged:
        return 1
    text = result.markdown()
    if args.out:
        args.out.write_bytes(text.encode("utf-8"))
    out(notes_summary(text) if args.summary else text.rstrip("\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
