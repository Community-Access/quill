"""The scrobble waiting list: retried with backoff, capped, aged out, kept on disk."""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.radio import scrobble_queue as sq
from quill.core.radio import scrobbling
from quill.core.radio.scrobble_tracker import Listen

NOW = 1_800_000_000.0


def _listen(n: int, when: float = NOW) -> Listen:
    return Listen(f"Artist {n}", f"Song {n}", int(when) - n)


def test_backoff_doubles_up_to_an_hour() -> None:
    assert sq.retry_delay(0) == 0
    assert sq.retry_delay(1) == 60
    assert sq.retry_delay(2) == 120
    assert sq.retry_delay(3) == 240
    assert sq.retry_delay(50) == 3600


def test_a_failed_batch_waits_then_comes_back(tmp_path: Path) -> None:
    queue = sq.ScrobbleQueue(tmp_path)
    queue.add("listenbrainz", _listen(1))
    batch = queue.due_batch("listenbrainz", now=NOW)
    assert batch == [_listen(1)]
    queue.settle("listenbrainz", batch, sq.Outcome(sq.RETRY), now=NOW)
    assert queue.due_batch("listenbrainz", now=NOW + 30) == []
    assert not queue.has_due("listenbrainz", now=NOW + 30)
    assert queue.due_batch("listenbrainz", now=NOW + 61) == [_listen(1)]
    queue.settle("listenbrainz", batch, sq.Outcome(sq.RETRY), now=NOW + 61)
    assert queue.due_batch("listenbrainz", now=NOW + 61 + 119) == []
    assert queue.due_batch("listenbrainz", now=NOW + 61 + 121) == [_listen(1)]


def test_sent_and_rejected_batches_leave_the_queue(tmp_path: Path) -> None:
    queue = sq.ScrobbleQueue(tmp_path)
    queue.add("lastfm", _listen(1))
    queue.add("lastfm", _listen(2))
    queue.settle("lastfm", [_listen(1)], sq.Outcome(sq.SENT), now=NOW)
    queue.settle("lastfm", [_listen(2)], sq.Outcome(sq.REJECTED, "bad"), now=NOW)
    assert queue.pending("lastfm") == []


def test_a_lost_sign_in_holds_the_songs_until_unblocked(tmp_path: Path) -> None:
    queue = sq.ScrobbleQueue(tmp_path)
    queue.add("lastfm", _listen(1))
    queue.settle("lastfm", [_listen(1)], sq.Outcome(sq.SIGN_IN), now=NOW)
    assert queue.is_blocked("lastfm")
    assert queue.due_batch("lastfm", now=NOW + 99999) == []
    assert queue.pending("lastfm") == [_listen(1)], "not thrown away"
    queue.unblock("lastfm")
    assert queue.due_batch("lastfm", now=NOW) == [_listen(1)]


def test_the_queue_is_capped_and_keeps_the_newest(tmp_path: Path) -> None:
    queue = sq.ScrobbleQueue(tmp_path)
    for n in range(sq.MAX_PER_SERVICE + 10):
        queue.add("listenbrainz", Listen("A", f"Song {n}", int(NOW) + n))
    pending = queue.pending("listenbrainz")
    assert len(pending) == sq.MAX_PER_SERVICE
    assert pending[-1].title == f"Song {sq.MAX_PER_SERVICE + 9}"
    assert pending[0].title == "Song 10"


def test_batches_are_fifty_at_most(tmp_path: Path) -> None:
    queue = sq.ScrobbleQueue(tmp_path)
    for n in range(70):
        queue.add("lastfm", Listen("A", f"Song {n}", int(NOW) + n))
    assert len(queue.due_batch("lastfm", now=NOW)) == sq.BATCH_SIZE == 50


