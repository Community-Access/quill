# ruff: noqa: E501 - HTML fixtures below have long, unbreakable stream-URL lines
from __future__ import annotations

import pytest

import quill.core.radio.xiph as xiph
from quill.core.radio import directory_cache
from quill.core.radio.xiph import (
    CATEGORY_LABEL,
    XiphError,
    fetch_genre_stations,
    fetch_genres,
    genre_display,
    parse_genres,
    parse_stations,
    refuse_in_safe_mode,
)


@pytest.fixture(autouse=True)
def _isolated_genre_cache(tmp_path, monkeypatch):
    """fetch_genres now caches to disk; keep every test on its own empty cache
    so one test's result can never satisfy the next one's fetch."""
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    directory_cache.clear()
    yield
    directory_cache.clear()


_GENRES_HTML = """
<a href="/genres/Jazz">Jazz</a>
<a href="/genres/jazz" class="badge">jazz</a>
<a href="/genres/80s">80s</a>
<a href="/genres/Pop">Pop</a>
"""

_GENRE_PAGE = """
<h2>Streams</h2>
<div class="card shadow-sm mt-3">
    <div class="card-body">
        <h5 class="card-title">SatinJazz</h5>
        <h6 class="card-subtitle mb-2 text-muted">On Air: Clare Teal</h6>
        <p class="card-text">Great women jazz vocalists</p>
    </div>
    <div class="card-footer d-block text-muted">
        31 Listeners &mdash;
        <a href="/genres/jazz" class="badge badge-secondary">jazz</a> &mdash;
        <a href="/codecs/MP3" class="badge badge-primary">MP3</a>
        <div class="d-inline-block float-right">
            <a href="http://quincy.torontocast.com:2720/stream" class="btn btn-sm btn-primary">Play</a>
        </div>
    </div>
</div>
<div class="card shadow-sm mt-3">
    <div class="card-body">
        <h5 class="card-title">Mother Earth &amp; Radio</h5>
    </div>
    <div class="card-footer">
        <a href="/codecs/OGG" class="badge badge-primary">OGG</a>
        <a href="https://stream.motherearthradio.de/listen/x/radio.ogg" class="btn btn-sm btn-primary">Play</a>
    </div>
</div>
"""


def test_parse_genres_dedups_case_insensitively_and_keeps_source_order() -> None:
    # Source order is the directory's *use* order, which is what a browse list
    # wants; sorting it alphabetically (as this used to) buried Jazz under "00".
    assert parse_genres(_GENRES_HTML) == ["Jazz", "80s", "Pop"]  # jazz/Jazz collapsed


def test_parse_genres_preserves_popularity_order_not_alphabetical() -> None:
    # The shape dir.xiph.org actually serves: most-used first.
    html = "".join(
        f'<a href="/genres/{name}">{name}</a>'
        for name in ("various", "Pop", "Rock", "Dance", "80s", "House", "Jazz")
    )
    assert parse_genres(html) == ["various", "Pop", "Rock", "Dance", "80s", "House", "Jazz"]


def test_is_useful_genre_drops_non_genres_and_keeps_odd_real_ones() -> None:
    for junk in (
        "NULL",
        "amp",
        "and",
        "x",
        "00",
        "100",
        "1989",
        "104.5",
        "103.9 Radyo Natin FM - Pinamungajan",
        "a" * 29,
    ):
        assert not xiph.is_useful_genre(junk), junk
    for real in ("Jazz", "80s", "Deep House", "R&B", "Pinoy", "Éclectique", "Smooth"):
        assert xiph.is_useful_genre(real), real


def test_parse_genres_filters_the_junk_the_directory_serves() -> None:
    html = (
        '<a href="/genres/Jazz">x</a><a href="/genres/NULL">x</a>'
        '<a href="/genres/104.5">x</a><a href="/genres/Rock">x</a>'
    )
    assert parse_genres(html) == ["Jazz", "Rock"]


def test_fetch_genres_is_bounded_by_default_and_unbounded_on_request(monkeypatch) -> None:
    html = "".join(f'<a href="/genres/Genre{n:04d}">x</a>' for n in range(500))
    monkeypatch.setattr(xiph, "_fetch", lambda url, **_kwargs: html)
    assert len(fetch_genres()) == xiph.POPULAR_GENRE_LIMIT
    assert fetch_genres()[0] == "Genre0000"  # the head of the directory's order
    assert len(fetch_genres(limit=0)) == 500
    assert len(fetch_genres(limit=5)) == 5


