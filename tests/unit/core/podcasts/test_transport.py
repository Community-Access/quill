"""Which schemes a podcast address may use, and in what order (ear.md R29).

Jeff: "http and https podcasts should be allowed." Cast refused http outright in
six places, which is defensible security advice and wrong as a product decision:
a great many long-running independent shows -- exactly the small and
accessibility-focused ones this app exists for -- are served over plain http by a
host that will never change. Refusing them sends the listener to an app with no
such scruples.
"""

from __future__ import annotations

from quill.core.podcasts.transport import (
    attempts_for,
    is_allowed,
    is_plain_http,
    may_retry_insecure,
    scheme_note,
    secure_form,
)


def test_both_schemes_are_allowed() -> None:
    assert is_allowed("https://a/f.xml")
    assert is_allowed("http://a/f.xml")


def test_nothing_else_is() -> None:
    """A feed address is somebody else's input, and this is the whole allowlist."""
    for bad in ("file:///etc/passwd", "ftp://a/f.xml", "a/f.xml", "", "javascript:alert(1)"):
        assert not is_allowed(bad)


def test_an_https_address_is_tried_once() -> None:
    assert attempts_for("https://a/f.xml") == ("https://a/f.xml",)


def test_a_plain_http_address_is_asked_for_over_https_first() -> None:
    """A host that supports both should be used securely whether its feed says so."""
    assert attempts_for("http://a/f.xml") == ("https://a/f.xml", "http://a/f.xml")


def test_a_disallowed_scheme_yields_no_attempts() -> None:
    """So a caller that loops over this makes no request rather than having to
    remember to check first."""
    assert attempts_for("ftp://a/f.xml") == ()


def test_the_scheme_is_matched_case_insensitively() -> None:
    assert is_allowed("HTTPS://a/f.xml")
    assert is_plain_http("HTTP://a/f.xml")


def test_secure_form_upgrades_only_http() -> None:
    assert secure_form("http://a/f.xml") == "https://a/f.xml"
    assert secure_form("https://a/f.xml") == "https://a/f.xml"
    assert secure_form("ftp://a/f.xml") == "ftp://a/f.xml"


def test_a_transport_failure_may_fall_back() -> None:
    """No certificate, no https listener, a reset: "https does not work here"."""
    assert may_retry_insecure(None) is True
    assert may_retry_insecure(503) is True
    assert may_retry_insecure(404) is True


def test_a_sign_in_refusal_is_never_retried_in_clear_text() -> None:
    """The server understood and declined. Retrying over http would put
    credentials on the wire to re-ask a question that was already answered."""
    for status in (401, 402, 403, 407, 451):
        assert may_retry_insecure(status) is False
    assert may_retry_insecure(None, had_auth_refusal=True) is False


def test_only_the_insecure_case_is_reported() -> None:
    """ "Encrypted" on every other show would be a line that is never read."""
    assert scheme_note("http://a/f.xml") == "Feed: not encrypted (plain http)"
    assert scheme_note("https://a/f.xml") == ""
