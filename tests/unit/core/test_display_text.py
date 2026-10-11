"""Publisher text reads as words, not as entity codes (QUILLVille list, 2026-10-11).

Quill Radio 3.2 read every apostrophe in a podcast's show notes as ``&#8217;``.
Two faults did it: plain-text notes were never decoded at all, and a feed that
encodes twice (``&amp;#8217;``, WordPress's habit) kept one layer after the HTML
parser took the other. Every reader of show notes is checked here, plus the
gate that keeps a new one from decoding by hand.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from quill.core.display_text import clean_display_text, decode_entities, unwrap_escaped_html
from quill.core.podcasts.notes_document import parse_notes
from quill.core.podcasts.notes_render import render_notes
from quill.core.podcasts.show_notes import html_to_plain_text

RSQUO = "\u2019"

_ENCODINGS = [
    ("Don&#8217;t", f"Don{RSQUO}t"),
    ("Don&amp;#8217;t", f"Don{RSQUO}t"),
    ("Don&amp;amp;#8217;t", f"Don{RSQUO}t"),
    ("Don&rsquo;t", f"Don{RSQUO}t"),
    ("Don&#x2019;t", f"Don{RSQUO}t"),
    ("Rock &amp; Roll", "Rock & Roll"),
]


@pytest.mark.parametrize(("raw", "expected"), _ENCODINGS)
def test_decode_entities_takes_off_every_layer(raw: str, expected: str) -> None:
    assert decode_entities(raw) == expected


@pytest.mark.parametrize(
    "text",
    [
        "AT&T and A&W",
        "https://example.com/?a=1&copy=2&reg=3",  # legacy names with no semicolon
        "&nosuch; stays",
        "",
    ],
)
def test_decode_entities_leaves_text_that_is_not_a_reference(text: str) -> None:
    assert decode_entities(text) == text


def test_decode_entities_stops_after_three_layers() -> None:
    # Text genuinely about entities is not ground down forever.
    assert decode_entities("&amp;amp;amp;amp;") == "&amp;"


def test_clean_display_text_tidies_invisible_characters() -> None:
    assert clean_display_text("a&nbsp;b\u200bc\ufeff") == "a bc"


def test_unwrap_escaped_html_only_touches_html_published_as_text() -> None:
    assert unwrap_escaped_html("&lt;p&gt;Hi&lt;/p&gt;") == "<p>Hi</p>"
    assert unwrap_escaped_html("<p>&lt;b&gt;</p>") == "<p>&lt;b&gt;</p>"
    assert unwrap_escaped_html("5 &lt; 6") == "5 &lt; 6"


@pytest.mark.parametrize(("raw", "expected"), _ENCODINGS)
@pytest.mark.parametrize("wrap", ["{}", "<p>{}</p>", "<![CDATA[]]><div>{}</div>"])
def test_html_to_plain_text_reads_words(raw: str, expected: str, wrap: str) -> None:
    assert html_to_plain_text(wrap.format(raw)) == expected


@pytest.mark.parametrize(("raw", "expected"), _ENCODINGS)
@pytest.mark.parametrize("wrap", ["{}", "<p>{}</p>"])
def test_notes_document_reads_words(raw: str, expected: str, wrap: str) -> None:
    assert parse_notes(wrap.format(raw)).text.strip() == expected


@pytest.mark.parametrize(("raw", "expected"), _ENCODINGS)
@pytest.mark.parametrize("wrap", ["{}", "<p>{}</p>"])
def test_notes_render_reads_words(raw: str, expected: str, wrap: str) -> None:
    document = render_notes(wrap.format(raw))
    assert expected in " ".join(block.text for block in document.blocks)


def test_escaped_html_in_a_plain_field_reads_as_html() -> None:
    raw = "&lt;p&gt;Don&amp;#8217;t miss it.&lt;/p&gt;&lt;p&gt;Next.&lt;/p&gt;"
    assert html_to_plain_text(raw) == f"Don{RSQUO}t miss it.\n\nNext."
    assert "<p>" not in parse_notes(raw).text


def test_a_link_keeps_its_place_after_cleaning() -> None:
    document = parse_notes('<p>We&amp;#8217;re at <a href="https://x.org/">our site</a>.</p>')
    assert document.text.strip() == f"We{RSQUO}re at our site."
    (link,) = document.unique_links()
    assert link.url == "https://x.org/"


# -- the gate -----------------------------------------------------------------

_REPO = Path(__file__).resolve().parents[3]
_SCOPES = ("quill/core/podcasts", "quill/core/radio", "quill/ui/podcasts", "quill/ui/radio")
#: Calls that decode markup rather than text a person reads, each with why.
_ALLOWED = {
    # XML attribute values (an enclosure URL, an attribute): exactly one layer.
    ("quill/core/podcasts/namespace_tags.py", "_attr"),
    ("quill/core/podcasts/namespace_tags.py", "parse_live_items"),
}


def _direct_unescapes(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[str, int]] = []

    def visit(node: ast.AST, scope: str) -> None:
        for child in ast.iter_child_nodes(node):
            is_function = isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
            inner = child.name if is_function else scope
            if isinstance(child, ast.Call):
                func = child.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                if name == "unescape":
                    found.append((scope, child.lineno))
            visit(child, inner)

    visit(tree, "<module>")
    return found


def test_publisher_text_is_decoded_through_display_text() -> None:
    offenders = []
    for scope in _SCOPES:
        for path in sorted((_REPO / scope).rglob("*.py")):
            rel = path.relative_to(_REPO).as_posix()
            for function, line in _direct_unescapes(path):
                if (rel, function) not in _ALLOWED:
                    offenders.append(f"{rel}:{line} in {function}")
    assert offenders == [], (
        "Decode publisher text with quill.core.display_text (clean_display_text or "
        "decode_entities), not html.unescape: one unescape leaves a double-encoded "
        f"feed reading '&#8217;' aloud. Found: {offenders}"
    )
