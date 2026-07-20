"""Capture bridge published-view routes (plan section 12).

The published pages are public (no bearer token header) and gated by the publish
token in the URL path. The bridge binds 127.0.0.1, so the preview is local-only.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import capture_bridge, db
from quill.apps.beacon.model import Beacon, Resource


def _get_raw(url):
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read().decode("utf-8")


class PublishedBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp, "beacons.db")
        self.store = db.BeaconStore(self.db_path)
        self.bridge = capture_bridge.CaptureBridge(self.db_path, data_dir=self.tmp, port=0)
        self.port = self.bridge.start()
        self.base = self.bridge.base_url
        # Seed a collection with one beacon via the bridge's own store so the
        # bridge's PublishManager (which uses bridge.store) can see it.
        res = Resource(title="A", type="web", primary_uri="https://x/a")
        b = Beacon(resource_id=res.resource_id, title="A", in_inbox=False)
        b.collections = ["Read"]
        self.bridge.store.put_beacon(b, resource=res)

    def tearDown(self):
        self.bridge.stop()
        self.store.close()

    def test_published_page_served_by_token(self):
        res = self.bridge.publisher.publish("Read", port=self.port)
        self.assertTrue(res["ok"], res)
        token = res["token"]
        code, ctype, body = _get_raw(f"{self.base}/published/{token}/")
        self.assertEqual(code, 200)
        self.assertTrue(ctype.startswith("text/html"), ctype)
        self.assertIn("Read", body)
        self.assertIn("<h1", body)

    def test_published_index_lists_collection(self):
        self.bridge.publisher.publish("Read", port=self.port)
        code, ctype, body = _get_raw(f"{self.base}/published/")
        self.assertEqual(code, 200)
        self.assertTrue(ctype.startswith("text/html"), ctype)
        self.assertIn("Read", body)

    def test_wrong_token_is_404(self):
        self.bridge.publisher.publish("Read", port=self.port)
        code, _ctype, _body = _get_raw(f"{self.base}/published/bogus-token/")
        self.assertEqual(code, 404)

    def test_published_route_needs_no_bearer_token(self):
        # No X-QuillBeacon-Token header is sent; the page is still served.
        res = self.bridge.publisher.publish("Read", port=self.port)
        code, _ctype, _body = _get_raw(f"{self.base}/published/{res['token']}/")
        self.assertEqual(code, 200)


if __name__ == "__main__":
    unittest.main()
