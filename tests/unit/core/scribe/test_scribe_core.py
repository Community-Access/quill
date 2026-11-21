"""Scribe for Documents, the wx-free core, against the fake server.

Covers the client (REST, 401 retry, redirects without the token, resumed
downloads), the channel (join, start, events, heartbeat), sign-in (PKCE,
the authorize URL's shape, the loopback redirect, refresh, revoke), the
family queue (one at a time, the runner lock, surviving a restart), every
error row of PRD section 11, Safe Mode, and that no password or token
reaches a log.
"""

from __future__ import annotations

import json
import logging
import threading
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from quill.core import scribe
from quill.core.scribe import errors as e
from quill.core.scribe import queue as q
from quill.core.scribe.auth import ScribeSession, authorization_url
from quill.core.scribe.channel import DocumentChannel, channel_url, parse_event
from quill.core.scribe.client import ScribeClient, content_disposition_file_name
from quill.core.scribe.library import Library, safe_file_name, unique_path
from quill.core.scribe.model import (
    ScribeSettings,
    ordered_for_conversion,
    settings_summary,
    visible_groups,
)
from quill.core.scribe.runner import QueueService, default_channel_opener
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


def _service(
    server: FakeScribe, tmp_path: Path, events: list | None = None, app: str = "QUILL"
) -> QueueService:
    clock = FakeClock()
    server.clock = clock
    record = events if events is not None else []
    return QueueService(
        app,
        queue=q.FamilyQueue(tmp_path / "scribe", now=clock),
        client_factory=lambda: _client(server),
        channel_opener=default_channel_opener(server.connector),
        download_root=lambda: str(tmp_path / "out"),
        listener=lambda kind, job: record.append((kind, job)),
        sleep=clock.sleep,
        clock=clock,
    )


# ----------------------------------------------------------------- model


def test_formats_convert_in_scribes_dependency_order() -> None:
    assert ordered_for_conversion(["daisy", "brf", "mp3", "docx", "html"]) == [
        "html",
        "docx",
        "brf",
        "mp3",
        "daisy",
    ]


def test_setting_groups_follow_the_chosen_formats() -> None:
    assert visible_groups(["docx"]) == ["language", "print", "pictures"]
    assert visible_groups(["brf"]) == ["language", "braille", "pictures"]
    assert (
        settings_summary(["brf"])
        == "Settings below: Language and voice, Braille, Pictures and maths"
    )


def test_settings_send_dialects_and_voices_as_json_strings() -> None:
    body = ScribeSettings(dialects={"en": "en-US"}, voices={"en-US": "Ava"}).to_update()
    assert body["dialects"] == '{"en": "en-US"}' and body["voices"] == '{"en-US": "Ava"}'
    assert "language" not in body  # empty means: detect it


def test_safe_file_names_and_never_overwriting(tmp_path: Path) -> None:
    assert safe_file_name('a<b>:c"/d.docx') == "a_b__c__d.docx"
    assert safe_file_name("CON.txt") == "CON_.txt"
    first = tmp_path / "Notes.docx"
    first.write_text("x")
    assert unique_path(first).name == "Notes (2).docx"


def test_content_disposition_prefers_utf8_and_keeps_only_the_name() -> None:
    header = "attachment; filename=\"x.pdf\"; filename*=UTF-8''..%2F%C3%A9t%C3%A9.pdf"
    assert content_disposition_file_name(header) == "été.pdf"


# ---------------------------------------------------------------- client


def test_rest_calls_carry_the_token_and_retry_once_on_401(server: FakeScribe) -> None:
    tokens = StaticTokens(server)
    client = ScribeClient(tokens, base_url=BASE, transport=server.transport)
    server.reject_token_once = True
    documents, pages = client.list_documents()
    assert tokens.refreshes == 1 and pages == 100 and documents == []


def test_a_download_follows_the_redirect_without_the_token(
    server: FakeScribe, tmp_path: Path
) -> None:
    doc = server.add_document(outputs={"docx": "complete"})
    saved = _client(server).download(doc.id, "docx", tmp_path)
    storage = [r for r in server.requests if r[1].startswith("https://storage")]
    assert storage and "authorization" not in storage[0][2]
    assert saved.name == "Notes.docx" and saved.read_bytes().startswith(b"docx content")