def test_bounded_fetch_reads_only_the_head_of_the_index(monkeypatch) -> None:
    # The whole index is ~5.3 MB and ~9 s; a bounded call must not pay that.
    calls: list[dict] = []
    html = "".join(f'<a href="/genres/Genre{n:04d}">x</a>' for n in range(500))

    def fake_fetch(url, **kwargs):
        calls.append(kwargs)
        return html

    monkeypatch.setattr(xiph, "_fetch", fake_fetch)
    assert len(fetch_genres(limit=10)) == 10
    assert len(calls) == 1, "a satisfied head read must not also fetch the full page"
    assert calls[0]["max_bytes"] == xiph._INDEX_HEAD_BYTES
    assert calls[0]["allow_partial"] is True


def test_bounded_fetch_falls_back_to_the_full_page_when_the_head_is_short(monkeypatch) -> None:
    # If the prefix yields fewer than asked for, read it all rather than pass a
    # short list off as the answer.
    short = '<a href="/genres/Jazz">x</a><a href="/genres/Rock">x</a>'
    full = "".join(f'<a href="/genres/Genre{n:04d}">x</a>' for n in range(50))
    calls: list[dict] = []

    def fake_fetch(url, **kwargs):
        calls.append(kwargs)
        return short if kwargs.get("allow_partial") else full

    monkeypatch.setattr(xiph, "_fetch", fake_fetch)
    assert len(fetch_genres(limit=20)) == 20
    assert len(calls) == 2
    assert calls[1].get("allow_partial") is not True
    assert calls[1]["max_bytes"] == xiph._MAX_INDEX_BYTES


def test_allow_partial_returns_a_prefix_instead_of_raising(monkeypatch) -> None:
    class _Resp:
        def read(self, size: int) -> bytes:
            return b"y" * min(size, 5_000_000)

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> bool:
            return False

    monkeypatch.setattr(xiph.urllib.request, "urlopen", lambda *a, **k: _Resp())
    partial = xiph._fetch("https://dir.xiph.org/genres", max_bytes=1000, allow_partial=True)
    assert len(partial) == 1000  # a prefix, no error
    with pytest.raises(XiphError, match="larger than"):
        xiph._fetch("https://dir.xiph.org/genres", max_bytes=1000)


def test_fetch_refuses_a_truncated_page_rather_than_dropping_entries(monkeypatch) -> None:
    # The real bug: the /genres index outgrew the shared 4 MB read cap, so the
    # tolerant parser silently lost 412 genres and the count drifted per refresh.
    class _Resp:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload

        def read(self, size: int) -> bytes:
            return self._payload[:size]

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> bool:
            return False

    monkeypatch.setattr(xiph.urllib.request, "urlopen", lambda *a, **k: _Resp(b"x" * 5_000_000))
    with pytest.raises(XiphError, match="larger than"):
        xiph._fetch("https://dir.xiph.org/genres", max_bytes=4_000_000)
    # Under the cap it reads normally.
    assert xiph._fetch("https://dir.xiph.org/genres", max_bytes=9_000_000).startswith("x")


def test_genres_index_cap_is_larger_than_a_genre_page_cap() -> None:
    # The index is ~5.3 MB and growing; the per-genre pages are small.
    assert xiph._MAX_INDEX_BYTES > 5_300_000 > xiph._MAX_BYTES


def test_second_open_is_served_from_cache_without_refetching(monkeypatch) -> None:
    # The point of the cache: opening the Xiph branch again must not re-download
    # a 5.3 MB page. The second call also reports an age, so the UI can say so.
    html = "".join(f'<a href="/genres/Genre{n:04d}">x</a>' for n in range(300))
    calls: list[str] = []

    def fake_fetch(url, **_kwargs):
        calls.append(url)
        return html

    monkeypatch.setattr(xiph, "_fetch", fake_fetch)
    first, age_first = xiph.fetch_genres_with_age()
    second, age_second = xiph.fetch_genres_with_age()
    assert first == second and len(first) == xiph.POPULAR_GENRE_LIMIT
    assert len(calls) == 1, "the second open must be served from cache"
    assert age_first is None, "a live fetch reports no age"
    assert age_second is not None, "a cached answer must report its age"


