"""Edit a Picture on the Site and Alt Text for the Whole Library (wordpress.md 9.15)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress import local as lc
from quill.core.wordpress import media_edit as me
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_api_writing_commands import WordPressApiWritingCommands

API = "/wp-json/wp/v2"
UPLOADS = "https://radio.example/wp-content/uploads"
EDIT_ROUTE = "/wp/v2/media/(?P<id>[\\d]+)/edit"
CAPS = {"edit_posts": True, "upload_files": True}


@pytest.fixture
def wpx(wp: Any) -> Any:
    wp.__class__ = type("Wired", (type(wp), WordPressApiWritingCommands), {})
    return wp


def site(wp_site: Any, routes: dict[str, Any], caps: Any = None) -> None:
    wp_site.on("GET", "/wp-json/", {"namespaces": ["wp/v2"], "routes": routes})
    wp_site.on(
        "GET",
        f"{API}/users/me",
        {"id": 1, "name": "Jeff", "roles": ["author"], "capabilities": caps or CAPS},
    )


def picture(item_id: int, name: str, *, alt: str = "", width: int = 1600) -> dict[str, Any]:
    return {
        "id": item_id,
        "title": {"raw": name.title()},
        "media_type": "image",
        "mime_type": "image/jpeg",
        "source_url": f"{UPLOADS}/{name}.jpg",
        "alt_text": alt,
        "caption": {"raw": ""},
        "media_details": {"width": width, "height": 1200},
    }


def edit_routes(*types: str) -> dict[str, Any]:
    entry: dict[str, Any] = {}
    if types:
        enum = {"type": {"enum": list(types)}}
        entry = {"endpoints": [{"args": {"modifiers": {"items": {"properties": enum}}}}]}
    return {"/wp/v2/media": {}, EDIT_ROUTE: entry}


def open_doc(wp: Any, text: str) -> Any:
    copy = lc.WorkingCopy(
        site_id="radio", kind="page", local_id=lc.new_local_id(), remote_id=41, text=text
    )
    wp.host.open_path(wp.local.write_document(copy))
    return copy


# --------------------------------------------------------------------------- #
# Edit a Picture on the Site


def test_a_site_without_the_edit_route_says_so(wpx: Any, wp_site: Any) -> None:
    site(wp_site, {"/wp/v2/media": {}})
    wpx.cmd_edit_picture_on_site()
    assert "does not offer picture editing" in wpx.host.announced[-1]
    assert wp_site.sent("GET", f"{API}/media") == []


def test_an_account_that_cannot_upload_cannot_edit(wpx: Any, wp_site: Any) -> None:
    site(wp_site, edit_routes(), caps={"read": True})
    wpx.cmd_edit_picture_on_site()
    assert wpx.host.announced[-1] == (
        "Your account on Community Radio is an Author, which cannot edit pictures in the Media "
        "Library."
    )


def test_crop_the_picture_at_the_caret_and_use_it_here(
    wpx: Any, wp_site: Any, wp_dialogs: Any
) -> None:
    site(wp_site, edit_routes("rotate", "crop", "flip"))
    text = f"Intro.\n\n![Volunteers]({UPLOADS}/fair.jpg) {{id=5}}\n"
    open_doc(wpx, text)
    wpx.host.caret = text.index("![")
    wp_site.on("GET", f"{API}/media/5", picture(5, "fair"))
    new = {
        **picture(9, "fair-edited", width=1200),
        "media_details": {"width": 1200, "height": 1200},
    }
    wp_site.on("POST", f"{API}/media/5/edit", new)
    described: list[Any] = []
    wpx.host.ai_describe_image = lambda *a: None
    wpx._describe = lambda *a: described.append(a)
    labels = [e.label for e in me.EDITS]
    wp_dialogs.answer("ask_choice", labels.index("Crop to a square"))
    wp_dialogs.answer("confirm", True, True)
    wpx.cmd_edit_picture_on_site()
    asked = wp_dialogs.asked("ask_choice")[0]["rows"]
    assert "Flip top to bottom" in asked
    confirm = wp_dialogs.asked("confirm")[0]["message"]
    assert "about 1200 by 1200" in confirm
    body = wp_site.body(wp_site.sent("POST", f"{API}/media/5/edit")[0])
    assert body["src"] == f"{UPLOADS}/fair.jpg"
    assert body["modifiers"] == [
        {"type": "crop", "args": {"left": 12.5, "top": 0.0, "width": 75.0, "height": 100.0}}
    ]
    assert f"{UPLOADS}/fair-edited.jpg" in wpx.host.text
    assert "Edited copy made on Community Radio: Fair-Edited, 1200 by 1200." in wpx.host.said
    assert described and described[0][0].id == 9


def test_edit_a_library_picture_without_a_document(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    site(wp_site, edit_routes())  # no enum in the index: rotate and crop only
    wp_site.on("GET", f"{API}/media", [picture(5, "fair")])
    wp_site.on("POST", f"{API}/media/5/edit", picture(9, "fair-rotated"))
    wp_dialogs.answer("ask_choice", 0, 0).answer("confirm", True)
    wpx.cmd_edit_picture_on_site()
    rows = wp_dialogs.asked("ask_choice")[1]["rows"]
    assert not any(r.startswith("Flip") for r in rows)
    body = wp_site.body(wp_site.sent("POST", f"{API}/media/5/edit")[0])
    assert body["modifiers"] == [{"type": "rotate", "args": {"angle": 90}}]
    assert len(wp_dialogs.asked("confirm")) == 1  # nothing to use it in


def test_edit_cancelled_at_each_step_sends_nothing(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    site(wp_site, edit_routes())
    wp_site.on("GET", f"{API}/media", [picture(5, "fair")])
    wpx.cmd_edit_picture_on_site()  # the picture choice is cancelled
    wp_dialogs.answer("ask_choice", 0)
    wpx.cmd_edit_picture_on_site()  # the edit choice is cancelled
    wp_dialogs.answer("ask_choice", 0, 0)
    wpx.cmd_edit_picture_on_site()  # the confirmation is cancelled
    assert wp_site.sent("POST", f"{API}/media/5/edit") == []


def test_edit_a_picture_not_in_the_library(wpx: Any, wp_site: Any) -> None:
    site(wp_site, edit_routes())
    text = "![A cat](https://elsewhere.example/cat.jpg)\n"
    open_doc(wpx, text)
    wp_site.on("GET", f"{API}/media", [])
    wpx.cmd_edit_picture_on_site()
    assert "not in Community Radio's Media Library" in wpx.host.announced[-1]


def test_an_empty_library_has_nothing_to_edit(wpx: Any, wp_site: Any) -> None:
    site(wp_site, edit_routes())
    wp_site.on("GET", f"{API}/media", [])
    wpx.cmd_edit_picture_on_site()
    assert wpx.host.announced[-1] == "Community Radio's Media Library has no pictures."


# --------------------------------------------------------------------------- #
# Alt Text for the Whole Library


def _library(wp_site: Any, *, batch: bool = True) -> None:
    routes: dict[str, Any] = {"/wp/v2/media": {}}
    if batch:
        routes["/batch/v1"] = {}
    site(wp_site, routes)
    wp_site.on(
        "GET",
        f"{API}/media",
        [picture(5, "fair"), picture(6, "band", alt="The band"), picture(7, "stall")],
    )


def test_every_picture_has_alt_text(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    site(wp_site, {"/wp/v2/media": {}})
    wp_site.on("GET", f"{API}/media", [picture(6, "band", alt="The band")])
    wpx.cmd_library_alt_text()
    assert wpx.host.announced[-1] == (
        "Every picture in Community Radio's Media Library has alternative text."
    )
    assert wp_dialogs.list_windows == []


def test_library_lists_only_pictures_without_alt(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _library(wp_site)
    wpx.cmd_library_alt_text()
    asked = wp_site.sent("GET", f"{API}/media")[0].full_url
    assert "media_type=image" in asked
    window = wp_dialogs.window
    assert window["rows"] == ["Fair, no alternative text", "Stall, no alternative text"]
    assert "2 pictures" in window["purpose"]
    assert "File: fair.jpg" in window["details"](0)


def test_write_then_save_now_in_one_batch(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _library(wp_site)
    wp_site.on("POST", "/wp-json/batch/v1", {"responses": [{"status": 200}, {"status": 200}]})
    wpx.cmd_library_alt_text()
    wp_dialogs.answer("ask_text", "Volunteers at the fair", "A cake stall")
    rows = wp_dialogs.press("&Write...", 0)
    assert rows[0] == "Fair, written, not saved yet: Volunteers at the fair"
    wp_dialogs.enter(1)
    rows = wp_dialogs.press("Save &Now", None)
    sent = wp_site.body(wp_site.sent("POST", "/wp-json/batch/v1")[0])
    assert [r["path"] for r in sent["requests"]] == ["/wp/v2/media/5", "/wp/v2/media/7"]
    assert sent["requests"][1]["body"] == {"alt_text": "A cake stall"}
    assert wpx.host.announced[-1] == "2 descriptions saved on Community Radio."
    assert rows[0].startswith("Fair, saved")
    wp_dialogs.press("Save &Now", None)
    assert wpx.host.announced[-1] == "Nothing is waiting to be saved."


def test_closing_the_window_saves_what_is_left_one_by_one(
    wpx: Any, wp_site: Any, wp_dialogs: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _library(wp_site, batch=False)
    wp_site.on("POST", f"{API}/media/5", {"id": 5})  # 7 has no route: refused

    def window(_parent: Any, _show: Any, **kwargs: Any) -> Any:
        for action in kwargs["actions"]:
            if action.label == "&Write...":
                action.run(0)
                action.run(1)
        return type("W", (), {"Destroy": lambda self: None})()

    monkeypatch.setattr(dlg, "show_list_window", window)
    wp_dialogs.answer("ask_text", "Volunteers", "Cakes")
    wpx.cmd_library_alt_text()
    assert wp_site.body(wp_site.sent("POST", f"{API}/media/5")[0]) == {"alt_text": "Volunteers"}
    assert wpx.host.announced[-1] == (
        "1 description saved on Community Radio. 1 could not be saved; Community Radio "
        "refused them, so try those again."
    )


def test_a_full_batch_saves_by_itself(
    wpx: Any, wp_site: Any, wp_dialogs: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(me, "BATCH_SIZE", 1)
    _library(wp_site)
    wp_site.on("POST", "/wp-json/batch/v1", {"responses": [{"status": 200}]})
    wpx.cmd_library_alt_text()
    wp_dialogs.answer("ask_text", "Volunteers")
    wp_dialogs.press("&Write...", 0)
    assert len(wp_site.sent("POST", "/wp-json/batch/v1")) == 1
    assert wpx.host.announced[-1] == "1 description saved on Community Radio."


def test_write_cancelled_keeps_nothing(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _library(wp_site)
    wpx.cmd_library_alt_text()
    assert wp_dialogs.press("&Write...", 0) is None


def test_suggest_fills_the_field_to_read_first(wpx: Any, wp_site: Any, wp_dialogs: Any) -> None:
    _library(wp_site)
    offered: list[str] = []

    def suggest(source: Any, _api: Any, name: str, _context: Any, fill: Any) -> None:
        offered.append(name)
        fill("Volunteers at the spring fair")

    wpx._suggest_alt = suggest
    wpx.cmd_library_alt_text()
    wp_dialogs.answer("ask_text", lambda **kw: kw["value"] + ", smiling")
    assert wp_dialogs.press("&Suggest...", 0) is None
    assert offered == ["Fair"]
    assert wpx.host.announced[-1] == (
        "Alternative text written for Fair. It is saved with the next batch."
    )
    rows = wp_dialogs.press("&Write...", 1)  # cancelled; the rows still show the first
    assert rows is None
