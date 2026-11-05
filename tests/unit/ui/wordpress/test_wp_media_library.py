"""The Media Library window, Insert from Media Library and Insert Picture (6.1, 6.4)."""

from __future__ import annotations

import io
from typing import Any

from quill.core.wordpress import local as lc
from quill.ui import wordpress_item_dialogs as idlg
from quill.ui import wordpress_media_dialogs as mdlg
from quill.ui import wordpress_media_library as mlib

API = "/wp-json/wp/v2"
UPLOADS = "https://radio.example/wp-content/uploads/2026/11"


def media(item_id: int, filename: str, *, mime: str = "image/jpeg", **extra: Any) -> dict:
    return {
        "id": item_id,
        "title": {"raw": filename.rsplit(".", 1)[0].title()},
        "media_type": "image" if mime.startswith("image/") else "file",
        "mime_type": mime,
        "source_url": f"{UPLOADS}/{filename}",
        "alt_text": extra.pop("alt", ""),
        "caption": {"raw": ""},
        "description": {"raw": ""},
        "media_details": {"width": 2400, "height": 1600, "filesize": 4000},
        "date_gmt": "2026-11-01T10:00:00",
        "post": extra.pop("post", 0),
        **extra,
    }


def open_document(wp, text: str = "Intro.\n", *, remote_id: int = 41, fmt: str = "markdown"):
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id=lc.new_local_id(),
        remote_id=remote_id,
        title="Our Schedule",
        text=text,
        text_format=fmt,
    )
    wp.host.open_path(wp.local.write_document(copy))
    wp.host.caret = len(text)
    return copy


def answer(alt: str = "Volunteers at the fair", **extra: Any) -> idlg.ImageAnswer:
    fields = {"decorative": False, "caption": "", "width": 0, "featured": False, "link": ""}
    fields.update(extra)
    return idlg.ImageAnswer(alt=alt, **fields)


def png() -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (40, 20), (10, 20, 30)).save(out, format="PNG")
    return out.getvalue()


def library(wp_site, items: list[dict], pages: list[dict] | None = None) -> None:
    wp_site.on("GET", f"{API}/media", items)
    wp_site.on("GET", f"{API}/pages", pages or [])
    wp_site.on("GET", f"{API}/posts", [])


def fake_ai(wp, reply: str = "Two volunteers behind a stall."):
    asked: list[tuple[Any, str]] = []

    def ai(path, question, on_done, on_error) -> bool:
        asked.append((path, question))
        on_done(reply)
        return True

    wp.host.ai_describe_image = ai
    return asked


# --------------------------------------------------------------------------- #
# the window


def test_media_library_lists_and_finds_used_in_for_a_small_library(wp, wp_site, wp_dialogs):
    page = {
        "id": 41,
        "title": {"raw": "Our Schedule"},
        "content": {"raw": f'<img src="{UPLOADS}/fair.jpg">'},
    }
    library(wp_site, [media(5, "fair.jpg"), media(6, "logo.png", mime="image/png")], [page])
    wp.cmd_media_library()
    window = wp_dialogs.window
    assert window["title"] == "Media Library: Community Radio"
    assert len(window["rows"]) == 2
    assert "Used In is ready: 1 of 2 files on Community Radio" in wp.host.said
    assert "Used in: Our Schedule (page)" in window["details"](0)
    assert "Used in: nothing" in window["details"](1)
    labels = [a.label for a in window["actions"]]
    assert "A&ttach to This Page or Post" in labels and "Set as Featured Ima&ge" in labels


def test_a_large_library_waits_for_used_in_on_request(wp, wp_site, wp_dialogs, monkeypatch):
    monkeypatch.setattr(mlib, "USED_IN_SCAN_LIMIT", 1)
    library(wp_site, [media(5, "fair.jpg"), media(6, "logo.png")])
    wp.cmd_media_library()
    assert wp_site.sent("GET", f"{API}/pages") == []
    assert "not checked yet" in wp_dialogs.window["details"](0)
    wp_dialogs.press("&Used In", 0)
    assert "Nothing on Community Radio links to Fair." in wp.host.said
    searched = wp_site.sent("GET", f"{API}/pages")
    assert searched and "search=fair" in searched[0].full_url
    wp_dialogs.press("&Used In", 0)  # cached: no second search
    assert len(wp_site.sent("GET", f"{API}/pages")) == len(searched)


