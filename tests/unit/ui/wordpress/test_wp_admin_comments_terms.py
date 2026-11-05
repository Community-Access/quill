"""Running the Site: the Comments window, the waiting count, and Categories and Tags."""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import parse_qs, urlparse

from quill.core.wordpress import sites as st
from quill.ui import wordpress_dialogs as dlg

API = "/wp-json/wp/v2"

ADMIN = {
    "id": 1,
    "name": "Jeff",
    "slug": "jeff",
    "roles": ["administrator"],
    "capabilities": {
        "moderate_comments": True,
        "manage_categories": True,
        "manage_options": True,
        "edit_posts": True,
    },
}
AUTHOR = {
    "id": 9,
    "name": "Ann",
    "slug": "ann",
    "roles": ["author"],
    "capabilities": {"edit_posts": True, "publish_posts": True},
}


def _comment(cid, parent=0, author="Ann", status="hold", date="2026-11-01T10:00:00", post=5):
    return {
        "id": cid,
        "post": post,
        "parent": parent,
        "author_name": author,
        "date_gmt": date,
        "status": status,
        "content": {"raw": f"<p>Comment number {cid}</p>"},
        "link": f"https://radio.example/?p={post}#comment-{cid}",
    }


def _queries(wp_site, path):
    return [parse_qs(urlparse(r.full_url).query) for r in wp_site.sent("GET", path)]


def _site(wp_site, account=ADMIN, comments=None):
    wp_site.on("GET", f"{API}/users/me", account)
    wp_site.on("GET", f"{API}/comments", comments if comments is not None else [])
    wp_site.on("GET", f"{API}/posts", [{"id": 5, "title": {"rendered": "Spring Schedule"}}])
    wp_site.on("GET", f"{API}/pages", [])


# --------------------------------------------------------------------------- #
# Comments


def test_waiting_comments_are_threaded_with_replies_under_their_parent(wp, wp_site, wp_dialogs):
    _site(
        wp_site,
        comments=[
            _comment(1, author="Ann", date="2026-11-01T10:00:00"),
            _comment(2, parent=1, author="Bob", date="2026-11-01T11:00:00"),
            _comment(3, author="Cy", date="2026-11-02T09:00:00"),
        ],
    )
    wp.cmd_comments()
    rows = wp_dialogs.window["rows"]
    assert rows[0].startswith("Cy on Spring Schedule")
    assert rows[1].startswith("Ann on Spring Schedule")
    assert rows[2].startswith("reply to Ann, Bob on Spring Schedule")
    assert rows[2].endswith("level 2")
    assert "Waiting comments on Community Radio: 3" in wp_dialogs.window["purpose"]
    assert wp_dialogs.window["details"](0) == "Comment number 3"
    assert _queries(wp_site, f"{API}/comments")[0]["status"] == ["hold"]


def test_approve_sends_the_status_and_drops_the_row(wp, wp_site, wp_dialogs):
    _site(wp_site, comments=[_comment(1)])
    wp_site.on("POST", f"{API}/comments/1", _comment(1, status="approved"))
    wp.cmd_comments()
    rows = wp_dialogs.press("&Approve", 0)
    assert rows == []
    assert wp_site.body(wp_site.sent("POST", f"{API}/comments/1")[0]) == {"status": "approve"}
    assert wp.host.announced[-1] == "Comment from Ann approved."


def test_each_status_offers_its_own_moderation(wp, wp_site, wp_dialogs):
    _site(wp_site, comments=[_comment(1, status="spam")])
    wp_dialogs.answer("ask_choice", 2)  # Spam
    wp.cmd_comments()
    labels = [a.label for a in wp_dialogs.window["actions"]]
    assert "&Approve" in labels
    wp_dialogs.press("Show...", None)
    assert _queries(wp_site, f"{API}/comments")[-1]["status"] == ["spam"]
    labels = [a.label for a in wp_dialogs.window["actions"]]
    assert "&Not Spam" in labels and "&Approve" not in labels and "Re&ply..." not in labels
    wp_site.on("POST", f"{API}/comments/1", _comment(1))
    wp_dialogs.press("Not Spam", 0)
    assert wp_site.body(wp_site.sent("POST", f"{API}/comments/1")[0]) == {"status": "hold"}


def test_choosing_the_same_status_keeps_the_window(wp, wp_site, wp_dialogs):
    _site(wp_site)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_comments()
    assert wp_dialogs.press("Show...", None) is None
    assert len(wp_dialogs.list_windows) == 1


