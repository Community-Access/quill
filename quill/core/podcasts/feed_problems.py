"""Why a feed could not be read, in one plain sentence (check.md bugs 6 and 7).

Cast used to hand the listener whatever text the network library produced:
"[QUILL-PODCASTS-FEED-READ] Could not reach that feed: <urlopen error [Errno
11001] getaddrinfo failed>" in Recent Problems, and the same angle brackets in
the import report. A screen reader reads every one of those characters aloud,
and none of them says what happened or what to do.

So every failure is sorted into a small set of **kinds**, and each kind has one
sentence written for a person. The technical text is kept (``detail``) for the
log and the diagnostic bundle, where it is useful, and never spoken.

Three call sites share this module so the wording cannot drift between them:
the feed reader (which raises with the sentence), the import check's probe
(which reports it) and the Feed Check window (which shows the last one).

Two distinctions the old code got wrong, and the reason the kinds exist:

* **A 401 or 403 is not always a sign-in problem.** It is one when the podcast
  has saved credentials, or when the server asked for them (``WWW-Authenticate``).
  Otherwise a 403 is a host refusing podcast apps -- usually a bot check such as
  Cloudflare's "checking your browser" page -- and a 401 with no challenge is a
  publisher that has locked the feed, typically behind a paid subscription.
  Sending somebody to Feed Credentials for either is sending them nowhere.
* **"The address may have changed" is advice for some failures only.** A
  removed feed, a domain that no longer exists or an address that now returns
  a web page are worth a search for the show's new feed (:data:`WORTH_A_SEARCH`);
  a slow host is not.

wx-free, strict-typed, pure: nothing here performs a request.
"""

from __future__ import annotations

import socket
import ssl
import urllib.error
from dataclasses import dataclass

__all__ = [
    "GONE",
    "KINDS",
    "WORTH_A_SEARCH",
    "Problem",
    "classify",
    "looks_like_html",
    "plain",
    "sentence_for",
]

GONE = "gone"
REMOVED = "removed"
NO_SUCH_HOST = "no_such_host"
REFUSED = "refused"
CERTIFICATE = "certificate"
TLS = "tls"
TIMEOUT = "timeout"
WEB_PAGE = "web_page"
NOT_A_FEED = "not_a_feed"
EMPTY = "empty"
PAYWALLED = "paywalled"
SIGN_IN = "sign_in"
BOT_CHECK = "bot_check"
SERVER = "server"
REFUSED_REQUEST = "refused_request"
BAD_ADDRESS = "bad_address"
SAFE_MODE = "safe_mode"
UNKNOWN = "unknown"

#: One sentence per kind. Written to be heard: no codes, no brackets, and each
#: one says what happened rather than which exception carried it.
_SENTENCES: dict[str, str] = {
    GONE: "The host no longer has a feed at this address.",
    REMOVED: "The host says this feed has been removed for good.",
    NO_SUCH_HOST: "This podcast's web address no longer exists.",
    REFUSED: "The podcast's site is refusing every connection.",
    CERTIFICATE: "The site's security certificate is not valid, so no podcast app can trust it.",
    TLS: "The site's secure connection is broken.",
    TIMEOUT: "The host took too long to answer.",
    WEB_PAGE: "This address returns a web page, not a podcast feed.",
    NOT_A_FEED: "This address does not return a podcast feed.",
    EMPTY: "The feed is there, but it has no episodes.",
    PAYWALLED: "The publisher has locked this feed; it may now need a paid subscription.",
    SIGN_IN: (
        "This feed needs a sign-in, or did not accept the username and password. "
        "Use Feed Credentials on the podcast's menu."
    ),
    BOT_CHECK: "The feed's host is refusing podcast apps.",
    SERVER: "The host is having trouble right now.",
    REFUSED_REQUEST: "The host would not send the feed.",
    BAD_ADDRESS: "This is not a complete web address.",
    SAFE_MODE: "Podcast feeds are disabled in Safe Mode. Restart QUILL normally to use them.",
    UNKNOWN: "This feed could not be read.",
}

KINDS: tuple[str, ...] = tuple(_SENTENCES)

#: Failures after which looking for the show's new feed is the useful next
#: step: the feed is not coming back at this address.
WORTH_A_SEARCH: frozenset[str] = frozenset({
    GONE,
    REMOVED,
    NO_SUCH_HOST,
    WEB_PAGE,
    NOT_A_FEED,
    EMPTY,
})


