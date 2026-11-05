"""The whole-site report, history, statement, palette and writing helpers (9.5 to 9.12)."""

from __future__ import annotations

from datetime import UTC, datetime

from quill.core.wordpress import checks as chk
from quill.core.wordpress import site_report as rpt

HOME = rpt.PageRef("page", 1, "Home")
NEWS = rpt.PageRef("post", 2, "News")


def _finding(kind: str) -> chk.Finding:
    return chk.Finding(kind, "problem", "msg.", 0, "")


def test_problems_group_by_kind_with_counts_and_pages() -> None:
    content = [
        (HOME, [_finding("image-no-alt"), _finding("image-no-alt"), _finding("site-not-default")]),
        (NEWS, [_finding("image-no-alt"), _finding("link-new-tab-unsaid")]),
    ]
    visitor = [(HOME, [("color-contrast", "Text too faint", "theme", 4)])]
    problems = rpt.group_problems(content, visitor)
    rows = [p.row() for p in problems]
    assert rows[0] == "Text too faint: 4, on 1 page, in the theme or a plugin"
    assert rows[1] == "Images with no alt text: 3, on 2 pages"
    assert any(r.endswith("can be fixed in bulk") for r in rows)
    assert all("site" not in p.key for p in problems)


def test_summary_and_history_compare_with_last_time(tmp_path) -> None:
    history = rpt.CheckHistory(tmp_path)
    problems = rpt.group_problems([(HOME, [_finding("image-no-alt")])])
    march = rpt.history_entry(
        problems, 5, visitor_checked=False, now=datetime(2026, 3, 2, tzinfo=UTC)
    )
    history.add("radio", march)
    previous = history.latest("radio")
    assert previous is not None and previous.month == "March 2026"
    line = rpt.site_summary("Community Radio", problems, 5, previous)
    assert line == "Community Radio: 1 problem on 1 of 5 pages. 1 in March 2026."
    assert rpt.site_summary("R", [], 3, None) == "R: no problems found on 3 pages."


def test_statement_names_standard_result_known_problems_and_contact() -> None:
    last = rpt.HistoryEntry("2026-10-01T00:00:00+00:00", 40, 12, {}, ["Text too faint"])
    title, text = rpt.accessibility_statement(
        "Community Radio",
        contact="hello@radio.example",
        last=last,
        today=datetime(2026, 11, 4, tzinfo=UTC),
    )
    assert title == "Accessibility Statement"
    assert "WCAG) 2.2 at level AA" in text
    assert "October 2026" in text and "12 things to fix" in text
    assert "- Text too faint" in text
    assert "hello@radio.example" in text and "4 November 2026" in text
    _title, html = rpt.accessibility_statement("R", contact="", last=None, html=True)
    assert html.startswith("<!-- wp:paragraph -->") and "please tell us. We will reply" in html


def test_palette_from_global_styles_puts_the_page_background_first() -> None:
    raw = {
        "settings": {
            "color": {
                "palette": {
                    "theme": [
                        {"slug": "base", "name": "Base", "color": "#ffffff"},
                        {"slug": "accent", "name": "Accent", "color": "#1a5e20"},
                    ]
                }
            }
        },
        "styles": {"color": {"background": "var:preset|color|accent"}},
    }
    palette, backgrounds = rpt.palette_from_global_styles(raw)
    assert palette == [("Base", "#ffffff"), ("Accent", "#1a5e20")]
    assert backgrounds[0] == ("Accent", "#1a5e20")
    _p, backgrounds = rpt.palette_from_global_styles({
        "settings": {"color": {"palette": [{"name": "A", "color": "#000"}]}},
        "styles": {"color": {"background": "#fafafa"}},
    })
    assert backgrounds[0] == ("Page background", "#fafafa")
    assert rpt.palette_from_global_styles("nonsense") == ([], [])


def test_language_tags_from_names_or_codes() -> None:
    assert rpt.valid_language("French") == "fr"
    assert rpt.valid_language(" pt-BR ") == "pt-BR"
    assert rpt.valid_language("not a language") == ""
    assert rpt.language_name("fr-CA") == "French"


def test_mark_language_in_each_form() -> None:
    assert rpt.mark_language("bonjour", "fr", html=False) == '<span lang="fr">bonjour</span>'
    html = "<!-- wp:paragraph -->\n<p>One</p>\n<!-- /wp:paragraph -->\n<h2>Two</h2>"
    marked = rpt.mark_language(html, "fr", html=True, whole=True)
    assert '<p><span lang="fr">One</span></p>' in marked
    assert '<h2><span lang="fr">Two</span></h2>' in marked
    assert "<!-- wp:paragraph -->" in marked
    md = "# Title\n\n- item\n<!-- wp:spacer -->\nPlain"
    marked = rpt.mark_language(md, "de", html=False, whole=True)
    assert marked.splitlines() == [
        '# <span lang="de">Title</span>',
        "",
        '- <span lang="de">item</span>',
        "<!-- wp:spacer -->",
        '<span lang="de">Plain</span>',
    ]


def test_in_short_goes_on_top_and_replaces_an_earlier_one() -> None:
    once = rpt.insert_in_short("Body text.\n", "Short one.", html=False)
    assert once == "**In short:** Short one.\n\nBody text.\n"
    twice = rpt.insert_in_short(once, "Short two.", html=False)
    assert twice == "**In short:** Short two.\n\nBody text.\n"
    html = "<!-- wp:paragraph -->\n<p>Body</p>\n<!-- /wp:paragraph -->"
    first = rpt.insert_in_short(html, "A & B.", html=True)
    assert first.startswith('<!-- wp:paragraph {"className":"quill-in-short"} -->')
    assert "A &amp; B." in first
    second = rpt.insert_in_short(first, "C.", html=True)
    assert second.count("quill-in-short") == 2  # the comment and the class, once
    assert "<p>Body</p>" in second and "A &amp; B" not in second
