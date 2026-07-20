"""Podcast feed parsing tests (no network; fixture XML)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import db, feeds
from quill.apps.beacon.model import TYPE_PODCAST_EPISODE, TYPE_PODCAST_SHOW

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>Accessible Tech</title>
    <link>https://example.org/show</link>
    <author>Jeff</author>
    <description>A show about accessible software.</description>
    <item>
      <title>Keyboard Interaction</title>
      <guid>ep-001</guid>
      <pubDate>Mon, 14 Jul 2026 10:00:00 GMT</pubDate>
      <enclosure url="https://example.org/ep1.mp3" length="1800000" type="audio/mpeg"/>
      <itunes:duration>22:41</itunes:duration>
      <description>How to design keyboard models.</description>
    </item>
    <item>
      <title>Screen Readers</title>
      <guid>ep-002</guid>
      <enclosure url="https://example.org/ep2.mp3" length="3600000" type="audio/mpeg"/>
      <itunes:duration>3600</itunes:duration>
    </item>
  </channel>
</rss>
"""


class FeedParseTests(unittest.TestCase):
    def test_parse_show_and_episodes(self):
        show = feeds.parse_feed(SAMPLE_RSS, feed_url="https://example.org/rss")
        self.assertEqual(show.title, "Accessible Tech")
        self.assertEqual(len(show.episodes), 2)
        ep = show.episodes[0]
        self.assertEqual(ep.title, "Keyboard Interaction")
        self.assertEqual(ep.guid, "ep-001")
        self.assertEqual(ep.enclosure_url, "https://example.org/ep1.mp3")
        self.assertEqual(ep.duration_ms, 22 * 60 * 1000 + 41 * 1000)

    def test_seconds_duration(self):
        show = feeds.parse_feed(SAMPLE_RSS)
        self.assertEqual(show.episodes[1].duration_ms, 3600 * 1000)

    def test_episode_to_beacon(self):
        show = feeds.parse_feed(SAMPLE_RSS)
        beacon, res = show.episodes[0].to_beacon("show_res_1")
        self.assertEqual(res.type, TYPE_PODCAST_EPISODE)
        self.assertEqual(res.canonical_id, "ep-001")
        self.assertEqual(res.metadata["show_resource_id"], "show_res_1")
        self.assertIn("podcast", beacon.tags)

    def test_show_to_beacon(self):
        show = feeds.parse_feed(SAMPLE_RSS, feed_url="https://example.org/rss")
        beacon, res = show.to_beacon()
        self.assertEqual(res.type, TYPE_PODCAST_SHOW)
        self.assertEqual(res.metadata["author"], "Jeff")


class FeedStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.store = db.BeaconStore(self.tmp.name)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def test_refresh_dedup_via_parse(self):
        # Drive refresh's dedup logic directly with a parsed show.
        show = feeds.parse_feed(SAMPLE_RSS, feed_url="https://example.org/rss")
        # add show + episodes once
        sbeacon, sres = show.to_beacon()
        self.store.put_beacon(sbeacon, resource=sres)
        added = 0
        for ep in show.episodes:
            beacon, res = ep.to_beacon(sres.resource_id)
            self.store.put_beacon(beacon, resource=res)
            added += 1
        self.assertEqual(added, 2)
        # second pass: all episodes already exist by guid -> skip
        added2 = 0
        for ep in show.episodes:
            if ep.guid and self.store.find_resource_by_canonical(ep.guid):
                continue
            added2 += 1
        self.assertEqual(added2, 0)

    def test_listen_later(self):
        from quill.apps.beacon import capture

        b, res = capture.capture("https://example.org/ep.mp3", title="ep")
        self.store.put_beacon(b, resource=res)
        feeds.listen_later(self.store, b.beacon_id)
        got = self.store.get_beacon(b.beacon_id)
        self.assertIn("Listen Later", got.collections)


if __name__ == "__main__":
    unittest.main()