def test_used_in_lists_places_and_a_long_list_opens_a_report(wp, wp_site, wp_dialogs, monkeypatch):
    monkeypatch.setattr(mlib, "USED_IN_SCAN_LIMIT", 0)
    pages = [
        {
            "id": n,
            "title": {"raw": f"Page {n}"},
            "content": {"raw": f'<img src="{UPLOADS}/fair.jpg">'},
        }
        for n in range(1, 8)
    ]
    library(wp_site, [media(5, "fair.jpg")], pages[:2])
    wp.cmd_media_library()
    wp_dialogs.press("&Used In", 0)
    assert (
        "Fair is used in 2 places on Community Radio: Page 1 (page); Page 2 (page)." in wp.host.said
    )
    wp._wp_used_in["radio"].clear()
    wp_site.on("GET", f"{API}/pages", pages)
    wp_dialogs.press("&Used In", 0)
    assert wp_dialogs.reports[-1]["title"] == "Used In: Fair"
    assert "used in 7 places" in wp_dialogs.reports[-1]["text"]


def test_insert_from_the_window_needs_a_document(wp, wp_site, wp_dialogs):
    library(wp_site, [media(5, "fair.jpg")])
    wp.cmd_media_library()
    assert wp_dialogs.press("&Insert...", 0) is None
    assert "Open a WordPress document first to insert" in wp.host.said


def test_insert_from_the_window_closes_it_and_sets_featured(wp, wp_site, wp_dialogs):
    open_document(wp)
    library(wp_site, [media(5, "fair.jpg", alt="Old alt")])
    wp_dialogs.answer("ask_image", answer(featured=True))
    wp.cmd_media_library()
    from quill.ui import wordpress_dialogs as dlg

    assert wp_dialogs.press("&Insert...", 0) is dlg.CLOSE
    assert f"![Volunteers at the fair]({UPLOADS}/fair.jpg) {{id=5}}" in wp.host.text
    asked = wp_dialogs.asked("ask_image")[0]
    assert asked["alt"] == "Old alt" and asked["size_text"] == "image is 2400 by 1600"
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert copy.properties["featured_media"] == 5
    assert "Picture inserted: Volunteers at the fair." in wp.host.said


def test_cancelling_the_image_dialog_inserts_nothing(wp, wp_site, wp_dialogs):
    open_document(wp)
    library(wp_site, [media(5, "fair.jpg")])
    wp.cmd_media_library()
    assert wp_dialogs.press("&Insert...", 0) is None
    assert wp.host.text == "Intro.\n"


def test_attach_sets_the_parent_or_says_why_not(wp, wp_site, wp_dialogs):
    library(wp_site, [media(5, "fair.jpg")])
    wp.cmd_media_library()
    wp_dialogs.press("A&ttach to This Page or Post", 0)
    assert "Open a WordPress document first to attach" in wp.host.said

    open_document(wp, remote_id=0)
    wp.cmd_media_library()
    wp_dialogs.press("A&ttach to This Page or Post", 0)
    assert "not on Community Radio yet. Save Draft to Site first" in wp.host.said

    open_document(wp, remote_id=41)
    wp_site.on("POST", f"{API}/media/5", media(5, "fair.jpg", post=41))
    wp.cmd_media_library()
    wp_dialogs.press("A&ttach to This Page or Post", 0)
    sent = wp_site.sent("POST", f"{API}/media/5")
    assert wp_site.body(sent[-1]) == {"post": 41}
    assert "Fair attached to Our Schedule on Community Radio." in wp.host.said
    assert "Attached to: item 41" in wp_dialogs.window["details"](0)


def test_set_as_featured_image(wp, wp_site, wp_dialogs):
    library(wp_site, [media(5, "fair.jpg"), media(6, "report.pdf", mime="application/pdf")])
    wp.cmd_media_library()
    wp_dialogs.press("Set as Featured Ima&ge", 0)
    assert "Open a WordPress document first to give it a featured image." in wp.host.said
    open_document(wp)
    wp.cmd_media_library()
    wp_dialogs.press("Set as Featured Ima&ge", 1)
    assert "Only a picture can be a featured image." in wp.host.said
    wp_dialogs.press("Set as Featured Ima&ge", 0)
    assert wp.local.copy_for_path(wp.host.current_path()).properties["featured_media"] == 5
    assert "with your next Save Draft to Site or Publish" in wp.host.said
    assert wp_site.sent("POST", f"{API}/media/5") == []


