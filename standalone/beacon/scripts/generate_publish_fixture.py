"""Generate a representative published-collection HTML fixture for axe-core CI.

Renders a sample collection through the real ``render_collection_html`` so the
accessibility check covers the actual output users get from Publish Collection.
Writes ``build/a11y-fixture.html``. No wx dependency; only the engine layers
(model/db/search/publish) are imported.

Run::

    PYTHONPATH=. python scripts/generate_publish_fixture.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Make the package importable when run from a checkout without installing.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill_beacon import db, publish
from quill_beacon.model import Beacon, Collection, Resource


def build_fixture() -> str:
    tmp = tempfile.mkdtemp()
    store = db.BeaconStore(os.path.join(tmp, "beacons.db"))
    col = Collection(name="Reading List",
                     description="Saved places I want to come back to.")
    store.put_collection(col)

    # 1) A web page with a note and tags.
    r1 = Resource(title="Designing Accessible Applications", type="web",
                  primary_uri="https://example.org/a11y")
    b1 = Beacon(resource_id=r1.resource_id, title="Designing Accessible Applications",
                in_inbox=False, note="Use this in the QuillBeacon design discussion.\n"
                "Keyboard interaction section is especially relevant.",
                tags=["a11y", "design"])
    b1.collections = ["Reading List"]
    store.put_beacon(b1, resource=r1)

    # 2) A note with no resolvable URI (exercises the plain-text fallback).
    r2 = Resource(title="Local idea", type="note", primary_uri="")
    b2 = Beacon(resource_id=r2.resource_id, title="Local idea", in_inbox=False,
                note="A thought I captured without a link.")
    b2.collections = ["Reading List"]
    store.put_beacon(b2, resource=r2)

    # 3) A podcast episode.
    r3 = Resource(title="Living Blindfully -- Keyboard tips", type="podcast-episode",
                  primary_uri="https://example.org/podcast/ep42")
    b3 = Beacon(resource_id=r3.resource_id, title="Living Blindfully -- Keyboard tips",
                in_inbox=False, note="Skip to 18:52 for the shortcuts.")
    b3.collections = ["Reading List"]
    store.put_beacon(b3, resource=r3)

    beacons = store.list_beacons()
    html = publish.render_collection_html(store, col, beacons, published_at=1700000000)
    store.close()
    return html


def main() -> int:
    out_dir = Path("build")
    out_dir.mkdir(parents=True, exist_ok=True)
    html = build_fixture()
    (out_dir / "a11y-fixture.html").write_text(html, encoding="utf-8")
    print(f"Wrote {out_dir / 'a11y-fixture.html'} ({len(html)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())