def test_a_dropped_download_resumes_with_range(server: FakeScribe, tmp_path: Path) -> None:
    doc = server.add_document(outputs={"mp3": "complete"})
    server.file_bytes["mp3"] = b"0123456789" * 100
    server.drop_download_after = 300
    saved = _client(server).download(doc.id, "mp3", tmp_path)
    assert saved.read_bytes() == b"0123456789" * 100
    assert any(r[2].get("range") == "bytes=300-" for r in server.requests)


def test_an_existing_file_is_never_overwritten(server: FakeScribe, tmp_path: Path) -> None:
    doc = server.add_document(outputs={"docx": "complete"})
    (tmp_path / "Notes.docx").write_text("mine")
    saved = _client(server).download(doc.id, "docx", tmp_path)
    assert saved.name == "Notes (2).docx" and (tmp_path / "Notes.docx").read_text() == "mine"


def test_plain_http_is_refused_except_on_this_computer(server: FakeScribe) -> None:
    with pytest.raises(e.ScribeError):
        ScribeClient(
            StaticTokens(server), base_url="http://scribe.example", transport=server.transport
        )
    ScribeClient(StaticTokens(server), base_url="http://127.0.0.1:9", transport=server.transport)


def test_trash_recover_rename_and_delete_forever(server: FakeScribe) -> None:
    client = _client(server)
    doc = server.add_document()
    with pytest.raises(e.ScribeError):
        client.delete_forever(doc.id)  # not trashed yet
    client.trash(doc.id)
    assert [d.id for d in client.list_trash()] == [doc.id]
    client.recover(doc.id)
    assert client.rename(doc.id, "Better").title == "Better"
    client.trash(doc.id)
    client.delete_forever(doc.id)
    assert doc.id not in server.documents


def test_account_and_choice_lists(server: FakeScribe) -> None:
    client = _client(server)
    account = client.account()
    assert account.name == "Pat Reader" and account.pages_phrase() == "100 pages left."
    assert client.languages() == [("English", "en"), ("French", "fr")]
    assert client.voices()["en-US"][0] == ("Ava", "en-US-Ava", True)
    assert client.voice_sample_url("en-US-Ava").endswith("/sounds/tts-samples/en-US-Ava.mp3")


# --------------------------------------------------------------- channel


def test_the_channel_address_and_frames(server: FakeScribe) -> None:
    url = channel_url(BASE, "tok")
    assert url.startswith("wss://scribe.test/socket/websocket?") and "vsn=2.0.0" in url
    doc = server.add_document()
    channel = DocumentChannel.open(BASE, server.access_token, doc.id, connector=server.connector)
    assert channel.start_conversion("docx") == "docx-1"
    kinds = []
    while (event := channel.next_event(0.05)) is not None:
        kinds.append((event.kind, event.stage))
    assert kinds[-1] == ("conversion_complete", "")
    assert ("status", "add_image_descriptions") in kinds
    join = server.sockets[0].sent[0]
    assert join[2] == f"documents:{doc.id}" and join[3] == "phx_join"


def test_the_heartbeat_goes_every_thirty_seconds(server: FakeScribe) -> None:
    doc = server.add_document()
    now = [0.0]
    channel = DocumentChannel.open(
        BASE, server.access_token, doc.id, connector=server.connector, clock=lambda: now[0]
    )
    now[0] = 31.0
    channel.next_event(0.0)
    assert any(f[2] == "phoenix" and f[3] == "heartbeat" for f in server.sockets[0].sent)


def test_parse_event_ignores_what_it_does_not_know() -> None:
    assert parse_event("presence_diff", {}) is None
    assert parse_event("error", {"reason": "rate_limited"}).reason == "rate_limited"


# ------------------------------------------------------------------ auth


