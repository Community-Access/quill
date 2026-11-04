"""Check Before Publishing content checks (quill.core.wordpress.checks)."""

from __future__ import annotations

import dataclasses

import pytest

from quill.core.wordpress.checks import (
    Finding,
    check_content,
    has_decorative_symbol,
    summary_line,
)


def kinds(html: str, **kwargs: str) -> list[str]:
    kwargs.setdefault("title", "A title")
    return [f.kind for f in check_content(html, **kwargs)]


def only(html: str, kind: str) -> Finding:
    found = [f for f in check_content(html, title="T") if f.kind == kind]
    assert len(found) == 1, found
    return found[0]


# -- clean content --------------------------------------------------------------


def test_clean_post_has_no_findings() -> None:
    html = (
        "<!-- wp:heading --><h2>Welcome</h2><!-- /wp:heading -->"
        '<!-- wp:paragraph --><p>Read <a href="/about">about us</a>.</p><!-- /wp:paragraph -->'
        '<!-- wp:image --><figure><img src="/a.jpg" alt="A red barn at dusk"></figure>'
        "<!-- /wp:image --><h3>Details</h3>"
    )
    assert check_content(html, title="Hello") == []


def test_block_comments_are_not_content() -> None:
    # A block comment's JSON mentions things that look like findings; none count.
    html = '<!-- wp:image {"alt":"","url":"x.gif"} --><!-- wp:heading {"level":1} -->'
    assert kinds(html) == []


def test_finding_is_frozen() -> None:
    finding = only("<img src='a.jpg'>", "image-no-alt")
    with pytest.raises(dataclasses.FrozenInstanceError):
        finding.kind = "other"  # type: ignore[misc]


# -- images -----------------------------------------------------------------------


def test_image_without_alt_is_a_problem() -> None:
    html = '<p>Hi</p><img src="/up/IMG_1.jpg">'
    f = only(html, "image-no-alt")
    assert f.severity == "problem"
    assert f.offset == html.index("<img")
    assert f.excerpt == "IMG_1.jpg"
    assert not f.fixable


def test_empty_alt_not_marked_decorative_is_a_problem() -> None:
    assert kinds('<img src="a.jpg" alt="">') == ["image-empty-alt"]


@pytest.mark.parametrize(
    "tag",
    [
        '<img src="a.jpg" alt="" role="presentation">',
        '<img src="a.jpg" alt="" role="none">',
        '<img src="a.jpg" alt="" data-quill-decorative>',
        '<img src="a.jpg" alt="" data-quill-decorative="1" />',
    ],
)
def test_decorative_image_passes(tag: str) -> None:
    assert kinds(tag) == []


def test_decorative_marker_without_alt_still_fails() -> None:
    assert kinds('<img src="a.jpg" data-quill-decorative>') == ["image-no-alt"]


@pytest.mark.parametrize("alt", ["IMG_2041.jpg", "DSC_0042", "photo.PNG", "screenshot 3"])
def test_alt_that_is_a_filename(alt: str) -> None:
    f = only(f'<img src="a.jpg" alt="{alt}">', "alt-is-filename")
    assert f.severity == "problem"
    assert alt in f.message


@pytest.mark.parametrize("alt", ["Image of a dog", "picture of the team", "A photo of Bob"])
def test_alt_that_says_image(alt: str) -> None:
    f = only(f'<img src="a.jpg" alt="{alt}">', "alt-says-image")
    assert f.severity == "check"
    assert f.fixable


@pytest.mark.parametrize("alt", ["Imagination at work", "The 2041 team photo", "Pictures"])
def test_good_alt_is_not_misread(alt: str) -> None:
    assert kinds(f'<img src="a.jpg" alt="{alt}">') == []


def test_gif_is_flagged() -> None:
    f = only('<img src="/up/dance.GIF?ver=2" alt="Dancing">', "animated-gif")
    assert f.severity == "check"
    assert f.fixable


def test_non_gif_not_flagged_for_motion() -> None:
    assert kinds('<img src="/up/gif-tips.png" alt="Tips">') == []


# -- linked images ------------------------------------------------------------------


def test_linked_image_with_empty_alt_names_nothing() -> None:
    html = '<a href="/home"><img src="logo.png" alt=""></a>'
    f = only(html, "linked-image-no-alt")
    assert f.offset == 0
    assert kinds(html) == ["linked-image-no-alt"]


def test_linked_image_with_no_alt_is_reported_once() -> None:
    assert kinds('<a href="/home"><img src="logo.png"></a>') == ["linked-image-no-alt"]


def test_linked_image_with_alt_passes() -> None:
    assert kinds('<a href="/home"><img src="logo.png" alt="Home"></a>') == []


def test_linked_image_with_empty_alt_and_text_passes() -> None:
    assert kinds('<a href="/home"><img src="i.png" alt=""> Home page</a>') == []


