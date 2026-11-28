"""SwiftLetter articles as editor working copies, and the Markdown round trip (item 13).

Michael's answer 13: before Markdown saves are enabled, opening and saving must
keep headings and anchors, links, images and alt text, and nested blocks; what
QUILL cannot keep stops the remote save, and the Markdown draft stays as it is.
These run that check against SwiftLetter's own contract fixtures, including kses
storing a contributor's ``"/>`` as ``" />``.
"""

from __future__ import annotations

import pytest

from quill.core.wordpress import fences
from quill.core.wordpress import swiftletter_copy as sc
from quill.core.wordpress import swiftletter_errors as se
from quill.core.wordpress.swiftletter import Article, SavedArticle
from tests.unit.core.wordpress.test_wp_swiftletter_contract import _SEED, _step

_GARDEN = _SEED["articles"]["garden"]["content"]
_SAVE = _step("article-save", "save-current-version")
_SENT = _SAVE["request"]["json"]["content"]
_STORED = _SAVE["response"]["example"]["content"]
_V1 = '"' + "a" * 64 + '"'
_V2 = '"' + "b" * 64 + '"'

_NESTED = (
    "<!-- wp:list -->\n"
    '<ul class="wp-block-list"><!-- wp:list-item -->\n'
    "<li>Beans<!-- wp:list -->\n"
    '<ul class="wp-block-list"><!-- wp:list-item -->\n'
    "<li>Runner beans</li>\n"
    "<!-- /wp:list-item --></ul>\n"
    "<!-- /wp:list --></li>\n"
    "<!-- /wp:list-item -->\n\n"
    "<!-- wp:list-item -->\n"
    "<li>Chard</li>\n"
    "<!-- /wp:list-item --></ul>\n"
    "<!-- /wp:list -->\n\n"
    "<!-- wp:columns -->\n"
    '<div class="wp-block-columns"><!-- wp:column -->\n'
    '<div class="wp-block-column"><!-- wp:paragraph -->\n'
    "<p>Morning watering.</p>\n"
    "<!-- /wp:paragraph --></div>\n"
    "<!-- /wp:column --></div>\n"
    "<!-- /wp:columns -->"
)


def _article(content: str = _GARDEN, state: str = "reviewed") -> Article:
    return Article("https://example.org", 4, "Community Garden", content, (9,), state, _V1)


def _copy(content: str = _GARDEN, fmt: str = "markdown", **kw):
    return sc.copy_for("site-1", _article(content, **kw), text_format=fmt, can_edit=True)


# -- the round trip -------------------------------------------------------------


@pytest.mark.parametrize(
    "content", [_GARDEN, _SENT, _STORED, _NESTED], ids=["seed", "sent", "kses-stored", "nested"]
)
def test_every_contract_article_opens_as_markdown_and_saves_back_unchanged(content):
    copy = _copy(content)
    assert sc.markdown_problem(sc.wordpress_void_tags(content)) == ""
    out = sc.outgoing(copy)
    assert out.problems == ()
    assert sc.wordpress_void_tags(out.html) == sc.wordpress_void_tags(content)
    assert sc.nothing_changed(copy, out.html)


def test_headings_keep_their_anchors_as_readable_markdown():
    markdown = _copy().text
    assert "## Planting day {#planting-day}" in markdown
    assert "### What grows next {#what-grows-next}" in markdown
    assert "::: block core/heading" not in markdown  # readable, not an opaque island


def test_links_and_image_alt_text_are_plain_markdown():
    markdown = _copy().text
    assert "[garden rota](https://example.org/lantern-street/garden-rota)" in markdown
    assert (
        "![Two volunteers lift a wooden raised bed into place beside a brick wall.]"
        "(https://example.org/lantern-street/raised-beds.jpg)" in markdown
    )


def test_a_kses_tidied_image_still_opens_as_markdown_with_its_alt_text():
    # Without the void-tag tidy the stored `" />` image would open as `::: block core/image`.
    assert '" />' in _STORED
    markdown = _copy(_STORED).text
    assert "::: block core/image" not in markdown
    assert "![Two volunteers lift" in markdown


