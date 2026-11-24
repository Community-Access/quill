"""The Scribe API pieces added by the coverage audit (docs/design/scribe-api-coverage.md).

* Sign-in sends a random ``state`` and refuses a redirect that does not
  bring it back, before any code is exchanged (Pneuma's client, 2026-11-23).
* The document channel joins with ``replay_chunks``: a late join or a
  reconnect gets the preview chunks already streamed, and a chunk already
  passed on (by its ``index``) is never passed on twice. A server from before
  ``index`` behaves as it always has.
* Rename refuses a blank title and one over 255 characters without sending.

All against the fake server; nothing touches the network.
"""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from quill.core.scribe import errors as e
from quill.core.scribe import queue as q
from quill.core.scribe.auth import ScribeSession, authorization_url, new_state
from quill.core.scribe.channel import (
    ChannelEvent,
    ChunkLedger,
    DocumentChannel,
    default_channel_opener,
    parse_event,
)
from quill.core.scribe.client import TITLE_LIMIT, ScribeClient
from quill.core.scribe.runner import QueueService
from quill.core.secrets import SecretsManager
from tests.unit.core.scribe.fake_scribe import (
    BASE,
    FakeClock,
    FakeScribe,
    MemorySecrets,
    StaticTokens,
)


@pytest.fixture
def server() -> FakeScribe:
    return FakeScribe()


def _client(server: FakeScribe) -> ScribeClient:
    return ScribeClient(
        StaticTokens(server), base_url=BASE, transport=server.transport, sleep=lambda _s: None
    )


def _chunks(channel: DocumentChannel) -> list[str]:
    said = []
    while (event := channel.next_event(0.05)) is not None:
        if event.kind == "chunk":
            said.append(event.content)
    return said


# ------------------------------------------------------------ sign-in state


def _inner(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(parse_qs(urlsplit(url).query)["next"][0]).query)


def test_the_authorize_url_carries_the_state_only_when_given() -> None:
    redirect = "http://127.0.0.1:5000/scribe/callback"
    assert _inner(authorization_url(BASE, "cid", redirect, "chal", state="s1"))["state"] == ["s1"]
    assert "state" not in _inner(authorization_url(BASE, "cid", redirect, "chal"))


def test_each_sign_in_gets_a_new_unguessable_state() -> None:
    first, second = new_state(), new_state()
    assert first != second and len(first) >= 43


def _session(server: FakeScribe) -> ScribeSession:
    return ScribeSession(
        secrets=SecretsManager(MemorySecrets()),
        poster=server.poster,
        client_id="cid",
        base_url=BASE,
    )


@pytest.mark.parametrize("state_part", ["&state=someone-elses", ""])
def test_a_redirect_without_our_state_is_refused_and_never_exchanged(
    server: FakeScribe, state_part: str
) -> None:
    session = _session(server)
    attempt = session.begin_sign_in()
    redirect = _inner(attempt.url)["redirect_uri"][0]
    result: dict = {}

    def wait() -> None:
        try:
            attempt.wait(10)
        except e.ScribeSignInError as error:
            result["error"] = error

    thread = threading.Thread(target=wait)
    thread.start()
    with pytest.raises(urllib.error.HTTPError) as refused:
        urllib.request.urlopen(f"{redirect}?code=good-code{state_part}", timeout=5)  # noqa: S310
    assert refused.value.code == 400
    assert b"Sign-in did not complete" in refused.value.read()
    thread.join(10)
    assert result["error"].reason == "state_mismatch"
    assert result["error"].message == "Scribe for Documents did not sign you in. Try again."
    assert server.token_posts == [] and not session.is_signed_in()


# ------------------------------------------------------- chunk replay on join


def test_the_join_asks_for_the_chunks_already_streamed(server: FakeScribe) -> None:
    doc = server.add_document()
    DocumentChannel.open(BASE, server.access_token, doc.id, connector=server.connector)
    assert server.join_payloads == [{"replay_chunks": True}]


def test_a_late_join_gets_the_preview_from_its_start(server: FakeScribe) -> None:
    doc = server.add_document()
    server.streamed = ["<h1>Notes</h1>", "<p>One.</p>"]
    channel = DocumentChannel.open(BASE, server.access_token, doc.id, connector=server.connector)
    assert _chunks(channel) == ["<h1>Notes</h1>", "<p>One.</p>"]