def test_the_authorize_url_is_wrapped_in_logout() -> None:
    url = authorization_url(BASE, "cid", "http://127.0.0.1:5000/scribe/callback", "chal")
    parts = urlsplit(url)
    assert parts.path == "/auth/logout"
    nxt = parse_qs(parts.query)["next"][0]
    assert nxt.startswith("/oauth/authorize?")
    inner = parse_qs(urlsplit(nxt).query)
    assert inner["code_challenge_method"] == ["S256"] and inner["client_id"] == ["cid"]


def test_sign_in_over_the_loopback_then_refresh_and_sign_out(server: FakeScribe) -> None:
    secrets = SecretsManager(MemorySecrets())
    session = ScribeSession(secrets=secrets, poster=server.poster, client_id="cid", base_url=BASE)
    attempt = session.begin_sign_in()
    redirect = parse_qs(urlsplit(parse_qs(urlsplit(attempt.url).query)["next"][0]).query)[
        "redirect_uri"
    ][0]
    assert redirect.startswith("http://127.0.0.1:") and redirect.endswith("/scribe/callback")
    result: dict = {}
    thread = threading.Thread(target=lambda: result.update(b=attempt.wait(10)))
    thread.start()
    with urllib.request.urlopen(f"{redirect}?code=good-code", timeout=5) as page:  # noqa: S310
        assert b"Signed in. You can close this tab" in page.read()
    thread.join(10)
    assert result["b"].access_token == "access-token-1" and session.is_signed_in()
    verifier = server.token_posts[0]["code_verifier"]
    assert len(verifier) >= 43
    assert session.force_refresh() == "access-token-1x"
    session.sign_out()
    assert server.revoked == ["refresh-token-1"] and not session.is_signed_in()


def test_a_cancelled_sign_in_returns_nothing(server: FakeScribe) -> None:
    session = ScribeSession(
        secrets=SecretsManager(MemorySecrets()),
        poster=server.poster,
        client_id="cid",
        base_url=BASE,
    )
    attempt = session.begin_sign_in()
    attempt.cancel()
    assert attempt.wait(5) is None


def test_a_refused_refresh_wipes_the_session(server: FakeScribe) -> None:
    session = ScribeSession(
        secrets=SecretsManager(MemorySecrets()),
        poster=server.poster,
        client_id="cid",
        base_url=BASE,
    )
    session.exchange("good-code", "http://127.0.0.1/scribe/callback", "v" * 43)
    server.refresh_token = "something else"
    with pytest.raises(e.ScribeSignInError):
        session.force_refresh()
    assert not session.is_signed_in()


def test_no_client_id_means_not_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scribe, "CLIENT_ID", "")
    monkeypatch.delenv("QUILL_SCRIBE_CLIENT_ID", raising=False)
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    assert "not available in this build of QUILL Lite yet" in scribe.unavailable_reason(
        "QUILL Lite"
    )


def test_safe_mode_turns_scribe_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scribe, "CLIENT_ID", "cid")
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    assert "disabled in Safe Mode" in scribe.unavailable_reason()


# ----------------------------------------------------------------- queue


def _job(tmp_path: Path, name: str = "Notes.pdf", formats: tuple = ("docx",), **kw) -> q.Job:
    source = tmp_path / name
    source.write_bytes(kw.pop("content", b"%PDF fake"))
    return q.Job(file_name=name, source_path=str(source), formats=list(formats), **kw)


def test_a_job_uploads_converts_each_format_and_downloads(
    server: FakeScribe, tmp_path: Path
) -> None:
    events: list = []
    service = _service(server, tmp_path, events)
    service.queue.add([_job(tmp_path, formats=("brf", "docx"))])
    assert service.tick()
    job = service.queue.jobs()[0]
    assert job.state == q.DONE and set(job.outputs) == {"docx", "brf"}
    assert all(Path(p).exists() for p in job.outputs.values())
    assert Path(job.folder).name == "Notes"
    kinds = [k for k, _ in events]
    assert kinds[0] == "holder" and "started" in kinds and kinds[-1] == "done"
    assert Library(tmp_path / "scribe" / "library.json").files_for(job.document_id)


