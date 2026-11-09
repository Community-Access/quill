"""QUILL Cast's one picture fetch and the pictures it can offer (codex.md 10B.5)."""

from __future__ import annotations

import pytest

from quill.core.podcasts import picture_fetch
from quill.core.podcasts.picture_fetch import (
    PictureFetchError,
    fetch_picture,
    pictures_for,
    show_note_pictures,
)


def test_show_note_pictures_keep_their_alt_text_once_each() -> None:
    html = (
        '<img src="https://a.invalid/1.png" alt=" A  chart ">'
        '<img src="https://a.invalid/1.png"><img src="data:image/png;base64,xx">'
        '<IMG SRC="http://a.invalid/2.jpg">'
    )
    assert show_note_pictures(html) == [
        ("https://a.invalid/1.png", "A chart"),
        ("http://a.invalid/2.jpg", ""),
    ]


def test_pictures_for_offers_artwork_then_the_notes() -> None:
    pictures = pictures_for(
        episode_title="Tides",
        episode_art="",
        show_title="Sea",
        show_art="https://a.invalid/art.jpg",
        notes_html='<img src="https://a.invalid/n.png" alt="A map">',
    )
    assert [(p.label, p.url, p.alt) for p in pictures] == [
        ("Podcast artwork for Sea", "https://a.invalid/art.jpg", ""),
        ("Show-note picture 1: A map", "https://a.invalid/n.png", "A map"),
    ]


def test_safe_mode_and_other_schemes_are_refused_before_any_fetch(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(picture_fetch, "_fetch_picture_bytes", lambda url: calls.append(url))
    with pytest.raises(PictureFetchError, match="Safe Mode"):
        fetch_picture("https://a.invalid/x.png", safe_mode=True)
    with pytest.raises(PictureFetchError, match="https://"):
        fetch_picture("file:///c:/x.png")
    assert calls == []


def test_a_picture_over_the_cap_is_refused(monkeypatch) -> None:
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def read(self, limit: int) -> bytes:
            return b"x" * limit

    class _Opener:
        def open(self, *_a, **_k):
            return _Resp()

    monkeypatch.setattr(picture_fetch, "refuse_local_host", lambda _url: None)
    monkeypatch.setattr(picture_fetch.urllib.request, "build_opener", lambda *_a: _Opener())
    with pytest.raises(PictureFetchError, match="20 megabytes"):
        fetch_picture("https://a.invalid/big.png")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin.png",
        "http://192.168.1.1/logo.png",
        "http://10.0.0.5/x.png",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/x.png",
        "http://[::ffff:192.168.0.1]/x.png",
        "https://localhost/x.png",
        "https://printer.local/x.png",
        "https://router.example/x.png",
    ],
)
def test_a_picture_on_the_local_network_is_never_fetched(monkeypatch, url: str) -> None:
    calls: list[str] = []
    monkeypatch.setattr(picture_fetch, "_fetch_picture_bytes", lambda u: calls.append(u))
    monkeypatch.setattr(
        picture_fetch.socket,
        "getaddrinfo",
        lambda host, *_a: [(2, 1, 6, "", ("192.168.1.20", 0))],
    )
    with pytest.raises(PictureFetchError, match="local network"):
        fetch_picture(url)
    assert calls == []


def test_a_public_picture_is_fetched_and_a_redirect_home_is_refused(monkeypatch) -> None:
    monkeypatch.setattr(
        picture_fetch.socket,
        "getaddrinfo",
        lambda host, *_a: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    monkeypatch.setattr(picture_fetch, "_fetch_picture_bytes", lambda u: b"PNG")
    assert fetch_picture("https://cdn.example/art.png") == b"PNG"
    handler = picture_fetch._PublicRedirects()
    with pytest.raises(PictureFetchError, match="local network"):
        handler.redirect_request(None, None, 302, "Found", {}, "http://10.1.2.3/x.png")
    with pytest.raises(PictureFetchError, match="does not fetch"):
        handler.redirect_request(None, None, 302, "Found", {}, "file:///c:/secret.png")


def test_a_cut_off_reply_is_a_fetch_error(monkeypatch) -> None:
    import http.client

    class _Opener:
        def open(self, *_a, **_k):
            raise http.client.IncompleteRead(b"half")

    monkeypatch.setattr(picture_fetch, "refuse_local_host", lambda _url: None)
    monkeypatch.setattr(picture_fetch.urllib.request, "build_opener", lambda *_a: _Opener())
    with pytest.raises(PictureFetchError, match="Could not fetch"):
        fetch_picture("https://cdn.example/art.png")
