"""Site-wide Find and Replace, behaviourally (wordpress.md 9.5)."""

from __future__ import annotations

import json

from quill.core.wordpress import site_fixes as sf

API = "/wp-json/wp/v2"
BATCH = "/wp-json/batch/v1"
CONTENT = (
    '<!-- wp:paragraph {"className":"call-555-0100"} -->\n'
    "<p>Call the studio on 555-0100 any time.</p>\n<!-- /wp:paragraph -->"
)


def _page(content=CONTENT, modified="2026-11-01T09:00:00"):
    return {
        "id": 5,
        "type": "page",
        "title": {"raw": "Contact"},
        "content": {"raw": content},
        "link": "https://radio.example/contact/",
        "modified_gmt": modified,
    }


def _ask(wp_dialogs, find="555-0100", replace="555-0199", mode=0):
    wp_dialogs.answer("ask_text", find, replace)
    wp_dialogs.answer("ask_choice", mode)


def _batch_ok(request, _query):
    count = len(json.loads(request.data)["requests"])
    return {"responses": [{"status": 200, "body": {"modified_gmt": "2026-11-04T12:00:00"}}] * count}


def test_cancelling_at_find_does_nothing(wp, wp_site) -> None:
    wp.cmd_site_find_replace()
    assert wp_site.requests == []


def test_a_bad_pattern_is_said_and_nothing_is_searched(wp, wp_site, wp_dialogs) -> None:
    _ask(wp_dialogs, find="(", mode=2)
    wp.cmd_site_find_replace()
    assert wp.host.announced[-1].startswith("That pattern does not work")
    assert wp_site.requests == []


def test_no_matches_says_so(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/pages", []).on("GET", f"{API}/posts", [])
    _ask(wp_dialogs)
    wp.cmd_site_find_replace()
    assert wp.host.announced[-1] == "No matches for '555-0100' on Community Radio."


def test_matches_are_chosen_then_replaced_and_kept_for_undo(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/pages", [_page()]).on("GET", f"{API}/posts", [])
    wp_site.on("POST", BATCH, _batch_ok)
    _ask(wp_dialogs)
    wp.cmd_site_find_replace()
    first = wp_site.requests[0].full_url
    assert "search=555-0100" in first and "context=edit" in first
    assert wp.host.announced[-1] == "1 match on 1 page on Community Radio."
    window = wp_dialogs.window
    assert window["rows"] == ["Included: Contact: ...Call the studio on [555-0100] any time...."]
    assert wp_dialogs.press("&Include or Skip", 0)[0].startswith("Skipped:")
    assert wp_dialogs.press("Include &All", None)[0].startswith("Included:")
    assert wp_dialogs.press("S&kip All", None)[0].startswith("Skipped:")
    assert wp_dialogs.press("&Replace...", None) is None
    assert "Nothing is included" in wp.host.said
    rows = wp_dialogs.press("Include &Block Settings", None)
    assert len(rows) == 2 and all(r.startswith("Included:") for r in rows)
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Replace...", None)
    assert wp_dialogs.asked("confirm")[-1]["yes_label"] == "Replace in 1 Page"
    sent = wp_site.body(wp_site.sent("POST", BATCH)[0])["requests"][0]["body"]["content"]
    assert "555-0100" not in sent and sent.count("555-0199") == 2
    assert (
        wp.host.announced[-1] == "Changed 1 page on Community Radio. Undo Site Fix puts them back."
    )
    record = sf.FixRecordStore(wp.local.root).load("radio")[0]
    assert record.label == "Replaced '555-0100' with '555-0199'"
    assert record.items[0].before == CONTENT


def test_block_settings_are_left_alone_by_default(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/pages", [_page()]).on("GET", f"{API}/posts", [])
    wp_site.on("POST", BATCH, _batch_ok)
    _ask(wp_dialogs)
    wp.cmd_site_find_replace()
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Replace...", None)
    sent = wp_site.body(wp_site.sent("POST", BATCH)[0])["requests"][0]["body"]["content"]
    assert '"className":"call-555-0100"' in sent and "on 555-0199 any" in sent


def test_only_block_settings_matching_is_said(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/pages", [_page()]).on("GET", f"{API}/posts", [])
    _ask(wp_dialogs, find="call-555")
    wp.cmd_site_find_replace()
    assert "only inside block settings" in wp.host.announced[-1]
    assert wp_dialogs.window["rows"] == []


def test_a_page_changed_since_the_search_is_left_alone(wp, wp_site, wp_dialogs) -> None:
    answers = iter([[_page()], [_page("<p>Someone rewrote it. 555-0100</p>")]])
    wp_site.on("GET", f"{API}/pages", lambda _r, _q: next(answers)).on("GET", f"{API}/posts", [])
    _ask(wp_dialogs)
    wp.cmd_site_find_replace()
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Replace...", None)
    assert wp_site.sent("POST", BATCH) == []
    assert wp.host.announced[-1] == (
        "Nothing was changed on Community Radio. 1 page changed on the site since and was left "
        "alone."
    )


def test_a_pattern_search_reads_everything_and_expands_groups(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/pages", [_page()]).on("GET", f"{API}/posts", [])
    wp_site.on("POST", BATCH, _batch_ok)
    _ask(wp_dialogs, find=r"555-(\d+)", replace=r"556-\1", mode=3)
    wp.cmd_site_find_replace()
    assert "search=" not in wp_site.requests[0].full_url
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Replace...", None)
    sent = wp_site.body(wp_site.sent("POST", BATCH)[0])["requests"][0]["body"]["content"]
    assert "on 556-0100 any" in sent
