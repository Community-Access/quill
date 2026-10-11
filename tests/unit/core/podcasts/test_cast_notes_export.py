"""The four Copy Notes formats and the View in Browser page (qc.md 5c).

One test per format, because "copy as Markdown" that drops a heading is worse than
no Markdown at all -- and one for what each must never carry.
"""

from __future__ import annotations

from quill.core.podcasts import notes_export
from quill.core.podcasts.notes_document import parse_notes

NOTES = (
    "<h2>About</h2>"
    "<p>Hello <b>world</b>, see <a href='https://example.com/x'>Support <em>the</em> show</a>.</p>"
    "<ol><li>One</li><li>Two at 12:34</li></ol>"
    "<p><img src='https://example.com/art.png' alt='Cover art'></p>"
    "<script>steal()</script>"
)


def test_plain_text_keeps_structure_and_drops_addresses() -> None:
    text = notes_export.to_plain(parse_notes(NOTES))
    assert text == "About\n\nHello world, see Support the show.\n\n1. One\n2. Two at 12:34"


def test_plain_text_with_links_puts_each_address_after_its_text_once() -> None:
    text = notes_export.to_plain(parse_notes(NOTES), with_links=True)
    assert "Support the show (https://example.com/x)." in text
    assert text.count("https://example.com/x") == 1


def test_markdown_keeps_headings_lists_links_and_emphasis() -> None:
    text = notes_export.to_markdown(parse_notes(NOTES))
    assert text.splitlines()[0] == "## About"
    assert "**world**" in text
    assert "[Support *the* show](https://example.com/x)" in text
    assert "1. One\n2. Two at 12:34" in text


def test_markdown_escapes_what_would_otherwise_become_markup() -> None:
    text = notes_export.to_markdown(parse_notes("<p># Not a heading [really]</p>"))
    assert text == "\\# Not a heading \\[really\\]"


def test_html_is_rebuilt_never_passed_through() -> None:
    html = notes_export.to_html(parse_notes(NOTES))
    assert "<h2>About</h2>" in html
    assert '<a href="https://example.com/x">Support <em>the</em> show</a>' in html
    assert "<ol>" in html and "<li>One</li>" in html
    assert '<img src="https://example.com/art.png" alt="Cover art">' in html
    assert "script" not in html and "steal" not in html


def test_rtf_carries_bold_headings_and_a_hyperlink_field() -> None:
    rtf = notes_export.to_rtf(parse_notes(NOTES + "<p>Café</p>"))
    assert rtf.startswith("{\\rtf1") and rtf.endswith("}")
    assert "{\\b\\fs32 About}" in rtf
    assert 'HYPERLINK "https://example.com/x"' in rtf
    assert "Caf\\u233?" in rtf


def test_render_picks_the_text_flavour_and_defaults_to_plain() -> None:
    doc = parse_notes(NOTES)
    assert notes_export.render(doc, "markdown") == notes_export.to_markdown(doc)
    assert notes_export.render(doc, "nonsense") == notes_export.to_plain(doc)
    assert notes_export.normalize_format("PLAIN_LINKS") == "plain_links"


def test_every_copy_says_what_it_copied_and_how_much() -> None:
    assert (
        notes_export.copied_sentence("plain", 412)
        == "Copied the show notes as plain text, 412 words."
    )
    assert notes_export.copied_sentence("markdown", 1).endswith("as Markdown, 1 word.")
    assert notes_export.word_count("It's twelve-thirty, isn't it?") == 5


def test_the_browser_page_has_the_episode_heading_and_no_scripts() -> None:
    page = notes_export.browser_page(
        parse_notes(NOTES), episode_title="Thursday's episode", podcast_title="The Daily"
    )
    assert "<title>The Daily</title>" in page
    assert "<h1>Thursday&#x27;s episode</h1>" in page
    # The notes' own headings sit under the page's heading.
    assert "<h3>About</h3>" in page
    assert "<script" not in page
    assert "default-src 'none'" in page


def test_the_browser_page_for_no_notes_says_so() -> None:
    page = notes_export.browser_page(parse_notes(""), episode_title="E", podcast_title="P")
    assert "This episode has no show notes." in page