def test_trash_status_offers_restore(wp, wp_site, wp_dialogs):
    _site(wp_site, comments=[_comment(4, status="trash")])
    wp.cmd_comments(status="trash")
    wp_site.on("POST", f"{API}/comments/4", _comment(4))
    wp_dialogs.press("Restore", 0)
    assert wp_site.body(wp_site.sent("POST", f"{API}/comments/4")[0]) == {"status": "hold"}
    assert "restored to Waiting" in wp.host.said


def test_an_author_reads_approved_comments_and_is_told_why(wp, wp_site, wp_dialogs):
    _site(wp_site, account=AUTHOR, comments=[_comment(1, status="approved")])
    wp.cmd_comments()
    assert _queries(wp_site, f"{API}/comments")[0]["status"] == ["approve"]
    labels = [a.label for a in wp_dialogs.window["actions"]]
    assert "&Approve" not in labels and "&Edit..." not in labels and "Sho&w..." not in labels
    assert "Re&ply..." in labels
    assert "is an Author, which cannot moderate comments" in wp_dialogs.window["purpose"]


def test_reply_posts_under_the_parent(wp, wp_site, wp_dialogs):
    _site(wp_site, comments=[_comment(1)])
    wp_site.on("POST", f"{API}/comments", _comment(8, parent=1, author="Jeff"))
    wp_dialogs.answer("ask_text", "  Thanks, Ann. ")
    wp.cmd_comments()
    wp_dialogs.press("Reply...", 0)
    body = wp_site.body(wp_site.sent("POST", f"{API}/comments")[0])
    assert body == {"post": 5, "parent": 1, "content": "Thanks, Ann."}
    assert wp.host.announced[-1] == "Reply to Ann published on Community Radio."


def test_cancelled_reply_sends_nothing(wp, wp_site, wp_dialogs):
    _site(wp_site, comments=[_comment(1)])
    wp.cmd_comments()
    wp_dialogs.press("Reply...", 0)
    assert wp_site.sent("POST", f"{API}/comments") == []


def test_edit_saves_the_new_text(wp, wp_site, wp_dialogs):
    _site(wp_site, comments=[_comment(1)])
    wp_site.on("POST", f"{API}/comments/1", _comment(1))
    wp_dialogs.answer("ask_text", "Fixed spelling")
    wp.cmd_comments()
    rows = wp_dialogs.press("Edit...", 0)
    assert wp_site.body(wp_site.sent("POST", f"{API}/comments/1")[0]) == {
        "content": "Fixed spelling"
    }
    assert "Fixed spelling" in rows[0]


def test_edit_unchanged_sends_nothing(wp, wp_site, wp_dialogs):
    _site(wp_site, comments=[_comment(1)])
    wp_dialogs.answer("ask_text", "<p>Comment number 1</p>")
    wp.cmd_comments()
    assert wp_dialogs.press("Edit...", 0) is None
    assert wp_site.sent("POST", f"{API}/comments/1") == []


def test_open_on_site_uses_the_comment_link(wp, wp_site, wp_dialogs):
    _site(wp_site, comments=[_comment(1)])
    wp.cmd_comments()
    wp_dialogs.press("Open on Site", 0)
    assert wp.host.browsed == ["https://radio.example/?p=5#comment-1"]


def test_approve_all_confirms_with_the_count(wp, wp_site, wp_dialogs):
    _site(wp_site, comments=[_comment(1), _comment(2)])
    wp_site.on("POST", f"{API}/comments/1", _comment(1)).on(
        "POST", f"{API}/comments/2", _comment(2)
    )
    wp.cmd_comments()
    assert wp_dialogs.press("Approve All...", None) is None  # cancelled
    assert wp_site.sent("POST", f"{API}/comments/1") == []
    wp_dialogs.answer("confirm", True)
    assert wp_dialogs.press("Approve All...", None) == []
    assert "Approve 2" in wp_dialogs.asked("confirm")[-1]["yes_label"]
    assert wp.host.announced[-1] == "2 comments approved on Community Radio."


def test_waiting_count_switch_is_kept_per_site(wp, wp_site, wp_dialogs):
    _site(wp_site)
    wp.cmd_comments()
    # The harness's site starts with the count off.
    wp_dialogs.press("Waiting Count on First Use", None)
    assert wp.sites().get("radio").announce_waiting_comments is True
    wp_dialogs.press("Waiting Count on First Use", None)
    assert wp.sites().get("radio").announce_waiting_comments is False
    assert "no longer" in wp.host.announced[-1]


