"""Notes on blocks (wordpress.md 9.15): the Notes window and Add Note, behaviourally."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import local as lc
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_api_writing_commands import WordPressApiWritingCommands

API = "/wp-json/wp/v2"
EDITOR_CAPS = {"edit_posts": True, "upload_files": True, "moderate_comments": True}
ROUTES = {"/wp/v2/comments": {}, "/wp/v2/media": {}}

P_A = "<!-- wp:paragraph -->\n<p>First words.</p>\n<!-- /wp:paragraph -->"
P_B = (
    '<!-- wp:paragraph {"metadata":{"noteId":12}} -->\n<p>Second words.</p>\n<!-- /wp:paragraph -->'
)
HTML = f"{P_A}\n\n{P_B}\n"

NOTES = [
    {"id": 12, "parent": 0, "author_name": "Sam", "date_gmt": "2026-11-01T10:00:00",
     "content": {"raw": "tighten this"}, "status": "approve"},
    {"id": 13, "parent": 12, "author_name": "Jeff", "date_gmt": "2026-11-01T11:00:00",
     "content": {"raw": "Will do."}, "status": "approve"},
    {"id": 14, "parent": 0, "author_name": "Ann", "date_gmt": "2026-11-02T10:00:00",
     "content": {"raw": "Gone block"}, "status": "hold"},
]  # fmt: skip


@pytest.fixture
def wpx(wp: Any) -> Any:
    wp.__class__ = type("Wired", (WordPressApiWritingCommands, type(wp)), {})
    return wp


def site(wp_site: Any, version: str = "6.9", caps: dict[str, bool] | None = None) -> None:
    wp_site.on(
        "GET",
        "/wp-json/",
        {
            "namespaces": ["wp/v2"],
            "routes": ROUTES,
            "generator": f"https://wordpress.org/?v={version}",
        },
    )
    wp_site.on(
        "GET",
        f"{API}/users/me",
        {"id": 1, "name": "Jeff", "roles": ["editor"], "capabilities": caps or EDITOR_CAPS},
    )


def open_doc(wp: Any, text: str = HTML, *, fmt: str = "html", remote_id: int = 41) -> Any:
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="post",
        local_id=lc.new_local_id(),
        remote_id=remote_id,
        title="Spring fair",
        text=text,
        text_format=fmt,
    )
    wp.host.open_path(wp.local.write_document(copy))
    return copy


# --------------------------------------------------------------------------- #
# what stops it


def test_notes_outside_a_wordpress_document_says_so(wpx: Any) -> None:
    wpx.cmd_notes()
    wpx.cmd_add_note()
    assert "This is not a WordPress document" in wpx.host.announced[0]
    assert len(wpx.host.announced) == 2


def test_notes_on_an_unsent_document_ask_for_a_draft_first(wpx: Any, wp_site: Any) -> None:
    open_doc(wpx, remote_id=0)
    wpx.cmd_notes()
    assert "Save Draft to Site first" in wpx.host.announced[-1]
    assert wp_site.requests == []


def test_notes_need_wordpress_6_9(wpx: Any, wp_site: Any) -> None:
    site(wp_site, version="6.8")
    open_doc(wpx)
    wpx.cmd_notes()
    assert "need WordPress 6.9 or later, and Community Radio runs 6.8" in wpx.host.announced[-1]
    assert wp_site.sent("GET", f"{API}/comments") == []


def test_notes_say_what_the_role_cannot_do(wpx: Any, wp_site: Any) -> None:
    site(wp_site, caps={"read": True})
    wp_site.requests.clear()
    open_doc(wpx)
    wpx.cmd_notes()
    assert wpx.host.announced[-1] == (
        "Your account on Community Radio is an Editor, which cannot read or write notes on blocks."
    )


def test_no_notes_is_one_sentence(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    site(wp_site)
    wp_site.on("GET", f"{API}/comments", [])
    open_doc(wpx)
    wpx.cmd_notes()
    assert "No notes on this post on Community Radio" in wpx.host.announced[-1]
    assert wp_dialogs.list_windows == []


# --------------------------------------------------------------------------- #
# the Notes window


def _shown(wpx: Any, wp_site: Any) -> None:
    site(wp_site)
    wp_site.on("GET", f"{API}/comments", NOTES)
    open_doc(wpx)
    wpx.cmd_notes()


def test_notes_list_reads_who_where_and_what(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _shown(wpx, wp_site)
    asked = wp_site.sent("GET", f"{API}/comments")[0].full_url
    assert "type=note" in asked and "post=41" in asked
    window = wp_dialogs.window
    assert window["rows"] == [
        "Sam on the second paragraph: tighten this, 1 reply",
        "Ann on a block not in your copy: Gone block, resolved",
    ]
    assert "2, 1 open" in window["purpose"]
    assert "Jeff" in window["details"](0) and "Will do." in window["details"](0)


def test_go_to_it_puts_the_caret_on_the_block(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _shown(wpx, wp_site)
    assert wp_dialogs.press("&Go to It", 0) is dlg.CLOSE
    assert wpx.host.caret == HTML.index(P_B)
    wpx.host.caret = 0
    assert wp_dialogs.enter(0) is dlg.CLOSE
    assert wpx.host.caret == HTML.index(P_B)


def test_go_to_a_note_whose_block_is_gone(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _shown(wpx, wp_site)
    assert wp_dialogs.press("&Go to It", 1) is None
    assert "not in your copy" in wpx.host.announced[-1]


def test_reply_sends_a_note_reply(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _shown(wpx, wp_site)
    wp_site.on("POST", f"{API}/comments", {"id": 20, "parent": 12})
    wp_dialogs.answer("ask_text", "Done now.")
    rows = wp_dialogs.press("&Reply...", 0)
    body = wp_site.body(wp_site.sent("POST", f"{API}/comments")[0])
    assert body == {"post": 41, "parent": 12, "content": "Done now.", "type": "note"}
    assert rows[0].endswith("2 replies")
    assert wpx.host.announced[-1] == "Reply to Sam's note saved on Community Radio."


def test_reply_cancelled_sends_nothing(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _shown(wpx, wp_site)
    assert wp_dialogs.press("&Reply...", 0) is None
    assert wp_site.sent("POST", f"{API}/comments") == []


def test_resolve_then_reopen(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _shown(wpx, wp_site)
    wp_site.on("POST", f"{API}/comments/12", {"id": 12})
    wp_site.on("POST", f"{API}/comments", {"id": 21})
    rows = wp_dialogs.press("Re&solve or Reopen", 0)
    assert wp_site.body(wp_site.sent("POST", f"{API}/comments/12")[0]) == {"status": "hold"}
    marker = wp_site.body(wp_site.sent("POST", f"{API}/comments")[0])
    assert marker["meta"] == {"_wp_note_status": "resolved"} and marker["parent"] == 12
    assert rows[0].endswith("resolved")
    assert wpx.host.announced[-1] == "Sam's note resolved on Community Radio."
    rows = wp_dialogs.press("Re&solve or Reopen", 0)
    assert wp_site.body(wp_site.sent("POST", f"{API}/comments/12")[1]) == {"status": "approve"}
    assert not rows[0].endswith("resolved")
    assert wpx.host.announced[-1] == "Sam's note reopened on Community Radio."


def test_resolve_keeps_working_when_the_marker_is_refused(
    wpx: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    _shown(wpx, wp_site)
    wp_site.on("POST", f"{API}/comments/12", {"id": 12})
    wp_dialogs.press("Re&solve or Reopen", 0)  # no POST comments route: a 404
    assert wpx.host.announced[-1] == "Sam's note resolved on Community Radio."


def test_add_note_button_closes_and_opens_add_note(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _shown(wpx, wp_site)
    wpx.host.caret = 2
    assert wp_dialogs.press("&Add Note...", None) is dlg.CLOSE
    assert wp_dialogs.asked("ask_text")[-1]["title"] == "Add Note on The first paragraph"


# --------------------------------------------------------------------------- #
# Add Note


def test_add_note_needs_the_caret_in_a_block(wpx: Any, wp_site: Any) -> None:
    open_doc(wpx, text="\n\n" + HTML)
    wpx.host.caret = 0
    wpx.cmd_add_note()
    assert "caret is not in a block" in wpx.host.announced[-1]


def test_add_note_in_html_ties_the_note_to_the_block(
    wpx: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    site(wp_site)
    wp_site.on("POST", f"{API}/comments", {"id": 30, "author_name": "Jeff"})
    open_doc(wpx)
    wpx.host.caret = 3
    wp_dialogs.answer("ask_text", "Check the date.")
    wpx.cmd_add_note()
    body = wp_site.body(wp_site.sent("POST", f"{API}/comments")[0])
    assert body == {"post": 41, "content": "Check the date.", "type": "note"}
    assert '"metadata":{"noteId":30}' in wpx.host.text.split("\n\n")[0]
    assert P_B in wpx.host.text
    assert wpx.host.announced[-1] == (
        "Note added on the first paragraph on Community Radio. Save Draft to Site or Publish "
        "to tie it to the block there."
    )


def test_add_note_cancelled_sends_nothing(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    site(wp_site)
    open_doc(wpx)
    wpx.host.caret = 3
    wpx.cmd_add_note()
    assert wp_site.requests == []


def test_add_note_in_markdown_asks_before_protecting_the_block(
    wpx: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    site(wp_site)
    wp_site.on("POST", f"{API}/comments", {"id": 31})
    copy = open_doc(wpx, text="Welcome to the fair.\n", fmt="markdown")
    wpx.cmd_add_note()  # the confirmation is cancelled
    assert wp_site.requests == [] and wp_dialogs.asked("ask_text") == []
    wp_dialogs.answer("confirm", True).answer("ask_text", "Name the day.")
    wpx.cmd_add_note()
    assert wpx.host.text.startswith("::: block core/paragraph island-")
    kept = wpx.local.copy_for_path(wpx.host.current_path()).properties["islands"]
    assert any('"noteId":31' in markup for markup in kept.values())
    assert copy.remote_id == 41


def test_add_note_on_an_old_site_explains_after_asking(
    wpx: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    site(wp_site, version="6.8")
    open_doc(wpx)
    wpx.host.caret = 3
    wp_dialogs.answer("ask_text", "Check the date.")
    wpx.cmd_add_note()
    assert "need WordPress 6.9" in wpx.host.announced[-1]
    assert "noteId" not in wpx.host.text.split("\n\n")[0]
