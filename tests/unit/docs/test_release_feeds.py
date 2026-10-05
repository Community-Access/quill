"""GATE-FEED: every published v2 release feed is signed, sound and in date.

``docs/site/updates/v2/<app>.json`` is what every channel-aware copy trusts,
so a feed may only land on ``main`` when:

* its ``.sig`` verifies against the bundled feed keys (a feed the promote
  workflow wrote with ``--no-sign`` fails here until the owner signs it);
* it parses as ``quillville-release-feed/2`` for the app its name says;
* Stable lists only final-numbered builds;
* every release's rollback fields equal what the publisher would compute;
* it has not expired.

No feed has been published yet; the gate is live the moment the first lands.
The 14-day expiry *warning* is not a failure here -- it is a row in
``platform_report`` and a line from every publish run.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from quill.core.updater.feed import parse_feed, trusted_feed_keys, verify_feed_bytes
from quill.core.updater.feed_publish import validate_feed

FEEDS = Path(__file__).resolve().parents[3] / "docs" / "site" / "updates" / "v2"


def _feeds() -> list[Path]:
    if not FEEDS.is_dir():
        return []
    return sorted(p for p in FEEDS.glob("*.json") if p.name != "index.json")


@pytest.mark.parametrize("path", _feeds(), ids=lambda p: p.name)
def test_feed_is_signed_sound_and_in_date(path: Path) -> None:
    pytest.importorskip("nacl")
    data = path.read_bytes()
    sig = path.with_name(path.name + ".sig")
    assert sig.is_file(), (
        f"{path.name} is unsigned: python scripts/feed_tool.py sign --app {path.stem}"
    )
    assert verify_feed_bytes(data, sig.read_text(encoding="utf-8"), trusted_feed_keys()), (
        f"{path.name}'s signature does not verify against quill/core/feed-pub.key(s)"
    )
    feed = parse_feed(data, app_key=path.stem)
    assert validate_feed(feed) == []
    assert not feed.is_expired(datetime.now(UTC)), (
        f"{path.name} expired on {feed.expires_at}: "
        f"python scripts/feed_tool.py refresh --app {path.stem}"
    )


def test_feed_folder_holds_only_feeds_signatures_and_the_index() -> None:
    if not FEEDS.is_dir():
        return
    for path in FEEDS.iterdir():
        assert path.suffix in (".json", ".sig"), f"unexpected file {path.name} in updates/v2"
