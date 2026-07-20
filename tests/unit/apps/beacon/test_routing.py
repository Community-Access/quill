"""Capture routing rules tests (PRD 14.5): keyword -> folder, first match wins.

Covers match semantics (case-insensitive substring, list order), the
one-keyword-one-folder uniqueness rule, persistence round-trip, and the
route() behavior: web resources only, explicit collection wins, Inbox flag
untouched.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import capture, routing
from quill.apps.beacon.routing import Rule


class MatchTests(unittest.TestCase):
    def test_first_match_wins(self):
        rules = [Rule("example.com", "First"), Rule("example", "Second")]
        self.assertEqual(routing.match_collection("https://example.com/a", rules), "First")

    def test_order_is_priority_not_specificity(self):
        rules = [Rule("example", "Broad"), Rule("example.com", "Narrow")]
        self.assertEqual(routing.match_collection("https://example.com/a", rules), "Broad")

    def test_case_insensitive_substring(self):
        rules = [Rule("NYTimes.com", "News")]
        self.assertEqual(routing.match_collection("https://www.nytimes.com/2026/x", rules), "News")

    def test_keyword_can_be_any_substring(self):
        rules = [Rule("/recipes/", "Cooking")]
        self.assertEqual(routing.match_collection("https://site.org/recipes/pie", rules), "Cooking")

    def test_no_match_returns_none(self):
        rules = [Rule("github.com", "Code")]
        self.assertIsNone(routing.match_collection("https://example.com", rules))

    def test_empty_rules_and_empty_url(self):
        self.assertIsNone(routing.match_collection("https://example.com", []))
        self.assertIsNone(routing.match_collection("", [Rule("a", "B")]))


class UniquenessTests(unittest.TestCase):
    def test_save_rejects_duplicate_keyword(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                routing.save_rules(tmp, [Rule("a.com", "One"), Rule("a.com", "Two")])

    def test_save_rejects_duplicate_keyword_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                routing.save_rules(tmp, [Rule("A.com", "One"), Rule("a.COM", "Two")])

    def test_save_rejects_empty_keyword_or_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                routing.save_rules(tmp, [Rule("", "One")])
            with self.assertRaises(ValueError):
                routing.save_rules(tmp, [Rule("a.com", "")])

    def test_load_drops_later_duplicates(self):
        # A hand-edited file with a reused keyword keeps the first rule only.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, routing.SETTINGS_FILE)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "rules": [
                            {"keyword": "a.com", "collection": "One"},
                            {"keyword": "A.COM", "collection": "Two"},
                        ]
                    },
                    fh,
                )
            rules = routing.load_rules(tmp)
            self.assertEqual([(r.keyword, r.collection) for r in rules], [("a.com", "One")])


class PersistenceTests(unittest.TestCase):
    def test_round_trip_preserves_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules = [
                Rule("github.com", "Code"),
                Rule("recipe", "Cooking"),
                Rule("nytimes.com", "News"),
            ]
            routing.save_rules(tmp, rules)
            loaded = routing.load_rules(tmp)
            self.assertEqual(
                [(r.keyword, r.collection) for r in loaded],
                [(r.keyword, r.collection) for r in rules],
            )

    def test_missing_and_corrupt_file_load_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(routing.load_rules(tmp), [])
            with open(os.path.join(tmp, routing.SETTINGS_FILE), "w", encoding="utf-8") as fh:
                fh.write("not json")
            self.assertEqual(routing.load_rules(tmp), [])


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.rules = [Rule("github.com", "Code"), Rule("recipe", "Cooking")]

    def test_routes_web_beacon_into_collection(self):
        beacon, res = capture.capture("https://github.com/quill/beacon")
        routed = routing.route(beacon, res, self.rules)
        self.assertEqual(routed, "Code")
        self.assertEqual(beacon.collections, ["Code"])

    def test_routed_beacon_stays_in_inbox(self):
        beacon, res = capture.capture("https://github.com/quill/beacon")
        routing.route(beacon, res, self.rules)
        self.assertTrue(beacon.in_inbox)

    def test_explicit_collection_wins(self):
        beacon, res = capture.capture("https://github.com/quill/beacon", collections=["Chosen"])
        routed = routing.route(beacon, res, self.rules)
        self.assertIsNone(routed)
        self.assertEqual(beacon.collections, ["Chosen"])

    def test_non_web_resource_not_routed(self):
        beacon, res = capture.capture("https://example.org/feed/rss")
        routed = routing.route(beacon, res, self.rules)
        self.assertIsNone(routed)
        beacon2, res2 = capture.capture(r"C:\github.com\notes.txt")
        self.assertIsNone(routing.route(beacon2, res2, self.rules))

    def test_web_passage_and_heading_are_routed(self):
        beacon, res = capture.capture("https://github.com/quill/beacon", selected_text="a passage")
        self.assertEqual(routing.route(beacon, res, self.rules), "Code")
        beacon2, res2 = capture.capture("https://github.com/quill/beacon", heading_path=["Intro"])
        self.assertEqual(routing.route(beacon2, res2, self.rules), "Code")

    def test_no_match_leaves_beacon_alone(self):
        beacon, res = capture.capture("https://example.com/page")
        self.assertIsNone(routing.route(beacon, res, self.rules))
        self.assertEqual(beacon.collections, [])


class BridgeIntegrationTests(unittest.TestCase):
    def test_handle_capture_applies_rules(self):
        from quill.apps.beacon import capture_bridge, db

        with tempfile.TemporaryDirectory() as tmp:
            routing.save_rules(tmp, [Rule("github.com", "Code")])
            db_path = os.path.join(tmp, "beacons.db")
            bridge = capture_bridge.CaptureBridge(db_path, data_dir=tmp, port=0)
            try:
                reply = bridge.handle_capture({"url": "https://github.com/quill/beacon"})
                self.assertTrue(reply["ok"])
                store = db.BeaconStore(db_path)
                b = store.get_beacon(reply["beacon_id"])
                self.assertEqual(b.collections, ["Code"])
                store.close()
            finally:
                bridge.stop()

    def test_handle_capture_explicit_collection_wins(self):
        from quill.apps.beacon import capture_bridge, db

        with tempfile.TemporaryDirectory() as tmp:
            routing.save_rules(tmp, [Rule("github.com", "Code")])
            db_path = os.path.join(tmp, "beacons.db")
            bridge = capture_bridge.CaptureBridge(db_path, data_dir=tmp, port=0)
            try:
                reply = bridge.handle_capture({
                    "url": "https://github.com/quill/beacon",
                    "collection": "Chosen",
                })
                store = db.BeaconStore(db_path)
                b = store.get_beacon(reply["beacon_id"])
                self.assertEqual(b.collections, ["Chosen"])
                store.close()
            finally:
                bridge.stop()


if __name__ == "__main__":
    unittest.main()
