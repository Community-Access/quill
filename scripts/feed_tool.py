"""Look after the signed v2 release feeds in ``docs/site/updates/v2``.

    python scripts/feed_tool.py verify              # every feed: signature, rules, expiry
    python scripts/feed_tool.py show --app radio    # what each channel lists
    python scripts/feed_tool.py sign --app radio    # sign a feed left unsigned (CI, --no-sign)
    python scripts/feed_tool.py refresh --app radio # re-sign with a fresh 90-day expiry
    python scripts/feed_tool.py revoke --app radio --version 3.4.0-beta.1 \\
        --reason "can lose favorites on first start" [--replacement 3.4.0-beta.2]
        # the same as scripts/revoke_release.py, which is the documented way in
    python scripts/feed_tool.py expiry              # the 14-day warning, on its own

Signing reads the owner's key (``QUILL_FEED_KEY_FILE`` or
``~/.config/quill/quill-feed-priv.key``) and nothing else. ``sign`` signs the
bytes as they are; ``refresh`` also bumps the sequence and the expiry, which
is what to run when a feed is near its date and no release is due.
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

from quill.core.updater.feed_publish import refresh, sign_bytes, validate_feed  # noqa: E402
from quill.tools import release_feed as rf  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    sub.add_parser("expiry")
    for name in ("show", "sign", "refresh", "revoke"):
        p = sub.add_parser(name)
        p.add_argument("--app", required=True, choices=sorted(rf.APPS))
        p.add_argument("--key-file", type=Path)
        if name == "revoke":
            p.add_argument("--version", required=True)
            p.add_argument("--reason", required=True)
            p.add_argument("--replacement", default="")
    return parser


def run(
    argv: list[str] | None = None,
    *,
    root: Path = rf.REPO_ROOT,
    now: datetime | None = None,
    seed_reader: Callable[[Path | None], bytes] = rf.read_seed,
    out: Callable[[str], None] = print,
    gh: rf.Gh = rf.gh_cli,
) -> int:
    args = build_parser().parse_args(argv)
    moment = now or datetime.now(UTC)
    if args.command == "expiry":
        warnings = rf.warnings_now(root, moment)
        for line in warnings or ["No feed expires within 14 days."]:
            out(line)
        return 0
    if args.command == "verify":
        failed = 0
        for feed in rf.all_feeds(root):
            path = rf.feed_dir(root) / f"{feed.app}.json"
            problems = validate_feed(feed)
            if not rf.feed_signature_ok(path):
                problems.append("the signature is missing or does not verify")
            for problem in problems:
                out(f"{feed.app}: {problem}")
            failed += bool(problems)
            if not problems:
                out(f"{feed.app}: sequence {feed.sequence}, expires {feed.expires_at}, signed")
        for warning in rf.warnings_now(root, moment):
            out(f"Warning: {warning}")
        return 1 if failed else 0
    feed = rf.load_feed(args.app, root)
    if args.command == "show":
        for channel in ("stable", "beta", "dev"):
            current = feed.current(channel)
            out(f"{channel:7} {current.version if current else '(nothing listed)'}")
        out(f"sequence {feed.sequence}, expires {feed.expires_at or '(never published)'}")
        return 0
    if args.command == "sign":
        path = rf.feed_dir(root) / f"{args.app}.json"
        data = path.read_bytes()
        seed = seed_reader(args.key_file)
        path.with_name(path.name + ".sig").write_bytes(sign_bytes(data, seed).encode("ascii"))
        rf.write_index(root=root, seed=seed)
        out(f"Signed {path.name} (sequence {feed.sequence}).")
        return 0
    if args.command == "revoke":
        return rf.withdraw(
            args.app,
            args.version,
            reason=args.reason,
            replacement=args.replacement,
            gh=gh,
            root=root,
            now=moment,
            seed=seed_reader(args.key_file),
            out=out,
        )
    feed = refresh(feed, moment)
    rf.write_feed(feed, seed=seed_reader(args.key_file), root=root)
    out(f"Wrote {args.app}.json: sequence {feed.sequence}, expires {feed.expires_at}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
