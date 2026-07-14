from __future__ import annotations

from quill.core.titles import suggested_title_from_text


def test_plain_first_line() -> None:
    assert suggested_title_from_text("My great document\nmore text") == "My great document"


def test_skips_leading_blank_lines() -> None:
    assert suggested_title_from_text("\n\n   \nReal title here\n") == "Real title here"


def test_strips_markdown_heading_marker() -> None:
    assert suggested_title_from_text("# Chapter One\nbody") == "Chapter One"
    assert suggested_title_from_text("### Deep heading") == "Deep heading"


def test_strips_list_and_quote_markers() -> None:
    assert suggested_title_from_text("- shopping list") == "shopping list"
    assert suggested_title_from_text("> a quote") == "a quote"


def test_strips_inline_html_tags() -> None:
    assert suggested_title_from_text("<h1>HTML Title</h1>") == "HTML Title"
    # A doctype/opening tag line is skipped to the first text-bearing line.
    assert suggested_title_from_text("<!DOCTYPE html>\n<title>Real Page</title>") == "Real Page"


def test_sanitizes_invalid_filename_characters() -> None:
    assert suggested_title_from_text('Re: Q3/Q4 "plan" <draft>') == "Re Q3Q4 plan"


def test_truncates_to_max_length() -> None:
    long = "word " * 40
    result = suggested_title_from_text(long, max_length=20)
    assert len(result) <= 20
    assert not result.endswith(" ")


def test_empty_or_markup_only_returns_blank() -> None:
    assert suggested_title_from_text("") == ""
    assert suggested_title_from_text("\n\n") == ""
    assert suggested_title_from_text("###   \n") == ""