def test_waiting_count_is_said_once_a_session(wp, wp_site):
    response = type(wp_site).__call__.__globals__["FakeResponse"]
    wp_site.on("GET", f"{API}/comments", response([{"id": 1}], headers={"X-WP-Total": "3"}))
    on = replace(wp.profile, announce_waiting_comments=True)
    wp.announce_waiting_once(on)
    wp.announce_waiting_once(on)
    assert wp.host.announced == ["Community Radio: 3 comments waiting."]
    assert len(wp_site.sent("GET", f"{API}/comments")) == 1


def test_waiting_count_respects_the_site_setting_and_stays_quiet(wp, wp_site):
    wp.announce_waiting_once(replace(wp.profile, announce_waiting_comments=False))
    assert wp_site.requests == []
    on = replace(wp.profile, announce_waiting_comments=True)
    wp.announce_waiting_once(on)  # no route: the failure is silent
    assert wp.host.announced == []
    wp_site.on("GET", f"{API}/comments", [])
    wp.announce_waiting_once(replace(on, id="other"))
    assert wp.host.announced == []  # none waiting: nothing to say


def test_comments_with_no_site_connects_first(wp, monkeypatch):
    monkeypatch.setattr(wp, "sites", lambda: st.SiteStore())
    started = []
    monkeypatch.setattr(wp.connect_flow, "start", lambda: started.append(1))
    wp.cmd_comments()
    assert started == [1]


# --------------------------------------------------------------------------- #
# Categories and tags


def _term(tid, name, count=0, parent=0, taxonomy="category"):
    return {
        "id": tid,
        "taxonomy": taxonomy,
        "name": name,
        "slug": name.lower(),
        "count": count,
        "parent": parent,
    }


def _terms_site(wp_site, account=ADMIN, terms=None):
    wp_site.on("GET", f"{API}/users/me", account)
    wp_site.on("GET", f"{API}/settings", {"default_category": 1})
    wp_site.on(
        "GET",
        f"{API}/categories",
        terms if terms is not None else [_term(1, "News", 4), _term(2, "Events", 0, parent=1)],
    )
    wp_site.on("GET", f"{API}/tags", [])


def test_terms_list_shows_slug_count_parent_and_default(wp, wp_site, wp_dialogs):
    _terms_site(wp_site)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_manage_terms()
    assert wp_dialogs.window["rows"] == [
        "News, news, 4 posts, the default",
        "Events, events, 0 posts, under News",
    ]
    assert "Make De&fault..." in [a.label for a in wp_dialogs.window["actions"]]


def test_terms_cancelled_choice_reads_nothing(wp, wp_site, wp_dialogs):
    wp.cmd_manage_terms()
    assert wp_site.requests == []


def test_terms_need_manage_categories(wp, wp_site, wp_dialogs):
    _terms_site(wp_site, account=AUTHOR)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_manage_terms()
    assert wp_dialogs.list_windows == []
    assert wp.host.announced == [
        "Your account on Community Radio is an Author, which cannot manage categories and tags."
    ]


def test_add_rename_merge_and_delete_terms(wp, wp_site, wp_dialogs):
    _terms_site(wp_site)
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_manage_terms()
    wp_site.on("POST", f"{API}/categories", _term(3, "Shows"))
    wp_dialogs.answer("ask_text", "Shows")
    wp_dialogs.press("Add...", None)
    assert "Category Shows added to Community Radio." in wp.host.said
    wp_site.on("POST", f"{API}/categories/2", _term(2, "Gigs"))
    wp_dialogs.answer("ask_text", "Gigs")
    rows = wp_dialogs.press("Rename...", 1)
    assert rows[1].startswith("Gigs")
    # deleting the default is refused with the reason
    assert wp_dialogs.press("Delete...", 0) is None
    assert "default category" in wp.host.announced[-1]
    wp_site.on("DELETE", f"{API}/categories/2", {"deleted": True})
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("Delete...", 1)
    assert "Posts with no other category go to News." in wp_dialogs.asked("confirm")[-1]["message"]
    assert "deleted from Community Radio" in wp.host.announced[-1]


