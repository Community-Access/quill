"""Tests for the Email hand-off spine (#900)."""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

from quill.core.email_handoff import build_mailto
from quill.core.fragment import Fragment, FragmentFormat


def test_build_mailto_uses_title_as_default_subject() -> None:
    frag = Fragment(markup="Ada Lovelace was a mathematician.", title="Ada Lovelace")
    url = build_mailto(frag, FragmentFormat.TEXT)
    parsed = urlparse(url)
    assert parsed.scheme == "mailto"
    query = parse_qs(parsed.query)
    assert query["subject"] == ["Ada Lovelace"]
    assert query["body"] == ["Ada Lovelace was a mathematician."]


def test_build_mailto_explicit_subject_overrides_title() -> None:
    frag = Fragment(markup="body text", title="Fragment Title")
    url = build_mailto(frag, FragmentFormat.TEXT, subject="My Subject")
    query = parse_qs(urlparse(url).query)
    assert query["subject"] == ["My Subject"]


def test_build_mailto_falls_back_to_generic_subject() -> None:
    frag = Fragment(markup="body text")
    url = build_mailto(frag, FragmentFormat.TEXT)
    query = parse_qs(urlparse(url).query)
    assert query["subject"] == ["Shared from QUILL"]


def test_build_mailto_body_matches_the_requested_format() -> None:
    frag = Fragment(markup="**bold** text")
    text_url = build_mailto(frag, FragmentFormat.TEXT)
    markdown_url = build_mailto(frag, FragmentFormat.MARKDOWN)
    text_body = unquote(parse_qs(urlparse(text_url).query)["body"][0])
    markdown_body = unquote(parse_qs(urlparse(markdown_url).query)["body"][0])
    assert text_body == "bold text"
    assert markdown_body == "**bold** text"


def test_build_mailto_percent_encodes_special_characters() -> None:
    frag = Fragment(markup="a & b = c?", title="Q & A")
    url = build_mailto(frag, FragmentFormat.TEXT)
    query = parse_qs(urlparse(url).query)
    assert query["subject"] == ["Q & A"]
    assert query["body"] == ["a & b = c?"]
