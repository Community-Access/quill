"""Import OPML after the Downcast test (check.md bugs 3, 4, 5, 6, 11, 12, 15, 16).

Planning, the reachability probe and the report text, against the shapes the
real 1,307-entry Downcast export had. The probe is driven through its real code
with a fake ``feed_auth.urlopen_auth_safe``; no network.
"""

from __future__ import annotations

import urllib.error
from email.message import Message

import pytest

from quill.core.podcasts import feed_auth, opml_import, settings_catalog
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.opml import ImportedShow, OpmlValidationResult
from quill.core.podcasts.settings_resolver import set_value
from quill.core.podcasts.settings_types import LEVEL_GLOBAL
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.opml_import_report_dialog import format_report_text


def _entry(title: str, url: str, **kwargs: str) -> ImportedShow:
    return ImportedShow(title=title, feed_url=url, homepage="", folder_path=[], **kwargs)


# -- planning ---------------------------------------------------------------------


def test_an_address_with_no_real_host_is_not_imported() -> None:
    # Braillecast's address in the Downcast file is just http://feed/.
    plan = opml_import.plan_import(PodcastLibrary(), [_entry("Braillecast", "http://feed/")])
    assert plan.new == []
    assert plan.unusable == [("Braillecast (http://feed/)", "not a complete web address")]


def test_localhost_and_ip_addresses_are_still_web_addresses() -> None:
    plan = opml_import.plan_import(
        PodcastLibrary(),
        [_entry("Mine", "http://localhost:8000/feed"), _entry("Lan", "http://192.168.1.4/feed")],
    )
    assert len(plan.new) == 2


def test_two_different_feeds_with_one_name_in_the_same_file_are_both_flagged() -> None:
    plan = opml_import.plan_import(
        PodcastLibrary(),
        [
            _entry("The Mayan Crystal", "https://feeds.megaphone.fm/mayan"),
            _entry("Someone Else", "https://other.example/feed"),
            _entry("The Mayan Crystal", "https://rss.art19.com/mayan-crystal"),
        ],
    )
    assert len(plan.new) == 3  # never dropped
    assert plan.same_title_different_feed == [
        "The Mayan Crystal (https://feeds.megaphone.fm/mayan)",
        "The Mayan Crystal (https://rss.art19.com/mayan-crystal)",
    ]


def test_description_language_and_category_reach_the_new_subscription() -> None:
    library = PodcastLibrary()
    plan = opml_import.plan_import(
        library,
        [
            _entry(
                "Show",
                "https://a.example/feed",
                description="About the show.",
                language="en-US",
                category="/Technology",
            )
        ],
    )
    added = opml_import.apply_plan(library, plan)
    assert (added[0].description, added[0].language, added[0].category) == (
        "About the show.",
        "en-US",
        "/Technology",
    )


def test_counts_are_said_in_agreeing_words() -> None:
    one = opml_import.plan_import(PodcastLibrary(), [_entry("A", "https://a.example/f")])
    assert one.summary().startswith("1 entry read: 1 new, 0 already followed")
    two = opml_import.plan_import(
        PodcastLibrary(), [_entry("A", "https://a.example/f"), _entry("B", "https://b.example/f")]
    )
    assert two.summary().startswith("2 entries read")
    assert "(" not in two.summary()


# -- the probe --------------------------------------------------------------------


class _Response:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self, _n: int = -1) -> bytes:
        return self._payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


def _serve(monkeypatch: pytest.MonkeyPatch, payload: bytes, hops=(), error=None) -> None:
    def fake(_request: object, **_kwargs: object) -> _Response:
        if error is not None:
            raise error
        recorder = getattr(feed_auth._REDIRECTS, "hops", None)
        if recorder is not None:
            recorder.extend(hops)
        return _Response(payload)

    monkeypatch.setattr(opml_import.feed_auth, "urlopen_auth_safe", fake)
    monkeypatch.setattr("quill.core.net_retry.time.sleep", lambda _s: None)


_FEED_HEAD = b'<?xml version="1.0"?><rss version="2.0"><channel><title>T</title><item>'


def test_the_probe_reports_a_web_page_where_the_feed_was(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, b'<!doctype html>\n<html lang="en"><head><title>ED.com</title>')
    result = opml_import.probe_feed("https://expireddomains.com/domain/euphonie.media")
    assert result.ok is False
    assert result.error == "This address returns a web page, not a podcast feed."


def test_the_probe_reports_a_small_feed_with_no_episodes(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, b'<?xml version="1.0"?><rss><channel><title>ReMade</title></channel></rss>')
    result = opml_import.probe_feed("https://feeds.megaphone.fm/remade")
    assert result.ok is False
    assert result.error == "The feed is there, but it has no episodes."


def test_a_bot_check_is_not_counted_as_a_private_feed(monkeypatch: pytest.MonkeyPatch) -> None:
    message = Message()
    message["Server"] = "cloudflare"
    error = urllib.error.HTTPError("https://www.macobserver.com/rss", 403, "F", message, None)
    _serve(monkeypatch, b"", error=error)
    result = opml_import.probe_feed("https://www.macobserver.com/rss/dailyobservations_mp3.xml")
    assert result.ok is False
    assert result.error == "The feed's host is refusing podcast apps."


def test_only_a_permanent_redirect_is_a_new_address(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, _FEED_HEAD, hops=[(302, "https://feeds.feedburner.com/x")])
    assert opml_import.probe_feed("http://feeds.feedburner.com/TEDTalks").corrected_url == ""
    _serve(monkeypatch, _FEED_HEAD, hops=[(301, "https://new.example/feed")])
    assert opml_import.probe_feed("https://old.example/feed").corrected_url == (
        "https://new.example/feed"
    )


def test_a_probe_failure_is_a_plain_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    _serve(monkeypatch, b"", error=urllib.error.URLError(socket.gaierror(11001, "getaddrinfo")))
    result = opml_import.probe_feed("http://xml.nfowars.example/Alex.rss")
    assert result.error == "This podcast's web address no longer exists."


# -- the report -------------------------------------------------------------------


def _moved() -> list[OpmlValidationResult]:
    return [
        OpmlValidationResult("Show", "https://old.example/f", True, "", "https://new.example/f")
    ]


def test_a_permanent_move_is_applied_only_when_the_setting_allows() -> None:
    show = PodcastShow(id="s1", title="Show", feed_url="https://old.example/f")
    library = PodcastLibrary(shows=[show])

    off = opml_import.apply_permanent_moves(library, _moved())
    assert off[0].applied is False
    assert show.feed_url == "https://old.example/f"

    definition = settings_catalog.definition("follow_redirects")
    assert definition is not None
    set_value(library, definition, True, level=LEVEL_GLOBAL)
    on = opml_import.apply_permanent_moves(library, _moved())
    assert on[0].applied is True
    assert show.feed_url == "https://new.example/f"


def test_the_report_says_what_actually_happened_to_moved_feeds() -> None:
    applied = [
        OpmlValidationResult(
            "Show", "https://old.example/f", True, "", "https://new.example/f", applied=True
        )
    ]
    text = format_report_text(applied)
    assert "Updated to the feed's new address" in text
    assert "- Show, now at https://new.example/f" in text
    assert "1 updated to a new address" in text
    for claim in ("iTunes", "Corrected", "->"):
        assert claim not in text

    left = format_report_text(_moved())
    assert "left alone because Follow permanent feed redirects is off" in left
    assert "0 updated to a new address" in left