def test_editing_markdown_changes_only_what_was_edited():
    copy = _copy()
    copy.text = copy.text.replace("forty raised beds", "forty-two raised beds")
    html = sc.outgoing(copy).html
    assert "forty-two raised beds" in html
    assert 'id="planting-day"' in html and 'id="what-grows-next"' in html
    assert 'alt="Two volunteers lift a wooden raised bed' in html
    assert not sc.nothing_changed(copy, html)


def test_a_heading_anchor_written_in_markdown_becomes_the_blocks_html_anchor():
    html = fences.convert_markdown("## Volunteers {#volunteers}\n").html
    assert html == (
        '<!-- wp:heading -->\n<h2 class="wp-block-heading" id="volunteers">Volunteers</h2>\n'
        "<!-- /wp:heading -->"
    )


def test_a_heading_that_only_looks_like_an_anchor_is_kept_exactly():
    content = (
        '<!-- wp:heading -->\n<h2 class="wp-block-heading">Odd {#x}</h2>\n<!-- /wp:heading -->'
    )
    markdown, islands = fences.post_to_markdown(content)
    assert markdown.startswith("::: block core/heading")
    assert fences.convert_markdown(markdown, islands).html == content


def test_something_markdown_cannot_keep_stops_the_save_and_keeps_the_draft():
    copy = _copy()
    copy.text += "\n::: block core/image island-99\n"  # an island nobody has
    draft = copy.text
    out = sc.outgoing(copy)
    assert out.problems
    assert out.blocked.startswith("Not saved to SwiftLetter: 1 line could not be turned")
    assert "Your Markdown draft is unchanged" in out.blocked
    assert copy.text == draft


def test_html_is_sent_exactly_as_written():
    copy = _copy(_SENT, fmt="html")
    assert copy.text == _SENT
    assert sc.outgoing(copy) == sc.Outgoing(_SENT)


# -- the working copy -------------------------------------------------------------


def test_the_working_copy_carries_what_the_next_if_match_needs():
    copy = _copy()
    assert copy.kind == sc.KIND and sc.is_article(copy) and copy.status == "draft"
    base = sc.article_of(copy)
    assert base == _article()


def test_a_save_makes_the_stored_text_the_baseline_and_keeps_the_persons_copy():
    copy = _copy(_SENT, fmt="html")
    mine = copy.text
    saved = SavedArticle(4, _V2, "Community Garden", _SENT, "Community Garden", _STORED)
    words = sc.saved_words(copy, saved, "Lantern Street")
    sc.record_saved(copy, saved)
    assert copy.text == mine  # never replaced silently
    base = sc.article_of(copy)
    assert base.edit_version == _V2 and base.content == _STORED
    assert base.review_state == "changed"
    assert words.startswith("Draft saved to SwiftLetter on Lantern Street. It is not published.")
    assert "Its review state is now Changed since review." in words
    assert "WordPress tidied the markup" in words


def test_a_kses_tidy_is_said_once_per_working_copy():
    copy = _copy(_SENT, fmt="html")
    saved = SavedArticle(4, _V2, "Community Garden", _SENT, "Community Garden", _STORED)
    sc.record_saved(copy, saved)
    again = sc.saved_words(copy, saved, "Lantern Street")
    assert "tidied" not in again and "changed the text" not in again


def test_a_real_change_by_wordpress_is_said_every_time():
    copy = _copy(_SENT, fmt="html")
    stored = _SENT.replace("garden rota", "rota")
    saved = SavedArticle(4, _V2, "Community Garden", _SENT, "Community Garden", stored)
    for _ in range(2):
        words = sc.saved_words(copy, saved, "Lantern Street")
        assert words.startswith("Draft saved to SwiftLetter on Lantern Street, but WordPress")
        assert "Compare with Site shows how. Your copy in QUILL is unchanged." in words
        sc.record_saved(copy, saved)


