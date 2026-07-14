"""Tests for the publishing core: RSS generation, destinations, Auphonic parsing."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.publish.auphonic import (
    AuphonicCancelled,
    ProductionStatus,
    _multipart,
    _ProgressReader,
)
from quill.core.publish.destinations import (
    DestinationStore,
    SftpDestination,
    load_destinations,
    save_destinations,
)
from quill.core.publish.rss import FeedItem, generate_rss, write_rss
from quill.core.publish.sftp_publish import companion_files, public_url
from quill.core.speech.ffmpeg import AudioMetadata


def _tags() -> AudioMetadata:
    return AudioMetadata(
        album="My Book", artist="Jane Doe", album_artist="Sam Reader", genre="Fiction"
    )


def _item(tmp_path: Path, *, chapters: bool = False) -> FeedItem:
    audio = tmp_path / "book.m4b"
    audio.write_bytes(b"x" * 1234)
    return FeedItem(
        path=audio,
        media_url="https://example.com/pod/book.m4b",
        title="My Book",
        duration_s=3600,
        has_chapters=chapters,
    )


def test_generate_rss_carries_tags_and_enclosure(tmp_path: Path) -> None:
    xml = generate_rss([_item(tmp_path)], _tags(), feed_url="https://example.com/feed.rss")
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<title>My Book</title>" in xml
    assert 'itunes:category text="Fiction"' in xml
    assert "<itunes:author>Jane Doe</itunes:author>" in xml
    assert "<itunes:author>Sam Reader</itunes:author>" in xml
    assert 'url="https://example.com/pod/book.m4b"' in xml
    assert 'type="audio/x-m4b"' in xml
    assert 'length="1234"' in xml
    assert "<itunes:duration>3600</itunes:duration>" in xml


def test_generate_rss_links_chapters_sidecar(tmp_path: Path) -> None:
    xml = generate_rss([_item(tmp_path, chapters=True)], _tags())
    assert 'url="https://example.com/pod/book.chapters.json"' in xml
    assert 'type="application/json+chapters"' in xml


def test_write_rss_enforces_extension(tmp_path: Path) -> None:
    out = write_rss([_item(tmp_path)], _tags(), tmp_path / "feed.xml")
    assert out.suffix == ".rss" and out.is_file()


def test_destinations_round_trip_without_secrets(tmp_path: Path) -> None:
    store = DestinationStore(
        destinations=[
            SftpDestination(
                name="My host",
                host="example.com",
                username="jeff",
                remote_dir="/pod",
                port=2222,
                url_base="https://example.com/pod",
            )
        ]
    )
    save_destinations(tmp_path, store)
    text = (tmp_path / "publish_destinations.json").read_text(encoding="utf-8")
    assert "password" not in text.lower() and "secret" not in text.lower()
    loaded = load_destinations(tmp_path)
    dest = loaded.find("My host")
    assert dest is not None
    assert dest.port == 2222 and dest.url_base == "https://example.com/pod"
    assert dest.credential_target == "quill:publish:sftp:My host"


def test_load_destinations_tolerates_junk(tmp_path: Path) -> None:
    (tmp_path / "publish_destinations.json").write_text("not json", encoding="utf-8")
    assert load_destinations(tmp_path).destinations == []


def test_public_url_and_companions(tmp_path: Path) -> None:
    dest = SftpDestination(
        name="x", host="h", username="u", remote_dir="/pod", url_base="https://e.com/pod/"
    )
    assert public_url(dest, "book.m4b") == "https://e.com/pod/book.m4b"
    assert public_url(SftpDestination(name="x", host="h", username="u", remote_dir="/"), "b") == ""
    book = tmp_path / "book.m4b"
    book.write_bytes(b"x")
    book.with_suffix(".chapters.json").write_text("{}", encoding="utf-8")
    book.with_suffix(".rss").write_text("<rss/>", encoding="utf-8")
    names = [p.name for p in companion_files(book)]
    assert names == ["book.chapters.json", "book.rss"]


def test_auphonic_multipart_shape(tmp_path: Path) -> None:
    payload = tmp_path / "a.mp3"
    payload.write_bytes(b"AUDIO")
    body, content_type = _multipart({"action": "start", "title": "T"}, "input_file", payload)
    assert content_type.startswith("multipart/form-data; boundary=")
    boundary = content_type.split("boundary=", 1)[1]
    assert body.count(f"--{boundary}".encode()) == 4  # 3 parts + terminator
    assert b'name="action"\r\n\r\nstart' in body
    assert b'filename="a.mp3"' in body
    assert b"AUDIO" in body
    assert body.endswith(f"--{boundary}--\r\n".encode())


def test_progress_reader_reports_and_streams() -> None:
    seen: list[tuple[int, int]] = []
    reader = _ProgressReader(b"abcdefghij", lambda done, total: seen.append((done, total)), None)
    assert reader.read(4) == b"abcd"
    assert reader.read(4) == b"efgh"
    assert reader.read(4) == b"ij"
    assert reader.read(4) == b""
    assert seen == [(4, 10), (8, 10), (10, 10)]


def test_progress_reader_cancel_aborts_before_sending() -> None:
    cancelled = {"flag": False}
    reader = _ProgressReader(b"abcdef", None, lambda: cancelled["flag"])
    assert reader.read(3) == b"abc"
    cancelled["flag"] = True
    with pytest.raises(AuphonicCancelled):
        reader.read(3)


def _fake_sftp_connection(puts: list[dict[str, object]], *, blocks: list[tuple[int, int]]):
    """A stand-in for quill.core.ssh.client.connect returning a put-recorder."""

    class FakeSftp:
        def put(self, local: str, remote: str, confirm: bool = True, callback=None) -> None:
            puts.append({"local": local, "remote": remote, "callback": callback})
            if callback is not None:
                for sent, total in blocks:
                    callback(sent, total)

    class FakeConnection:
        service = SimpleNamespace(_sftp=FakeSftp())

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

    return FakeConnection()


def test_publish_files_reports_bytes_per_file(tmp_path: Path, monkeypatch) -> None:
    import quill.core.ssh.client as ssh_client
    from quill.core.publish.sftp_publish import publish_files

    book = tmp_path / "book.m4b"
    book.write_bytes(b"x" * 10)
    puts: list[dict[str, object]] = []
    monkeypatch.setattr(
        ssh_client,
        "connect",
        lambda *a, **k: _fake_sftp_connection(puts, blocks=[(5, 10), (10, 10)]),
    )
    seen: list[tuple[str, int, int]] = []
    dest = SftpDestination(name="d", host="h", username="u", remote_dir="/pod")
    remote = publish_files(
        dest,
        [book],
        "pw",
        on_bytes=lambda name, sent, total: seen.append((name, sent, total)),
    )
    assert remote == ["/pod/book.m4b"]
    assert seen == [("book.m4b", 5, 10), ("book.m4b", 10, 10)]


def test_publish_files_cancel_raises_publish_cancelled(tmp_path: Path, monkeypatch) -> None:
    import quill.core.ssh.client as ssh_client
    from quill.core.publish.sftp_publish import PublishCancelled, publish_files

    book = tmp_path / "book.m4b"
    book.write_bytes(b"x" * 10)
    puts: list[dict[str, object]] = []
    monkeypatch.setattr(
        ssh_client,
        "connect",
        lambda *a, **k: _fake_sftp_connection(puts, blocks=[(5, 10)]),
    )
    dest = SftpDestination(name="d", host="h", username="u", remote_dir="/pod")
    with pytest.raises(PublishCancelled):
        publish_files(dest, [book], "pw", is_cancelled=lambda: True)


def test_feed_config_round_trip(tmp_path: Path) -> None:
    from quill.core.publish.feed_folder import (
        FeedFolderConfig,
        load_feed_config,
        save_feed_config,
    )

    config = FeedFolderConfig(
        title="My Show",
        author="Jane",
        description="A show",
        media_base="https://e.com/pod",
        feed_url="https://e.com/pod/feed.rss",
        cover_url="https://e.com/pod/cover.jpg",
    )
    config.episode("ep1.mp3").description = "The first one"
    save_feed_config(tmp_path, config)
    loaded = load_feed_config(tmp_path)
    assert loaded.title == "My Show" and loaded.media_base == "https://e.com/pod"
    assert loaded.episodes["ep1.mp3"].description == "The first one"
    assert load_feed_config(tmp_path / "nowhere").title == ""


def test_folder_feed_items_order_urls_and_dates(tmp_path: Path) -> None:
    import os

    from quill.core.publish.feed_folder import FeedFolderConfig, folder_feed_items

    older = tmp_path / "b-older.mp3"
    newer = tmp_path / "a-newer.m4b"
    older.write_bytes(b"x" * 10)
    newer.write_bytes(b"y" * 20)
    os.utime(older, (1_600_000_000, 1_600_000_000))
    os.utime(newer, (1_700_000_000, 1_700_000_000))
    newer.with_suffix(".chapters.json").write_text('{"chapters": []}', encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not audio", encoding="utf-8")

    config = FeedFolderConfig(media_base="https://e.com/pod/")
    config.episode("b-older.mp3").description = "Origins"
    items = folder_feed_items(tmp_path, config)
    assert [i.path.name for i in items] == ["b-older.mp3", "a-newer.m4b"]
    assert items[0].media_url == "https://e.com/pod/b-older.mp3"
    assert items[0].description == "Origins"
    assert items[1].has_chapters and not items[0].has_chapters
    assert items[0].pub_date.endswith("+0000") and "2020" in items[0].pub_date


def test_write_folder_feed_and_show_notes(tmp_path: Path) -> None:
    from quill.core.publish.feed_folder import (
        FeedFolderConfig,
        write_folder_feed,
        write_show_notes,
    )

    (tmp_path / "ep1.mp3").write_bytes(b"x" * 10)
    (tmp_path / "ep2.mp3").write_bytes(b"y" * 10)
    config = FeedFolderConfig(title="My Show", author="Jane", media_base="https://e.com/pod")
    config.episode("ep1.mp3").description = "About <things>"
    written, count = write_folder_feed(tmp_path, config)
    assert written.name == "feed.rss" and count == 2
    xml = written.read_text(encoding="utf-8")
    assert xml.count("<item>") == 2
    assert "https://e.com/pod/ep1.mp3" in xml and "isPermaLink" in xml

    notes = write_show_notes(tmp_path, config)
    text = notes.read_text(encoding="utf-8")
    assert "<h1>My Show</h1>" in text
    assert "<h2>Episode 1:" in text and "<h2>Episode 2:" in text
    assert "About &lt;things&gt;" in text  # descriptions are escaped


def test_write_folder_feed_refuses_empty_folder(tmp_path: Path) -> None:
    from quill.core.publish.feed_folder import FeedFolderConfig, write_folder_feed

    with pytest.raises(ValueError):
        write_folder_feed(tmp_path, FeedFolderConfig(media_base="https://e.com"))


def test_auphonic_account_info_parses(monkeypatch) -> None:
    import quill.core.publish.auphonic as auphonic

    monkeypatch.setattr(
        auphonic,
        "_json",
        lambda url, token, **k: {"data": {"username": "jeff", "credits": 3.5}},
    )
    info = auphonic.account_info("tok")
    assert info.username == "jeff" and info.credits == 3.5


def test_auphonic_account_info_tolerates_junk_credits(monkeypatch) -> None:
    import quill.core.publish.auphonic as auphonic

    monkeypatch.setattr(
        auphonic,
        "_json",
        lambda url, token, **k: {"data": {"username": "jeff", "credits": "lots"}},
    )
    assert auphonic.account_info("tok").credits == 0.0


def test_auphonic_status_flags() -> None:
    assert ProductionStatus(uuid="u", status=3, status_string="Done").done
    assert ProductionStatus(uuid="u", status=2, status_string="Error").failed
    running = ProductionStatus(uuid="u", status=1, status_string="Processing")
    assert not running.done and not running.failed
