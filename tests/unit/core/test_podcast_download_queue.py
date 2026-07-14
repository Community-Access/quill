"""Tests for the podcast download queue: chunked/resumable transfer and the
two independent pause controls (podcasts.md §4) -- no real network calls."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

import quill.core.podcasts.download_queue as download_queue
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
        download_queue.urllib.request,
        "urlopen",
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
    monkeypatch.setattr(
        download_queue.urllib.request, "urlopen", lambda *a, **k: _FakeResponse([b"data"])
    )
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
        download_queue.urllib.request,
        "urlopen",
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

    monkeypatch.setattr(download_queue.urllib.request, "urlopen", fake_urlopen)
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

    monkeypatch.setattr(download_queue.urllib.request, "urlopen", always_fail)
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
        download_queue.urllib.request,
        "urlopen",
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
        download_queue.urllib.request,
        "urlopen",
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
        download_queue.urllib.request,
        "urlopen",
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
    monkeypatch.setattr(
        download_queue.urllib.request, "urlopen", lambda *a, **k: _FakeResponse([b"hello"])
    )
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
