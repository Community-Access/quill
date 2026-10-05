"""Every feed failure gets a plain sentence (check.md bugs 6 and 7).

The shapes are the real ones from the 2026-10-04 Downcast import test
(``diag.json``): a domain that no longer resolves, 404 and 410 pages,
Cloudflare's 403 "Just a moment..." page, art19's bare 401, FeedBurner's gone
page served as ``text/xml``, an expired domain's sales page.
"""

from __future__ import annotations

import socket
import ssl
import urllib.error
from email.message import Message

import pytest

from quill.core.podcasts import feed_problems
from quill.core.podcasts.feed_problems import classify, looks_like_html, plain


def _http(code: int, headers: dict[str, str] | None = None) -> urllib.error.HTTPError:
    message = Message()
    for name, value in (headers or {}).items():
        message[name] = value
    return urllib.error.HTTPError("https://feeds.example.com/x.rss", code, "r", message, None)


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (_http(404), feed_problems.GONE),
        (_http(410), feed_problems.REMOVED),
        (_http(503), feed_problems.SERVER),
        # art19's Wondery+ shows answer a bare 401: a locked feed, not a sign-in.
        (_http(401), feed_problems.PAYWALLED),
        # The Mac Observer: Cloudflare's bot check answers 403 to every podcast app.
        (_http(403, {"Server": "cloudflare"}), feed_problems.BOT_CHECK),
        (_http(401, {"WWW-Authenticate": 'Basic realm="x"'}), feed_problems.SIGN_IN),
        (
            urllib.error.URLError(socket.gaierror(11001, "getaddrinfo failed")),
            feed_problems.NO_SUCH_HOST,
        ),
        (urllib.error.URLError(ConnectionRefusedError(10061, "refused")), feed_problems.REFUSED),
        (
            urllib.error.URLError(ssl.SSLCertVerificationError(1, "certificate verify failed")),
            feed_problems.CERTIFICATE,
        ),
        (urllib.error.URLError(ssl.SSLError(1, "handshake failure")), feed_problems.TLS),
        (TimeoutError("The read operation timed out"), feed_problems.TIMEOUT),
    ],
)
def test_each_failure_is_sorted_into_its_kind(error: BaseException, kind: str) -> None:
    assert classify(error).kind == kind


def test_a_403_is_a_sign_in_problem_only_when_credentials_were_sent() -> None:
    assert classify(_http(403), had_credentials=True).kind == feed_problems.SIGN_IN
    assert classify(_http(403)).kind == feed_problems.BOT_CHECK


def test_what_is_said_never_carries_codes_brackets_or_exception_text() -> None:
    raw = urllib.error.URLError(socket.gaierror(11001, "getaddrinfo failed"))
    said = plain(raw)
    assert said == "This podcast's web address no longer exists."
    for leak in ("[QUILL", "<urlopen", "Errno", "getaddrinfo"):
        assert leak not in said
    # ...and the technical text is kept for the log.
    assert "getaddrinfo" in classify(raw).detail


def test_a_reader_error_keeps_the_kind_it_was_raised_with() -> None:
    from quill.core.podcasts.feed_reader import FeedReaderError

    error = FeedReaderError("ignored", kind=feed_problems.WEB_PAGE, detail="d")
    assert classify(error).sentence == "This address returns a web page, not a podcast feed."


def test_only_lost_feeds_are_worth_a_search() -> None:
    assert feed_problems.GONE in feed_problems.WORTH_A_SEARCH
    assert feed_problems.WEB_PAGE in feed_problems.WORTH_A_SEARCH
    assert feed_problems.TIMEOUT not in feed_problems.WORTH_A_SEARCH
    assert feed_problems.BOT_CHECK not in feed_problems.WORTH_A_SEARCH


def test_web_pages_are_told_apart_from_feeds_by_their_body() -> None:
    # FeedBurner's gone page for Seminars@Hadley, served as text/xml.
    hadley = b'<!DOCTYPE html>\n<html lang="en" dir="ltr" prefix="content: http://purl.org/'
    expired = b'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">'
    feed = b'<?xml version="1.0"?><rss version="2.0"><channel><description><![CDATA[<html>'
    assert looks_like_html(hadley)
    assert looks_like_html(expired)
    assert not looks_like_html(feed)
