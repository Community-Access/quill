"""Uploads by address, sizes, smaller copies and Used In, with no network (wordpress.md 6)."""

from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any

import pytest

from quill.core.wordpress import media_tools as mt
from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi
from quill.core.wordpress.site_media import media_from_payload

SITE = "https://radio.example"
UPLOADS = f"{SITE}/wp-content/uploads/2026/11"


class Response:
    def __init__(self, body: Any, headers: dict[str, str] | None = None, url: str = "") -> None:
        self._raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.headers = headers or {}
        self.status = 200
        if url:
            self.url = url

    def read(self, size: int = -1) -> bytes:
        return self._raw if size < 0 else self._raw[:size]

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


def opener_for(answers: dict[str, Any]):
    seen: list[str] = []

    def opener(request: Any, timeout: Any = None, context: Any = None) -> Any:
        seen.append(request.full_url)
        for prefix, answer in answers.items():
            if request.full_url.startswith(prefix):
                return answer(request) if callable(answer) else answer
        raise OSError("no route")

    opener.seen = seen  # type: ignore[attr-defined]
    return opener


def api_with(opener: Any) -> WordPressApi:
    return WordPressApi(
        SiteAddress(SITE), SiteAuth("app_password", "jeff", "secret"), opener=opener
    )


def png(width: int = 400, height: int = 200) -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(out, format="PNG")
    return out.getvalue()


def media(item_id: int, filename: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": item_id,
        "title": {"raw": filename.rsplit(".", 1)[0]},
        "media_type": "image",
        "mime_type": "image/jpeg",
        "source_url": f"{UPLOADS}/{filename}",
        "alt_text": "",
        "media_details": {"width": 2400, "height": 1600, "filesize": 4000},
        **extra,
    }


# --------------------------------------------------------------------------- #
# names


def test_names_are_plain_and_safe() -> None:
    assert mt.safe_filename("Spring Fair (2).JPG") == "spring-fair-2.jpg"
    assert mt.pasted_picture_name("Volunteers at the spring fair", datetime(2026, 11, 4)) == (
        "volunteers-at-the-spring-fair.png"
    )
    assert mt.pasted_picture_name("", datetime(2026, 11, 4, 10, 30, 5)) == (
        "pasted-picture-2026-11-04-103005.png"
    )
    assert mt.smaller_copy_name("fair.jpg", 1200, "webp") == "fair-1200w.webp"


def test_picture_extension_reads_the_first_bytes() -> None:
    assert mt.picture_extension(png()) == "png"
    assert mt.picture_extension(b"\xff\xd8\xff\xe0") == "jpg"
    assert mt.picture_extension(b"GIF89a...") == "gif"
    assert mt.picture_extension(b"RIFF\x00\x00\x00\x00WEBPVP8") == "webp"
    assert mt.picture_extension(b"hello") == ""


# --------------------------------------------------------------------------- #
# Upload from Web Address


def test_only_https_is_fetched() -> None:
    with pytest.raises(mt.MediaDownloadError, match="HTTPS"):
        mt.check_download_address("http://pictures.example/fair.jpg")
    with pytest.raises(mt.MediaDownloadError, match="complete web address"):
        mt.check_download_address("https://")
    assert mt.check_download_address(" https://pictures.example/fair.jpg ") == "pictures.example"


def test_a_picture_is_fetched_with_its_name_and_type() -> None:
    opener = opener_for({
        "https://pictures.example/": Response(png(), {"Content-Type": "image/png; charset=x"})
    })
    got = mt.download_file(opener, "https://pictures.example/photos/Spring%20Fair.png")
    assert got.filename == "spring-fair.png"
    assert got.content_type == "image/png"
    assert got.host == "pictures.example"
    assert got.content.startswith(b"\x89PNG")


def test_a_name_comes_from_content_disposition_and_type_from_the_name() -> None:
    opener = opener_for({
        "https://files.example/": Response(
            b"%PDF-1.7",
            {
                "Content-Type": "application/octet-stream",
                "Content-Disposition": 'attachment; filename="Annual Report.pdf"',
            },
        )
    })
    got = mt.download_file(opener, "https://files.example/download?id=4")
    assert got.filename == "annual-report.pdf"
    assert got.content_type == "application/pdf"


def test_a_web_page_is_refused() -> None:
    opener = opener_for({
        "https://news.example/": Response(b"<html>", {"Content-Type": "text/html"})
    })
    with pytest.raises(mt.MediaDownloadError, match="does not take"):
        mt.download_file(opener, "https://news.example/story")


def test_too_large_is_refused_by_header_and_by_body() -> None:
    big = opener_for({"https://a.example/": Response(b"x", {"Content-Length": "999999999"})})
    with pytest.raises(mt.MediaDownloadError, match="more than"):
        mt.download_file(big, "https://a.example/huge.mp4")
    body = opener_for({"https://a.example/": Response(b"x" * 50, {"Content-Type": "image/png"})})
    with pytest.raises(mt.MediaDownloadError, match="more than"):
        mt.download_file(body, "https://a.example/p.png", max_bytes=10)


