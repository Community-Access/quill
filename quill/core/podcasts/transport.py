"""Which schemes a podcast address may use, and how to try them (ear.md R29).

Jeff, 2026-09-30: "http and https podcasts should be allowed."

Cast refused ``http://`` outright, in six places, which is defensible security
advice and wrong as a product decision: a great many long-running independent
podcasts -- exactly the small, community and accessibility-focused shows this app
exists for -- are still served over plain http by a host that will never change.
Refusing them does not make the listener safer. It makes the app useless for them
and sends them to an app with no such scruples.

So both schemes are allowed, and the rule is **https first**:

1. A ``https://`` address is fetched as given.
2. A ``http://`` address is *first* asked for over https, because a host that
   supports both should be used securely whether or not its feed says so.
3. Only when the secure attempt genuinely fails does the plain-http address get
   used.

**A sign-in refusal is never retried over http**, and that is the one rule here
with teeth. A 401 or 403 means the server understood the request and declined it;
retrying it in clear text would put credentials on the wire to answer a question
that had already been answered. It is the difference between "https did not work
here" and "https worked and said no".

Nothing in this module performs a request. It decides *what to try in what order*
and answers whether a failure is retryable, so one rule serves the feed reader,
the download queue, chapters, transcripts and add-by-URL rather than each growing
its own version.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

__all__ = [
    "ALLOWED_SCHEMES",
    "attempts_for",
    "is_allowed",
    "is_plain_http",
    "may_retry_insecure",
    "scheme_note",
    "secure_form",
]

#: The two schemes a podcast address may use. Anything else -- ``file://``,
#: ``ftp://``, a bare hostname -- is refused, because a feed address is somebody
#: else's input and this is the whole allowlist.
ALLOWED_SCHEMES: tuple[str, ...] = ("https://", "http://")

#: Status codes that mean "understood, and no". Never retried in clear text.
_REFUSALS: frozenset[int] = frozenset({401, 402, 403, 407, 451})


def is_allowed(url: str) -> bool:
    """Whether *url* is a scheme Cast will fetch at all."""
    return str(url or "").lower().startswith(ALLOWED_SCHEMES)


def is_plain_http(url: str) -> bool:
    return str(url or "").lower().startswith("http://")


def secure_form(url: str) -> str:
    """*url* as https, whatever it arrived as. Unchanged if it is not http."""
    text = str(url or "")
    return "https://" + text[len("http://") :] if is_plain_http(text) else text


def attempts_for(url: str) -> tuple[str, ...]:
    """The addresses to try, in order.

    One entry for an https address; two for a plain-http one, secure first. An
    address whose scheme is not allowed yields nothing, so a caller that loops
    over this makes no request rather than having to remember to check first.
    """
    if not is_allowed(url):
        return ()
    if not is_plain_http(url):
        return (str(url),)
    secure = secure_form(url)
    return (secure, str(url)) if secure != url else (str(url),)


def may_retry_insecure(status: int | None = None, *, had_auth_refusal: bool = False) -> bool:
    """Whether a failed secure attempt may fall back to plain http.

    ``False`` for a sign-in refusal: the server understood and declined, so
    retrying in clear text would put credentials on the wire to re-ask a question
    that was already answered. ``True`` for a transport failure -- no certificate,
    no https listener, a connection reset -- which is "https does not work here".
    """
    if had_auth_refusal:
        return False
    if status is not None and int(status) in _REFUSALS:
        return False
    return True


def scheme_note(url: str) -> str:
    """What Player Information says about the address, or ``""`` when it is https.

    Only the insecure case is reported. "Feed: encrypted" on every other show
    would be a line that is always there and therefore never read, and the point
    is to make the exception visible.
    """
    return "Feed: not encrypted (plain http)" if is_plain_http(url) else ""
