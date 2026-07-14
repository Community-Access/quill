"""Owner tool: add, remove, and publish remote feature kill switches.

A small, accessible console for the QUILL owner to disable (or re-enable) a
feature on users' machines by editing the signed update feed's `advisories`.
Wraps the same signing used everywhere else (`quill.core.updates`), so what it
writes always verifies on the client.

Two ways to use it:

* **Interactive** (no arguments) — a numbered menu: list current locks, add a
  lock (it lists the real feature ids to choose from), remove a lock, and
  publish (git commit + push the feed). Screen-reader friendly, plain text.
* **Flags** — for scripting or a one-liner during an incident::

      python scripts/manage_feature_locks.py --list
      python scripts/manage_feature_locks.py --add core.glow \
          --reason "Investigating a crash; back in 0.9.6" --max-version 0.9.5
      python scripts/manage_feature_locks.py --remove core.glow
      python scripts/manage_feature_locks.py --add core.glow --reason "…" --publish

Signing uses `QUILL_UPDATE_MANIFEST_KEY` exactly as the release feed does; set it
before running so the edited feed verifies. The feed file defaults to the one
GitHub Pages serves; `--publish` runs `git add/commit/push` on it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from quill.core.updates import (  # noqa: E402
    FeatureAdvisory,
    manifest_signature,
    parse_update_manifest,
)

_DEFAULT_FEED = _ROOT / "docs" / "site" / "updates" / ".quill-update-feed-v1.json"


# --------------------------------------------------------------------------- #
# Pure feed operations (unit-tested)
# --------------------------------------------------------------------------- #
def _advisory_tuple(feed: dict) -> tuple[FeatureAdvisory, ...]:
    return tuple(
        FeatureAdvisory(
            feature_id=str(a.get("feature_id", "")),
            reason=str(a.get("reason", "")),
            min_version=str(a.get("min_version", "")),
            max_version=str(a.get("max_version", "")),
            advisory_id=str(a.get("advisory_id", "")),
        )
        for a in feed.get("advisories", [])
    )


def resign(feed: dict, *, key: str | None = None) -> dict:
    """Recompute the feed signature over its current fields + advisories."""
    import os

    key = key if key is not None else (os.getenv("QUILL_UPDATE_MANIFEST_KEY", "").strip() or None)
    feed["signature"] = manifest_signature(
        version=str(feed.get("version", "")),
        download_url=str(feed.get("download_url", "")),
        published_at=str(feed.get("published_at", "")),
        notes=str(feed.get("notes", "")),
        key=key,
        advisories=_advisory_tuple(feed),
    )
    return feed


def list_locks(feed: dict) -> list[dict]:
    return list(feed.get("advisories", []))


def add_lock(
    feed: dict,
    feature_id: str,
    *,
    reason: str = "",
    min_version: str = "",
    max_version: str = "",
    key: str | None = None,
) -> dict:
    """Add (or replace) a lock for ``feature_id`` and re-sign the feed."""
    advisories = [a for a in feed.get("advisories", []) if a.get("feature_id") != feature_id]
    advisories.append({
        "feature_id": feature_id,
        "reason": reason,
        "min_version": min_version,
        "max_version": max_version,
        "advisory_id": f"lock-{feature_id}",
    })
    feed["advisories"] = advisories
    return resign(feed, key=key)


def remove_lock(feed: dict, feature_id: str, *, key: str | None = None) -> dict:
    """Remove the lock for ``feature_id`` and re-sign; drop the key when empty."""
    advisories = [a for a in feed.get("advisories", []) if a.get("feature_id") != feature_id]
    if advisories:
        feed["advisories"] = advisories
    else:
        feed.pop("advisories", None)  # keep the backward-compatible no-advisory shape
    return resign(feed, key=key)


# --------------------------------------------------------------------------- #
# I/O + git
# --------------------------------------------------------------------------- #
def load_feed(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Feed file is not a JSON object.")
    return data


def save_feed(path: Path, feed: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(feed, indent=2) + "\n", encoding="utf-8")
    # Prove it verifies before we hand it to users.
    parse_update_manifest(json.dumps(feed))


def _known_feature_ids() -> list[str]:
    """The authoritative feature ids (the catalog the client resolves against)."""
    try:
        from quill.core.features import FEATURE_DEFINITIONS

        return sorted(FEATURE_DEFINITIONS)
    except Exception:  # noqa: BLE001 - degrade gracefully if the catalog can't import
        return []


def is_known_feature(feature_id: str) -> bool:
    known = _known_feature_ids()
    return not known or feature_id in known  # empty catalog => cannot validate, allow


def suggest_feature_ids(feature_id: str) -> list[str]:
    """Up to 3 nearest known ids for a typo'd ``feature_id`` (deterministic)."""
    import difflib

    return difflib.get_close_matches(feature_id, _known_feature_ids(), n=3, cutoff=0.5)


