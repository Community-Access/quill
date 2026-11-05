"""Check the Whole Site, Fix in Bulk and Undo Site Fix, behaviourally (wordpress.md 9.5)."""

from __future__ import annotations

from pathlib import Path

from quill.core.wordpress import cdp
from quill.core.wordpress import page_audit as pa
from quill.core.wordpress import site_fixes as sf

API = "/wp-json/wp/v2"
BATCH = "/wp-json/batch/v1"

NEW_TAB = '<p><a href="https://x.example" target="_blank">Listen live</a></p>'


def _page(item_id, content, title="Home", kind="page", modified="2026-11-01T09:00:00"):
    return {
        "id": item_id,
        "type": kind,
        "title": {"raw": title},
        "content": {"raw": content},
        "link": f"https://radio.example/?p={item_id}",
        "modified_gmt": modified,
    }


def _site(wp_site, pages, posts=()):
    wp_site.on("GET", f"{API}/pages", list(pages)).on("GET", f"{API}/posts", list(posts))


def _batch_ok(stamp="2026-11-04T11:00:00"):
    def answer(request, _query):
        import json

        count = len(json.loads(request.data)["requests"])
        return {"responses": [{"status": 200, "body": {"modified_gmt": stamp}}] * count}

    return answer


def _no_axe(monkeypatch):
    monkeypatch.setattr(pa, "axe_available", lambda path=None: False)


def test_an_empty_site_says_so(wp, wp_site, monkeypatch) -> None:
    _no_axe(monkeypatch)
    _site(wp_site, [])
    wp.cmd_check_site()
    assert wp.host.announced[-1] == "Community Radio has no published pages or posts to check."


def test_content_check_groups_problems_and_keeps_history(
    wp, wp_site, wp_dialogs, monkeypatch
) -> None:
    _no_axe(monkeypatch)
    _site(wp_site, [_page(1, NEW_TAB)], [_page(2, '<img src="a.jpg">', "News", "post")])
    wp.cmd_check_site()
    assert wp.host.announced[-1] == "Community Radio: 2 problems on 2 of 2 pages."
    rows = wp_dialogs.window["rows"]
    assert any(r.startswith("Links that open a new tab without saying so: 1") for r in rows)
    assert "Only your content was checked" in wp_dialogs.window["purpose"]
    wp.cmd_check_site()
    assert wp.host.announced[-1].endswith(
        ". 2 in " + wp._check_history().load("radio")[1].month + "."
    )


def test_fix_in_bulk_previews_confirms_batches_and_keeps_the_old_text(
    wp, wp_site, wp_dialogs, monkeypatch
) -> None:
    _no_axe(monkeypatch)
    _site(wp_site, [_page(1, NEW_TAB)], [_page(2, '<img src="a.jpg">', "News", "post")])
    wp_site.on("POST", BATCH, _batch_ok())
    wp.cmd_check_site()
    rows = wp_dialogs.window["rows"]
    index = next(i for i, r in enumerate(rows) if r.startswith("Links that open"))
    wp_dialogs.answer("confirm", True)
    assert wp_dialogs.press("Fix in &Bulk...", index) is not None
    assert "Listen live (opens in a new tab)" in wp_dialogs.reports[-1]["text"]
    assert wp_dialogs.asked("confirm")[-1]["yes_label"] == "Fix 1 Page"
    body = wp_site.body(wp_site.sent("POST", BATCH)[0])
    assert body["requests"][0]["path"] == "/wp/v2/pages/1"
    assert "(opens in a new tab)" in body["requests"][0]["body"]["content"]
    assert wp.host.announced[-1] == "Fixed 1 page on Community Radio. Undo Site Fix puts them back."
    record = sf.FixRecordStore(wp.local.root).load("radio")[0]
    assert record.items[0].before == NEW_TAB


def test_fix_in_bulk_cancelled_sends_nothing(wp, wp_site, wp_dialogs, monkeypatch) -> None:
    _no_axe(monkeypatch)
    _site(wp_site, [_page(1, NEW_TAB)])
    wp.cmd_check_site()
    wp_dialogs.press("Fix in &Bulk...", 0)
    assert wp_site.sent("POST", BATCH) == []


def test_a_problem_that_needs_words_is_not_fixed_in_bulk(
    wp, wp_site, wp_dialogs, monkeypatch
) -> None:
    _no_axe(monkeypatch)
    _site(wp_site, [_page(1, '<img src="a.jpg">')])
    wp.cmd_check_site()
    assert wp_dialogs.press("Fix in &Bulk...", 0) is None
    assert "each needs your words" in wp.host.said


def test_pages_lists_and_opens(wp, wp_site, wp_dialogs, monkeypatch) -> None:
    _no_axe(monkeypatch)
    _site(wp_site, [_page(1, '<img src="a.jpg">')])
    opened = []
    wp.open_item = lambda profile, kind, item_id: opened.append((kind, item_id))
    wp.cmd_check_site()
    wp_dialogs.press("&Pages...", 0)
    assert wp_dialogs.window["rows"] == ["Home"]
    wp_dialogs.press("Open on the &Site", 0)
    assert wp.host.browsed == ["https://radio.example/?p=1"]
    wp_dialogs.press("&Open", 0)
    assert opened == [("page", 1)]


