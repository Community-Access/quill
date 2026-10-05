"""Where a document can come from: the clipboard, a link (2026-10-04).

The wx-free decisions behind Open from Clipboard and Open from URL in both
editors, plus the transport changes that make Open from URL ask first, stop on
Cancel and leave no temp file behind.
"""

from __future__ import annotations

import os
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from quill.core.external_change import FileSnapshot, changed_since
from quill.core.open_sources import (
    FILES,
    NONE,
    NOTHING_TO_OPEN,
    URL,
    classify_clipboard,
    clipboard_sentence,
    consent_question,
    dropped_sentence,
    failure_sentence,
    format_size,
    github_raw_url,
    path_from_text,
    prepare_url,
)
from quill.io import http_transport
from quill.io.http_transport import (
    TEMP_PREFIX,
    DownloadCancelledError,
    discard_download,
    download_url,
    sweep_stale_downloads,
)
from quill.io.remote_transport import RemoteAuthError, RemoteNotFoundError, RemoteTransportError

# -- links -------------------------------------------------------------------- #


def test_a_github_page_link_becomes_the_raw_file_behind_it() -> None:
    assert (
        github_raw_url("https://github.com/Oire/plan-cake/blob/main/docs/plan.md?plain=1#L3")
        == "https://raw.githubusercontent.com/Oire/plan-cake/main/docs/plan.md"
    )
    assert github_raw_url("https://example.com/plan.md") == "https://example.com/plan.md"


@pytest.mark.parametrize(
    ("pasted", "expected"),
    [
        ("https://example.com/a.md", "https://example.com/a.md"),
        ('"https://example.com/a.md"', "https://example.com/a.md"),
        ("<https://example.com/a.md>", "https://example.com/a.md"),
        ("www.example.com/a.md", "https://www.example.com/a.md"),
        ("ftp://example.com/a.md", ""),
        ("not a link", ""),
        ("", ""),
    ],
)
def test_prepare_url_tolerates_what_a_chat_does_to_a_link(pasted: str, expected: str) -> None:
    assert prepare_url(pasted) == expected


def test_a_path_copied_as_text_loses_its_quotes_and_file_scheme() -> None:
    assert path_from_text('"C:\\Plans\\plan one.md"') == Path("C:\\Plans\\plan one.md")
    assert path_from_text("file:///C:/Plans/plan.md") == Path("C:/Plans/plan.md")
    assert path_from_text("two\nlines") is None


# -- the clipboard -------------------------------------------------------------- #


def _exists(*names: str) -> Any:
    return lambda path: path.name in names


def test_files_copied_in_explorer_come_first_and_folders_are_counted() -> None:
    found = classify_clipboard(
        ["C:/x/a.md", "C:/x/folder", "C:/x/b.md"],
        "https://example.com",
        is_file=_exists("a.md", "b.md"),
    )
    assert found.kind == FILES
    assert [p.name for p in found.paths] == ["a.md", "b.md"]
    assert found.skipped == 1


def test_a_path_per_line_opens_each() -> None:
    found = classify_clipboard([], "C:/x/a.md\r\nC:/x/b.md\r\n", is_file=_exists("a.md", "b.md"))
    assert found.kind == FILES and len(found.paths) == 2


def test_a_link_is_the_last_thing_tried() -> None:
    found = classify_clipboard([], "https://github.com/o/r/blob/main/p.md", is_file=_exists())
    assert found.kind == URL
    assert found.url == "https://raw.githubusercontent.com/o/r/main/p.md"


def test_ordinary_text_is_nothing_to_open() -> None:
    assert classify_clipboard([], "just some words", is_file=_exists()).kind == NONE
    assert classify_clipboard([], None).kind == NONE
    assert NOTHING_TO_OPEN == "The clipboard holds no file, path or link."


def test_what_is_said_after_opening() -> None:
    assert clipboard_sentence(1, 0) == ""
    assert clipboard_sentence(3, 0) == "Opened 3 files from the clipboard."
    assert dropped_sentence(1, 0) == "Opened 1 dropped file."
    assert dropped_sentence(0, 2) == "Nothing dropped could be opened."


# -- what Open from URL says -------------------------------------------------- #


