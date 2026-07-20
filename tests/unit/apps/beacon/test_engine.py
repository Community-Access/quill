"""Engine unit tests (stdlib unittest, no pytest dependency).

Covers model round-trips, db persistence + FTS, ULD resolution, and the
search grammar. Run: ``python -m unittest tests.test_engine``.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import db, search, uld
from quill.apps.beacon.model import (
    HEALTH_BROKEN,
    TYPE_PODCAST_EPISODE,
    TYPE_WEB,
    Beacon,
    Resource,
)


class ModelRoundTripTests(unittest.TestCase):
    def test_beacon_to_row_from_row(self):
        b = Beacon(title="A", note="n", favorite=True, tags=["x", "y"])
        row = b.to_row()
        b2 = Beacon.from_row(row)
        self.assertEqual(b2.title, "A")
        self.assertTrue(b2.favorite)

    def test_resource_json_fields(self):
        r = Resource(
            type=TYPE_WEB,
            title="T",
            alt_uris=["u1", "u2"],
            provider_ids={"a": "1"},
            metadata={"k": "v"},
        )
        row = r.to_row()
        r2 = Resource.from_row(row)
        self.assertEqual(r2.alt_uris, ["u1", "u2"])
        self.assertEqual(r2.provider_ids, {"a": "1"})
        self.assertEqual(r2.metadata, {"k": "v"})


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.store = db.BeaconStore(self.tmp.name)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def _add_web(self, title="Page", url="https://example.org/a", note=""):
        res = Resource(type=TYPE_WEB, canonical_id=url, title=title, primary_uri=url)
        loc = uld.build_uld(
            resource_id=res.resource_id,
            text_quote="hello world",
            heading_path=["Intro", "Overview"],
        )
        b = Beacon(title=title, note=note, tags=["research"], in_inbox=True)
        b.locations = [loc]
        self.store.put_beacon(b, resource=res)
        return b

    def test_put_and_get(self):
        b = self._add_web(note="important")
        got = self.store.get_beacon(b.beacon_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.note, "important")
        self.assertEqual(got.tags, ["research"])
        self.assertEqual(len(got.locations), 1)
        self.assertEqual(got.locations[0].heading_path, ["Intro", "Overview"])

    def test_count_and_list(self):
        self._add_web("A")
        self._add_web("B")
        self.assertEqual(self.store.count(), 2)

    def test_trash_restore(self):
        b = self._add_web()
        self.store.trash(b.beacon_id)
        self.assertEqual(self.store.count(), 0)
        self.store.restore(b.beacon_id)
        self.assertEqual(self.store.count(), 1)

    def test_integrity(self):
        self.assertTrue(self.store.integrity_check())


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.store = db.BeaconStore(self.tmp.name)
        res = Resource(
            type=TYPE_WEB,
            canonical_id="https://arizona.edu/policy",
            title="Title II Policy",
            primary_uri="https://arizona.edu/policy",
        )
        b = Beacon(
            title="Title II Policy",
            note="accessibility matters",
            tags=["research", "policy"],
            collections=["Title II"],
        )
        b.locations = [
            uld.build_uld(
                resource_id=res.resource_id,
                text_quote="Alternative formats required",
                heading_path=["Policy", "Alternative Formats"],
            )
        ]
        self.store.put_beacon(b, resource=res)

        res2 = Resource(
            type=TYPE_PODCAST_EPISODE,
            canonical_id="feed/ep1",
            title="Designing Accessible Apps",
            primary_uri="https://example.org/ep1.mp3",
        )
        b2 = Beacon(
            title="Keyboard Interaction point",
            note="use in PRD",
            tags=["accessibility", "product-design"],
        )
        b2.locations = [
            uld.build_uld(
                resource_id=res2.resource_id,
                text_quote="Accessibility must be part of architecture",
                media_start_ms=1132000,
            )
        ]
        self.store.put_beacon(b2, resource=res2)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def test_free_text(self):
        results = search.search(self.store, "accessibility")
        self.assertEqual(len(results), 2)

    def test_field_type(self):
        results = search.search(self.store, "type:podcastEpisode")
        self.assertEqual(len(results), 1)
        self.assertIn("Keyboard", results[0].title)

    def test_field_tag(self):
        results = search.search(self.store, "tag:policy")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Title II Policy")

    def test_domain(self):
        results = search.search(self.store, "domain:arizona.edu")
        self.assertEqual(len(results), 1)

    def test_collection(self):
        results = search.search(self.store, 'collection:"Title II"')
        self.assertEqual(len(results), 1)

    def test_phrase(self):
        results = search.search(self.store, '"alternative formats"')
        self.assertEqual(len(results), 1)

    def test_empty_returns_all(self):
        results = search.search(self.store, "")
        self.assertEqual(len(results), 2)

    def test_health_filter(self):
        b = self.store.list_beacons()[0]
        self.store.conn.execute(
            "UPDATE beacons SET health=? WHERE beacon_id=?", (HEALTH_BROKEN, b.beacon_id)
        )
        self.store.conn.commit()
        results = search.search(self.store, "health:broken")
        self.assertEqual(len(results), 1)

    def test_duplicates(self):
        # add a tracking-param duplicate of the policy page
        res = Resource(
            type=TYPE_WEB,
            canonical_id="https://arizona.edu/policy?utm_source=newsletter",
            title="Title II Policy dup",
            primary_uri="https://arizona.edu/policy?utm_source=newsletter",
        )
        b = Beacon(title="dup")
        self.store.put_beacon(b, resource=res)
        dups = search.find_duplicates(self.store)
        self.assertTrue(any(len(g) == 2 for g in dups))


class ULDTests(unittest.TestCase):
    def test_native_locator_strongest(self):
        loc = uld.build_uld(resource_id="r", native={"anchor": "sec2"}, text_quote="hello")
        r = uld.resolve(loc, "hello world")
        self.assertEqual(r.layer, "native")
        self.assertEqual(r.confidence, 1.0)

    def test_exact_text_match(self):
        loc = uld.build_uld(resource_id="r", text_quote="exact passage here")
        r = uld.resolve(loc, "some text exact passage here more text")
        self.assertEqual(r.layer, "textQuote")
        self.assertGreaterEqual(r.confidence, 0.9)

    def test_heading_path_match(self):
        loc = uld.build_uld(resource_id="r", heading_path=["Policy", "Alternative Formats"])
        content = "Policy section\nAlternative Formats body text"
        r = uld.resolve(loc, content)
        self.assertEqual(r.layer, "structural")

    def test_no_match_returns_review(self):
        loc = uld.build_uld(resource_id="r", text_quote="something not present")
        r = uld.resolve(loc, "totally different content")
        self.assertFalse(r.matched)
        self.assertEqual(r.layer, "none")

    def test_fuzzy_needs_review(self):
        loc = uld.build_uld(resource_id="r", text_quote="accessibility architecture planning")
        content = "the accessibility and architecture of planning matters"
        r = uld.resolve(loc, content)
        # fuzzy match should be under 0.9 -> needs review
        self.assertTrue(r.matched)
        self.assertLess(r.confidence, 0.9)


if __name__ == "__main__":
    unittest.main()
