"""The everyday path, behaviourally: new, local save, draft to site, publish, address."""

from __future__ import annotations

from quill.ui import wordpress_item_dialogs as idlg

API = "/wp-json/wp/v2"

EDITOR = {
    "id": 7,
    "name": "Jeff",
    "slug": "jeff",
    "roles": ["editor"],
    "capabilities": {"publish_posts": True, "publish_pages": True, "edit_posts": True},
}


def _saved(status: str, item_id: int = 41):
    def answer(request, _query):
        return {
            "id": item_id,
            "type": "page",
            "title": {"raw": "Our Schedule"},
            "content": {"raw": "<!-- wp:paragraph --><p>Hi</p><!-- /wp:paragraph -->"},
            "status": status,
            "link": f"https://radio.example/?page_id={item_id}",
            "modified_gmt": "2026-11-04T10:00:00",
        }

    return answer


def _new_page(wp, wp_dialogs, title="Our Schedule"):
    wp_dialogs.answer(
        "ask_new_item",
        idlg.NewItemAnswer(
            site_index=0,
            title=title,
            slug="our-schedule",
            text_format="markdown",
            category_ids=[],
            tag_ids=[],
        ),
    )
    wp.cmd_new_page()
    wp.host.text = "Hi\n"


def test_a_command_outside_a_wordpress_document_says_so(wp) -> None:
    wp.cmd_copy_address()
    assert "This is not a WordPress document" in wp.host.said


def test_new_page_opens_a_local_file_and_sends_nothing(wp, wp_dialogs, wp_site) -> None:
    _new_page(wp, wp_dialogs)
    assert len(wp.host.opened) == 1
    assert wp.host.opened[0].exists()
    assert "nothing is sent" in wp.host.said
    assert wp_site.requests == []


def test_cancelling_new_page_opens_nothing(wp) -> None:
    wp.cmd_new_page()
    assert wp.host.opened == []


def test_save_draft_creates_the_page_as_a_draft(wp, wp_dialogs, wp_site) -> None:
    _new_page(wp, wp_dialogs)
    wp_site.on("GET", f"{API}/users/me", EDITOR).on("POST", f"{API}/pages", _saved("draft"))
    wp.cmd_save_draft()
    sent = wp_site.sent("POST", f"{API}/pages")
    assert len(sent) == 1
    assert wp_site.body(sent[0])["status"] == "draft"
    assert wp.host.announced[-1] == "Draft saved to Community Radio. It is not public."
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert copy.remote_id == 41


def test_publish_asks_first_and_cancel_sends_nothing(wp, wp_dialogs, wp_site) -> None:
    _new_page(wp, wp_dialogs)
    wp.cmd_publish()
    assert wp_dialogs.asked("confirm")
    assert wp_site.sent("POST", f"{API}/pages") == []


def test_publish_puts_the_address_on_the_clipboard(wp, wp_dialogs, wp_site) -> None:
    _new_page(wp, wp_dialogs)
    wp_dialogs.answer("confirm", True)
    wp_site.on("GET", f"{API}/users/me", EDITOR).on("POST", f"{API}/pages", _saved("publish"))
    wp.cmd_publish()
    assert wp.host.clipboard == "https://radio.example/?page_id=41"
    assert wp.host.announced[-1].startswith("Published on Community Radio")
    wp.cmd_copy_address()
    assert wp.host.announced[-1] == "Address copied."


def test_a_contributor_publish_is_submit_for_review(wp, wp_dialogs, wp_site) -> None:
    _new_page(wp, wp_dialogs)
    wp_dialogs.answer("confirm", True)
    contributor = dict(EDITOR, roles=["contributor"], capabilities={"edit_posts": True})
    wp_site.on("GET", f"{API}/users/me", contributor).on("POST", f"{API}/pages", _saved("pending"))
    wp.cmd_publish()
    assert wp_site.body(wp_site.sent("POST", f"{API}/pages")[0])["status"] == "pending"
    assert wp.host.announced[-1] == "Submitted for review on Community Radio."


def test_a_refused_send_is_spoken_and_the_local_draft_stands(wp, wp_dialogs, wp_site) -> None:
    _new_page(wp, wp_dialogs)
    wp_site.on("GET", f"{API}/users/me", EDITOR)
    wp.cmd_save_draft()  # no route for POST pages: the site answers 404
    assert "Community Radio" in wp.host.announced[-1]
    assert wp.host.current_path().exists()
    assert wp.local.copy_for_path(wp.host.current_path()).remote_id == 0