def test_an_rc1_answer_without_stored_text_uses_what_was_sent():
    copy = _copy(_SENT, fmt="html", state="not_reviewed")
    saved = SavedArticle(4, _V2, "Community Garden", _SENT)
    words = sc.saved_words(copy, saved, "Lantern Street")
    sc.record_saved(copy, saved)
    assert words == "Draft saved to SwiftLetter on Lantern Street. It is not published."  # rc.1
    assert sc.article_of(copy).content == _SENT
    assert sc.article_of(copy).review_state == "not_reviewed"


# -- what is said -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("state", "said"),
    [
        ("reviewed", "Reviewed."),
        ("not_reviewed", "Not reviewed."),
        ("changed", "Changed since review."),
    ],
)
def test_opening_says_the_title_and_the_review_state_in_words(state, said):
    words = sc.opened_words(
        _article(state=state), "Lantern Street", can_edit=True, can_save_here=True
    )
    assert words == f"Opened Community Garden from SwiftLetter on Lantern Street. {said}"


def test_an_account_that_cannot_edit_hears_it_opened_read_only():
    words = sc.opened_words(_article(), "Lantern Street", can_edit=False, can_save_here=True)
    assert words.endswith("Your account cannot edit this article, so it opened read-only.")
    copy = sc.copy_for("s", _article(), text_format="html", can_edit=False)
    assert not sc.can_save(copy)


def _refused(step_id: str) -> se.SwiftLetterError:
    from quill.core.wordpress.api import WordPressApiError

    step = _step("article-save", step_id)
    body = step["response"]["body"]
    exc = WordPressApiError("x", status=step["response"]["status"], wp_code=body["code"], body=body)
    refused = se.coded_refusal(exc, saving=True)
    assert isinstance(refused, se.SwiftLetterError)
    return refused


def test_a_stale_save_says_swiftletters_words_and_offers_compare_and_reopen():
    refused = _refused("stale-save-after-wordpress-edit-is-refused")
    said = sc.refusal(refused)
    assert said.words == refused.plain
    assert said.offers == (sc.COMPARE, sc.REOPEN)


@pytest.mark.parametrize("step_id", ["save-without-version", "save-with-wildcard-version"])
def test_428_and_400_say_the_exact_message_and_offer_reopen(step_id):
    refused = _refused(step_id)
    said = sc.refusal(refused)
    assert said.words == _step("article-save", step_id)["response"]["body"]["message"]
    assert said.offers == (sc.REOPEN,)


def test_a_lock_names_who_has_it_open_and_offers_nothing():
    exc = se.SwiftLetterArticleLocked(
        "Pat Reyes is editing this article in WordPress. Your changes are still in QUILL.",
        status=409,
    )
    said = sc.refusal(exc)
    assert said.words.startswith("Pat Reyes is editing this article")
    assert said.offers == ()


def test_compare_names_the_title_and_review_state_then_the_differences():
    copy = _copy(_SENT, fmt="html")
    site = _article(_STORED, state="changed")
    report = sc.compare_report(site, copy, _SENT, lambda a, b: f"same={a == b}")
    lines = report.splitlines()
    assert lines[0].startswith("Title: the same on the site and in your copy")
    assert lines[1] == "On the site it is changed since review."
    assert lines[-1] == "same=True"  # kses spacing is not a difference anyone should hear


def test_a_failure_that_is_not_wordpress_is_one_plain_sentence():
    said = sc.refusal(OSError("HTTPSConnectionPool(host=...)"), site="Lantern Street")
    assert (
        said.words == "QUILL could not reach SwiftLetter on Lantern Street, so nothing was saved."
    )
    assert sc.with_kept(said.words).endswith(sc.KEPT)


def test_reopen_takes_the_sites_baseline_and_keeps_the_rest():
    copy = _copy(_SENT, fmt="html")
    copy.properties["document_file"] = "garden.html"
    copy.properties["swiftletter"]["newsletter_title"] = "Gazette"
    fresh = sc.copy_for(
        "site-1", _article(_STORED, state="changed"), text_format="html", can_edit=True
    )
    sc.adopt_site(copy, fresh)
    assert copy.properties["document_file"] == "garden.html"
    assert copy.properties["swiftletter"]["newsletter_title"] == "Gazette"
    assert sc.article_of(copy).content == _STORED and copy.text == sc.wordpress_void_tags(_STORED)