def test_suggest_fills_the_edit_field_and_saves_only_on_ok(wp, wp_site, wp_dialogs):
    library(wp_site, [media(5, "fair.jpg")])
    wp_site.on("GET", "/wp-content/uploads/2026/11/fair.jpg", png())
    asked = fake_ai(wp, '"Image of two volunteers behind a stall."')
    wp.cmd_media_library()
    wp_dialogs.press("&Suggest Alternative Text...", 0)  # cancelled: nothing saved
    assert wp_dialogs.asked("ask_text")[-1]["value"] == "Two volunteers behind a stall."
    assert wp_site.sent("POST", f"{API}/media/5") == []
    assert "sends the picture to your chosen AI" in wp.host.said
    assert asked[0][0].read_bytes() == png()
    assert "Do not invent names" in asked[0][1]

    wp_site.on("POST", f"{API}/media/5", media(5, "fair.jpg", alt="Two volunteers"))
    wp_dialogs.answer("ask_text", "Two volunteers")
    wp_dialogs.press("&Suggest Alternative Text...", 0)
    assert wp_site.body(wp_site.sent("POST", f"{API}/media/5")[-1]) == {
        "alt_text": "Two volunteers"
    }
    assert "Alternative text saved on Community Radio." in wp.host.said


def test_suggest_and_describe_need_a_picture_and_the_ai(wp, wp_site, wp_dialogs):
    library(wp_site, [media(6, "report.pdf", mime="application/pdf"), media(5, "fair.jpg")])
    wp.cmd_media_library()
    wp_dialogs.press("&Suggest Alternative Text...", 0)
    assert "That file is not a picture." in wp.host.said
    wp_site.on("GET", "/wp-content/uploads/2026/11/fair.jpg", png())
    wp_dialogs.press("Describe I&mage...", 1)
    assert "AI help is not available in this window." in wp.host.said


def test_describe_opens_the_answer_in_a_report(wp, wp_site, wp_dialogs):
    library(wp_site, [media(5, "fair.jpg")])
    wp_site.on("GET", "/wp-content/uploads/2026/11/fair.jpg", png())
    asked = fake_ai(wp, "A stall under bunting, slightly cropped at the left.")
    wp.cmd_media_library()
    wp_dialogs.press("Describe I&mage...", 0)
    assert "Describe Image sends the picture to your chosen AI." in wp.host.said
    assert "problems" in asked[0][1]
    assert wp_dialogs.reports[-1]["title"] == "Describe Image: Fair"
    assert "bunting" in wp_dialogs.reports[-1]["text"]


def test_the_ai_saying_no_is_spoken(wp, wp_site, wp_dialogs):
    library(wp_site, [media(5, "fair.jpg")])
    wp_site.on("GET", "/wp-content/uploads/2026/11/fair.jpg", png())
    wp.host.ai_describe_image = lambda p, q, done, err: err("Your plan has run out.") or True
    wp.cmd_media_library()
    wp_dialogs.press("Describe I&mage...", 0)
    assert "The AI did not answer: Your plan has run out." in wp.host.said


def test_suggest_decorative_says_so(wp, wp_site, wp_dialogs):
    library(wp_site, [media(5, "fair.jpg")])
    wp_site.on("GET", "/wp-content/uploads/2026/11/fair.jpg", png())
    fake_ai(wp, "DECORATIVE")
    wp.cmd_media_library()
    wp_dialogs.press("&Suggest Alternative Text...", 0)
    assert "Your AI thinks Fair is decorative." in wp.host.said
    assert wp_dialogs.asked("ask_text") == []


def test_edit_copy_and_remove(wp, wp_site, wp_dialogs, monkeypatch, tmp_path):
    library(
        wp_site,
        [media(5, "fair.jpg")],
        [{"id": 41, "title": {"raw": "A"}, "content": {"raw": f"{UPLOADS}/fair.jpg"}}],
    )
    wp.cmd_media_library()
    wp_dialogs.press("&Edit Alternative Text...", 0)
    assert wp_site.sent("POST", f"{API}/media/5") == []
    wp_dialogs.press("Copy &Address", 0)
    assert wp.host.clipboard == f"{UPLOADS}/fair.jpg"
    wp_dialogs.press("&Remove from Library...", 0)
    message = wp_dialogs.asked("confirm")[-1]["message"]
    assert "1 page or post use it" in message and "Community Radio" in message
    assert wp_site.sent("DELETE", f"{API}/media/5") == []

    monkeypatch.setattr(mlib, "backup_media", lambda api, m, name: tmp_path / "fair.jpg")
    wp_site.on("DELETE", f"{API}/media/5", {"deleted": True})
    wp_dialogs.answer("confirm", True)
    wp_dialogs.press("&Remove from Library...", 0)
    assert "force=true" in wp_site.sent("DELETE", f"{API}/media/5")[0].full_url
    assert f"A copy is in {tmp_path}" in wp.host.said