def test_linked_image_missing_alt_beside_text_still_flags_image() -> None:
    assert kinds('<a href="/home"><img src="i.png"> Home page</a>') == ["image-no-alt"]


# -- links -----------------------------------------------------------------------


def test_link_with_no_text() -> None:
    html = '<p>See <a href="/x"></a></p>'
    f = only(html, "link-no-text")
    assert f.offset == html.index("<a")
    assert f.excerpt == "/x"


def test_aria_label_names_a_link() -> None:
    assert kinds('<a href="/x" aria-label="Search"></a>') == []


@pytest.mark.parametrize(
    "text",
    ["https://example.com/page", "example.com/page/", "www.example.com", "http://other.org"],
)
def test_link_text_is_the_address(text: str) -> None:
    html = f'<a href="https://example.com/page">{text}</a>'
    assert "link-text-is-address" in kinds(html)


@pytest.mark.parametrize(
    "text", ["click here", "Here", "read more", "More", "link", "Read more..."]
)
def test_vague_link_text(text: str) -> None:
    f = only(f'<a href="/x">{text}</a>', "link-vague-text")
    assert f.severity == "problem"
    assert text in f.message


@pytest.mark.parametrize("text", ["Read more about pricing", "Where to find us", "Morel recipes"])
def test_specific_link_text_passes(text: str) -> None:
    assert kinds(f'<a href="/x">{text}</a>') == []


def test_new_tab_without_saying_so() -> None:
    f = only('<a href="/x" target="_blank">Our menu</a>', "link-new-tab-unsaid")
    assert f.fixable
    assert f.severity == "check"


@pytest.mark.parametrize(
    "html",
    [
        '<a href="/x" target="_blank">Our menu (opens in a new tab)</a>',
        '<a href="/x" target="_blank">Our menu <span class="screen-reader-text">'
        "(opens in a new tab)</span></a>",
        '<a href="/x" target="_blank" aria-label="Our menu, opens in a new tab">Menu</a>',
        '<a href="/x" target="_self">Our menu</a>',
    ],
)
def test_new_tab_said_or_not_new_tab_passes(html: str) -> None:
    assert kinds(html) == []


def test_link_with_emoji() -> None:
    assert kinds('<a href="/x">Sale \U0001f525</a>') == ["link-has-emoji"]


def test_unclosed_link_is_still_checked() -> None:
    assert kinds('<p><a href="/x">here') == ["link-vague-text"]


# -- headings -------------------------------------------------------------------


def test_heading_skip() -> None:
    html = "<h2>One</h2><p>x</p><h4>Deep</h4>"
    f = only(html, "heading-skips-level")
    assert f.offset == html.index("<h4>")
    assert "Heading 2 to Heading 4" in f.message
    assert f.excerpt == "Deep"


def test_first_heading_skipping_from_title() -> None:
    f = only("<h3>Start</h3>", "heading-skips-level")
    assert "the title to Heading 3" in f.message


def test_heading_going_back_up_passes() -> None:
    assert kinds("<h2>A</h2><h3>B</h3><h4>C</h4><h2>D</h2><h3>E</h3>") == []


def test_heading_one_in_body() -> None:
    f = only("<h1>Title again</h1>", "heading-1-in-body")
    assert f.fixable
    assert f.severity == "problem"


def test_heading_with_emoji() -> None:
    assert kinds("<h2>✨ New</h2>") == ["heading-has-emoji"]


def test_heading_without_symbols_passes() -> None:
    assert kinds("<h2>Café menu, 2026 – © us</h2>") == []


# -- title and site -------------------------------------------------------------


@pytest.mark.parametrize("title", ["", "   "])
def test_empty_title(title: str) -> None:
    findings = check_content("<p>Body</p>", title=title)
    assert [f.kind for f in findings] == ["title-empty"]
    assert findings[0].offset == 0


def test_different_site_is_named() -> None:
    findings = check_content(
        "<p>x</p>", title="T", site_name="Work Blog", default_site_name="My Garden"
    )
    assert [f.kind for f in findings] == ["site-not-default"]
    assert findings[0].severity == "check"
    assert "Work Blog" in findings[0].message
    assert "My Garden" in findings[0].message


@pytest.mark.parametrize(
    ("site", "default"),
    [("My Garden", "My Garden"), ("my garden", "My Garden"), ("Work", ""), ("", "Work")],
)
def test_same_or_unknown_site_passes(site: str, default: str) -> None:
    assert kinds("<p>x</p>", site_name=site, default_site_name=default) == []


def test_document_wide_findings_come_first() -> None:
    findings = check_content("<h1>x</h1>", title="", site_name="A", default_site_name="B")
    assert [f.kind for f in findings] == ["title-empty", "site-not-default", "heading-1-in-body"]


# -- tables ---------------------------------------------------------------------


