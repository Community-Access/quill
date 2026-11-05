"""Upload Files, Paste Image and Upload from Web Address (wordpress.md 6.2, 6.4)."""

from __future__ import annotations

import io
from typing import Any

from quill.core.wordpress import local as lc
from quill.ui import wordpress_item_dialogs as idlg
from quill.ui import wordpress_media_dialogs as mdlg
from quill.ui import wordpress_media_upload as mup

API = "/wp-json/wp/v2"
UPLOADS = "https://radio.example/wp-content/uploads/2026/11"


def media(item_id: int, filename: str, size: int = 4000) -> dict:
    return {
        "id": item_id,
        "title": {"raw": filename},
        "media_type": "image",
        "mime_type": "image/png",
        "source_url": f"{UPLOADS}/{filename}",
        "alt_text": "",
        "media_details": {"width": 40, "height": 20, "filesize": size},
    }


def png() -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (40, 20), (10, 20, 30)).save(out, format="PNG")
    return out.getvalue()


def open_document(wp, text: str = "Intro.\n"):
    copy = lc.WorkingCopy(
        site_id="radio",
        kind="page",
        local_id=lc.new_local_id(),
        remote_id=41,
        title="Our Schedule",
        text=text,
    )
    wp.host.open_path(wp.local.write_document(copy))
    wp.host.caret = len(text)


def uploads(wp_site, library: list[dict] | None = None, fail: set[str] | None = None) -> list[str]:
    """A site that takes uploads (ids from 100) and answers duplicate searches."""
    names: list[str] = []

    def upload(request, _query):
        name = request.get_header("Content-disposition").split('filename="')[1].rstrip('"')
        if fail and name in fail:
            from urllib.error import HTTPError

            raise HTTPError(
                request.full_url,
                413,
                "big",
                {},
                io.BytesIO(b'{"code":"rest_upload_file_too_big","message":"Too big"}'),
            )
        names.append(name)
        return media(100 + len(names), name)

    wp_site.on("POST", f"{API}/media", upload)
    wp_site.on("GET", f"{API}/media", lambda _r, q: library or [] if "search" in q else [])
    for n in range(101, 110):
        wp_site.on("POST", f"{API}/media/{n}", media(n, f"file-{n}.png"))
    return names


def file_answer(wp_site, body: bytes, content_type: str) -> Any:
    """The harness's own FakeResponse, which FakeSite hands back as it is."""
    response = type(wp_site).__call__.__globals__["FakeResponse"]
    return response(body, headers={"Content-Type": content_type})


def details(alt: str = "", title: str = "A title") -> mdlg.UploadDetails:
    return mdlg.UploadDetails(title=title, alt=alt, caption="", decorative=False)


def test_upload_files_progress_duplicates_and_failures(
    wp, wp_site, wp_dialogs, monkeypatch, tmp_path
):
    files = []
    for name in ("a.png", "b.png", "c.png", "notes.txt"):
        path = tmp_path / name
        path.write_bytes(png() if name.endswith(".png") else b"hello")
        files.append(path)
    missing = tmp_path / "gone.png"
    monkeypatch.setattr(mdlg, "choose_files", lambda *a, **k: [*files, missing])
    answers = iter([details("First"), details("Second"), details("Third"), None])
    shown: list[dict[str, Any]] = []

    def ask(_parent, _show, **kwargs):
        shown.append(kwargs)
        return next(answers)

    monkeypatch.setattr(mdlg, "ask_upload_details", ask)
    twin = media(7, "b.png", size=len(png()))
    names = uploads(wp_site, [twin], fail={"c.png"})
    wp_dialogs.answer("confirm", True)  # use the one already there for b.png
    wp.cmd_upload_files()
    assert names == ["a.png"]
    assert shown[0]["is_image"] and not shown[3]["is_image"]
    assert shown[0]["on_suggest_async"] is not None and shown[3]["on_suggest_async"] is None
    assert (
        "b.png is already in Community Radio's Media Library"
        in wp_dialogs.asked("confirm")[0]["message"]
    )
    said = wp.host.said
    assert "gone.png could not be read" in said
    assert "Uploading 1 of 3: a.png." in said and "Uploading 3 of 3: c.png." in said
    assert "Uploading 2 of 3" not in said  # b.png was reused, not uploaded
    last = wp.host.announced[-1]
    assert last.startswith("1 of 3 files uploaded to Community Radio.")
    assert "1 was already there" in last and "c.png did not upload" in last and "2 skipped." in last
    alt_sent = [wp_site.body(r) for r in wp_site.sent("POST", f"{API}/media/101")]
    assert alt_sent == [{"title": "A title", "alt_text": "First"}]


def test_upload_files_cancelled_sends_nothing(wp, wp_site, monkeypatch):
    monkeypatch.setattr(mdlg, "choose_files", lambda *a, **k: [])
    wp.cmd_upload_files()
    assert wp_site.requests == []


def test_every_file_skipped_says_nothing_was_uploaded(wp, wp_site, monkeypatch, tmp_path):
    path = tmp_path / "a.png"
    path.write_bytes(png())
    monkeypatch.setattr(mdlg, "choose_files", lambda *a, **k: [path])
    monkeypatch.setattr(mdlg, "ask_upload_details", lambda *a, **k: None)
    wp.cmd_upload_files()
    assert wp.host.announced[-1] == "Nothing was uploaded to Community Radio."
    assert wp_site.requests == []