def test_songs_older_than_two_weeks_are_dropped_unsent(tmp_path: Path) -> None:
    queue = sq.ScrobbleQueue(tmp_path)
    queue.add("lastfm", Listen("A", "Old", int(NOW - sq.MAX_AGE_SECONDS - 10)))
    queue.add("lastfm", Listen("A", "New", int(NOW)))
    assert [item.title for item in queue.due_batch("lastfm", now=NOW)] == ["New"]
    assert [item.title for item in queue.pending("lastfm")] == ["New"]


def test_the_queue_survives_a_restart_and_a_bad_file(tmp_path: Path) -> None:
    queue = sq.ScrobbleQueue(tmp_path)
    queue.add("listenbrainz", _listen(1))
    assert sq.ScrobbleQueue(tmp_path).pending("listenbrainz") == [_listen(1)]
    data = json.loads((tmp_path / "radio_scrobble_queue.json").read_text("utf-8"))
    assert data["version"] == 1
    (tmp_path / "radio_scrobble_queue.json").write_text("{not json", "utf-8")
    assert sq.ScrobbleQueue(tmp_path).pending("listenbrainz") == []


def test_a_duplicate_is_not_queued_twice(tmp_path: Path) -> None:
    queue = sq.ScrobbleQueue(tmp_path)
    queue.add("listenbrainz", _listen(1))
    queue.add("listenbrainz", _listen(1))
    assert len(queue.pending("listenbrainz")) == 1


def test_submit_due_sends_each_signed_in_service_and_stops_on_retry(tmp_path: Path) -> None:
    queue = sq.ScrobbleQueue(tmp_path)
    for service in ("listenbrainz", "lastfm"):
        queue.add(service, _listen(1))
    accounts = scrobbling.Accounts(
        listenbrainz_token="LB", lastfm_session="SK", api_key="K", secret="S"
    )
    seen: list[str] = []

    def _post(url: str, body: bytes, **_kwargs: object):
        from quill.core.radio.scrobble_http import Reply

        seen.append(url)
        if "listenbrainz" in url:
            return Reply(200, '{"status": "ok"}')
        return Reply(503, "")

    results = scrobbling.submit_due(queue, accounts, now=NOW, post=_post)
    assert [service for service, _ in results] == ["listenbrainz", "lastfm"]
    assert results[0][1].kind == sq.SENT and results[1][1].kind == sq.RETRY
    assert queue.pending("listenbrainz") == []
    assert queue.pending("lastfm") == [_listen(1)]
    assert len(seen) == 2


def test_nothing_is_sent_for_a_service_without_its_sign_in() -> None:
    assert scrobbling.Accounts().services() == []
    assert scrobbling.Accounts(lastfm_session="SK").services() == [], "no app key"
    assert scrobbling.Accounts(
        lastfm_session="SK", librefm_session="L", api_key="K", secret="S"
    ).services() == ["lastfm", "librefm"]


def test_one_refused_song_never_throws_away_the_rest_of_its_batch(tmp_path: Path) -> None:
    from quill.core.radio.scrobble_http import Reply

    queue = sq.ScrobbleQueue(tmp_path)
    for n in (1, 2, 3):
        queue.add("listenbrainz", _listen(n))
    accounts = scrobbling.Accounts(listenbrainz_token="LB")
    retried: list[str] = []

    def _post(_url: str, body: bytes, **_kwargs: object):
        if b"import" in body:
            return Reply(400, '{"error": "bad track"}')
        if b"Song 2" in body and not retried:
            retried.append("once")
            return Reply(503, "")
        return Reply(400, '{"error": "bad track"}') if b"Song 3" in body else Reply(200, "{}")

    results = scrobbling.submit_due(queue, accounts, now=NOW, post=_post)
    assert [outcome.kind for _, outcome in results] == [sq.SENT, sq.RETRY]
    assert queue.pending("listenbrainz") == [_listen(2), _listen(3)], "only Song 1 went"
    results = scrobbling.submit_due(queue, accounts, now=NOW + 3600, post=_post)
    assert [outcome.kind for _, outcome in results] == [sq.SENT, sq.REJECTED]
    assert queue.pending("listenbrainz") == [], "Song 2 sent; only Song 3 was refused"
