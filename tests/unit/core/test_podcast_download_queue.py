"""Tests for the podcast download queue: chunked/resumable transfer and the
two independent pause controls -- no real network calls."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

import quill.core.podcasts.download_queue as download_queue
from quill.core.podcasts import feed_auth
from quill.core.podcasts.download_queue import (
    DownloadError,
    PodcastDownloadQueue,
    _fetch_chunked,
)


class _FakeResponse:
    def __init__(
        self, chunks: list[bytes], *, status: int = 200, content_length: int | None = None
    ) -> None:
        self._chunks = list(chunks)
        self.status = status
        self.headers = {"Content-Length": str(content_length)} if content_length is not None else {}

    def read(self, _n: int = -1) -> bytes:
        if self._chunks:
            return self._chunks.pop(0)
        return b""

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


# -- _fetch_chunked (pure-ish, one mocked egress site) ----------------------


def test_fetch_chunked_refuses_non_https(tmp_path: Path) -> None:
    with pytest.raises(DownloadError):
        _fetch_chunked(
            "http://x/e.mp3",
            tmp_path / "e.mp3",
            pause_event=threading.Event(),
            cancel_event=threading.Event(),
            on_progress=lambda _w, _t: None,
        )


def test_fetch_chunked_downloads_full_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        feed_auth,
        "urlopen_auth_safe",
        lambda *a, **k: _FakeResponse([b"hello ", b"world"], content_length=11),
    )
    dest = tmp_path / "ep.mp3"
    progress_calls: list[tuple[int, int]] = []
    status = _fetch_chunked(
        "https://x/e.mp3",
        dest,
        pause_event=threading.Event(),
        cancel_event=threading.Event(),
        on_progress=lambda w, t: progress_calls.append((w, t)),
    )
    assert status == "completed"
    assert dest.read_bytes() == b"hello world"
    assert progress_calls[-1] == (11, 11)


def test_fetch_chunked_cancel_event_preempts_before_any_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(feed_auth, "urlopen_auth_safe", lambda *a, **k: _FakeResponse([b"data"]))
    dest = tmp_path / "e.mp3"
    cancel_event = threading.Event()
    cancel_event.set()
    status = _fetch_chunked(
        "https://x/e.mp3",
        dest,
        pause_event=threading.Event(),
        cancel_event=cancel_event,
        on_progress=lambda _w, _t: None,
    )
    assert status == "cancelled"
    assert dest.read_bytes() == b""


def test_fetch_chunked_pause_mid_transfer_stops_before_next_chunk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        feed_auth,
        "urlopen_auth_safe",
        lambda *a, **k: _FakeResponse([b"chunk1", b"chunk2"]),
    )
    dest = tmp_path / "e.mp3"
    pause_event = threading.Event()

    def on_progress(_written: int, _total: int) -> None:
        pause_event.set()  # simulate the user pausing right as the first chunk lands

    status = _fetch_chunked(
        "https://x/e.mp3",
        dest,
        pause_event=pause_event,
        cancel_event=threading.Event(),
        on_progress=on_progress,
    )
    assert status == "paused"
    assert dest.read_bytes() == b"chunk1"


def test_fetch_chunked_resumes_from_partial_file_with_range_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = tmp_path / "e.mp3"
    dest.write_bytes(b"chunk1")
    captured_headers: dict[str, str] = {}

    def fake_urlopen(request: object, timeout: float, context: object) -> _FakeResponse:
        captured_headers.update(dict(request.headers))  # type: ignore[attr-defined]
        return _FakeResponse([b"chunk2"], status=206, content_length=6)

    monkeypatch.setattr(feed_auth, "urlopen_auth_safe", fake_urlopen)
    status = _fetch_chunked(
        "https://x/e.mp3",
        dest,
        pause_event=threading.Event(),
        cancel_event=threading.Event(),
        on_progress=lambda _w, _t: None,
    )
    assert status == "completed"
    assert dest.read_bytes() == b"chunk1chunk2"
    assert "Range" in captured_headers


def test_fetch_chunked_raises_on_network_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def always_fail(*_a: object, **_k: object) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(feed_auth, "urlopen_auth_safe", always_fail)
    with pytest.raises(DownloadError):
        _fetch_chunked(
            "https://x/e.mp3",
            tmp_path / "e.mp3",
            pause_event=threading.Event(),
            cancel_event=threading.Event(),
            on_progress=lambda _w, _t: None,
        )


# -- PodcastDownloadQueue (integration: real worker thread, mocked egress) -


def test_enqueue_downloads_and_completes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        feed_auth,
        "urlopen_auth_safe",
        lambda *a, **k: _FakeResponse([b"hello world"], content_length=11),
    )
    completed = threading.Event()
    completed_items: list[object] = []
    queue = PodcastDownloadQueue(
        on_completed=lambda item: (completed_items.append(item), completed.set())
    )
    try:
        dest = tmp_path / "ep.mp3"
        queue.enqueue(
            "item1", show_id="s1", episode_guid="g1", url="https://x/e.mp3", destination=dest
        )
        assert completed.wait(timeout=5)
        assert dest.read_bytes() == b"hello world"
        item = queue.get("item1")
        assert item is not None and item.status == "completed"
    finally:
        queue.shutdown()


def test_pause_all_blocks_new_start_until_resume_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        feed_auth,
        "urlopen_auth_safe",
        lambda *a, **k: _FakeResponse([b"hello"], content_length=5),
    )
    completed = threading.Event()
    queue = PodcastDownloadQueue(on_completed=lambda _item: completed.set())
    try:
        queue.pause_all()
        dest = tmp_path / "ep.mp3"
        queue.enqueue(
            "item1", show_id="s1", episode_guid="g1", url="https://x/e.mp3", destination=dest
        )
        time.sleep(0.3)
        item = queue.get("item1")
        assert item is not None and item.status == "queued"  # never started

        queue.resume_all()
        assert completed.wait(timeout=5)
        item = queue.get("item1")
        assert item is not None and item.status == "completed"
    finally:
        queue.shutdown()


def test_pause_item_then_resume_item_completes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        feed_auth,
        "urlopen_auth_safe",
        lambda *a, **k: _FakeResponse([b"hello"], content_length=5),
    )
    completed = threading.Event()
    queue = PodcastDownloadQueue(on_completed=lambda _item: completed.set())
    try:
        queue.pause_all()  # keep the worker from racing the assertions below
        dest = tmp_path / "ep.mp3"
        queue.enqueue(
            "item1", show_id="s1", episode_guid="g1", url="https://x/e.mp3", destination=dest
        )

        assert queue.pause_item("item1") is True
        item = queue.get("item1")
        assert item is not None and item.status == "paused"

        assert queue.resume_item("item1") is True
        item = queue.get("item1")
        assert item is not None and item.status == "queued"

        queue.resume_all()
        assert completed.wait(timeout=5)
    finally:
        queue.shutdown()


def test_cancel_item_marks_cancelled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(feed_auth, "urlopen_auth_safe", lambda *a, **k: _FakeResponse([b"hello"]))
    queue = PodcastDownloadQueue()
    try:
        queue.pause_all()
        dest = tmp_path / "ep.mp3"
        queue.enqueue(
            "item1", show_id="s1", episode_guid="g1", url="https://x/e.mp3", destination=dest
        )
        assert queue.cancel_item("item1") is True
        item = queue.get("item1")
        assert item is not None and item.status == "cancelled"
    finally:
        queue.shutdown()


def test_pause_item_unknown_id_returns_false() -> None:
    queue = PodcastDownloadQueue()
    try:
        assert queue.pause_item("missing") is False
        assert queue.resume_item("missing") is False
        assert queue.cancel_item("missing") is False
    finally:
        queue.shutdown()


def test_active_count_reflects_downloading_items(tmp_path: Path) -> None:
    queue = PodcastDownloadQueue()
    try:
        assert queue.active_count() == 0
    finally:
        queue.shutdown()


# -- reconnect on a dropped connection ---------------------------------------


def test_reconnect_retries_and_completes_after_a_dropped_connection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"n": 0}

    def flaky_urlopen(*_a: object, **_k: object) -> _FakeResponse:
        calls["n"] += 1
        if calls["n"] == 1:
            raise download_queue.urllib.error.URLError("connection dropped")
        return _FakeResponse([b"hello world"], content_length=11)

    monkeypatch.setattr(feed_auth, "urlopen_auth_safe", flaky_urlopen)
    completed = threading.Event()
    reconnects: list[tuple[int, int]] = []
    queue = PodcastDownloadQueue(
        on_completed=lambda _item: completed.set(),
        on_reconnect=lambda _item, attempt, max_attempts: reconnects.append((
            attempt,
            max_attempts,
        )),
        reconnect_wait_seconds=0.05,
    )
    try:
        dest = tmp_path / "ep.mp3"
        queue.enqueue(
            "item1", show_id="s1", episode_guid="g1", url="https://x/e.mp3", destination=dest
        )
        assert completed.wait(timeout=5)
        item = queue.get("item1")
        assert item is not None
        assert item.status == "completed"
        assert item.reconnect_attempts == 1
        assert reconnects == [(1, 5)]
        assert calls["n"] == 2
    finally:
        queue.shutdown()


def test_reconnect_disabled_fails_immediately_on_a_dropped_connection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def always_fails(*_a: object, **_k: object) -> _FakeResponse:
        raise download_queue.urllib.error.URLError("connection dropped")

    monkeypatch.setattr(feed_auth, "urlopen_auth_safe", always_fails)
    failed = threading.Event()
    queue = PodcastDownloadQueue(
        on_status_changed=lambda item: failed.set() if item.status == "failed" else None,
        reconnect_enabled=False,
        reconnect_wait_seconds=0.05,
    )
    try:
        dest = tmp_path / "ep.mp3"
        queue.enqueue(
            "item1", show_id="s1", episode_guid="g1", url="https://x/e.mp3", destination=dest
        )
        assert failed.wait(timeout=5)
        item = queue.get("item1")
        assert item is not None
        assert item.status == "failed"
        assert item.reconnect_attempts == 0
    finally:
        queue.shutdown()


def test_reconnect_gives_up_after_max_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def always_fails(*_a: object, **_k: object) -> _FakeResponse:
        raise download_queue.urllib.error.URLError("connection dropped")

    monkeypatch.setattr(feed_auth, "urlopen_auth_safe", always_fails)
    failed = threading.Event()
    queue = PodcastDownloadQueue(
        on_status_changed=lambda item: failed.set() if item.status == "failed" else None,
        reconnect_max_attempts=2,
        reconnect_wait_seconds=0.02,
    )
    try:
        dest = tmp_path / "ep.mp3"
        queue.enqueue(
            "item1", show_id="s1", episode_guid="g1", url="https://x/e.mp3", destination=dest
        )
        assert failed.wait(timeout=5)
        item = queue.get("item1")
        assert item is not None
        assert item.status == "failed"
        assert item.reconnect_attempts == 2
    finally:
        queue.shutdown()


def test_set_reconnect_settings_updates_live() -> None:
    queue = PodcastDownloadQueue(reconnect_enabled=True, reconnect_max_attempts=5)
    try:
        queue.set_reconnect_settings(enabled=False, max_attempts=1, wait_seconds=2.0)
        assert queue._reconnect_enabled is False
        assert queue._reconnect_max_attempts == 1
        assert queue._reconnect_wait_seconds == 2.0
    finally:
        queue.shutdown()


def test_fetch_chunked_sends_auth_header_when_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, str] = {}

    def _fake_urlopen(request: object, **_k: object) -> _FakeResponse:
        captured["auth"] = dict(request.headers).get("Authorization", "MISSING")
        return _FakeResponse([b"ok"], content_length=2)

    monkeypatch.setattr(feed_auth, "urlopen_auth_safe", _fake_urlopen)
    status = _fetch_chunked(
        "https://feeds.example.com/e.mp3",
        tmp_path / "e.mp3",
        auth_header="Basic abc123",
        pause_event=threading.Event(),
        cancel_event=threading.Event(),
        on_progress=lambda _w, _t: None,
    )
    assert status == "completed"
    assert captured["auth"] == "Basic abc123"


def test_fetch_chunked_sends_no_auth_header_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, str] = {}

    def _fake_urlopen(request: object, **_k: object) -> _FakeResponse:
        captured["auth"] = dict(request.headers).get("Authorization", "MISSING")
        return _FakeResponse([], content_length=0)

    monkeypatch.setattr(feed_auth, "urlopen_auth_safe", _fake_urlopen)
    _fetch_chunked(
        "https://feeds.example.com/e.mp3",
        tmp_path / "e.mp3",
        pause_event=threading.Event(),
        cancel_event=threading.Event(),
        on_progress=lambda _w, _t: None,
    )
    assert captured["auth"] == "MISSING"


def test_enqueue_carries_auth_header_to_the_transfer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, str] = {}

    def _fake_urlopen(request: object, **_k: object) -> _FakeResponse:
        captured["auth"] = dict(request.headers).get("Authorization", "MISSING")
        return _FakeResponse([b"ok"], content_length=2)

    monkeypatch.setattr(feed_auth, "urlopen_auth_safe", _fake_urlopen)
    queue = PodcastDownloadQueue()
    item = queue.enqueue(
        "i1",
        show_id="s1",
        episode_guid="g1",
        url="https://feeds.example.com/e.mp3",
        destination=tmp_path / "e.mp3",
        auth_header="Basic zzz",
    )
    deadline = time.time() + 5
    while item.status not in ("completed", "failed") and time.time() < deadline:
        time.sleep(0.02)
    queue.shutdown()
    assert item.status == "completed"
    assert captured["auth"] == "Basic zzz"
