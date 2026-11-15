"""A static copy of a site for an archive: HTML files, local media, own host only (15.11)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.static_archive import archive_site, same_host

HOME = "https://radio.example"
PIC = f"{HOME}/wp-content/uploads/2024/05/logo.png"
PDF = f"{HOME}/wp-content/uploads/schedule.pdf"
AWAY = "https://cdn.elsewhere.example/banner.jpg"

PAGES = [
    {
        "id": 2,
        "type": "page",
        "slug": "about",
        "title": {"rendered": "About &amp; Us"},
        "link": f"{HOME}/about/",
        "content": {
            "rendered": (
                f'<p><img src="{PIC}" srcset="{PIC} 2x" alt="Logo"></p>'
                f'<p><a href="{PDF}">Schedule</a> <a href="{HOME}/2024/05/hello/">Hello</a></p>'
                f'<p><img src="{AWAY}" alt="Banner"></p>'
            )
        },
    }
]
POSTS = [
    {
        "id": 1,
        "type": "post",
        "slug": "hello",
        "date": "2024-05-01T10:00:00",
        "title": {"rendered": "Hello"},
        "link": f"{HOME}/2024/05/hello/",
        "content": {"rendered": f'<p><img src="{PIC}" alt="Logo again"></p>'},
    }
]


class Api:
    def __init__(self, refuse: str = "") -> None:
        self.refuse = refuse
        self.asked: list[tuple[str, dict[str, Any]]] = []

    def iter_collection(self, route: str, params: Any = None, **_k: Any) -> Iterator[Any]:
        self.asked.append((route, dict(params or {})))
        if route == self.refuse:
            raise WordPressApiError("Sorry, you are not allowed.", status=403)
        yield from PAGES if route == "wp/v2/pages" else POSTS


def test_pages_posts_and_own_host_media_are_written_and_linked(tmp_path: Path) -> None:
    fetched: list[str] = []

    def fetch(url: str) -> bytes:
        fetched.append(url)
        return b"bytes of " + url.encode()

    api = Api()
    report = archive_site(api, tmp_path, site_url=HOME, site_name="Radio", fetch=fetch)
    assert (report.pages, report.posts, report.files) == (1, 1, 2)
    assert fetched == [PIC, PDF]  # each once, never the other host
    assert all(params["status"] == "publish" for _r, params in api.asked)
    about = (tmp_path / "pages" / "about.html").read_text(encoding="utf-8")
    assert '<html lang="en">' in about and "<title>About &amp; Us</title>" in about
    assert "<h1>About &amp; Us</h1>" in about
    assert 'src="../media/2024/05/logo.png"' in about and "srcset" not in about
    assert 'href="../media/schedule.pdf"' in about
    assert 'href="../posts/2024-05-01-hello.html"' in about
    assert f'src="{AWAY}"' in about
    assert (
        tmp_path / "media" / "2024" / "05" / "logo.png"
    ).read_bytes() == b"bytes of " + PIC.encode()
    post = (tmp_path / "posts" / "2024-05-01-hello.html").read_text(encoding="utf-8")
    assert "Published 2024-05-01." in post and 'href="../index.html"' in post
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert '<a href="pages/about.html">About &amp; Us</a>' in index
    assert '<a href="posts/2024-05-01-hello.html">Hello</a>' in index
    assert report.left_out == [f"Not fetched, on another host: {AWAY}"]
    assert "Archived 1 pages, 1 posts and 2 files" in report.sentence(str(tmp_path))


def test_a_refused_list_and_a_failed_file_are_named_not_hidden(tmp_path: Path) -> None:
    def fetch(url: str) -> bytes:
        raise OSError("timed out")

    report = archive_site(
        Api(refuse="wp/v2/posts"), tmp_path, site_url=HOME, site_name="Radio", fetch=fetch
    )
    assert report.posts == 0 and report.files == 0
    assert "wp/v2/posts: not read, Sorry, you are not allowed." in report.left_out
    assert f"Not fetched, timed out: {PIC}" in report.left_out
    assert "None were published." in (tmp_path / "index.html").read_text(encoding="utf-8")


def test_without_a_fetcher_the_text_is_archived_and_every_file_named(tmp_path: Path) -> None:
    report = archive_site(Api(), tmp_path, site_url=HOME, site_name="Radio", fetch=None)
    assert report.files == 0 and not (tmp_path / "media").exists()
    assert f"Not fetched, files were not asked for: {PIC}" in report.left_out


def test_same_host_compares_host_names_only() -> None:
    assert same_host("https://RADIO.example/x.png", HOME)
    assert not same_host(AWAY, HOME) and not same_host("", HOME)