def test_upload_details_suggest_reaches_the_ai(wp, wp_site, monkeypatch, tmp_path):
    path = tmp_path / "stall.png"
    path.write_bytes(png())
    monkeypatch.setattr(mdlg, "choose_files", lambda *a, **k: [path])
    asked: list[Any] = []
    wp.host.ai_describe_image = lambda p, q, done, err: asked.append(p) or done("A stall") or True
    filled: list[str] = []

    def ask(_parent, _show, **kwargs):
        kwargs["on_suggest_async"](filled.append)
        return None

    monkeypatch.setattr(mdlg, "ask_upload_details", ask)
    wp.cmd_upload_files()
    assert filled == ["A stall"]
    assert asked[0].read_bytes() == png()


def test_upload_summary_words() -> None:
    def result(name: str, ok: bool = True, reused: bool = False) -> mup.UploadResult:
        entry = mup.UploadEntry(name, b"", "image/png")
        from quill.core.wordpress.site_media import media_from_payload

        item = media_from_payload(media(1, name)) if ok else None
        if reused:
            entry.reuse = item
        return mup.UploadResult(entry, item, "" if ok else "Too big.")

    assert mup.upload_summary("R", [result("a.png")]) == "a.png uploaded to R."
    assert mup.upload_summary("R", [result("a.png", reused=True)]) == (
        "1 was already there and is used as they are."
    )
    assert mup.upload_summary("R", [result("a.png", ok=False)]) == (
        "Nothing was uploaded to R. a.png did not upload: Too big."
    )
    assert mup.default_title("spring_fair-2026.jpg") == "Spring fair 2026"
    assert mup.bytes_size_text(png()).startswith("image is 40 by 20")
    assert mup.bytes_size_text(b"hello") == "5 bytes"


# --------------------------------------------------------------------------- #
# Paste Image


def test_paste_image_needs_a_document_and_a_picture(wp, wp_site):
    wp.cmd_paste_image()
    assert "This is not a WordPress document" in wp.host.said
    open_document(wp)
    wp.cmd_paste_image()  # FakeHost has no clipboard picture at all
    assert "There is no picture on the clipboard." in wp.host.said
    wp.host.clipboard_image_png = lambda: None
    wp.cmd_paste_image()
    assert wp.host.announced.count(wp.host.announced[-1]) == 2
    assert wp_site.requests == []


def test_paste_image_uploads_named_from_alt_and_inserts(wp, wp_site, wp_dialogs):
    open_document(wp)
    wp.host.clipboard_image_png = png
    names = uploads(wp_site)
    wp_dialogs.answer(
        "ask_image",
        idlg.ImageAnswer(
            alt="Volunteers at the fair",
            decorative=False,
            caption="",
            width=0,
            featured=True,
            link="",
        ),
    )
    wp.cmd_paste_image()
    assert names == ["volunteers-at-the-fair.png"]
    assert wp_dialogs.asked("ask_image")[0]["size_text"].startswith("image is 40 by 20")
    assert f"![Volunteers at the fair]({UPLOADS}/file-101.png) {{id=101}}" in wp.host.text
    assert wp.local.copy_for_path(wp.host.current_path()).properties["featured_media"] == 101
    assert wp.host.announced[-1] == "Picture inserted: Volunteers at the fair."


def test_paste_image_cancel_and_failure(wp, wp_site, wp_dialogs):
    open_document(wp)
    wp.host.clipboard_image_png = png
    wp.cmd_paste_image()
    assert wp_site.requests == []
    wp_site.on("POST", f"{API}/media", RuntimeError("the site went away"))
    wp_dialogs.answer(
        "ask_image",
        idlg.ImageAnswer(alt="", decorative=True, caption="", width=0, featured=False, link=""),
    )
    wp.cmd_paste_image()
    assert wp.host.announced[-1].startswith("The picture was not uploaded.")
    assert wp.host.text == "Intro.\n"


# --------------------------------------------------------------------------- #
# Upload from Web Address


def test_upload_from_address_refuses_http(wp, wp_site, wp_dialogs):
    wp_dialogs.answer("ask_text", "http://pictures.example/fair.png")
    wp.cmd_upload_from_address()
    assert "only fetches files over HTTPS" in wp.host.said
    assert wp_site.requests == []
    wp.cmd_upload_from_address()  # cancelled
    assert wp_site.requests == []


def test_upload_from_address_fetches_then_uploads(wp, wp_site, wp_dialogs, monkeypatch):
    wp_site.on("GET", "/photos/fair.png", file_answer(wp_site, png(), "image/png"))
    names = uploads(wp_site)
    monkeypatch.setattr(mdlg, "ask_upload_details", lambda *a, **k: details("A stall"))
    wp_dialogs.answer("ask_text", "https://pictures.example/photos/fair.png")
    wp.cmd_upload_from_address()
    assert "Fetching the file from pictures.example." in wp.host.said
    assert names == ["fair.png"]
    assert wp.host.announced[-1] == "fair.png uploaded to Community Radio."


def test_upload_from_address_wrong_type_and_cancelled_details(wp, wp_site, wp_dialogs, monkeypatch):
    wp_site.on("GET", "/story", file_answer(wp_site, b"<html>", "text/html"))
    wp_dialogs.answer("ask_text", "https://news.example/story")
    wp.cmd_upload_from_address()
    assert "does not take" in wp.host.said
    wp_site.on("GET", "/fair.png", file_answer(wp_site, png(), "image/png"))
    monkeypatch.setattr(mdlg, "ask_upload_details", lambda *a, **k: None)
    wp_dialogs.answer("ask_text", "https://pictures.example/fair.png")
    wp.cmd_upload_from_address()
    assert wp.host.announced[-1] == "Nothing was uploaded to Community Radio."
    assert wp_site.sent("POST", f"{API}/media") == []
