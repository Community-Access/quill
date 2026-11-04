"""The offline queue and what counts as "the site cannot be reached" (wordpress.md 5.10)."""

from __future__ import annotations

import ssl
from pathlib import Path
from urllib.error import URLError

from quill.core.wordpress import offline as off
from quill.core.wordpress.api import WordPressApiError


def _raised(cause: BaseException, status: int = 0) -> WordPressApiError:
    try:
        raise WordPressApiError("x", status=status) from cause
    except WordPressApiError as exc:
        return exc


def test_time_outs_and_lost_connections_are_unreachable() -> None:
    assert off.is_unreachable(_raised(URLError("timed out")))
    assert off.is_unreachable(_raised(TimeoutError()))
    assert off.is_unreachable(_raised(URLError(ConnectionResetError("reset"))))


def test_refusals_and_certificates_are_not() -> None:
    assert not off.is_unreachable(_raised(URLError("x"), status=401))
    assert not off.is_unreachable(_raised(URLError(ssl.SSLError("bad"))))
    assert not off.is_unreachable(_raised(URLError("certificate verify failed")))
    assert not off.is_unreachable(_raised(ValueError("not json")))
    assert not off.is_unreachable(ValueError("x"))


def test_the_queue_keeps_one_entry_per_document_and_a_publish_wins(tmp_path: Path) -> None:
    queue = off.OfflineQueue(tmp_path)
    queue.add(key="radio/page-1", site_id="radio", title="A", publish=False, since_gmt="s1")
    queue.add(key="radio/page-2", site_id="radio", title="B", publish=False)
    queue.add(key="radio/page-1", site_id="radio", title="A", publish=True, since_gmt="s2")
    entries = off.OfflineQueue(tmp_path).entries()
    assert [e.key for e in entries] == ["radio/page-1", "radio/page-2"]
    assert entries[0].publish and entries[0].since_gmt == "s1"
    queue.drop("radio/page-1")
    assert [e.key for e in queue.entries()] == ["radio/page-2"]


def test_a_broken_queue_file_is_an_empty_queue(tmp_path: Path) -> None:
    (tmp_path / off.QUEUE_FILE).write_text('{"not": "a list"}', encoding="utf-8")
    assert off.OfflineQueue(tmp_path).entries() == []


def test_back_online_sentences() -> None:
    assert off.back_online_sentence("Community Radio", 2, 0) == (
        "Back online: 2 drafts sent to Community Radio."
    )
    assert off.back_online_sentence("Community Radio", 0, 1) == (
        "Back online: 1 item published on Community Radio."
    )
    assert off.back_online_sentence("Community Radio", 1, 2) == (
        "Back online: 1 draft sent and 2 items published to Community Radio."
    )
