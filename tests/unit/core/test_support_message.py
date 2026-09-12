"""The one message every app sends to support.

Pure by design, so the whole shape -- subject, body, the mailto handoff and the
rule about what is optional -- is testable without a mail client, a network or
wx.
"""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

from quill.core.support_message import (
    MAILTO_URL_LIMIT,
    SUPPORT_EMAIL,
    SupportMessage,
    build_body,
    build_mailto_url,
    build_subject,
    validate,
)


def _message(**overrides: object) -> SupportMessage:
    fields: dict[str, object] = {
        "product": "Quill Radio 3.0.0",
        "summary": "The stream stops after a second",
        "message": "I press Play and it stops.",
    }
    fields.update(overrides)
    return SupportMessage(**fields)  # type: ignore[arg-type]


def test_the_subject_names_the_product_first() -> None:
    """Triage's first job is "which of nine products is this?" -- and the app
    already knows. Making a person infer it from the body is work we handed
    them for nothing."""
    assert build_subject(_message()).startswith("[Quill Radio 3.0.0] ")


def test_an_empty_summary_still_produces_a_usable_subject() -> None:
    assert build_subject(_message(summary="")) == "[Quill Radio 3.0.0] Support request"


def test_the_body_omits_sections_nobody_filled_in() -> None:
    """Empty headings read as noise to a screen reader and as sloppiness to
    the person answering."""
    body = build_body(_message())
    assert "What happened" in body
    assert "What I expected" not in body
    assert "Steps to reproduce" not in body


def test_the_body_carries_what_the_app_knows() -> None:
    body = build_body(
        _message(
            platform="Windows-11-10.0.26200",
            screen_reader="JAWS",
            reply_email="reader@example.com",
        )
    )
    assert "Product: Quill Radio 3.0.0" in body
    assert "Operating system: Windows-11-10.0.26200" in body
    assert "Screen reader: JAWS" in body
    assert "Reply to: reader@example.com" in body


def test_the_mailto_url_addresses_support_and_encodes_the_message() -> None:
    url, shortened = build_mailto_url(_message())
    parsed = urlparse(url)
    assert parsed.scheme == "mailto"
    assert unquote(parsed.path) == SUPPORT_EMAIL
    query = parse_qs(parsed.query)
    assert query["subject"][0].startswith("[Quill Radio 3.0.0]")
    assert "I press Play and it stops." in query["body"][0]
    assert shortened is False


def test_a_long_message_is_shortened_and_says_so() -> None:
    """A mail client that quietly opens with half a bug report is the failure
    this flag exists to prevent: the caller puts the whole text on the
    clipboard and says that out loud."""
    url, shortened = build_mailto_url(_message(message="z" * 6000))
    assert shortened is True
    assert len(url) <= MAILTO_URL_LIMIT
    assert "clipboard" in unquote(url)


def test_the_email_address_is_optional_and_a_wrong_one_is_caught() -> None:
    """Somebody who does not want to give an address should still be able to
    report a problem. They simply will not get an answer."""
    assert validate(_message(reply_email="")) == []
    assert validate(_message(reply_email="reader@example.com")) == []
    assert validate(_message(reply_email="reader.example.com"))


def test_a_message_with_nothing_in_it_is_refused_in_reading_order() -> None:
    problems = validate(_message(summary="", message=""))
    assert len(problems) == 2
    assert "subject" in problems[0]
