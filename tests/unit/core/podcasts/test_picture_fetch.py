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

    monkeypatch.setattr(picture_fetch.urllib.request, "urlopen", lambda *_a, **_k: _Resp())
    with pytest.raises(PictureFetchError, match="20 megabytes"):
        fetch_picture("https://a.invalid/big.png")