def _unknown_feature_message(feature_id: str) -> str:
    suggestions = suggest_feature_ids(feature_id)
    hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
    return f"Unknown feature id {feature_id!r} — not in the catalog.{hint}"


def publish(path: Path, message: str) -> int:
    """git add + commit + push the feed file. Returns the process exit code."""
    for args in (
        ["git", "add", str(path)],
        ["git", "commit", "-m", message],
        ["git", "push"],
    ):
        result = subprocess.run(args, cwd=str(_ROOT))  # noqa: S603 - fixed argv
        if result.returncode != 0:
            return result.returncode
    return 0


# --------------------------------------------------------------------------- #
# Rendering + interactive menu
# --------------------------------------------------------------------------- #
def render_locks(feed: dict) -> str:
    locks = list_locks(feed)
    if not locks:
        return "No features are currently locked."
    lines = [f"{len(locks)} feature lock(s) active:"]
    for a in locks:
        bound = ""
        if a.get("min_version") or a.get("max_version"):
            bound = f" [versions {a.get('min_version') or '*'}..{a.get('max_version') or '*'}]"
        lines.append(f"  - {a.get('feature_id')}{bound}: {a.get('reason') or '(no reason)'}")
    return "\n".join(lines)


def _prompt(text: str) -> str:
    try:
        return input(text).strip()
    except EOFError:
        return ""


def interactive(path: Path) -> int:
    feed = load_feed(path)
    while True:
        print("\n" + render_locks(feed))
        print("\nActions: [1] add lock  [2] remove lock  [3] save  [4] save + publish  [5] quit")
        choice = _prompt("Choose: ")
        if choice == "1":
            ids = _known_feature_ids()
            if ids:
                print("Known feature ids (see feature_command_map.py):")
                print("  " + ", ".join(ids))
            feature_id = _prompt("Feature id to lock: ")
            if not feature_id:
                continue
            if not is_known_feature(feature_id):
                print(_unknown_feature_message(feature_id) + " Not locked.")
                continue
            reason = _prompt("Reason users will hear: ")
            max_version = _prompt("Last affected version (blank = all): ")
            feed = add_lock(feed, feature_id, reason=reason, max_version=max_version)
            print(f"Locked {feature_id}.")
        elif choice == "2":
            feature_id = _prompt("Feature id to unlock: ")
            if feature_id:
                feed = remove_lock(feed, feature_id)
                print(f"Unlocked {feature_id}.")
        elif choice == "3":
            save_feed(path, feed)
            print(f"Saved {path}.")
        elif choice == "4":
            save_feed(path, feed)
            code = publish(path, "chore(feed): update feature safety advisories")
            print("Published." if code == 0 else f"Publish failed (git exit {code}).")
        elif choice in {"5", "q", "quit", ""}:
            return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage QUILL remote feature kill switches.")
    parser.add_argument("--feed", type=Path, default=_DEFAULT_FEED, help="Feed file to edit.")
    parser.add_argument("--list", action="store_true", help="Print current locks and exit.")
    parser.add_argument("--add", metavar="FEATURE_ID", help="Lock this feature id.")
    parser.add_argument("--remove", metavar="FEATURE_ID", help="Unlock this feature id.")
    parser.add_argument("--reason", default="", help="Spoken reason for --add.")
    parser.add_argument("--min-version", default="", help="Lower version bound for --add.")
    parser.add_argument("--max-version", default="", help="Upper version bound for --add.")
    parser.add_argument("--publish", action="store_true", help="git add/commit/push the feed.")
    args = parser.parse_args(argv)

    if not any([args.list, args.add, args.remove]):
        return interactive(args.feed)

    feed = load_feed(args.feed)
    if args.list:
        print(render_locks(feed))
        return 0
    if args.add:
        if not is_known_feature(args.add):
            print("ERROR: " + _unknown_feature_message(args.add), file=sys.stderr)
            return 2
        feed = add_lock(
            feed,
            args.add,
            reason=args.reason,
            min_version=args.min_version,
            max_version=args.max_version,
        )
        print(f"Locked {args.add}.")
    if args.remove:
        feed = remove_lock(feed, args.remove)
        print(f"Unlocked {args.remove}.")
    save_feed(args.feed, feed)
    print(f"Saved {args.feed}.")
    if args.publish:
        code = publish(args.feed, "chore(feed): update feature safety advisories")
        print("Published." if code == 0 else f"Publish failed (git exit {code}).")
        return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