def test_filter_narrows_the_rows(wp, wp_site, wp_dialogs):
    library(wp_site, [media(5, "fair.jpg"), media(6, "logo.png")])
    wp.cmd_media_library()
    rows = wp_dialogs.window["on_filter"]("logo")
    assert len(rows) == 1 and rows[0].startswith("Logo")


# --------------------------------------------------------------------------- #
# Insert from Media Library, Insert Picture


def test_insert_from_library_outside_a_document_says_so(wp):
    wp.cmd_insert_from_library()
    assert "This is not a WordPress document" in wp.host.said


def test_insert_from_library_picture_and_sound(wp, wp_site, wp_dialogs):
    open_document(wp, fmt="html", text="<p>Hi</p>")
    wp_site.on("GET", f"{API}/media", [])
    wp.cmd_insert_from_library()
    assert "Community Radio's Media Library is empty." in wp.host.said

    wp_site.on(
        "GET", f"{API}/media", [media(5, "fair.jpg"), media(8, "jingle.mp3", mime="audio/mpeg")]
    )
    wp_dialogs.answer("ask_choice", 0, 1, None)
    wp_dialogs.answer("ask_image", answer(caption="Photo: Sam"))
    wp.cmd_insert_from_library()
    assert (
        'class="wp-image-5"' in wp.host.text
        and "<figcaption>Photo: Sam</figcaption>" in wp.host.text
    )
    wp.cmd_insert_from_library()
    assert f'<audio controls src="{UPLOADS}/jingle.mp3">' in wp.host.text
    assert "Audio inserted: Jingle." in wp.host.said
    before = wp.host.text
    wp.cmd_insert_from_library()  # cancelled choice
    assert wp.host.text == before


def test_documents_insert_as_links() -> None:
    from quill.core.wordpress.site_media import media_from_payload

    doc = media_from_payload(media(6, "report.pdf", mime="application/pdf"))
    assert mlib.media_markup("markdown", doc) == f"[Report]({UPLOADS}/report.pdf)"
    assert mlib.media_markup("html", doc) == f'<a href="{UPLOADS}/report.pdf">Report</a>'


def test_insert_picture_from_this_computer(wp, wp_dialogs, monkeypatch, tmp_path):
    picture = tmp_path / "fair.png"
    picture.write_bytes(png())
    open_document(wp, text="## Fair\n\nWe had a stall.\n\n")
    monkeypatch.setattr(mdlg, "choose_picture", lambda *a, **k: None)
    wp.cmd_insert_picture()
    assert wp_dialogs.asked("ask_image") == []

    monkeypatch.setattr(mdlg, "choose_picture", lambda *a, **k: picture)
    asked = fake_ai(wp, "A red stall.")
    filled: list[str] = []

    def dialog(**kwargs):
        kwargs["on_suggest_async"](filled.append)
        kwargs["on_describe"]()
        return answer()

    wp_dialogs.answer("ask_image", dialog)
    wp.cmd_insert_picture()
    assert filled == ["A red stall."]
    assert "The heading above it: Fair" in asked[0][1]
    assert asked[0][0] == picture
    assert picture.as_uri() in wp.host.text
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert copy.pending_uploads[0]["alt"] == "Volunteers at the fair"
    assert "It is uploaded when you next send." in wp.host.said

    wp.cmd_insert_picture()  # cancelled image dialog
    assert len(wp.local.copy_for_path(wp.host.current_path()).pending_uploads) == 1


def test_a_chart_offers_a_fuller_description_after_it(wp, wp_site, wp_dialogs):
    open_document(wp, fmt="html", text="<p>Hi</p>")
    wp_site.on("GET", "/wp-content/uploads/2026/11/chart.png", png())
    fake_ai(wp, "Listeners by year.\nFULLER DESCRIPTION: 2024 had 400 & 2025 had 600.")
    library(wp_site, [media(5, "chart.png", mime="image/png")])
    filled: list[str] = []

    def dialog(**kwargs):
        kwargs["on_suggest_async"](filled.append)
        return answer(filled[0])

    wp_dialogs.answer("ask_image", dialog, dialog)
    wp_dialogs.answer("ask_choice", 0, 0)
    wp_dialogs.answer("confirm", True)
    wp.cmd_insert_from_library()
    assert filled == ["Listeners by year."]
    assert wp.host.text.endswith("</figure>\n<p>2024 had 400 &amp; 2025 had 600.</p>\n")
    before = wp.host.text
    wp.cmd_insert_from_library()  # declined this time
    assert "2025 had 600" not in wp.host.text[len(before) :]