def test_a_reconnect_passes_on_only_the_chunks_not_yet_passed_on(server: FakeScribe) -> None:
    doc = server.add_document()
    opener = default_channel_opener(server.connector)
    client = _client(server)
    server.streamed = ["<h1>Notes</h1>", "<p>One.</p>"]
    first = opener(client, doc.id)
    assert _chunks(first) == ["<h1>Notes</h1>", "<p>One.</p>"]
    first.close()
    server.streamed.append("<p>Two.</p>")  # streamed while the connection was down
    second = opener(client, doc.id)
    assert _chunks(second) == ["<p>Two.</p>"]


def test_an_older_server_without_indexes_passes_every_chunk(server: FakeScribe) -> None:
    server.chunk_indexes = False
    doc = server.add_document()
    server.in_progress_once = True
    server.chunks = ["<p>Live.</p>"]
    channel = DocumentChannel.open(BASE, server.access_token, doc.id, connector=server.connector)
    with pytest.raises(e.ScribeInProgressError):
        channel.start_conversion("docx")
    assert _chunks(channel) == ["<p>Live.</p>"]


def test_the_ledger_keeps_documents_apart_and_ignores_other_events() -> None:
    ledger = ChunkLedger()
    chunk = ChannelEvent("chunk", content="x", index=0)
    assert ledger.admit("a", chunk) and not ledger.admit("a", chunk)
    assert ledger.admit("b", chunk)
    assert ledger.admit("a", ChannelEvent("chunk", content="y"))  # no index: passed on
    assert ledger.admit("a", ChannelEvent("status", format="docx", stage="queue"))


@pytest.mark.parametrize(
    ("raw", "index"), [(3, 3), (0, 0), (-2, -1), (True, -1), ("4", -1), (None, -1), (2.0, -1)]
)
def test_a_chunk_index_is_read_only_from_a_whole_number(raw: object, index: int) -> None:
    payload = {"content": "x"} if raw is None else {"content": "x", "index": raw}
    assert parse_event("chunk", payload).index == index


def test_the_queue_passes_on_the_replayed_preview_then_the_live_one_once(
    server: FakeScribe, tmp_path: Path
) -> None:
    clock = FakeClock()
    server.clock = clock
    server.in_progress_once = True
    server.streamed = ["<h1>Notes</h1>"]
    server.chunks = ["<p>One.</p>"]
    events: list = []
    service = QueueService(
        "QUILL",
        queue=q.FamilyQueue(tmp_path / "scribe", now=clock),
        client_factory=lambda: _client(server),
        channel_opener=default_channel_opener(server.connector),
        download_root=lambda: str(tmp_path / "out"),
        listener=lambda kind, job: events.append((kind, job)),
        sleep=clock.sleep,
        clock=clock,
    )
    source = tmp_path / "Notes.pdf"
    source.write_bytes(b"%PDF fake")
    service.queue.add([q.Job(file_name="Notes.pdf", source_path=str(source), formats=["docx"])])
    service.tick()
    assert service.queue.jobs()[0].state == q.DONE
    assert [j.message for k, j in events if k == "chunk"] == ["<h1>Notes</h1>", "<p>One.</p>"]


# ------------------------------------------------------------------ rename


@pytest.mark.parametrize("title", ["", "   ", "x" * (TITLE_LIMIT + 1)])
def test_rename_refuses_a_blank_or_too_long_title_without_sending(
    server: FakeScribe, title: str
) -> None:
    doc = server.add_document()
    before = len(server.requests)
    with pytest.raises(e.ScribeError) as refused:
        _client(server).rename(doc.id, title)
    assert len(server.requests) == before
    assert "Nothing was changed." in refused.value.message
    assert refused.value.reason in {"blank_title", "title_too_long"}


def test_rename_sends_a_title_of_exactly_the_limit(server: FakeScribe) -> None:
    doc = server.add_document()
    _client(server).rename(doc.id, "x" * TITLE_LIMIT)
    assert any(method == "PATCH" for method, *_ in server.requests)


def test_a_finished_preview_is_forgotten_so_a_new_one_passes_whole() -> None:
    ledger = ChunkLedger()
    first = ChannelEvent("chunk", content="x", index=0)
    assert ledger.admit("a", first) and not ledger.admit("a", first)
    assert ledger.admit("a", ChannelEvent("conversion_complete", format="html_stream"))
    assert ledger.admit("a", first)  # a new preview of the same document starts at 0 again
    assert ledger.admit("a", ChannelEvent("conversion_complete", format="docx"))
    assert not ledger.admit("a", first)  # another format finishing forgets nothing