def test_the_question_names_the_host_the_file_and_the_size() -> None:
    assert consent_question("example.com", "plan.md", 12 * 1024) == (
        "Download plan.md from example.com? It is 12 KB."
    )
    assert consent_question("example.com", "plan.md", None).endswith(
        "The server did not say how large it is."
    )
    assert format_size(3 * 1024 * 1024) == "3.0 MB"
    assert format_size(1) == "1 byte"


@pytest.mark.parametrize(
    ("error", "start"),
    [
        (RemoteNotFoundError("HTTP 404"), "Nothing was found"),
        (RemoteAuthError("HTTP 403"), "example.com would not allow"),
        (RemoteTransportError("GET failed: timed out"), "Could not download from example.com."),
        (OSError("boom"), "Could not download from example.com."),
    ],
)
def test_a_failure_is_one_plain_sentence(error: BaseException, start: str) -> None:
    sentence = failure_sentence(error, "example.com")
    assert sentence.startswith(start)
    assert sentence.endswith(".")
    assert "HTTP" not in sentence


# -- the transport: ask first, stop on Cancel, leave nothing behind ------------ #


class _Response:
    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self._stream = BytesIO(body)
        self.status = 200
        self.headers = headers

    def read(self, n: int = -1) -> bytes:
        return self._stream.read(n)

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


def _serve(monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    headers = {"Content-Length": str(len(body)), "Content-Type": "text/markdown"}
    monkeypatch.setattr(
        http_transport.urllib.request,
        "urlopen",
        lambda request, timeout, context: _Response(body, headers),
    )


def test_the_question_is_asked_before_the_body_and_no_stops_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _serve(monkeypatch, b"# Plan")
    monkeypatch.setattr(http_transport.tempfile, "tempdir", str(tmp_path))
    asked: list[tuple[str, str, int | None]] = []

    def refuse(host: str, filename: str, size: int | None) -> bool:
        asked.append((host, filename, size))
        return False

    with pytest.raises(DownloadCancelledError):
        download_url("https://example.com/plan.md", confirm=refuse)
    assert asked == [("example.com", "plan.md", 6)]
    assert list(tmp_path.glob(f"{TEMP_PREFIX}*")) == []


def test_yes_downloads_it(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, b"# Plan")
    result = download_url("https://example.com/plan.md", confirm=lambda *_a: True)
    try:
        assert Path(result.local_path).read_bytes() == b"# Plan"
    finally:
        discard_download(result.local_path)
    assert not Path(result.local_path).exists()


def test_cancel_part_way_removes_the_partial_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _serve(monkeypatch, b"x" * (200 * 1024))
    monkeypatch.setattr(http_transport.tempfile, "tempdir", str(tmp_path))
    calls = {"n": 0}

    def stop_after_first_chunk() -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    with pytest.raises(DownloadCancelledError):
        download_url("https://example.com/big.md", should_cancel=stop_after_first_chunk)
    assert list(tmp_path.glob(f"{TEMP_PREFIX}*")) == []


def test_discard_refuses_anything_that_is_not_a_download(tmp_path: Path) -> None:
    precious = tmp_path / "plan.md"
    precious.write_text("mine", encoding="utf-8")
    discard_download(precious)
    assert precious.exists()


def test_the_sweep_removes_only_old_downloads(tmp_path: Path) -> None:
    old = tmp_path / f"{TEMP_PREFIX}old.md"
    new = tmp_path / f"{TEMP_PREFIX}new.md"
    other = tmp_path / "keep.md"
    for path in (old, new, other):
        path.write_text("x", encoding="utf-8")
    two_days_ago = time.time() - 2 * 24 * 3600
    os.utime(old, (two_days_ago, two_days_ago))
    os.utime(other, (two_days_ago, two_days_ago))
    assert sweep_stale_downloads(directory=tmp_path) == 1
    assert not old.exists() and new.exists() and other.exists()


# -- the save-time check -------------------------------------------------------- #


def test_changed_since_sees_a_change_and_ignores_the_rest(tmp_path: Path) -> None:
    target = tmp_path / "plan.md"
    target.write_text("first", encoding="utf-8")
    baseline = FileSnapshot.of(target)
    assert changed_since(baseline, target) is None
    target.write_text("second", encoding="utf-8")
    assert changed_since(baseline, target) is not None
    assert changed_since(None, target) is None
    target.unlink()
    assert changed_since(baseline, target) is None