def test_table_without_header_or_caption() -> None:
    html = "<p>x</p><table><tr><td>1</td></tr></table>"
    found = check_content(html, title="T")
    assert [f.kind for f in found] == ["table-no-header", "table-no-caption"]
    assert {f.offset for f in found} == {html.index("<table>")}
    assert found[0].severity == "problem"
    assert found[1].severity == "check"


def test_table_with_header_and_caption_passes() -> None:
    html = (
        "<figure class='wp-block-table'><table><caption>Prices</caption>"
        "<thead><tr><th>Item</th></tr></thead><tbody><tr><td>1</td></tr></tbody>"
        "</table></figure>"
    )
    assert kinds(html) == []


def test_nested_table_judged_on_its_own() -> None:
    html = (
        "<table><caption>Outer</caption><tr><th>A</th></tr><tr><td>"
        "<table><tr><td>inner</td></tr></table></td></tr></table>"
    )
    assert kinds(html) == ["table-no-header", "table-no-caption"]


# -- motion -----------------------------------------------------------------------


def test_autoplay_video() -> None:
    f = only('<video src="/v/intro.mp4" autoplay muted></video>', "video-autoplay")
    assert f.fixable
    assert f.excerpt == "intro.mp4"


def test_video_without_autoplay_passes() -> None:
    assert kinds('<video src="/v/intro.mp4" controls></video>') == []


# -- colour alone -----------------------------------------------------------------


def test_colour_alone_on_short_phrase() -> None:
    html = '<p>Friday: <span style="color:#c00">cancelled</span></p>'
    f = only(html, "colour-alone")
    assert f.offset == html.index("<span")
    assert "cancelled" in f.message
    assert f.severity == "check"


def test_wordpress_inline_colour_mark_is_checked() -> None:
    # What the block editor writes for Highlight > Text colour.
    html = (
        '<p><mark style="background-color:rgba(0, 0, 0, 0);color:#cf2e2e" '
        'class="has-inline-color">sold out</mark></p>'
    )
    assert kinds(html) == ["colour-alone"]


@pytest.mark.parametrize(
    "html",
    [
        '<span style="color:red"><strong>cancelled</strong></span>',
        '<strong><span style="color:red">cancelled</span></strong>',
        '<em><span style="color:red">cancelled</span></em>',
        '<span style="background-color:yellow">cancelled</span>',
        '<span style="color:red">this whole sentence is red for some reason today</span>',
        '<span style="color:red"> </span>',
        '<span class="red">cancelled</span>',
    ],
)
def test_colour_alone_stays_quiet(html: str) -> None:
    assert kinds(html) == []


def test_nested_plain_span_inside_colour_span() -> None:
    html = '<span style="color:red">now <span>closed</span></span>'
    assert kinds(html) == ["colour-alone"]


# -- scripts, styles, ordering ------------------------------------------------------


def test_script_and_style_are_not_content() -> None:
    html = "<style>a{color:red}</style><script>var a = '<a href=x></a>';</script>"
    assert kinds(html) == []


def test_offsets_across_lines() -> None:
    html = "<p>one</p>\n<p>two</p>\n<img src='x.jpg'>"
    assert only(html, "image-no-alt").offset == html.index("<img")


def test_findings_are_in_document_order() -> None:
    html = '<a href="/x">here</a><h1>T</h1><img src="a.jpg">'
    assert kinds(html) == ["link-vague-text", "heading-1-in-body", "image-no-alt"]


def test_excerpt_is_short() -> None:
    long = "word " * 40
    f = only(f"<h1>{long}</h1>", "heading-1-in-body")
    assert len(f.excerpt) <= 60
    assert f.excerpt.endswith("...")


# -- symbols helper -----------------------------------------------------------------


@pytest.mark.parametrize("text", ["★ Star", "Next →", "✔ done", "\U0001f600"])
def test_decorative_symbol_detected(text: str) -> None:
    assert has_decorative_symbol(text)


@pytest.mark.parametrize("text", ["Plain text", "Café", "50% off – today", "© 2026"])
def test_plain_text_has_no_symbol(text: str) -> None:
    assert not has_decorative_symbol(text)


# -- summary line -------------------------------------------------------------------


def _f(severity: str) -> Finding:
    return Finding("k", severity, "m", 0, "")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("severities", "expected"),
    [
        ([], "Ready to publish: no problems found"),
        (["problem"], "1 thing to look at: 1 problem"),
        (["check"], "1 thing to look at: 1 to check"),
        (["problem", "check"], "2 things to look at: 1 problem, 1 to check"),
        (["problem", "problem", "check"], "3 things to look at: 2 problems, 1 to check"),
        (["check", "check"], "2 things to look at: 2 to check"),
    ],
)
def test_summary_line(severities: list[str], expected: str) -> None:
    assert summary_line([_f(s) for s in severities]) == expected
