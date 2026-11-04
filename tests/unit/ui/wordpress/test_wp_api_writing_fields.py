"""Custom fields, which password, picture sizes and bulk moderation (wordpress.md 9.15)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from quill.core.wordpress import local as lc
from quill.core.wordpress import sites as st
from quill.core.wordpress.media_edit import dialog_sizes
from quill.core.wordpress.site_media import media_from_payload
from quill.ui import wordpress_block_dialogs as bdlg
from quill.ui import wordpress_item_dialogs as idlg
from quill.ui.wordpress_api_writing_commands import WordPressApiWritingCommands
from quill.ui.wordpress_more_commands import item_from_copy

API = "/wp-json/wp/v2"
INTROSPECT = "/wp/v2/users/(?P<user_id>(?:[\\d]+|me))/application-passwords/introspect"
CAPS = {"edit_posts": True, "upload_files": True, "moderate_comments": True}
SCHEMA = {
    "schema": {
        "properties": {
            "meta": {
                "properties": {
                    "seo_title": {"type": "string", "description": "The SEO title"},
                    "event_count": {"type": "integer"},
                    "on_front": {"type": "boolean", "title": "Show on the front page"},
                    "speakers": {"type": "array"},
                }
            }
        }
    }
}


@pytest.fixture
def wpx(wp: Any) -> Any:
    wp.__class__ = type("Wired", (type(wp), WordPressApiWritingCommands), {})
    return wp


class Form(list):
    def __init__(self) -> None:
        super().__init__()
        self.answers: list[Any] = []

    def __call__(self, _parent: Any, _show_modal: Any, **kwargs: Any) -> Any:
        self.append(kwargs)
        return self.answers.pop(0) if self.answers else None


@pytest.fixture
def form(monkeypatch: pytest.MonkeyPatch) -> Form:
    script = Form()
    monkeypatch.setattr(bdlg, "ask_fields", script)
    return script


def site(wp_site: Any, routes: dict[str, Any] | None = None, caps: Any = None) -> None:
    wp_site.on(
        "GET",
        "/wp-json/",
        {"namespaces": ["wp/v2"], "routes": routes if routes is not None else {INTROSPECT: {}}},
    )
    wp_site.on(
        "GET",
        f"{API}/users/me",
        {"id": 1, "name": "Jeff", "roles": ["editor"], "capabilities": caps or CAPS},
    )


def open_doc(wp: Any, *, kind: str = "post", remote_id: int = 41) -> Any:
    copy = lc.WorkingCopy(
        site_id="radio",
        kind=kind,
        local_id=lc.new_local_id(),
        remote_id=remote_id,
        title="Spring fair",
        text="Hello.\n",
    )
    wp.host.open_path(wp.local.write_document(copy))
    return copy


def kept(wp: Any) -> dict[str, Any]:
    return dict(wp.local.copy_for_path(wp.host.current_path()).properties.get("meta") or {})


# --------------------------------------------------------------------------- #
# custom fields


def _fields_site(wp_site: Any, kind: str = "posts") -> None:
    site(wp_site)
    wp_site.on("OPTIONS", f"{API}/{kind}", SCHEMA)
    wp_site.on(
        "GET",
        f"{API}/{kind}/41",
        {"meta": {"seo_title": "Old", "event_count": 3, "on_front": False}},
    )


def test_custom_fields_outside_a_document_says_so(wpx: Any) -> None:
    wpx.cmd_custom_fields()
    assert wpx.host.announced[-1].startswith("Custom Fields works in a WordPress page or post")


def test_custom_fields_are_labelled_fields_from_the_schema(
    wpx: Any, wp_site: Any, form: Form
) -> None:
    _fields_site(wp_site)
    open_doc(wpx)
    form.answers.append({"seo_title": "Spring fair 2027", "event_count": "3", "on_front": False})
    wpx.cmd_custom_fields()
    shown = form[0]
    labels = [f.label for f in shown["fields"]]
    assert labels == ["&Seo title:", "&Event count:", "S&how on the front page"]
    assert shown["fields"][0].value == "Old"
    assert "1 more are lists or groups" in shown["purpose"]
    assert kept(wpx) == {"seo_title": "Spring fair 2027"}
    assert wpx.host.announced[-1] == (
        "1 custom field kept with your copy. They go to Community Radio when you next send."
    )


def test_custom_fields_go_with_the_next_send(wpx: Any) -> None:
    copy = open_doc(wpx)
    copy.properties["meta"] = {"seo_title": "New"}
    body = item_from_copy(copy, "<p>x</p>", status="draft").to_body()
    assert body["meta"] == {"seo_title": "New"}
    copy.properties.pop("meta")
    assert "meta" not in item_from_copy(copy, "<p>x</p>", status="draft").to_body()


def test_custom_fields_with_a_bad_number_keep_nothing(wpx: Any, wp_site: Any, form: Form) -> None:
    _fields_site(wp_site)
    open_doc(wpx)
    form.answers.append({"seo_title": "Old", "event_count": "three", "on_front": False})
    wpx.cmd_custom_fields()
    assert wpx.host.announced[-1] == "Event count needs a number. Nothing was kept; try again."
    assert kept(wpx) == {}


def test_custom_fields_unchanged_and_cancelled(wpx: Any, wp_site: Any, form: Form) -> None:
    _fields_site(wp_site)
    open_doc(wpx)
    form.answers.append({"seo_title": "Old", "event_count": "3", "on_front": False})
    wpx.cmd_custom_fields()
    assert wpx.host.announced[-1] == "No custom fields changed."
    said = len(wpx.host.announced)
    wpx.cmd_custom_fields()  # the form is cancelled
    assert len(wpx.host.announced) == said and kept(wpx) == {}


def test_a_site_without_custom_fields_says_so_only_when_asked(
    wpx: Any, wp_site: Any, form: Form
) -> None:
    site(wp_site)
    wp_site.on("OPTIONS", f"{API}/posts", {"schema": {"properties": {}}})
    copy = open_doc(wpx)
    wpx.cmd_custom_fields()
    assert wpx.host.announced[-1] == "Community Radio has no custom fields for a post."
    said = len(wpx.host.announced)
    wpx.custom_fields_after_properties(copy, wpx.profile)
    assert len(wpx.host.announced) == said and form == []


def test_properties_then_opens_the_custom_fields(
    wpx: Any, wp_site: Any, wp_dialogs: Any, form: Form
) -> None:
    _fields_site(wp_site, "pages")
    open_doc(wpx, kind="page")
    wp_dialogs.answer(
        "ask_properties",
        idlg.PropertiesAnswer(
            title="Spring fair",
            slug="fair",
            status="draft",
            excerpt="",
            category_ids=[],
            tag_ids=[],
            comments_open=True,
            sticky=False,
        ),
    )
    form.answers.append({"seo_title": "Fair", "event_count": "4", "on_front": True})
    wpx.cmd_properties()
    assert kept(wpx) == {"seo_title": "Fair", "event_count": 4, "on_front": True}
    assert "3 custom fields kept" in wpx.host.announced[-1]


# --------------------------------------------------------------------------- #
# which application password, and Sign Out


def test_which_password_names_the_one_quill_uses(wpx: Any, wp_site: Any) -> None:
    site(wp_site)
    wp_site.on(
        "GET",
        f"{API}/users/me/application-passwords/introspect",
        {"uuid": "q1", "name": "QUILL on Desk", "created": "2026-10-01T09:00:00"},
    )
    action = wpx.which_password_action()
    assert action.label == "&Which Password"
    assert action.run(0) is None
    assert wpx.host.announced[-1] == (
        "On Community Radio, QUILL is using the application password named QUILL on Desk, "
        "made 1 October 2026, 9:00 AM."
    )
    assert action.run(5) is None  # no such row


def test_which_password_on_a_site_too_old_to_say(wpx: Any, wp_site: Any) -> None:
    site(wp_site, routes={})
    wpx.which_password_action().run(0)
    assert "cannot say which application password" in wpx.host.announced[-1]
    assert wp_site.sent("GET", f"{API}/users/me/application-passwords/introspect") == []


def test_which_password_when_the_site_does_not_answer(wpx: Any, wp_site: Any) -> None:
    site(wp_site)  # the route is listed, but answers 404
    wpx.which_password_action().run(0)
    assert wpx.host.announced[-1] == (
        "Community Radio did not say which application password QUILL is using."
    )


def test_which_password_on_wordpress_com_with_a_token(wpx: Any, tmp_path: Any) -> None:
    profile = replace(wpx.profile, kind="wpcom", username="", wpcom_site="radio.example")
    wpx.say_which_password(profile)
    assert "WordPress.com token" in wpx.host.announced[-1]


def test_sign_out_names_the_password_it_revoked(
    wpx: Any, wp_site: Any, wp_dialogs: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(st, "forget_secret", lambda _id: None)
    wp_site.on(
        "GET",
        f"{API}/users/me/application-passwords/introspect",
        {"uuid": "q1", "name": "QUILL on Desk"},
    )
    wp_site.on("DELETE", f"{API}/users/me/application-passwords/q1", {"deleted": True})
    wp_dialogs.answer("ask_choice", 1)
    wpx.cmd_sign_out()
    assert len(wp_site.sent("DELETE", f"{API}/users/me/application-passwords/q1")) == 1
    assert wpx.host.announced[-1] == (
        "Signed out of Community Radio: the password QUILL on Desk is revoked on the site and "
        "forgotten here, and the site is kept in your list."
    )


# --------------------------------------------------------------------------- #
# choose a size when inserting


UPLOADS = "https://radio.example/wp-content/uploads"
FAIR = {
    "id": 5,
    "title": {"raw": "Fair"},
    "media_type": "image",
    "mime_type": "image/jpeg",
    "source_url": f"{UPLOADS}/fair.jpg",
    "alt_text": "Volunteers",
    "media_details": {
        "width": 1600,
        "height": 1200,
        "sizes": {
            "medium": {"width": 300, "height": 225, "source_url": f"{UPLOADS}/fair-300x225.jpg"},
            "thumbnail": {"width": 150, "height": 150, "source_url": f"{UPLOADS}/fair-150.jpg"},
            "full": {"width": 1600, "height": 1200, "source_url": f"{UPLOADS}/fair.jpg"},
        },
    },
}


def test_sizes_are_offered_by_name_and_width() -> None:
    rows = dialog_sizes(media_from_payload(FAIR))
    assert [r[0] for r in rows] == [
        "Thumbnail, 150 wide",
        "Medium, 300 wide",
        "Full size, 1600 wide",
    ]
    assert rows[1][1:] == ("medium", f"{UPLOADS}/fair-300x225.jpg")
    assert dialog_sizes(media_from_payload({**FAIR, "media_details": {"width": 9}})) == []


def test_inserting_a_smaller_size_uses_the_sites_file(
    wpx: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    copy = open_doc(wpx)
    copy.text = ""
    wp_site.on("GET", f"{API}/media", [FAIR])
    wp_dialogs.answer("ask_choice", 0)
    wp_dialogs.answer(
        "ask_image",
        idlg.ImageAnswer(
            alt="Volunteers",
            decorative=False,
            caption="",
            width=0,
            featured=False,
            link="",
            source=f"{UPLOADS}/fair-300x225.jpg",
            size_slug="medium",
        ),
    )
    wpx.cmd_insert_from_library()
    assert len(wp_dialogs.asked("ask_image")[0]["sizes"]) == 3
    assert f"![Volunteers]({UPLOADS}/fair-300x225.jpg) {{id=5 size=medium}}" in wpx.host.text


# --------------------------------------------------------------------------- #
# bulk moderation


WAITING = [
    {"id": n, "post": 0, "author_name": who, "date_gmt": f"2026-11-0{n}T10:00:00",
     "status": "hold", "content": {"raw": f"Comment {n}"}}
    for n, who in ((1, "Ann"), (2, "Bob"), (3, "Cy"))
]  # fmt: skip


def _comments(wpx: Any, wp_site: Any, caps: Any = None) -> None:
    wp_site.on(
        "GET",
        f"{API}/users/me",
        {"id": 1, "name": "Jeff", "roles": ["editor"], "capabilities": caps or CAPS},
    )
    wp_site.on("GET", f"{API}/comments", WAITING)
    for n in (1, 2, 3):
        wp_site.on("POST", f"{API}/comments/{n}", {"id": n})
    wpx.cmd_comments()


def test_mark_then_moderate_together(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _comments(wpx, wp_site)
    rows = wp_dialogs.press("Mar&k", 0)
    rows = wp_dialogs.press("Mar&k", 2)
    assert rows[0].startswith("Marked, ") and rows[2].startswith("Marked, ")
    assert not rows[1].startswith("Marked")
    wp_dialogs.answer("ask_choice", 2).answer("confirm", True)
    rows = wp_dialogs.press("&Do with Marked...", None)
    asked = wp_dialogs.asked("confirm")[-1]
    assert asked["yes_label"] == "Trash 2"
    assert asked["message"] == "Trash: 2 marked comments on Community Radio?"
    trashed = [r for r in wp_site.requests if r.get_method() == "POST"]
    assert [wp_site.body(r) for r in trashed] == [{"status": "trash"}, {"status": "trash"}]
    assert len(rows) == 1 and "Bob" in rows[0]
    assert wpx.host.announced[-1] == "2 comments moved to the Trash on Community Radio."


def test_do_with_marked_needs_marks_and_respects_cancel(
    wpx: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    _comments(wpx, wp_site)
    assert wp_dialogs.press("&Do with Marked...", None) is None
    assert wpx.host.announced[-1] == "Mark the comments first, with Mark."
    wp_dialogs.press("Mark Ever&ything", None)
    assert wpx.host.announced[-1] == "3 comments marked."
    wp_dialogs.answer("ask_choice", 0)  # Approve, then the confirmation is cancelled
    assert wp_dialogs.press("&Do with Marked...", None) is None
    assert [r for r in wp_site.requests if r.get_method() == "POST"] == []
    rows = wp_dialogs.press("Mark Ever&ything", None)
    assert wpx.host.announced[-1] == "0 comments marked."
    assert not any(r.startswith("Marked") for r in rows)


def test_without_moderation_there_is_nothing_to_mark(
    wpx: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    _comments(wpx, wp_site, caps={"read": True})
    labels = [a.label for a in wp_dialogs.window["actions"]]
    assert "Mar&k" not in labels and "&Do with Marked..." not in labels