@dataclass(frozen=True, slots=True)
class Problem:
    """A failure, sorted: its kind, the sentence to say, the text to log."""

    kind: str
    sentence: str
    detail: str = ""


def sentence_for(kind: str) -> str:
    """The plain sentence for *kind* (an unknown kind reads as unknown)."""
    return _SENTENCES.get(kind, _SENTENCES[UNKNOWN])


def looks_like_html(head: bytes | str) -> bool:
    """Whether the start of a response is a web page rather than a feed.

    Sniffed from the body, not the Content-Type: FeedBurner serves its
    "this feed is gone" page as ``text/xml``, and plenty of real feeds are
    served as ``text/html``. A body that opens a feed element is a feed even
    if an HTML fragment appears later (a show-notes ``<html>`` inside CDATA).
    """
    text = head.decode("utf-8", errors="replace") if isinstance(head, bytes) else head
    sample = text[:4096].lower()
    for marker in ("<rss", "<feed", "<rdf:rdf", "<channel"):
        if marker in sample:
            return False
    return "<html" in sample or "<!doctype html" in sample


def _http_kind(code: int, *, challenged: bool, had_credentials: bool) -> str:
    if code in (401, 403) and (had_credentials or challenged):
        return SIGN_IN
    if code == 401:
        return PAYWALLED
    if code == 403:
        return BOT_CHECK
    if code == 404:
        return GONE
    if code == 410:
        return REMOVED
    if code >= 500:
        return SERVER
    return REFUSED_REQUEST


def _chain(error: BaseException) -> list[BaseException]:
    """*error* and everything that caused it, outermost first, without loops."""
    seen: list[BaseException] = []
    current: BaseException | None = error
    while current is not None and current not in seen:
        seen.append(current)
        nxt = current.__cause__ or current.__context__
        if isinstance(current, urllib.error.URLError) and isinstance(current.reason, BaseException):
            nxt = current.reason
        current = nxt
    return seen


def classify(error: BaseException, *, had_credentials: bool = False) -> Problem:
    """Sort *error* into a :class:`Problem`. Never raises.

    An error that already carries a kind (a :class:`FeedReaderError` raised by
    the reader) keeps it. Otherwise the exception chain is walked for the
    first thing that says what happened: an HTTP status, a name lookup that
    failed, a refused connection, a certificate, a timeout.
    """
    detail = f"{error.__class__.__name__}: {error}"
    own = getattr(error, "kind", "")
    if isinstance(own, str) and own in _SENTENCES and own != UNKNOWN:
        return Problem(own, sentence_for(own), str(getattr(error, "detail", "") or detail))
    for link in _chain(error):
        if isinstance(link, urllib.error.HTTPError):
            headers = getattr(link, "headers", None)
            challenged = bool(headers is not None and headers.get("WWW-Authenticate"))
            kind = _http_kind(link.code, challenged=challenged, had_credentials=had_credentials)
            return Problem(kind, sentence_for(kind), detail)
        if isinstance(link, socket.gaierror):
            return Problem(NO_SUCH_HOST, sentence_for(NO_SUCH_HOST), detail)
        if isinstance(link, ConnectionRefusedError):
            return Problem(REFUSED, sentence_for(REFUSED), detail)
        if isinstance(link, ssl.SSLCertVerificationError):
            return Problem(CERTIFICATE, sentence_for(CERTIFICATE), detail)
        if isinstance(link, ssl.SSLError):
            return Problem(TLS, sentence_for(TLS), detail)
        if isinstance(link, TimeoutError | socket.timeout):
            return Problem(TIMEOUT, sentence_for(TIMEOUT), detail)
    lowered = detail.lower()
    if "getaddrinfo" in lowered or "name or service not known" in lowered:
        return Problem(NO_SUCH_HOST, sentence_for(NO_SUCH_HOST), detail)
    if "timed out" in lowered:
        return Problem(TIMEOUT, sentence_for(TIMEOUT), detail)
    if "certificate" in lowered:
        return Problem(CERTIFICATE, sentence_for(CERTIFICATE), detail)
    return Problem(UNKNOWN, sentence_for(UNKNOWN), detail)


def plain(error: BaseException) -> str:
    """The sentence to say or write down for *error* -- never the raw text."""
    return classify(error).sentence