def test_several_files_are_one_batch_sent_one_after_another(tmp_path: Path) -> None:
    queue = q.FamilyQueue(tmp_path / "scribe")
    queue.add([_job(tmp_path, "a.pdf"), _job(tmp_path, "b.pdf")])
    jobs = queue.jobs()
    assert [j.state for j in jobs] == [q.QUEUED, q.QUEUED]  # no Send Next File any more
    assert jobs[0].batch and jobs[0].batch == jobs[1].batch
    assert [j.file_name for j in queue.batch_jobs(jobs[0].batch)] == ["a.pdf", "b.pdf"]


def test_a_queue_file_from_before_the_exception_just_runs(tmp_path: Path) -> None:
    queue = q.FamilyQueue(tmp_path / "scribe")
    (tmp_path / "scribe").mkdir()
    (tmp_path / "scribe" / "queue.json").write_text(
        json.dumps({"jobs": [{"id": "x", "file_name": "b.pdf", "state": "waiting_you"}]})
    )
    assert queue.jobs()[0].state == q.QUEUED


def test_only_one_app_holds_the_queue(tmp_path: Path) -> None:
    first = q.FamilyQueue(tmp_path / "scribe")
    second = q.FamilyQueue(tmp_path / "scribe")
    assert first.try_acquire("QUILL") and not second.try_acquire("QUILL Lite")
    first.release()
    assert second.try_acquire("QUILL Lite") and second.holder()["app"] == "QUILL Lite"


def test_a_job_survives_closing_the_app_and_is_not_uploaded_again(
    server: FakeScribe, tmp_path: Path
) -> None:
    doc = server.add_document(outputs={})
    queue = q.FamilyQueue(tmp_path / "scribe")
    queue.add([_job(tmp_path, state=q.CONVERTING, document_id=doc.id)])
    events: list = []
    service = _service(server, tmp_path, events)
    service.note_resumed()  # what start() notes: under way when the app last closed
    service.tick()
    assert not [r for r in server.requests if r[0] == "POST" and r[1].endswith("/api/documents")]
    service.tick()
    assert [k for k, _ in events if k == "closed_while"]


def test_cancel_waiting_stops_the_runner(server: FakeScribe, tmp_path: Path) -> None:
    service = _service(server, tmp_path)
    (job,) = service.queue.add([_job(tmp_path)])
    service.queue.update(job.id, state=q.STOPPED)
    assert service.queue.next_runnable() is None
    service.queue.update(job.id, state=q.CONVERTING)  # the runner's later write
    assert service.queue.get(job.id).state == q.STOPPED


def test_conversion_in_progress_waits_and_is_never_an_error(
    server: FakeScribe, tmp_path: Path
) -> None:
    server.in_progress_once = True
    server.chunks = ["<h1>Notes</h1>"]
    events: list = []
    service = _service(server, tmp_path, events)
    service.queue.add([_job(tmp_path)])
    service.tick()
    assert service.queue.jobs()[0].state == q.DONE
    assert "error" not in [k for k, _ in events]
    assert [j.message for k, j in events if k == "chunk"] == ["<h1>Notes</h1>"]


def test_rate_limited_is_said_once_and_retried(server: FakeScribe, tmp_path: Path) -> None:
    server.rate_limited_once = True
    events: list = []
    service = _service(server, tmp_path, events)
    service.queue.add([_job(tmp_path)])
    service.tick()
    assert [k for k, _ in events].count("busy") == 1
    assert service.queue.jobs()[0].state == q.DONE


def test_needs_purchase_fails_with_the_purchase_link(server: FakeScribe, tmp_path: Path) -> None:
    server.needs_purchase = True
    service = _service(server, tmp_path)
    service.queue.add([_job(tmp_path)])
    service.tick()
    job = service.queue.jobs()[0]
    assert job.state == q.FAILED and job.error_code == "QUILL-SCRIBE-PAGES"
    assert job.purchase_url == "https://scribe.test/buy" and job.message == "You need more pages."


