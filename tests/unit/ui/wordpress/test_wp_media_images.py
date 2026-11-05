"""Image Size, Make a Smaller Copy and the Alt Text Review (wordpress.md 6.5, 6.8)."""

from __future__ import annotations

import io
from typing import Any

from quill.core.wordpress import local as lc
from quill.ui import wordpress_dialogs as dlg

API = "/wp-json/wp/v2"
UPLOADS = "https://radio.example/wp-content/uploads/2026/11"

SIZES = {
    "thumbnail": {"width": 150, "height": 100, "source_url": f"{UPLOADS}/fair-150x100.jpg"},
    "large": {"width": 1024, "height": 683, "source_url": f"{UPLOADS}/fair-1024x683.jpg"},
}


def media(item_id: int = 5, filename: str = "fair.jpg", width: int = 2400) -> dict:
    return {
        "id": item_id,
        "title": {"raw": "Fair"},
        "media_type": "image",
        "mime_type": "image/jpeg",
        "source_url": f"{UPLOADS}/{filename}",
        "alt_text": "Our stall",
        "caption": {"raw": ""},
        "media_details": {
            "width": width,
            "height": width * 2 // 3,
            "filesize": 9000,
            "sizes": SIZES,
        },
    }


def png(width: int = 2400, height: int = 1600) -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (width, height), (90, 20, 30)).save(out, format="PNG")
    return out.getvalue()


def open_document(wp, text: str, caret: int, *, fmt: str = "html"):
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id=lc.new_local_id(),
        remote_id=41,
        title="Our Schedule",
        text=text,
        text_format=fmt,
    )
    wp.host.open_path(wp.local.write_document(copy))
    wp.host.caret = caret


PICTURE = (
    f'<p>Fair day.</p>\n<img src="{UPLOADS}/fair-1024x683.jpg" alt="Our stall" '
    'class="wp-image-5" width="1024"/>\n'
)


# --------------------------------------------------------------------------- #
# Image Size


def test_image_size_needs_a_picture_at_the_caret(wp):
    open_document(wp, "<p>No pictures.</p>", 3)
    wp.cmd_image_size()
    assert "Put the caret on a picture in the document first" in wp.host.said


def test_image_size_then_back_to_earlier_size(wp, wp_site, wp_dialogs):
    open_document(wp, PICTURE, PICTURE.index("wp-image-5"))
    wp_site.on("GET", f"{API}/media/5", media())
    wp_dialogs.answer("ask_choice", 0)  # Thumbnail
    wp.cmd_image_size()
    asked = wp_dialogs.asked("ask_choice")[0]
    assert asked["rows"] == [
        "Thumbnail, 150 by 100",
        "Large, 1024 by 683, the size it is now",
        "Full size, 2400 by 1600",
    ]
    assert asked["initial"] == 1
    assert f'src="{UPLOADS}/fair-150x100.jpg"' in wp.host.text and 'width="150"' in wp.host.text
    assert wp.host.announced[-1] == "Picture shown at Thumbnail, 150 by 100."

    # Saved in the document's local history, so it survives this session.
    wp.host.caret = wp.host.text.index("wp-image-5")
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_image_size()
    assert wp_dialogs.asked("ask_choice")[1]["rows"][0] == (
        "Back to Earlier Size: Large, 1024 by 683"
    )
    assert f'src="{UPLOADS}/fair-1024x683.jpg"' in wp.host.text and 'width="1024"' in wp.host.text
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert copy.properties["image_size_history"] == {}


def test_image_size_same_size_and_cancel(wp, wp_site, wp_dialogs):
    open_document(wp, PICTURE, PICTURE.index("wp-image-5"))
    wp_site.on("GET", f"{API}/media/5", media())
    wp.cmd_image_size()  # cancelled
    assert wp.host.text == PICTURE
    wp_dialogs.answer("ask_choice", 1)
    wp.cmd_image_size()
    assert "already that size" in wp.host.said
    assert wp.host.text == PICTURE