def test_a_redirect_to_http_is_refused() -> None:
    opener = opener_for({
        "https://a.example/": Response(
            png(), {"Content-Type": "image/png"}, url="http://a.example/p.png"
        )
    })
    with pytest.raises(mt.MediaDownloadError, match="not HTTPS"):
        mt.download_file(opener, "https://a.example/p.png")


def test_a_network_failure_is_one_sentence() -> None:
    with pytest.raises(
        mt.MediaDownloadError, match="could not fetch the file from nowhere.example"
    ):
        mt.download_file(opener_for({}), "https://nowhere.example/p.png")


# --------------------------------------------------------------------------- #
# sizes and finding an item by address


def test_image_sizes_narrowest_first_full_last() -> None:
    raw = media(
        5,
        "fair-scaled.jpg",
        media_details={
            "width": 2560,
            "height": 1707,
            "sizes": {
                "large": {
                    "width": 1024,
                    "height": 683,
                    "source_url": f"{UPLOADS}/fair-1024x683.jpg",
                },
                "thumbnail": {
                    "width": 150,
                    "height": 150,
                    "source_url": f"{UPLOADS}/fair-150x150.jpg",
                },
                "broken": {"width": 1},
            },
        },
    )
    sizes = mt.image_sizes(raw)
    assert [s.name for s in sizes] == ["thumbnail", "large", "full"]
    assert sizes[-1].spoken() == "Full size, 2560 by 1707"
    assert sizes[0].spoken() == "Thumbnail, 150 by 150"
    assert mt.ImageSize("hero-wide", 1, 1, "x").spoken() == "Hero Wide, 1 by 1"


def test_find_media_by_address_matches_sized_variants() -> None:
    seen: list[str] = []

    def answer(request: Any) -> Response:
        seen.append(request.full_url)
        return Response([media(5, "fair-scaled.jpg"), media(6, "other.jpg")])

    api = api_with(opener_for({f"{SITE}/wp-json/wp/v2/media": answer}))
    found = mt.find_media_by_address(api, f"{UPLOADS}/fair-1024x683.jpg")
    assert found is not None and found.id == 5
    assert "search=fair" in seen[0]
    assert mt.find_media_by_address(api, "https://radio.example/") is None


# --------------------------------------------------------------------------- #
# Make a Smaller Copy


def test_smaller_copy_keeps_proportions_and_reports() -> None:
    small = mt.make_smaller_copy(png(2000, 1000), 800, "JPEG")
    assert (small.width, small.height) == (800, 400)
    assert small.mime == "image/jpeg" and small.extension == "jpg"
    assert small.data.startswith(b"\xff\xd8")
    assert small.report().startswith("Before: 2000 by 1000,")
    assert "After: 800 by 400" in small.report()


def test_a_narrow_picture_is_reencoded_not_enlarged() -> None:
    small = mt.make_smaller_copy(png(300, 100), 800, "webp")
    assert (small.width, small.height) == (300, 100)
    assert small.extension == "webp"


def test_smaller_copy_refusals() -> None:
    with pytest.raises(mt.MediaImageError, match="not a picture"):
        mt.make_smaller_copy(b"not a picture", 800, "PNG")
    with pytest.raises(mt.MediaImageError, match="Choose JPEG"):
        mt.make_smaller_copy(png(), 800, "TIFF")


# --------------------------------------------------------------------------- #
# Used In


def _site_with_pages() -> Any:
    pages = [
        {
            "id": 41,
            "title": {"raw": "Our Schedule"},
            "content": {"raw": f'<img src="{UPLOADS}/fair-1024x683.jpg">'},
        },
        {"id": 42, "title": {"raw": "About"}, "content": {"raw": "<p>No pictures</p>"}},
    ]
    posts = [
        {
            "id": 7,
            "title": {"raw": "Fair report"},
            "content": {"raw": '<!-- wp:image {"id":5,"sizeSlug":"large"} --><figure></figure>'},
        }
    ]
    return opener_for({
        f"{SITE}/wp-json/wp/v2/pages": Response(pages),
        f"{SITE}/wp-json/wp/v2/posts": Response(posts),
    })


def test_used_in_all_finds_addresses_and_block_ids() -> None:
    api = api_with(_site_with_pages())
    items = [media_from_payload(media(5, "fair-scaled.jpg")), media_from_payload(media(9, "x.jpg"))]
    found = mt.used_in_all(api, items)
    assert [p.spoken() for p in found[5]] == ["Our Schedule (page)", "Fair report (post)"]
    assert found[9] == []


def test_used_in_one_searches_by_name() -> None:
    opener = _site_with_pages()
    api = api_with(opener)
    found = mt.used_in_one(api, media_from_payload(media(5, "fair-scaled.jpg")))
    assert len(found) == 2
    assert all("search=fair" in url for url in opener.seen)  # type: ignore[attr-defined]


def test_mentions_ignores_a_different_block() -> None:
    item = media_from_payload(media(5, "fair.jpg"))
    assert not mt.mentions('<!-- wp:image {"id":55} -->', item)
    assert mt.mentions('<img class="wp-image-5" src="x">', item)
    assert not mt.mentions(f'<img src="{UPLOADS}/fairground.jpg">', item)
