"""The wx-free 9.16 helpers: routes, links, icons, sizes, copies, archives."""

from __future__ import annotations

import pytest

from quill.core.wordpress import cross_site as xs
from quill.core.wordpress import icons as ic
from quill.core.wordpress import link_targets as lt
from quill.core.wordpress import routes as rt
from quill.core.wordpress import site_space as ss
from quill.core.wordpress.site import Account, Term
from quill.core.wordpress.site_features import SiteIndex


def account(*caps: str, role: str = "editor") -> Account:
    return Account(1, "Jeff", "jeff", (role,), frozenset(caps))


def test_every_feature_names_a_route_and_a_reason() -> None:
    for name, need in rt.FEATURES.items():
        assert need.pattern.startswith("^/"), name
        assert need.missing.endswith("."), name


def test_unavailable_checks_the_route_then_the_role() -> None:
    index = SiteIndex(("wp/v2",), {"/wp-site-health/v1/directory-sizes": {}})
    assert rt.unavailable("export", index, account(), "Radio").startswith("Radio cannot export")
    assert "is an Editor" in rt.unavailable("directory_sizes", index, account(), "Radio")
    admin = account("manage_options", role="administrator")
    assert rt.unavailable("directory_sizes", index, admin, "Radio") == ""


def test_route_patterns_match_the_real_index_keys() -> None:
    index = SiteIndex(
        (),
        {
            "/wp/v2/media/(?P<id>[\\d]+)/post-process": {},
            "/wp/v2/global-styles/(?P<parent>[\\d]+)/revisions": {},
        },
    )
    me = account("upload_files", "edit_theme_options")
    for feature in ("post_process", "style_revisions"):
        assert rt.unavailable(feature, index, me, "Radio") == "", feature


def test_links_in_both_formats_and_the_one_at_the_caret() -> None:
    text = 'A [b](https://x.org/b) and <a href="https://x.org/c">c &amp; d</a>, ![i](p.png)'
    links = lt.links_in(text, "markdown")
    assert [(link.words, link.url) for link in links] == [
        ("b", "https://x.org/b"),
        ("c & d", "https://x.org/c"),
    ]
    assert lt.link_at(text, 4, "markdown").url == "https://x.org/b"
    assert lt.link_at(text, 0, "markdown") is None


def test_vague_words_and_web_links() -> None:
    links = lt.links_in("[Click here.](https://a.org) [x](#top) [y](https://a.org)", "markdown")
    assert links[0].vague
    assert lt.web_links(links) == ["https://a.org"]
    assert lt.dead_link_sentence([], 0) == "No links to other pages."
    assert lt.dead_link_sentence([], 3) == "All 3 links reach their pages."


def test_fixed_text_keeps_html_escaped() -> None:
    link = lt.links_in('<a href="https://a.org">here</a>', "html")[0]
    assert lt.fixed_text(link.with_words("x"), link, "Fish & Chips") == (
        '<a href="https://a.org">Fish &amp; Chips</a>'
    )


ICON = ic.Icon(
    "core/phone",
    "Phone",
    "WordPress",
    '<svg role="presentation" viewBox="0 0 1 1"><title>t</title></svg>',
)


def test_an_icon_is_named_or_decorative_never_neither() -> None:
    named = ic.icon_markup(ICON, label='Call "us"')
    assert 'role="img" aria-label="Call &quot;us&quot;"' in named
    assert "presentation" not in named and "<title" not in named
    assert named.startswith("<!-- wp:html -->")
    assert 'aria-hidden="true"' in ic.icon_markup(ICON, decorative=True)
    with pytest.raises(ic.IconLabelError):
        ic.icon_markup(ICON, label="  ")
    with pytest.raises(ic.IconLabelError):
        ic.icon_markup(ic.Icon("x", "X", "", ""), decorative=True)


def test_sizes_in_words() -> None:
    assert ss.size_words(1288490189) == "1.2 GB"
    assert ss.size_words(512) == "512 bytes"


def test_title_and_body_from_the_first_heading() -> None:
    assert xs.title_and_body("Intro\n## News\nText", "markdown", "f") == ("News", "Intro\n\nText")
    assert xs.title_and_body("<h1>A &amp; B</h1><p>x</p>", "html", "f") == ("A & B", "<p>x</p>")
    assert xs.title_and_body("No heading", "markdown", "notes") == ("notes", "No heading")


def test_local_pictures_and_file_addresses(tmp_path) -> None:
    (tmp_path / "a.png").write_bytes(b"x")
    text = '![A](a.png) ![W](https://x.org/w.png) <img src="a.png" alt="B"> ![M](missing.png)'
    found = xs.local_pictures(text, tmp_path)
    assert [(p.reference, p.alt) for p in found] == [("a.png", "A")]
    rewritten = xs.with_file_addresses(text, found)
    uri = (tmp_path / "a.png").resolve().as_uri()
    assert f"![A]({uri})" in rewritten and f'src="{uri}"' in rewritten


def test_match_terms_by_name_in_any_case() -> None:
    source = [Term(5, "category", "News", "news", 1), Term(6, "category", "Gigs", "gigs", 1)]
    target = [Term(50, "category", "news", "news", 1)]
    mapping, missing = xs.match_terms(source, target)
    assert mapping == {5: 50}
    assert [t.name for t in missing] == ["Gigs"]


def test_site_pictures_only_from_that_site() -> None:
    content = '<img src="https://radio.example/u/a.png"><img src="https://other.org/b.png">'
    assert xs.site_pictures(content, "https://radio.example") == ["https://radio.example/u/a.png"]