def test_merge_moves_posts_in_one_batch(wp, wp_site, wp_dialogs):
    _terms_site(wp_site, terms=[_term(1, "News", 4), _term(2, "Events", 1)])
    wp_site.on("GET", f"{API}/posts", [{"id": 30, "categories": [2]}])
    wp_site.on("POST", "/wp-json/batch/v1", {"responses": [{}]})
    wp_site.on("DELETE", f"{API}/categories/2", {"deleted": True})
    wp_dialogs.answer("ask_choice", 0, 0).answer("confirm", True)
    wp.cmd_manage_terms()
    wp_dialogs.press("Merge Into...", 1)
    batch = wp_site.body(wp_site.sent("POST", "/wp-json/batch/v1")[0])
    assert batch["requests"][0]["body"] == {"categories": [1]}
    assert wp.host.announced[-1] == "1 posts moved to News; Events deleted."


def test_convert_category_to_tag(wp, wp_site, wp_dialogs):
    _terms_site(wp_site, terms=[_term(1, "News", 4), _term(2, "Events", 1)])
    wp_site.on("POST", f"{API}/tags", _term(7, "Events", taxonomy="post_tag"))
    wp_site.on("GET", f"{API}/posts", [{"id": 30, "categories": [2, 1], "tags": [5]}])
    wp_site.on("POST", "/wp-json/batch/v1", {"responses": [{}]})
    wp_site.on("DELETE", f"{API}/categories/2", {"deleted": True})
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_manage_terms()
    assert wp_dialogs.press("Convert to Tag...", 1) is None  # cancelled
    assert wp_site.sent("POST", f"{API}/tags") == []
    assert wp_dialogs.press("Convert to Tag...", 0) is None  # the default
    assert "cannot become a tag" in wp.host.announced[-1]
    wp_dialogs.answer("confirm", True)
    rows = wp_dialogs.press("Convert to Tag...", 1)
    assert len(rows) == 1
    batch = wp_site.body(wp_site.sent("POST", "/wp-json/batch/v1")[0])
    assert batch["requests"][0]["body"] == {"categories": [1], "tags": [5, 7]}
    assert wp.host.announced[-1] == "Events is now a tag on Community Radio; 1 posts moved."


def test_find_unused_deletes_them_together_but_never_the_default(wp, wp_site, wp_dialogs):
    _terms_site(wp_site, terms=[_term(1, "News", 0), _term(2, "Events", 0), _term(3, "Old", 0)])
    wp_site.on("POST", "/wp-json/batch/v1", {"responses": [{}, {}]})
    wp_dialogs.answer("ask_choice", 0).answer("confirm", True)
    wp.cmd_manage_terms()
    rows = wp_dialogs.press("Find Unused...", None)
    assert rows == ["News, news, 0 posts, the default"]
    message = wp_dialogs.asked("confirm")[-1]["message"]
    assert message.startswith("2 categories on Community Radio have no posts: Events, Old.")
    paths = [
        r["path"] for r in wp_site.body(wp_site.sent("POST", "/wp-json/batch/v1")[0])["requests"]
    ]
    assert paths == ["/wp/v2/categories/2?force=true", "/wp/v2/categories/3?force=true"]
    assert wp.host.announced[-1] == "2 unused categories deleted from Community Radio."


def test_find_unused_with_none_says_so(wp, wp_site, wp_dialogs):
    _terms_site(wp_site, terms=[_term(1, "News", 3)])
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_manage_terms()
    wp_dialogs.press("Find Unused...", None)
    assert wp.host.announced[-1] == "Every category on Community Radio is used by a post."


def test_make_default_sets_the_setting(wp, wp_site, wp_dialogs):
    _terms_site(wp_site)
    wp_site.on("POST", f"{API}/settings", {"default_category": 2})
    wp_dialogs.answer("ask_choice", 0).answer("confirm", True)
    wp.cmd_manage_terms()
    rows = wp_dialogs.press("Make Default...", 1)
    assert wp_site.body(wp_site.sent("POST", f"{API}/settings")[0]) == {"default_category": 2}
    assert rows[1].endswith("the default")
    assert wp.host.announced[-1] == "Events is now the default category on Community Radio."


def test_an_editor_is_not_offered_the_default_category(wp, wp_site, wp_dialogs):
    editor = {**ADMIN, "roles": ["editor"], "capabilities": {"manage_categories": True}}
    _terms_site(wp_site, account=editor)
    wp_dialogs.answer("ask_choice", 1)
    wp.cmd_manage_terms()
    labels = [a.label for a in wp_dialogs.window["actions"]]
    assert "Make De&fault..." not in labels
    assert wp_site.sent("GET", f"{API}/settings") == []
    assert dlg.CLOSE is not None
