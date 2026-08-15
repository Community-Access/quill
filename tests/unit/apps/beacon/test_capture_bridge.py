"""Capture bridge tests (PRD 46): localhost HTTP, token auth, origin check.

Uses only stdlib urllib so it runs without ``requests``. The bridge listens on
an ephemeral port (port=0) and writes to a temp data dir.

The request timeout is deliberately generous: these are loopback calls, so a
slow one means the machine is busy (a full-suite run) rather than that the
bridge is broken, and a timeout surfaces as an uncaught URLError -- a failure
about load wearing the costume of a failure about behaviour.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import capture_bridge, db


def _get(url, token=None, origin=None):
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("X-QuillBeacon-Token", token)
    if origin:
        req.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def _post(url, body, token=None, origin=None):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-QuillBeacon-Token", token)
    if origin:
        req.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


class CaptureBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp, "beacons.db")
        self.store = db.BeaconStore(self.db_path)
        self.bridge = capture_bridge.CaptureBridge(self.db_path, data_dir=self.tmp, port=0)
        self.port = self.bridge.start()
        self.base = self.bridge.base_url

    def tearDown(self):
        self.bridge.stop()
        self.store.close()

    def test_health_public(self):
        code, body = _get(self.base + "/health")
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])

    def test_capture_requires_token(self):
        code, body = _post(self.base + "/capture", {"url": "https://example.org/a"})
        self.assertEqual(code, 401)

    def test_capture_writes_beacon(self):
        code, body = _post(
            self.base + "/capture",
            {
                "url": "https://example.org/a",
                "title": "A",
                "tags": ["t1", "t2"],
                "collection": "Read",
            },
            token=self.bridge.token,
        )
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])
        bid = body["beacon_id"]
        b = self.store.get_beacon(bid)
        self.assertIsNotNone(b)
        self.assertEqual(b.title, "A")
        self.assertIn("t1", b.tags)
        self.assertIn("Read", b.collections)

    def test_capture_selection_becomes_note(self):
        code, body = _post(
            self.base + "/capture",
            {"url": "https://example.org/b", "title": "B", "selection": "quoted text"},
            token=self.bridge.token,
        )
        self.assertEqual(code, 200)
        b = self.store.get_beacon(body["beacon_id"])
        self.assertEqual(b.note, "quoted text")
        self.assertIn("selection", b.tags)

    def test_capture_batch(self):
        tabs = [
            {"url": "https://example.org/x", "title": "X"},
            {"url": "https://example.org/y", "title": "Y"},
        ]
        code, body = _post(self.base + "/capture-batch", {"tabs": tabs}, token=self.bridge.token)
        self.assertEqual(code, 200)
        self.assertEqual(body["count"], 2)
        self.assertEqual(self.store.count(), 2)

    def test_rejects_bad_origin(self):
        # A non-extension origin must be rejected even with a valid token.
        code, body = _post(
            self.base + "/capture",
            {"url": "https://example.org/z"},
            token=self.bridge.token,
            origin="https://evil.com",
        )
        self.assertEqual(code, 401)

    def test_collections_endpoint(self):
        _post(
            self.base + "/capture",
            {"url": "https://example.org/c", "title": "C", "collection": "Read"},
            token=self.bridge.token,
        )
        code, body = _get(self.base + "/collections", token=self.bridge.token)
        self.assertEqual(code, 200)
        names = body["collections"]
        self.assertIn("Read", names)

    def test_token_persisted(self):
        # A second bridge over the same data dir reuses the token.
        b2 = capture_bridge.CaptureBridge(self.db_path, data_dir=self.tmp, port=0)
        self.assertEqual(b2.token, self.bridge.token)
        b2.stop()


if __name__ == "__main__":
    unittest.main()
