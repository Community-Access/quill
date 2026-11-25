"""GATE-FEED for the scorecard: the signed v2 release feeds, and their expiry.

Fails (exit 1) when a feed in ``docs/site/updates/v2`` is unsigned, does not
verify, breaks a listing rule, or has expired. Passes with a ``Warning:`` line
-- which ``platform_report`` shows as a warning, not a failure -- when any
app's feed expires within 14 days. The
protected `release-feeds.yml` workflow can refresh the whole set without moving
the seed to a local computer.

    python -m quill.tools.release_feed_audit
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

from quill.core.updater.feed import parse_feed
from quill.core.updater.feed_publish import expiry_warnings, validate_feed

_FEEDS = Path(__file__).resolve().parents[2] / "docs" / "site" / "updates" / "v2"


def audit(folder: Path = _FEEDS, *, now: datetime | None = None) -> tuple[list[str], list[str]]:
    """``(problems, warnings)`` for every feed in *folder*."""
    from quill.tools.release_feed import APPS, feed_signature_ok, index_signature_ok

    moment = now or datetime.now(UTC)
    problems: list[str] = []
    feeds = []
    authoritative = folder.resolve() == _FEEDS.resolve()
    if authoritative and folder.is_dir():
        product_names = {path.stem for path in folder.glob("*.json") if path.name != "index.json"}
        expected = set(APPS)
        if product_names != expected:
            missing = sorted(expected - product_names)
            extra = sorted(product_names - expected)
            problems.extend(
                part
                for part in (
                    f"missing product feeds: {', '.join(missing)}" if missing else "",
                    f"unknown product feeds: {', '.join(extra)}" if extra else "",
                )
                if part
            )
        index = folder / "index.json"
        if not index_signature_ok(index):
            problems.append("index.json: missing or the signature does not verify")
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        if path.name == "index.json":
            continue
        try:
            feed = parse_feed(path.read_bytes(), app_key=path.stem)
        except Exception as error:  # noqa: BLE001 - a feed that cannot be read is a problem
            problems.append(f"{path.name}: {error}")
            continue
        feeds.append(feed)
        if not feed_signature_ok(path):
            problems.append(f"{path.name}: unsigned or the signature does not verify")
        problems.extend(f"{path.name}: {p}" for p in validate_feed(feed))
        if feed.is_expired(moment):
            problems.append(f"{path.name}: expired on {feed.expires_at}")
    warnings = [w for w in expiry_warnings(feeds, now=moment) if "expired on" not in w]
    return problems, warnings


def main() -> int:
    problems, warnings = audit()
    for line in problems:
        print(line)
    for line in warnings:
        print(f"Warning: {line}")
    if not problems and not warnings:
        print("Release feeds: none published yet, or all signed and in date.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