def test_image_size_finds_the_item_by_address_or_says_it_is_not_there(wp, wp_site, wp_dialogs):
    text = f"![Our stall]({UPLOADS}/fair-1024x683.jpg)\n"
    open_document(wp, text, 3, fmt="markdown")
    wp_site.on(
        "GET", f"{API}/media", lambda _r, q: [media()] if q.get("search") == ["fair"] else []
    )
    wp_site.on("GET", f"{API}/media/5", media())
    wp_dialogs.answer("ask_choice", 2)
    wp.cmd_image_size()
    assert f"({UPLOADS}/fair.jpg)" in wp.host.text

    other = "![x](https://elsewhere.example/cat.jpg)\n"
    open_document(wp, other, 3, fmt="markdown")
    wp.cmd_image_size()
    assert "not in Community Radio's Media Library, so it has no other sizes" in wp.host.said


# --------------------------------------------------------------------------- #
# Make a Smaller Copy


def _upload_route(wp_site) -> list[Any]:
    def upload(request, _query):
        return {**media(9, "fair-1200w.jpg", 1200), "media_details": {"width": 1200, "height": 800}}

    wp_site.on("POST", f"{API}/media", upload)
    wp_site.on("POST", f"{API}/media/9", upload)
    return wp_site.sent("POST", f"{API}/media")


def test_smaller_copy_from_the_caret_uploads_and_uses_it_here(wp, wp_site, wp_dialogs):
    open_document(wp, PICTURE, PICTURE.index("wp-image-5"))
    wp_site.on("GET", f"{API}/media/5", media())
    wp_site.on("GET", "/wp-content/uploads/2026/11/fair.jpg", png())
    _upload_route(wp_site)
    wp_dialogs.answer("ask_choice", 1, 0)  # 1200 wide, JPEG
    wp_dialogs.answer("confirm", True)
    wp.cmd_smaller_copy()
    widths = wp_dialogs.asked("ask_choice")[0]["rows"]
    assert widths[0] == "1600 pixels wide"
    message = wp_dialogs.asked("confirm")[0]["message"]
    assert "Before: 2400 by 1600" in message and "After: 1200 by 800" in message
    assert "The original stays in the library." in message
    upload = wp_site.sent("POST", f"{API}/media")[0]
    assert 'filename="fair-1200w.jpg"' in upload.get_header("Content-disposition")
    assert upload.get_header("Content-type") == "image/jpeg"
    assert wp_site.body(wp_site.sent("POST", f"{API}/media/9")[0])["alt_text"] == "Our stall"
    assert f'src="{UPLOADS}/fair-1200w.jpg"' in wp.host.text
    assert wp.host.announced[-1].startswith(
        "Smaller copy uploaded to Community Radio and used here."
    )
    assert wp_site.sent("DELETE", f"{API}/media/5") == []


