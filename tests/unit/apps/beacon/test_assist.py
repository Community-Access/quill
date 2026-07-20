"""Intelligent assistance tests (PRD 47): tags, summary, relationships, semantic hook."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import assist, capture, db


class TagSuggestTests(unittest.TestCase):
    def test_suggests_by_frequency(self):
        text = "accessibility keyboard navigation keyboard focus keyboard access"
        tags = assist.suggest_tags(text, limit=3)
        self.assertIn("keyboard", tags)
        self.assertEqual(tags[0], "keyboard")

    def test_excludes_existing(self):
        text = "keyboard keyboard mouse mouse"
        tags = assist.suggest_tags(text, existing=["keyboard"], limit=5)
        self.assertIn("mouse", tags)
        self.assertNotIn("keyboard", tags)

    def test_stopwords_filtered(self):
        tags = assist.suggest_tags("the quick brown fox jumps over the lazy dog")
        self.assertNotIn("the", tags)
        self.assertIn("fox", tags)


class SummaryTests(unittest.TestCase):
    def test_short_text_returned(self):
        s = "Just one sentence here."
        self.assertEqual(assist.extractive_summary(s), s)

    def test_picks_top_sentences_in_order(self):
        text = (
            "Keyboard access is essential. "
            "Accessibility matters a great deal for keyboard users. "
            "The weather is mild today. "
            "Keyboard users need focus management."
        )
        summary = assist.extractive_summary(text, max_sentences=2)
        # The two keyboard sentences should win over the weather sentence.
        self.assertIn("Keyboard", summary)
        self.assertNotIn("weather", summary)
        # Order preserved: the earlier keyboard sentence comes first.
        self.assertLess(summary.index("Keyboard access"), summary.index("Keyboard users"))

    def test_empty(self):
        self.assertEqual(assist.extractive_summary(""), "")


class RelationshipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.store = db.BeaconStore(self.tmp.name)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def _add(self, url, title, tags=None, collection=None):
        b, res = capture.capture(url, title=title, tags=tags or [])
        if collection:
            b.collections = [collection]
        self.store.put_beacon(b, resource=res)
        return b

    def test_shared_tags_rank_first(self):
        a = self._add("https://example.org/a", "A", tags=["accessibility", "keyboard"])
        self._add("https://example.org/b", "B", tags=["keyboard", "focus"])
        self._add("https://other.example/c", "C", tags=["cooking"])
        rels = assist.suggest_relationships(self.store, a.beacon_id)
        self.assertEqual(rels[0]["title"], "B")
        self.assertGreater(rels[0]["score"], 0)
        self.assertTrue(any("keyboard" in r for r in rels[0]["reasons"]))
        # C shares no tags, collections, or domain -> not suggested.
        self.assertFalse(any(r["title"] == "C" for r in rels))

    def test_excludes_self_and_already_related(self):
        a = self._add("https://example.org/a", "A", tags=["t"])
        b = self._add("https://example.org/b", "B", tags=["t"])
        from quill.apps.beacon.model import Relationship

        self.store.add_relationship(Relationship(src_beacon=a.beacon_id, tgt_beacon=b.beacon_id))
        rels = assist.suggest_relationships(self.store, a.beacon_id)
        self.assertFalse(any(r["beacon_id"] == a.beacon_id for r in rels))
        self.assertFalse(any(r["beacon_id"] == b.beacon_id for r in rels))


class SemanticHookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.store = db.BeaconStore(self.tmp.name)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def test_no_index_returns_empty(self):
        b, res = capture.capture("https://example.org/a", title="A")
        self.store.put_beacon(b, resource=res)
        self.assertEqual(assist.semantic_search(self.store, "anything"), [])

    def test_index_plugged_in(self):
        b, res = capture.capture("https://example.org/a", title="A")
        self.store.put_beacon(b, resource=res)

        class FakeIndex:
            def search(self, query, *, limit=20):
                return [(b.beacon_id, 0.9)]

        results = assist.semantic_search(self.store, "a", index=FakeIndex())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "A")
        self.assertAlmostEqual(results[0]["score"], 0.9)

    def test_index_filters_trashed(self):
        b, res = capture.capture("https://example.org/a", title="A")
        self.store.put_beacon(b, resource=res)
        self.store.trash(b.beacon_id)

        class FakeIndex:
            def search(self, query, *, limit=20):
                return [(b.beacon_id, 0.9)]

        self.assertEqual(assist.semantic_search(self.store, "a", index=FakeIndex()), [])


if __name__ == "__main__":
    unittest.main()
