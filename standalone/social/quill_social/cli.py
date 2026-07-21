"""Headless command-line interface for QUILL Social (wx-free).

Enough of the engine to script and test without the GUI: list accounts, refresh
the local cache from each account's adapter, full-text search, and preview an
intelligent thread split. Mirrors ``quill_beacon.cli`` in spirit -- the GUI and
CLI share the same store and services, so anything the CLI does is exactly what
the app does.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC

from quill_social import __title__, __version__, paths
from quill_social.adapters.registry import adapter_for
from quill_social.db import SocialStore
from quill_social.services.thread_splitter import split_thread


def _store() -> SocialStore:
    return SocialStore(paths.db_path())


def cmd_accounts(args: argparse.Namespace) -> int:
    with _store() as store:
        for a in store.list_accounts():
            flag = " (default)" if a.is_default else ""
            paused = " [paused]" if a.paused else ""
            print(f"{a.account_id}  {a.network:9} {a.label}{flag}{paused}")
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    with _store() as store:
        total = 0
        for acct in store.list_accounts(include_paused=False):
            adapter = adapter_for(acct)
            try:
                for it in adapter.home_timeline(limit=args.limit):
                    it.account_id = acct.account_id
                    store.upsert_item(it)
                    total += 1
            except Exception as exc:  # noqa: BLE001
                print(f"{acct.label}: {exc}", file=sys.stderr)
        print(f"Refreshed {total} posts.")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    with _store() as store:
        hits = store.search_items(args.query, limit=args.limit)
        for it in hits:
            print(f"{_fmt(it.created_at)}  {it.author_display}: "
                  f"{it.text[:80].replace(chr(10), ' ')}")
        print(f"{len(hits)} result(s).")
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    text = sys.stdin.read() if args.text == "-" else args.text
    result = split_thread(text, args.limit, numbering=not args.no_number)
    for seg in result.segments:
        print(f"[{seg.index}/{result.count}] ({seg.length}) {seg.text}")
    if result.any_over_limit:
        print("WARNING: a segment exceeds the limit (unbreakable token).",
              file=sys.stderr)
    return 0


def _fmt(ms: int) -> str:
    from datetime import datetime
    return datetime.fromtimestamp(ms / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quill-social-cli",
                                description=f"{__title__} {__version__} (headless)")
    p.add_argument("--version", action="version", version=f"{__title__} {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("accounts", help="list connected accounts").set_defaults(
        func=cmd_accounts)

    r = sub.add_parser("refresh", help="pull each account's timeline into the cache")
    r.add_argument("--limit", type=int, default=60)
    r.set_defaults(func=cmd_refresh)

    s = sub.add_parser("search", help="full-text search cached posts")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=50)
    s.set_defaults(func=cmd_search)

    sp = sub.add_parser("split", help="preview an intelligent thread split")
    sp.add_argument("text", help="text to split, or - to read stdin")
    sp.add_argument("--limit", type=int, default=300)
    sp.add_argument("--no-number", action="store_true")
    sp.set_defaults(func=cmd_split)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
