"""Withdraw a listed build from the signed v2 release feed (plan 4.2).

    python scripts/revoke_release.py --app radio --version 3.4.0-beta.1 \\
        --reason "can lose favorites on first start" --replacement 3.4.0-beta.2
    python scripts/revoke_release.py --app radio --version 3.4.0-beta.1 \\
        --reason "..." --dry-run

What it does:

* marks the build ``revoked`` in the feed, with the reason and the build that
  replaces it (when there is one), so it is never offered again and is never a
  way back;
* each channel that offered it falls back to the build before it -- printed,
  so you can see what people will be offered now;
* adds "(withdrawn)" to the GitHub release title;
* deletes nothing. People who already have the build can still move forward
  or back from it, and its files stay downloadable.

The feed is signed with the owner's key, as ``promote_release.py`` does, or
left unsigned with ``--no-sign`` and signed later with
``python scripts/feed_tool.py sign --app <app>``. ``feed_tool.py revoke`` runs
the same function; this script is the documented way in.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from quill.tools import release_feed as rf  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app", required=True, choices=sorted(rf.APPS))
    parser.add_argument("--version", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--replacement", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-sign", action="store_true")
    parser.add_argument("--key-file", type=Path)
    return parser


def run(
    argv: list[str] | None = None,
    *,
    gh: rf.Gh = rf.gh_cli,
    root: Path = rf.REPO_ROOT,
    now: datetime | None = None,
    seed_reader: Callable[[Path | None], bytes] = rf.read_seed,
    out: Callable[[str], None] = print,
) -> int:
    args = build_parser().parse_args(argv)
    if not args.reason.strip():
        out("Give a reason: it is shown to people who have this build.")
        return 2
    seed = None if (args.no_sign or args.dry_run) else seed_reader(args.key_file)
    return rf.withdraw(
        args.app,
        args.version,
        reason=args.reason.strip(),
        replacement=args.replacement,
        gh=gh,
        root=root,
        now=now or datetime.now(UTC),
        seed=seed,
        dry_run=args.dry_run,
        out=out,
    )


if __name__ == "__main__":
    raise SystemExit(run())
