"""Release channels, Phase 2: the signed v2 feed on the client side.

Signature over the exact bytes, the sequence high-water mark, expiry, the
offline cache, "not published yet" handing back to the old path, the feed
builds travelling through the existing flows, the channel listing deciding
what is visible, resumable verified downloads, and the background-download
rules. No network: every fetch goes through a fake ``get``.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("nacl")
from nacl.signing import SigningKey  # noqa: E402

from quill.core.updater.background import Conditions, background_gate  # noqa: E402
from quill.core.updater.channels import ChannelState  # noqa: E402
from quill.core.updater.download import (  # noqa: E402
    DownloadVerifyError,
    NotEnoughSpaceError,
    download_verified,
)
from quill.core.updater.feed import (  # noqa: E402
    FeedAsset,
    parse_feed,
    trusted_feed_keys,
    verify_feed_bytes,
)
from quill.core.updater.feed_fetch import (  # noqa: E402
    FeedCheckFailed,
    FeedMissing,
    fetch_feed,
    offers_from_feed,
    releases_for_check,
)
from quill.core.updater.feed_publish import (  # noqa: E402
    list_release,
    new_feed,
    promote,
    sign_bytes,
)
from quill.core.updater.policy import choose_offer, visible_on  # noqa: E402

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
SHA = "a" * 64


def _asset(kind: str, version: str) -> FeedAsset:
    name = f"Quill-Radio-{'Setup-Shared' if kind == 'installer' else 'Portable'}-{version}"
    name += ".exe" if kind == "installer" else ".zip"
    url = (
        f"https://github.com/Community-Access/quill/releases/download/quill-radio-v{version}/{name}"
    )
    return FeedAsset(kind=kind, name=name, url=url, size=100, sha256=SHA)


def _feed(*, stable: str = "3.2.0", beta: str = "3.3.0-beta.1", dev: str = ""):
    feed = new_feed("radio", "Quill Radio")
    moment = NOW - timedelta(days=30)
    for version, channel in ((stable, "beta"), (beta, "beta"), (dev, "dev")):
        if not version:
            continue
        feed = list_release(
            feed,
            version=version,
            tag=f"quill-radio-v{version}",
            channel=channel,
            assets=[_asset("installer", version), _asset("portable", version)],
            now=moment,
            data_formats={"radio.favorites": 1},
            reads_formats={"radio.favorites": 1},
        )
    feed = promote(feed, stable, "stable", now=moment + timedelta(days=8))
    return feed


@pytest.fixture
def key() -> SigningKey:
    return SigningKey.generate()


def _server(feed, key, *, sig: str | None = None):
    data = feed.to_bytes()
    signature = sig if sig is not None else sign_bytes(data, bytes(key))
    calls: list[str] = []

    def get(url: str) -> bytes:
        calls.append(url)
        return signature.encode() if url.endswith(".sig") else data

    get.calls = calls  # type: ignore[attr-defined]
    return get


# -- signature -----------------------------------------------------------------


def test_signature_is_over_the_exact_bytes(key) -> None:
    data = _feed().to_bytes()
    sig = sign_bytes(data, bytes(key))
    trusted = [bytes(key.verify_key)]
    assert verify_feed_bytes(data, sig, trusted)
    assert not verify_feed_bytes(data + b" ", sig, trusted)
    assert not verify_feed_bytes(data, sig, [bytes(SigningKey.generate().verify_key)])
    assert not verify_feed_bytes(data, "", trusted)


def test_the_bundled_feed_key_is_trusted() -> None:
    assert len(trusted_feed_keys()) >= 1


def test_a_rotation_sidecar_with_two_signatures_verifies_under_either_key(key) -> None:
    other = SigningKey.generate()
    data = b'{"format": "x"}\n'
    both = sign_bytes(data, bytes(other)) + sign_bytes(data, bytes(key)).split("\n", 2)[2]
    assert verify_feed_bytes(data, both, [bytes(key.verify_key)])
    assert verify_feed_bytes(data, both, [bytes(other.verify_key)])


# -- fetching ------------------------------------------------------------------


def test_fetch_verifies_remembers_and_caches(key, tmp_path: Path) -> None:
    feed = _feed()
    result = fetch_feed(
        "radio", get=_server(feed, key), keys=[bytes(key.verify_key)], state_dir=tmp_path, now=NOW
    )
    assert result.status == "ok"
    assert result.feed is not None and result.feed.current("stable").version == "3.2.0"
    assert (tmp_path / "feed-cache" / "radio.json").read_bytes() == feed.to_bytes()
    assert '"sequence"' in (tmp_path / "feed-state.json").read_text(encoding="utf-8")


def test_an_unsigned_or_forged_feed_is_never_used(key, tmp_path: Path) -> None:
    feed = _feed()
    forged = sign_bytes(feed.to_bytes(), bytes(SigningKey.generate()))
    for sig in ("", forged):
        result = fetch_feed(
            "radio",
            get=_server(feed, key, sig=sig),
            keys=[bytes(key.verify_key)],
            state_dir=tmp_path,
            now=NOW,
        )
        assert result.status == "invalid"
        assert result.feed is None
        assert "signed" in result.reason


def test_an_older_feed_served_again_is_refused(key, tmp_path: Path) -> None:
    old = _feed()
    newer = promote(old, "3.3.0-beta.1", "dev", now=NOW)
    keys = [bytes(key.verify_key)]
    assert fetch_feed(
        "radio", get=_server(newer, key), keys=keys, state_dir=tmp_path, now=NOW
    ).usable
    replay = fetch_feed("radio", get=_server(old, key), keys=keys, state_dir=tmp_path, now=NOW)
    assert replay.status == "invalid"
    assert "older" in replay.reason


def test_an_expired_feed_offers_nothing(key, tmp_path: Path) -> None:
    feed = _feed()
    later = NOW + timedelta(days=200)
    result = fetch_feed(
        "radio", get=_server(feed, key), keys=[bytes(key.verify_key)], state_dir=tmp_path, now=later
    )
    assert result.status == "stale"
    assert not result.usable


def test_offline_answers_from_the_verified_cache(key, tmp_path: Path) -> None:
    feed = _feed()
    keys = [bytes(key.verify_key)]
    fetch_feed("radio", get=_server(feed, key), keys=keys, state_dir=tmp_path, now=NOW)

    def unreachable(_url: str) -> bytes:
        raise OSError("no network")

    result = fetch_feed("radio", get=unreachable, keys=keys, state_dir=tmp_path, now=NOW)
    assert result.status == "offline"
    assert result.usable
    (tmp_path / "feed-cache" / "radio.json").write_bytes(b"tampered")
    assert fetch_feed("radio", get=unreachable, keys=keys, state_dir=tmp_path, now=NOW).status == (
        "unreachable"
    )


def test_no_published_feed_hands_back_to_the_old_path(tmp_path: Path) -> None:
    def missing(url: str) -> bytes:
        raise FeedMissing(url)

    legacy = [SimpleNamespace(version="3.0.4", prerelease=False)]
    got = releases_for_check(
        "radio", lambda: legacy, portable=False, get=missing, state_dir=tmp_path
    )
    assert got == legacy


def test_a_feed_that_cannot_be_trusted_never_falls_back(key, tmp_path: Path) -> None:
    with pytest.raises(FeedCheckFailed):
        releases_for_check(
            "radio",
            lambda: [SimpleNamespace(version="9.9.9", prerelease=False)],
            portable=False,
            get=_server(_feed(), key, sig=""),
            state_dir=tmp_path,
            keys=[bytes(key.verify_key)],
        )


def test_a_feed_for_another_app_is_refused(key, tmp_path: Path) -> None:
    result = fetch_feed(
        "cast", get=_server(_feed(), key), keys=[bytes(key.verify_key)], state_dir=tmp_path, now=NOW
    )
    assert result.status == "invalid"


def test_rehearsal_override_changes_only_where_to_look(monkeypatch, key, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_UPDATE_FEED_BASE", "https://community-access.github.io/rehearsal")
    get = _server(_feed(), key)
    fetch_feed("radio", get=get, keys=[bytes(key.verify_key)], state_dir=tmp_path, now=NOW)
    assert get.calls[0] == "https://community-access.github.io/rehearsal/radio.json"


# -- what the flows consume ------------------------------------------------------


def test_offers_carry_the_signed_hash_and_the_right_file(key) -> None:
    feed = _feed()
    installed = {o.version: o for o in offers_from_feed(feed, portable=False)}
    portable = {o.version: o for o in offers_from_feed(feed, portable=True)}
    assert installed["3.2.0"].download_url.endswith(".exe")
    assert portable["3.2.0"].download_url.endswith(".zip")
    assert installed["3.2.0"].download_digest == SHA
    assert installed["3.2.0"].prerelease is False
    assert installed["3.3.0-beta.1"].prerelease is True


def test_the_listing_not_the_spelling_decides_what_a_channel_sees() -> None:
    feed = _feed(dev="3.3.0-dev.20261019.2")
    feed = promote(feed, "3.3.0-dev.20261019.2", "beta", now=NOW)
    offers = offers_from_feed(feed, portable=False)
    promoted = next(o for o in offers if o.version.startswith("3.3.0-dev"))
    assert visible_on(promoted, ChannelState(channel="beta"))
    assert not visible_on(promoted, ChannelState(channel="stable"))
    stable = ChannelState()
    assert choose_offer("3.1.0", offers, stable).target.version == "3.2.0"
    assert choose_offer("3.2.0", offers, ChannelState(channel="beta")).target.version == (
        "3.3.0-beta.1"
    )
    dev_only = next(
        o
        for o in offers_from_feed(_feed(dev="3.4.0-dev.1"), portable=False)
        if o.channels == ("dev",)
    )
    assert visible_on(dev_only, ChannelState(channel="dev"))
    assert not visible_on(dev_only, ChannelState(channel="beta"))
    waiting = ChannelState(channel="dev", pending_return=True, keep_beta_while_waiting=True)
    assert not visible_on(dev_only, waiting)


def test_a_withdrawn_build_is_never_offered() -> None:
    from quill.core.updater.feed_publish import revoke

    feed = revoke(_feed(), "3.3.0-beta.1", reason="bad", now=NOW)
    versions = [o.version for o in offers_from_feed(feed, portable=False)]
    assert "3.3.0-beta.1" not in versions


def test_parse_refuses_a_v1_or_broken_list() -> None:
    from quill.core.updater.feed import FeedError

    with pytest.raises(FeedError):
        parse_feed(b'{"version": "1.0.0"}')
    with pytest.raises(FeedError):
        parse_feed(b"not json")


# -- downloads -------------------------------------------------------------------


class _Response:
    def __init__(self, body: bytes, status: int) -> None:
        self._body = body
        self.status = status

    def read(self, size: int = -1) -> bytes:
        chunk, self._body = self._body[:size], self._body[size:]
        return chunk

    def close(self) -> None:
        return None


def _opener(body: bytes, *, honour_range: bool = True):
    seen: list[int] = []

    def open_range(_url: str, start: int) -> _Response:
        seen.append(start)
        if start and honour_range:
            return _Response(body[start:], 206)
        return _Response(body, 200)

    open_range.seen = seen  # type: ignore[attr-defined]
    return open_range


def test_download_resumes_a_partial_and_verifies(tmp_path: Path) -> None:
    body = b"x" * 200_000
    digest = hashlib.sha256(body).hexdigest()
    dest = tmp_path / "Setup.exe"
    (tmp_path / "Setup.exe.partial").write_bytes(body[:50_000])
    opener = _opener(body)
    got = download_verified(
        "u", dest, sha256=digest, size=len(body), open_range=opener, free_space=lambda _p: 10**12
    )
    assert got.read_bytes() == body
    assert opener.seen == [50_000]
    assert not (tmp_path / "Setup.exe.partial").exists()


def test_download_restarts_when_the_server_ignores_the_range(tmp_path: Path) -> None:
    body = b"y" * 100_000
    dest = tmp_path / "a.zip"
    (tmp_path / "a.zip.partial").write_bytes(b"y" * 10)
    download_verified(
        "u",
        dest,
        sha256=hashlib.sha256(body).hexdigest(),
        size=len(body),
        open_range=_opener(body, honour_range=False),
        free_space=lambda _p: 10**12,
    )
    assert dest.read_bytes() == body


def test_a_mismatch_deletes_the_file(tmp_path: Path) -> None:
    dest = tmp_path / "a.exe"
    with pytest.raises(DownloadVerifyError):
        download_verified(
            "u", dest, sha256=SHA, size=5, open_range=_opener(b"hello"), free_space=lambda _p: 10**9
        )
    assert not dest.exists()
    assert not (tmp_path / "a.exe.partial").exists()


def test_not_enough_space_is_said_plainly(tmp_path: Path) -> None:
    with pytest.raises(NotEnoughSpaceError, match="free space"):
        download_verified(
            "u",
            tmp_path / "a.exe",
            sha256=SHA,
            size=200 * 1024 * 1024,
            open_range=_opener(b""),
            free_space=lambda _p: 100 * 1024 * 1024,
        )


# -- background downloads ----------------------------------------------------------


@pytest.mark.parametrize(
    ("state", "conditions", "download", "reason_word", "may_show"),
    [
        (ChannelState(), Conditions(), False, "", True),
        (ChannelState(channel="beta"), Conditions(), True, "", True),
        (ChannelState(channel="dev"), Conditions(), True, "", True),
        (ChannelState(channel="beta"), Conditions(metered=True), False, "metered", True),
        (ChannelState(channel="beta"), Conditions(quiet=True), False, "Quiet", False),
        (ChannelState(channel="dev"), Conditions(recording=True), False, "recording", False),
        (ChannelState(channel="beta", pending_return=True), Conditions(), False, "", True),
    ],
)
def test_background_gate(state, conditions, download, reason_word, may_show) -> None:
    gate = background_gate(state, conditions)
    assert gate.download is download
    assert reason_word in gate.reason
    assert gate.may_show is may_show


def test_a_live_radio_recording_marker_holds_downloads(tmp_path: Path, monkeypatch) -> None:
    from quill.core.radio.recording_resume import ActiveRecordingMarker, save_marker
    from quill.core.updater import background

    now = datetime.now().astimezone()
    marker = ActiveRecordingMarker(
        station_name="KSPN",
        stream_url="https://example.invalid/s",
        temp_path="t",
        output_path="o",
        started_at=now.isoformat(),
        scheduled_end=(now + timedelta(minutes=30)).isoformat(),
        duration_minutes=30,
        job_id="j1",
    )
    save_marker(tmp_path, marker)
    assert background._radio_recording(tmp_path, now)
    assert not background._radio_recording(tmp_path, now + timedelta(hours=2))