def test_a_locked_pdf_waits_for_its_password_then_three_tries(
    server: FakeScribe, tmp_path: Path
) -> None:
    events: list = []
    service = _service(server, tmp_path, events)
    (job,) = service.queue.add([_job(tmp_path, content=b"LOCKED pdf")])
    service.tick()
    assert service.queue.get(job.id).state == q.NEEDS_PASSWORD
    server.documents[service.queue.get(job.id).document_id].password = "right"
    for attempt in (1, 2):
        service.provide_password(job.id, f"wrong{attempt}")
        service.tick()
        assert service.queue.get(job.id).password_tries == attempt
    service.provide_password(job.id, "wrong3")
    service.tick()
    stored = service.queue.get(job.id)
    assert stored.state == q.FAILED and "password not accepted" in stored.message


def test_the_right_password_converts(server: FakeScribe, tmp_path: Path) -> None:
    service = _service(server, tmp_path)
    (job,) = service.queue.add([_job(tmp_path, content=b"LOCKED pdf")])
    service.tick()
    server.documents[service.queue.get(job.id).document_id].password = "right"
    service.provide_password(job.id, "right")
    service.tick()
    assert service.queue.get(job.id).state == q.DONE


@pytest.mark.parametrize(
    ("reason", "state", "code"),
    [
        ("server_error", q.FAILED, "QUILL-SCRIBE-FAILED"),
        ("not_found", q.GONE, "QUILL-SCRIBE-GONE"),
        ("forbidden", q.GONE, "QUILL-SCRIBE-GONE"),
        ("unauthenticated", q.NEEDS_SIGNIN, "QUILL-SCRIBE-SIGNIN"),
    ],
)
def test_each_error_row(
    server: FakeScribe, tmp_path: Path, reason: str, state: str, code: str
) -> None:
    server.error_for_format["docx"] = (reason, "Scribe's own words.")
    service = _service(server, tmp_path)
    service.queue.add([_job(tmp_path)])
    service.tick()
    job = service.queue.jobs()[0]
    assert (job.state, job.error_code, job.message) == (state, code, "Scribe's own words.")


def test_a_network_drop_reconnects_without_uploading_again(
    server: FakeScribe, tmp_path: Path
) -> None:
    events: list = []
    service = _service(server, tmp_path, events)
    service.queue.add([_job(tmp_path)])
    server.fail_connect = 3
    service.tick()
    uploads = [r for r in server.requests if r[0] == "POST" and r[1].endswith("/api/documents")]
    assert len(uploads) == 1 and service.queue.jobs()[0].state == q.DONE
    assert "offline" in [k for k, _ in events]


def test_a_folder_that_cannot_be_written_is_a_save_error(
    server: FakeScribe, tmp_path: Path
) -> None:
    blocker = tmp_path / "out"
    blocker.write_text("a file where the folder should be")
    service = _service(server, tmp_path)
    service.queue.add([_job(tmp_path)])
    service.tick()
    assert service.queue.jobs()[0].error_code == "QUILL-SCRIBE-SAVE"


def test_every_server_reason_maps_to_its_code() -> None:
    assert isinstance(e.error_from_server("needs_purchase"), e.ScribePagesError)
    assert isinstance(e.error_from_server("invalid_password"), e.ScribePasswordError)
    assert isinstance(e.error_from_server("rate_limited"), e.ScribeBusyError)
    assert isinstance(e.error_from_server("conversion_in_progress"), e.ScribeInProgressError)
    assert e.error_from_server("weird", "Words.").message == "Words."
    assert "[QUILL-SCRIBE-PAGES]" in str(e.ScribePagesError("x"))


# ------------------------------------------------------------- redaction


def test_no_password_or_token_reaches_a_log(
    server: FakeScribe, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    service = _service(server, tmp_path)
    (job,) = service.queue.add([_job(tmp_path, content=b"LOCKED pdf")])
    service.tick()
    server.documents[service.queue.get(job.id).document_id].password = "hunter2-secret"
    service.provide_password(job.id, "hunter2-secret")
    service.tick()
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "hunter2-secret" not in logged and server.access_token not in logged
    stored = (tmp_path / "scribe" / "queue.json").read_text(encoding="utf-8")
    assert "hunter2-secret" not in stored and server.access_token not in stored
    assert json.loads(stored)["jobs"][0]["state"] == q.DONE
