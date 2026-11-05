"""Block markup round trips against representative Gutenberg-style fixtures (wordpress.md 8.5).

``fixtures_blocks/`` holds hand-written markup in the shape WordPress 6.4 and
later saves: one file per kind of block, including a plugin's block and a
dynamic one. They are *not* the official Gutenberg fixture corpus
(``test/integration/fixtures/blocks`` in the Gutenberg repository), which is
not vendored; these check the promises QUILL makes on the shapes people meet.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.wordpress import block_edit as be
from quill.core.wordpress import block_spans as bs
from quill.core.wordpress.blocks import parse, serialize
from quill.core.wordpress.fences import convert_markdown, post_to_markdown

FIXTURES = Path(__file__).with_name("fixtures_blocks")
NAMES = sorted(p.name for p in FIXTURES.glob("*.html"))


def _read(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("utf-8")


def test_the_fixture_set_covers_the_blocks_people_write() -> None:
    wanted = {
        "paragraph", "heading", "list", "image", "gallery", "columns", "group", "buttons",
        "embed", "table", "quote", "cover", "details", "separator", "spacer", "third_party",
    }  # fmt: skip
    assert wanted <= {n.removesuffix(".html") for n in NAMES}


@pytest.mark.parametrize("name", NAMES)
def test_parse_and_serialize_is_byte_exact(name: str) -> None:
    text = _read(name)
    assert serialize(parse(text)) == text


@pytest.mark.parametrize("name", NAMES)
def test_every_html_span_is_exactly_one_block(name: str) -> None:
    text = _read(name)
    spans = bs.html_spans(text)
    assert spans
    for span in spans:
        found = [b for b in parse(text[span.start : span.end]) if not b.freeform]
        assert len(found) == 1
        assert found[0].name == span.name


@pytest.mark.parametrize("name", NAMES)
def test_markdown_and_back_is_byte_exact(name: str) -> None:
    text = _read(name)
    markdown, islands = post_to_markdown(text)
    assert convert_markdown(markdown, islands).html.strip("\n") == text.strip("\n")


@pytest.mark.parametrize("name", NAMES)
def test_markdown_spans_describe_the_same_top_level_blocks(name: str) -> None:
    text = _read(name)
    markdown, islands = post_to_markdown(text)
    html = bs.html_spans(text)
    md = bs.markdown_spans(markdown)
    tops_html = [
        bs.describe_span(text, "html", html, i) for i, s in enumerate(html) if s.depth == 0
    ]
    tops_md = [
        bs.describe_span(markdown, "markdown", md, i, islands)
        for i, s in enumerate(md)
        if s.depth == 0
    ]
    assert tops_md == tops_html


@pytest.mark.parametrize("name", NAMES)
def test_duplicating_the_first_block_keeps_every_other_byte(name: str) -> None:
    text = _read(name)
    spans = bs.html_spans(text)
    edit = be.duplicate(text, "html", spans, 0)
    first = text[spans[0].start : spans[0].end]
    assert edit.text.count(first) == text.count(first) + 1
    assert edit.text[edit.caret : edit.caret + len(first)] == first
    assert serialize(parse(edit.text)) == edit.text
    after = bs.html_spans(edit.text)
    copy = next(i for i, s in enumerate(after) if s.depth == 0 and s.start == edit.caret)
    assert be.remove(edit.text, after, copy).text == text


def test_moving_blocks_inside_a_container_round_trips() -> None:
    text = _read("columns.html")
    spans = bs.html_spans(text)
    first_column = next(i for i, s in enumerate(spans) if s.name == "core/column")
    moved = be.move(text, spans, first_column, 1)
    assert isinstance(moved, be.Edit)
    assert moved.text.index("Evening") < moved.text.index("Morning")
    back = be.move(moved.text, bs.html_spans(moved.text), first_column, 1)
    assert isinstance(back, be.Edit)
    assert back.text == text