def test_refresh_refetches_even_when_the_cache_is_fresh(monkeypatch) -> None:
    pages = ['<a href="/genres/Old">x</a>', '<a href="/genres/New">x</a>']
    counter = {"n": 0}

    def counting_fetch(url, **_kwargs):
        page = pages[min(counter["n"], len(pages) - 1)]
        counter["n"] += 1
        return page

    monkeypatch.setattr(xiph, "_fetch", counting_fetch)
    assert xiph.fetch_genres(limit=1) == ["Old"]
    assert xiph.fetch_genres(limit=1) == ["Old"], "cached"
    assert xiph.fetch_genres(limit=1, refresh=True) == ["New"], "Refresh must refetch"


def test_a_failed_refresh_keeps_the_previous_list(monkeypatch) -> None:
    # A branch that blanks itself because the directory hiccuped is worse than
    # a branch that quietly stays as it was and says how old it is.
    monkeypatch.setattr(xiph, "_fetch", lambda url, **_kw: '<a href="/genres/Jazz">x</a>')
    assert xiph.fetch_genres(limit=1) == ["Jazz"]

    def boom(url, **_kwargs):
        raise XiphError("directory down")

    monkeypatch.setattr(xiph, "_fetch", boom)
    genres, age = xiph.fetch_genres_with_age(limit=1, refresh=True)
    assert genres == ["Jazz"]
    assert age is not None, "a stale list must be reported as stale"


def test_a_cached_head_read_is_refetched_when_all_genres_are_wanted(monkeypatch) -> None:
    # The bounded call caches an incomplete prefix; limit=0 must not be handed
    # that prefix as if it were the whole directory.
    head = "".join(f'<a href="/genres/G{n:04d}">x</a>' for n in range(200))
    full = "".join(f'<a href="/genres/G{n:04d}">x</a>' for n in range(900))
    calls: list[bool] = []

    def fake_fetch(url, **kwargs):
        partial = bool(kwargs.get("allow_partial"))
        calls.append(partial)
        return head if partial else full

    monkeypatch.setattr(xiph, "_fetch", fake_fetch)
    assert len(xiph.fetch_genres(limit=50)) == 50
    assert calls == [True]
    assert len(xiph.fetch_genres(limit=0)) == 900
    assert calls == [True, False], "limit=0 must not be served an incomplete cache entry"


def test_parse_genres_url_decodes_names() -> None:
    # The href segment is percent-encoded; the genre name must come out decoded
    # so it isn't double-encoded when fetch_genre_stations re-encodes it.
    html = '<a href="/genres/%C3%89clectique">x</a>'
    assert parse_genres(html) == ["Éclectique"]


def test_genre_display() -> None:
    assert genre_display("jazz") == "Jazz"
    assert genre_display("80s") == "80s"  # digits left alone
    assert genre_display("MP3") == "MP3"


def test_parse_stations_extracts_title_url_codec_and_unescapes() -> None:
    stations = parse_stations(_GENRE_PAGE)
    assert [s.name for s in stations] == ["SatinJazz", "Mother Earth & Radio"]
    assert stations[0].stream_url == "http://quincy.torontocast.com:2720/stream"
    assert stations[0].codec == "MP3"
    assert stations[0].source == CATEGORY_LABEL and CATEGORY_LABEL in stations[0].tags
    assert stations[1].stream_url.endswith("radio.ogg")


def test_parse_stations_tolerates_junk() -> None:
    assert parse_stations("<html>no cards here</html>") == []


def test_fetch_genre_stations_uses_fetch(monkeypatch) -> None:
    monkeypatch.setattr(xiph, "_fetch", lambda url: _GENRE_PAGE)
    stations = fetch_genre_stations("jazz")
    assert len(stations) == 2


def test_fetch_genres_returns_empty_on_error(monkeypatch) -> None:
    def boom(url, **_kwargs):
        raise XiphError("offline")

    monkeypatch.setattr(xiph, "_fetch", boom)
    assert fetch_genres() == []


def test_fetch_genre_stations_empty_genre() -> None:
    assert fetch_genre_stations("   ") == []


def test_safe_mode_refuses() -> None:
    with pytest.raises(XiphError):
        refuse_in_safe_mode(True)
    with pytest.raises(XiphError):
        fetch_genres(safe_mode=True)
    with pytest.raises(XiphError):
        fetch_genre_stations("jazz", safe_mode=True)