def test_smaller_copy_from_the_library_and_declining(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/media", [media()])
    wp_site.on("GET", "/wp-content/uploads/2026/11/fair.jpg", png())
    sent = _upload_route(wp_site)
    wp_dialogs.answer("ask_choice", 0, 3, 1)  # the picture, 800 wide, WebP
    wp.cmd_smaller_copy()  # the upload question is declined
    assert "After: 800 by 533" in wp_dialogs.asked("confirm")[0]["message"]
    assert sent == [] and wp_site.sent("POST", f"{API}/media") == []

    wp_dialogs.answer("ask_choice", 0, 3, 1)
    wp_dialogs.answer("confirm", True)
    wp.cmd_smaller_copy()
    assert wp.host.announced[-1] == (
        "Smaller copy uploaded to Community Radio as fair-1200w.jpg. The original is still in "
        "the library."
    )


def test_smaller_copy_has_nothing_to_do(wp, wp_site, wp_dialogs):
    wp_site.on("GET", f"{API}/media", [])
    wp.cmd_smaller_copy()
    assert "Community Radio's Media Library has no pictures." in wp.host.said
    wp_site.on("GET", f"{API}/media", [media(width=500)])
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_smaller_copy()
    assert "Fair is already 500 pixels wide or less." in wp.host.said
    open_document(wp, "![x](https://elsewhere.example/cat.jpg)\n", 3, fmt="markdown")
    wp_site.on("GET", f"{API}/media", [])
    wp.cmd_smaller_copy()
    assert (
        "This picture is not in Community Radio's Media Library. Upload it first." in wp.host.said
    )


# --------------------------------------------------------------------------- #
# Alt Text Review


REVIEW = (
    "<h2>Fair</h2>\n<p>We had a stall.</p>\n"
    f'<img src="{UPLOADS}/IMG_2041.jpg" alt="IMG_2041.jpg"/>\n'
    f'<img src="{UPLOADS}/door.jpg" alt=""/>\n'
    '<img src="https://radio.example/line.png" alt="" role="presentation"/>\n'
    f'<img src="{UPLOADS}/ok.jpg" alt="Two presenters"/>\n'
)


def test_alt_text_review_needs_pictures(wp):
    open_document(wp, "<p>Words only.</p>", 0)
    wp.cmd_alt_text_review()
    assert wp.host.announced[-1] == "This document has no pictures."


def test_alt_text_review_lists_marks_and_edits(wp, wp_dialogs):
    open_document(wp, REVIEW, 0)
    wp.cmd_alt_text_review()
    window = wp_dialogs.window
    assert window["rows"] == [
        "1. IMG_2041.jpg: looks like a file name: IMG_2041.jpg",
        "2. door.jpg: no alternative text",
        "3. line.png: decorative",
        "4. ok.jpg: Two presenters",
    ]
    assert "4 pictures, 2 to look at" in window["purpose"]
    assert "Problem: no alternative text" in window["details"](1)
    assert window["details"](2).endswith("Decorative")

    assert wp_dialogs.press("&Edit...", 1) is None  # cancelled
    wp_dialogs.answer("ask_text", "A red door")
    rows = wp_dialogs.press("&Edit...", 1)
    assert rows[1] == "2. door.jpg: A red door"
    assert 'alt="A red door"' in wp.host.text

    rows = wp_dialogs.press("Mark Decorati&ve", 0)
    assert rows[0] == "1. IMG_2041.jpg: decorative"
    assert '<img role="presentation" src=' in wp.host.text

    assert wp_dialogs.press("&Go to Picture", 3) is dlg.CLOSE
    assert wp.host.caret == wp.host.text.index(f'<img src="{UPLOADS}/ok.jpg"')


def test_alt_text_review_suggest_goes_through_an_edit(wp, wp_site, wp_dialogs):
    open_document(wp, REVIEW, 0)
    wp_site.on("GET", "/wp-content/uploads/2026/11/door.jpg", png(20, 20))
    asked: list[Any] = []

    def ai(path, question, done, err):
        asked.append(question)
        done("A red door with a brass knocker.")
        return True

    wp.host.ai_describe_image = ai
    wp.cmd_alt_text_review()
    wp_dialogs.press("&Suggest...", 1)  # the edit is cancelled: nothing set
    assert wp_dialogs.asked("ask_text")[-1]["value"] == "A red door with a brass knocker."
    assert 'alt=""' in wp.host.text.split("door.jpg")[1][:10]
    assert "The heading above it: Fair" in asked[0]
    assert "sends the picture and the text around it to your chosen AI" in wp.host.said

    wp_dialogs.answer("ask_text", "A red door")
    wp_dialogs.press("&Suggest...", 1)
    assert 'alt="A red door"' in wp.host.text
    assert wp.host.announced[-1] == "Alternative text set for picture 2."


def test_alt_text_review_suggest_for_a_picture_that_is_nowhere(wp, wp_dialogs):
    open_document(wp, '<img src="missing/where.png" alt=""/>', 0)
    wp.host.ai_describe_image = lambda *a: True
    wp.cmd_alt_text_review()
    wp_dialogs.press("&Suggest...", 0)
    assert "where.png is not on this computer, so the AI cannot look at it." in wp.host.said
