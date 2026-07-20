"""Tests for capture, importers, exporters, media. Stdlib unittest."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import capture, db, exporters, importers, media
from quill.apps.beacon.model import (
    TYPE_FOLDER,
    TYPE_PODCAST_EPISODE,
    TYPE_RADIO_STREAM,
    TYPE_WEB,
)


class CaptureTests(unittest.TestCase):
    def test_canonicalize_drops_utm(self):
        c = capture.canonicalize_url("https://EXAMPLE.org/a?utm_source=x&keep=1#frag")
        self.assertEqual(c, "https://example.org/a?keep=1")

    def test_detect_web(self):
        self.assertEqual(capture.detect_type("https://example.org/page"), TYPE_WEB)

    def test_detect_folder(self):
        d = tempfile.mkdtemp()
        self.assertEqual(capture.detect_type(d), TYPE_FOLDER)

    def test_capture_web_builds_uld(self):
        b, res = capture.capture(
            "https://example.org/p", title="P", selected_text="hello world", heading_path=["Intro"]
        )
        self.assertEqual(res.type, "webPassage")
        self.assertEqual(b.title, "P")
        self.assertTrue(b.locations[0].text_quote.get("exact"))

    def test_capture_podcast_timepoint(self):
        b, res = capture.capture("https://example.org/ep.mp3", media_start_ms=1132000, title="ep")
        self.assertEqual(res.type, TYPE_PODCAST_EPISODE)
        self.assertEqual(b.locations[0].media_start_ms, 1132000)

    def test_clipboard_picks_first_url(self):
        res = capture.capture_from_clipboard("notes\nhttps://example.org/x\nmore")
        self.assertIsNotNone(res)


class ImporterTests(unittest.TestCase):
    HTML = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p>
  <DT><H3>Research</H3>
  <DL><p>
    <DT><A HREF="https://example.org/a">Page A</A>
  </DL><p>
</DL><p>"""

    def test_import_html(self):
        items = list(importers.import_html(self.HTML))
        self.assertEqual(len(items), 1)
        b, res, folders = items[0]
        self.assertEqual(res.primary_uri, "https://example.org/a")
        self.assertEqual(b.title, "Page A")
        self.assertEqual(folders, ["Research"])
        self.assertEqual(b.collections, ["Research"])

    def test_import_m3u(self):
        text = "#EXTM3U\n#EXTINF:-1,Station\nhttps://stream.example.org/live\n"
        items = list(importers.import_m3u(text))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][1].type, TYPE_RADIO_STREAM)

    def test_import_text(self):
        items = list(importers.import_text("https://a.org\nhttps://b.org"))
        self.assertEqual(len(items), 2)

    def test_import_csv(self):
        text = "url,title,note,tags,collection\nhttps://a.org,A,note,x; y,Col\n"
        items = list(importers.import_csv(text))
        self.assertEqual(len(items), 1)
        b, res = items[0]
        self.assertEqual(b.title, "A")
        self.assertEqual(b.note, "note")
        self.assertEqual(b.tags, ["x", "y"])
        self.assertEqual(b.collections, ["Col"])

    def test_import_opml(self):
        text = (
            '<?xml version="1.0"?><opml><body><outline text="Tech">'
            '<outline type="rss" text="Show" xmlUrl="https://feed.example.org/rss"/>'
            '</outline></body></opml>'
        )
        items = list(importers.import_opml(text))
        self.assertEqual(len(items), 1)
        self.assertIn("podcast", items[0][0].tags)


class ExporterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.store = db.BeaconStore(self.tmp.name)
        from quill.apps.beacon import uld
        from quill.apps.beacon.model import Beacon, Resource

        res = Resource(
            type=TYPE_WEB,
            canonical_id="https://example.org/a",
            title="A",
            primary_uri="https://example.org/a",
        )
        b = Beacon(title="A", note="note", tags=["t"], collections=["Research"])
        b.locations = [uld.build_uld(resource_id=res.resource_id, text_quote="hi")]
        self.store.put_beacon(b, resource=res)
        self.beacon_id = b.beacon_id

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def test_json_roundtrip(self):
        js = exporters.export_json(self.store)
        self.assertIn('"beacons"', js)
        self.assertIn("example.org/a", js)
        # re-import
        items = list(importers.import_json(js))
        self.assertEqual(len(items), 1)

    def test_html_has_link(self):
        html = exporters.export_html(self.store)
        self.assertIn('HREF="https://example.org/a"', html)
        self.assertIn("Research", html)

    def test_markdown(self):
        md = exporters.export_markdown(self.store)
        self.assertIn("[A](https://example.org/a)", md)

    def test_csv(self):
        csv_text = exporters.export_csv(self.store)
        self.assertIn("https://example.org/a", csv_text)

    def test_text(self):
        t = exporters.export_text(self.store)
        self.assertIn("https://example.org/a", t)


class MediaTests(unittest.TestCase):
    def test_p2_chapters(self):
        data = {
            "version": "1.2",
            "chapters": [
                {"startTime": 0, "title": "Intro"},
                {"startTime": 22.41, "title": "Keyboard Interaction"},
            ],
        }
        ch = media.parse_podcasting2_chapters(data, "r1")
        self.assertEqual(len(ch), 2)
        self.assertEqual(ch[1].start_ms, 22410)
        self.assertEqual(ch[1].source_type, "publisher")

    def test_id3_chapters(self):
        frames = [
            {"kind": "CHAP", "element_id": "ch1", "start_ms": 0, "end_ms": 10000, "title": "Intro"},
            {
                "kind": "CHAP",
                "element_id": "ch2",
                "start_ms": 10000,
                "end_ms": 20000,
                "title": "Body",
            },
        ]
        ch = media.parse_id3_chapters(frames, "r1")
        self.assertEqual(len(ch), 2)
        self.assertEqual(ch[0].title, "Intro")

    def test_merge_publisher_wins(self):
        pub = media.parse_podcasting2_chapters(
            {"chapters": [{"startTime": 0, "title": "Pub Intro"}]}, "r1"
        )
        pers = [
            media.MediaChapter(
                resource_id="r1", source_type="personal", title="My Intro", start_ms=0
            )
        ]
        merged = media.merge_chapters(pub, pers)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].title, "Pub Intro")

    def test_fmt_time(self):
        self.assertEqual(media.fmt_time(0), "0:00")
        self.assertEqual(media.fmt_time(2241000), "37:21")
        self.assertEqual(media.fmt_time(3721000 + 3600 * 1000), "2:02:01")


if __name__ == "__main__":
    unittest.main()
