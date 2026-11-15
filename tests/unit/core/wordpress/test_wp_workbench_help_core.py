"""WordPress PRD Part D, WP-R-046 to WP-R-048, in the wx-free core.

The glossary D1 names, with examples from the person's own site; the Help and
Learning topics GitHub's Workbench has; Search Help and Explain That; Site
Health and broken-link explanations; changelogs read before an update; what
depends on a plugin; and the settings REST does not share, explained from the
site's own posts and comments. No network: every site and WordPress.org
answer is a fake.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from quill.core.wordpress import dotorg
from quill.core.wordpress import workbench_changelog as changelog
from quill.core.wordpress import workbench_update_check as uc
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site_health import health_test_lines
from quill.core.wordpress.workbench_actions import WINDOW_MENU, WORDPRESS_ACTIONS
from quill.core.wordpress.workbench_glossary import GLOSSARY, example_for, term_for
from quill.core.wordpress.workbench_help import help_rows
from quill.core.wordpress.workbench_help_actions import KEYLESS
from quill.core.wordpress.workbench_help_topics import (
    GUIDE_CHAPTERS,
    TASKS,
    chapter_for,
    explain_result,
    search_help,
)
from quill.core.wordpress.workbench_node_help import node_help, row_help
from quill.core.wordpress.workbench_plugin_depends import dependents
from quill.core.wordpress.workbench_problem_help import check_of, explanation, problem_help
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_settings_more import (
    discussion_lines,
    more_rows,
    permalink_lines,
)
from quill.core.wordpress.workbench_tree import WORDPRESS_TREE
from quill.core.workbench.menus import all_rows

SITE = "Community Radio"
GUIDE = Path(__file__).resolve().parents[4] / "docs" / "user guide" / "wordpress-and-forms"

#: Every word PRD D1 names, and every default role.
D1_WORDS = (
    "post|page|slug|permalink|excerpt|featured image|block|pattern|synced pattern|template|"
    "template part|theme|block theme|classic theme|child theme|plugin|widget|sidebar|"
    "menu location|navigation block|taxonomy|category|tag|term|custom post type|"
    "custom field|sticky|revision|autosave|trash|pending review|scheduled|draft|private|"
    "password protected|role|capability|application password|multisite|network|"
    "site health|rest api|ability|shortcode|oembed|cron|cache|redirect|404|sitemap|"
    "super admin|administrator|editor|author|contributor|subscriber|site set|"
    "content model|held as spam"
)


# -- the glossary (D1, WP-R-047) ------------------------------------------------------


def test_the_glossary_has_every_word_d1_names_each_explained() -> None:
    have = {term.casefold(): meaning for term, meaning in GLOSSARY}
    wanted = [w.strip() for w in D1_WORDS.split("|")]
    assert [w for w in wanted if w not in have] == []
    assert len(GLOSSARY) >= 60 and all(m.strip() for m in have.values())
    assert len(have) == len(GLOSSARY)  # no word twice


def _item(title: str, status: str, **raw: Any) -> WbRow:
    return WbRow(
        "item", SITE, "1", {"title": title}, "", status=status, subkind="post",
        link="https://radio.example/hello/", raw={"slug": "hello", **raw},
    )  # fmt: skip


def test_examples_come_from_what_the_site_already_showed() -> None:
    seen = {
        "item": [_item("Hello", "draft"), _item("News", "publish", sticky=True)],
        "theme": [WbRow("theme", SITE, "tt5", {"theme": "TT5"}, "", status="active")],
        "user": [WbRow("user", SITE, "4", {"name": "Ann", "role": "Author"}, "")],
    }
    assert example_for("Slug", None, seen).startswith('"Hello" has the slug hello')
    assert example_for("Draft", None, seen) == (
        f'On {SITE}, 1 of the 2 loaded items is still in draft, such as "Hello".'
    )
    assert example_for("Theme", None, seen) == f"On {SITE}, TT5 is the active theme."
    assert example_for("Author", None, seen) == f"On {SITE}, Ann is an Author."
    assert example_for("Sticky", None, seen) == f'On {SITE}, "News" is sticky.'
    assert example_for("Cron", None, seen) == ""  # nothing loaded shows it
    assert example_for("Tag", None, {}) == ""


def test_the_words_node_carries_the_examples_and_alt_f1_names_the_row() -> None:
    seen = {"item": [_item("Hello", "draft")]}
    words = {r.cell("word"): r for r in help_rows("words", seen)}
    assert '"Hello" has the slug hello' in words["Slug"].cell("meaning")
    assert term_for("item", _item("Hello", "draft")) == "Post"
    assert term_for("term", WbRow("term", SITE, "5", {}, "", subkind="post_tag")) == "Tag"
    assert term_for("problem") == "Site Health" and term_for("nothing") == ""


# -- Help and Learning, Search Help, Explain That (WP-R-046) -----------------------------


def test_help_and_learning_has_what_githubs_has() -> None:
    labels = {node.label for template, node in WORDPRESS_TREE.all_nodes() if not template}
    assert {"Do Something", "The Guide", "What Changed", "Ask a Person", "Words", "Keys"} <= labels
    for key in ("help_tasks", "help_guide", "help_changes", "help_ask"):
        assert node_help(key), key
    assert row_help("help_topic") and row_help("setting_help")


def test_every_task_goes_to_a_real_place_and_every_chapter_is_a_real_page() -> None:
    nodes = {(template, node.key) for template, node in WORDPRESS_TREE.all_nodes()}
    for _id, title, steps, place in TASKS:
        assert place in nodes and steps, title
    for row in help_rows("tasks"):
        assert row.kind == "help_topic" and ":" in row.raw["target"]
    for number, _title in GUIDE_CHAPTERS:
        assert list(GUIDE.glob(f"wordpress-forms-{number}-*.md")), number
    assert [r.raw["target"] for r in help_rows("guide")][1] == "chapter:02"


def test_ask_a_person_opens_a_blank_message_and_never_carries_a_secret() -> None:
    [row] = help_rows("ask")
    assert row.raw["target"] == "mailto:support@community-access.org"  # no subject, no body
    assert row.link == row.raw["target"]
    assert "password" in row.detail and "sends nothing" in row.detail


def test_search_help_finds_tasks_places_commands_and_words() -> None:
    labels = {"site:plugins": ("Plugins", "The site's plugins.")}
    commands = {"wordpress.workbench.approve": ("Approve", "Ctrl+Shift+A")}
    kinds = {hit.kind for hit in search_help("plugin", commands, labels)}
    assert {"task", "node", "word"} <= kinds
    [command] = [h for h in search_help("approve", commands, labels) if h.kind == "command"]
    assert command.spoken() == "Command: Approve, Ctrl+Shift+A"
    assert search_help("   ", commands, labels) == []


def test_explain_that_says_what_a_result_means() -> None:
    assert "settings stay" in explain_result("Akismet is now inactive on Community Radio.")
    assert "Recycle Bin" in explain_result("Moved Hello to the Trash.")
    assert explain_result("") == ""
    assert explain_result("Something odd.").startswith("The Workbench last said: Something odd.")


def test_ctrl_f1_opens_the_chapter_for_the_place() -> None:
    assert chapter_for("posts_drafts") == "03"
    assert chapter_for("site_health") == "08" and chapter_for("broken_links") == "07"
    assert chapter_for("overview") == "02"


def test_the_help_menu_has_every_help_key_and_the_new_rows_say_why_no_chord() -> None:
    keys = {row.key for _menu, row in all_rows(WINDOW_MENU)}
    assert {"F1", "Alt+F1", "Ctrl+F1", "Ctrl+Shift+F1", "Alt+Shift+F1", "F9", "Shift+F9"} <= keys
    for kind in ("problem", "help_topic", "setting_help"):
        rows = WORDPRESS_ACTIONS.rows_for(kind)
        assert rows[0].default and all(r.help for r in rows), kind
    offered = {r.command_id for k in ("problem", "help_topic", "setting_help", "plugin")
               for r in WORDPRESS_ACTIONS.rows_for(k)}  # fmt: skip
    assert set(KEYLESS) <= offered and all(KEYLESS.values())


# -- Site Health and broken links (D3, WP-R-048) --------------------------------------


def test_a_health_test_keeps_its_name_and_wordpress_words_as_plain_text() -> None:
    [line] = health_test_lines(
        "page-cache",
        {
            "status": "recommended",
            "label": "Page cache is not detected",
            "description": "<p>Page cache <strong>helps</strong>.</p><script>alert(1)</script>",
        },
    )
    assert (line.test, line.detail) == ("page-cache", "Page cache helps.")


def _problem(text: str, test: str = "", status: str = "recommended") -> WbRow:
    return WbRow(
        "problem", SITE, "0", {"says": text}, text, status=status,
        raw={"test": test, "description": "WordPress's words."},
    )  # fmt: skip


def test_each_problem_says_what_it_means_why_and_the_steps() -> None:
    row = _problem("Page cache is not detected.", "page-cache")
    said = explanation(row)
    for part in ("What it means for visitors", "What usually causes it", "What to do"):
        assert part in said
    assert said.endswith("WordPress says: WordPress's words.")
    assert check_of(_problem("Permalinks: plain (?p=123).")) == "permalinks"
    assert problem_help(_problem("Time zone: a fixed offset of 1 hours.")).fix == "timezone"
    assert problem_help(_problem("Who knows.", "new-test")).screen == "site_health"
    assert "This check passed" in explanation(_problem("HTTPS: ok.", "https-status", "good"))


def test_a_broken_link_is_explained_with_the_link_and_where_it_is() -> None:
    row = WbRow(
        "problem", SITE, "broken:2:https://gone.example",
        {"problem": "Broken link", "test": "News", "target": "https://gone.example"},
        "News links to https://gone.example.",
        raw={"source_id": 2, "source_type": "post", "target_url": "https://gone.example"},
    )  # fmt: skip
    found = problem_help(row)
    assert found.fix == "link"
    assert "The link: https://gone.example, in News." in explanation(row)


# -- changelogs before an update (D3) -------------------------------------------------

_LOG = (
    "<h4>5.5</h4><ul><li>Security: fixed an <a href='https://x'>XSS</a> issue.</li></ul>"
    "<h4>5.4</h4><ul><li>Runs a database update for comments.</li></ul>"
    "<h4>5.3</h4><ul><li>1. Old work.</li></ul><script>steal()</script>"
)


def test_a_changelog_is_plain_text_and_says_what_the_skipped_versions_bring() -> None:
    text = changelog.plain_text(_LOG)
    assert "<" not in text and "steal" not in text and "https://x" not in text
    assert [v for v, _b in changelog.skipped(text, "5.3", "5.5")] == ["5.5", "5.4"]
    said = changelog.summary("Akismet", text, "5.3", "5.5")
    assert "2 versions after 5.3 (5.5, 5.4)" in said
    assert "security fixes and a database update" in said and "Back up" in said
    quiet = changelog.summary("A", "5.1\n- Tidier words.\n5.0\n- First.", "5.0", "5.1")
    assert "does not mention security" in quiet


def test_wordpress_org_is_asked_for_the_changelog_with_only_the_slug() -> None:
    asked: list[str] = []

    class _Answer:
        def __init__(self, body: dict[str, Any]) -> None:
            self.body = json.dumps(body).encode()

        def __enter__(self) -> _Answer:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

        def read(self, _n: int) -> bytes:
            return self.body

    def opener(request: Any, timeout: float) -> _Answer:
        asked.append(request.full_url)
        return _Answer({"slug": "akismet", "name": "Akismet", "version": "5.5",
                        "sections": {"changelog": _LOG}})  # fmt: skip

    logs: dict[str, str] = {}
    assert uc.latest_plugins(["akismet"], opener=opener, changelogs=logs) == {"akismet": "5.5"}
    query = parse_qs(urlparse(asked[0]).query)
    assert query["request[slug]"] == ["akismet"] and query["request[fields][sections]"] == ["1"]
    assert "XSS" in logs["akismet"]
    assert "sections" not in dotorg.plugin_info_url("akismet") or (
        parse_qs(urlparse(dotorg.plugin_info_url("akismet")).query)["request[fields][sections]"]
        == ["0"]
    )
    row = WbRow("plugin", SITE, "akismet/akismet", {"plugin": "Akismet", "version": "5.3"}, ".")
    [marked] = uc.mark_rows([row], uc.Latest(plugins={"akismet": "5.5"}, changelogs=logs))
    assert "What changed in Akismet: 2 versions after 5.3" in marked.detail
    assert "Version 5.4:" in marked.detail


# -- what depends on a plugin (D3) ----------------------------------------------------


class _Site:
    def __init__(self, *, refuse_blocks: bool = False) -> None:
        self.refuse_blocks = refuse_blocks
        self.asked: list[tuple[str, dict[str, Any]]] = []

    def get(self, route: str, **params: Any) -> Any:
        self.asked.append((route, params))
        if route == "wp/v2/plugins":
            return [
                {"plugin": "gravityforms/gravityforms", "name": "Gravity Forms",
                 "textdomain": "gravityforms"},
                {"plugin": "gf-mailchimp/mc", "name": "Mailchimp Add-On",
                 "requires_plugins": ["gravityforms"]},
            ]  # fmt: skip
        if route == "wp/v2/block-types":
            if self.refuse_blocks:
                raise WordPressApiError("Forbidden", status=403)
            return [{"name": "gravityforms/form"}, {"name": "core/paragraph"}]
        if route == "wp/v2/pages" and params.get("search") == "wp:gravityforms/":
            return [{"id": 9, "title": {"rendered": "Contact"}}]
        if route == "wp/v2/posts" and params.get("search") == "[gravityform":
            return [{"id": 3, "title": {"rendered": "Sign Up"}}]
        return []


def test_what_depends_on_a_plugin_comes_from_what_the_site_exposes() -> None:
    site = _Site()
    found = dependents(site, "gravityforms/gravityforms", name="Gravity Forms",  # type: ignore[arg-type]
                       namespaces=["gf/v2"])  # fmt: skip
    assert found.plugins == ["Mailchimp Add-On"]
    assert ('"Contact"', "its gravityforms blocks") in found.content
    assert ('"Sign Up"', "its [gravityform] shortcode") in found.content
    said = found.sentence()
    assert said.startswith("What depends on Gravity Forms: Mailchimp Add-On requires it;")
    assert "QUILL uses it for Gravity Forms forms" in said and "turn it back on" in said
    assert all(not route.startswith(("http", "/")) for route, _p in site.asked)


def test_a_site_that_will_not_say_is_named_not_guessed() -> None:
    found = dependents(_Site(refuse_blocks=True), "akismet/akismet", name="Akismet")  # type: ignore[arg-type]
    assert not found.any and "would not say which pages use its blocks" in found.sentence()


# -- settings REST does not share (D2, WP-R-047) --------------------------------------


def test_each_permalinks_choice_shows_the_newest_posts_address() -> None:
    post = {"id": 12, "slug": "hello", "date": "2026-11-09T10:00:00",
            "link": "https://radio.example/2026/11/hello/"}  # fmt: skip
    lines = permalink_lines(post, "https://radio.example/")
    assert lines[0] == "Plain: your newest post would be at https://radio.example/?p=12"
    assert lines[2] == (
        "Month and name, the one this site uses now: your newest post would be at "
        "https://radio.example/2026/11/hello/"
    )
    assert lines[4].endswith("https://radio.example/hello/")
    assert permalink_lines({}, "https://radio.example") == []


def test_each_discussion_rule_says_how_many_recent_comments_it_would_have_held() -> None:
    comments = [
        {"author_email": "ann@x", "status": "approved", "date_gmt": "1", "author": 0,
         "content": {"raw": "Nice"}},
        {"author_email": "ann@x", "status": "approved", "date_gmt": "2", "author": 0,
         "content": {"raw": "Again"}},
        {"author_email": "bot@x", "status": "spam", "date_gmt": "3", "author": 0,
         "content": {"raw": "<a href='http://a'>a</a> http://b"}},
        {"author_email": "me@x", "status": "approved", "date_gmt": "4", "author": 3,
         "content": {"raw": "Thanks"}},
    ]  # fmt: skip
    lines = discussion_lines(comments)
    assert (
        lines[0]
        == "Comment must be manually approved: would have held all 4 of your last 4 comments."
    )
    assert "would have held 3 of your last 4" in lines[1]  # Ann once, the bot, me
    assert "would have held 1 of your last 4" in lines[2]  # the bot's links
    assert "would have refused 3 of your last 4" in lines[3]  # not signed in
    assert discussion_lines([]) == []


class _Settings:
    def get(self, route: str, **_params: Any) -> Any:
        if route == "wp/v2/posts":
            return [{"id": 1, "slug": "hi", "date": "2026-01-02T00:00:00",
                     "link": "https://radio.example/?p=1"}]  # fmt: skip
        if route == "wp/v2/comments":
            raise WordPressApiError("Forbidden", status=403)
        return []


def test_settings_rows_explain_permalinks_discussion_visibility_and_plugins() -> None:
    rows = more_rows(_Settings(), SITE, "https://radio.example", ["wp/v2", "wc/v3"])  # type: ignore[arg-type]
    by_name = {r.cell("setting"): r for r in rows}
    assert "Plain, the one this site uses now" in by_name["Permalinks"].detail
    assert by_name["Permalinks"].raw["screen"] == "permalinks"
    assert "no recent comments" in rows[1].detail
    assert "does not hide" not in by_name["Search engine visibility"].detail
    assert "not hidden" in by_name["Search engine visibility"].detail
    shop = by_name["WooCommerce settings"]
    assert shop.link == "https://woocommerce.com/documentation/woocommerce/"
    assert "Yoast SEO settings" not in by_name  # only the plugins the site has
    assert {r.kind for r in rows} == {"setting_help"}


@pytest.mark.parametrize("kind", ["problem", "help_topic", "setting_help"])
def test_new_row_kinds_have_f1_help(kind: str) -> None:
    assert row_help(kind)