def _with_axe(monkeypatch, result):
    monkeypatch.setattr(pa, "axe_available", lambda path=None: True)
    monkeypatch.setattr(cdp, "find_browser", lambda candidates=None: Path("chrome.exe"))
    calls = []

    def audit_urls(urls, **_kw):
        calls.append(list(urls))
        if isinstance(result, BaseException):
            raise result
        return [result for _ in urls]

    monkeypatch.setattr(pa, "audit_urls", audit_urls)
    return calls


def test_the_visitors_view_runs_in_tens_with_progress(wp, wp_site, wp_dialogs, monkeypatch) -> None:
    finding = pa.AxeFinding(
        "color-contrast",
        "",
        "",
        "",
        "",
        (),
        "violation",
        (pa.AxeNode(("footer",), "<p>x</p>", "", "theme"),),
    )
    calls = _with_axe(monkeypatch, pa.PageAudit("u", (finding,)))
    _site(wp_site, [_page(i, "<p>Fine</p>", f"P{i}") for i in range(1, 13)])
    wp_dialogs.answer("ask_choice", 1)
    wp.cmd_check_site()
    assert [len(c) for c in calls] == [10, 2]
    assert "Checked 10 of 12 pages on Community Radio." in wp.host.said
    assert wp_dialogs.window["rows"] == [
        "Text too faint against its background: 12, on 12 pages, in the theme or a plugin"
    ]
    assert wp._check_history().latest("radio").visitor_checked


def test_choosing_content_only_skips_the_browser(wp, wp_site, wp_dialogs, monkeypatch) -> None:
    calls = _with_axe(monkeypatch, pa.PageAudit("u", ()))
    _site(wp_site, [_page(1, '<img src="a.jpg">')])
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_check_site()
    assert calls == []
    assert "1 problem" in wp.host.said


def test_cancelling_the_choice_stops(wp, wp_site, wp_dialogs, monkeypatch) -> None:
    calls = _with_axe(monkeypatch, pa.PageAudit("u", ()))
    _site(wp_site, [_page(1, "<p>x</p>")])
    wp.cmd_check_site()
    assert calls == [] and wp_dialogs.list_windows == []


def test_a_browser_failure_falls_back_to_the_content_report(
    wp, wp_site, wp_dialogs, monkeypatch
) -> None:
    _with_axe(monkeypatch, cdp.CdpError("The browser closed the connection."))
    _site(wp_site, [_page(1, '<img src="a.jpg">')])
    wp_dialogs.answer("ask_choice", 1)
    wp.cmd_check_site()
    assert "The visitor's view stopped: The browser closed the connection." in wp.host.said
    assert wp_dialogs.window["rows"][0].startswith("Images with no alt text")


# --------------------------------------------------------------------------- #
# Undo Site Fix


def _record(wp, *, undone=""):
    store = sf.FixRecordStore(wp.local.root)
    fix = sf.SiteFix(
        "fix1",
        "radio",
        "2026-11-04T10:00:00",
        "Stop videos playing by themselves",
        [sf.FixedItem("page", 1, "Home", "<p>old</p>", "2026-11-04T11:00:00")],
        undone,
    )
    store.add(fix)
    return store


def test_undo_with_nothing_to_undo(wp) -> None:
    wp.cmd_undo_site_fix()
    assert wp.host.announced[-1] == "There are no site fixes to undo on Community Radio."


def test_undo_puts_pages_back_after_a_named_confirmation(wp, wp_site, wp_dialogs) -> None:
    store = _record(wp)
    _site(wp_site, [_page(1, "<p>new</p>", modified="2026-11-04T11:00:00")])
    wp_site.on("POST", BATCH, _batch_ok())
    wp.cmd_undo_site_fix()
    assert "Stop videos playing by themselves, 1 page" in wp_dialogs.window["rows"][0]
    wp_dialogs.press("&View...", 0)
    assert "Home" in wp_dialogs.reports[-1]["text"]
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Undo...", 0)
    assert wp_dialogs.asked("confirm")[-1]["yes_label"] == "Put Back 1 Page"
    body = wp_site.body(wp_site.sent("POST", BATCH)[0])
    assert body["requests"][0]["body"]["content"] == "<p>old</p>"
    assert wp.host.announced[-1] == "Put back 1 page on Community Radio."
    assert store.load("radio")[0].undone


def test_undo_leaves_pages_changed_since_alone(wp, wp_site, wp_dialogs) -> None:
    _record(wp)
    _site(wp_site, [_page(1, "<p>edited</p>", modified="2026-11-05T08:00:00")])
    wp.cmd_undo_site_fix()
    wp_dialogs.press("&Undo...", 0)
    assert "Every page in that fix has changed on Community Radio since" in wp.host.said
    assert wp_site.sent("POST", BATCH) == []


def test_undo_cancelled_sends_nothing(wp, wp_site, wp_dialogs) -> None:
    _record(wp)
    _site(wp_site, [_page(1, "<p>new</p>", modified="2026-11-04T11:00:00")])
    wp.cmd_undo_site_fix()
    wp_dialogs.press("&Undo...", 0)
    assert wp_site.sent("POST", BATCH) == []


def test_a_fix_already_put_back_says_so(wp, wp_dialogs) -> None:
    _record(wp, undone="2026-11-04T12:00:00")
    wp.cmd_undo_site_fix()
    assert wp_dialogs.press("&Undo...", 0) is None
    assert "already been put back" in wp.host.said
