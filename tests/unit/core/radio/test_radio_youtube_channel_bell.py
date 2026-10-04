"""Notify Me About New Videos: a baseline first, then one notice per new upload."""

from __future__ import annotations

from quill.core.radio import youtube_channel_alerts as ca

CHANNEL = "https://www.youtube.com/@RickSteves"


def _listing(*ids: str) -> dict:
    return {
        "channel": "Rick Steves' Europe",
        "entries": [{"id": video_id, "title": f"Video {video_id}"} for video_id in ids],
    }


class _YouTube:
    def __init__(self) -> None:
        self.answer = _listing("v3", "v2", "v1")
        self.asked: list[tuple[str, dict]] = []

    def __call__(self, target, options):
        self.asked.append((target, dict(options)))
        return self.answer


def test_off_by_default(tmp_path) -> None:
    assert not ca.AlertStore(tmp_path).is_notifying(CHANNEL)
    assert ca.check_channels(store=ca.AlertStore(tmp_path), fetch=_YouTube()) == ([], [])


def test_first_look_is_a_baseline_then_new_uploads_are_news(tmp_path) -> None:
    store = ca.AlertStore(tmp_path)
    store.set_notifying(CHANNEL, True)
    youtube = _YouTube()
    assert ca.check_channels(store=store, fetch=youtube) == ([], [])
    youtube.answer = _listing("v5", "v4", "v3", "v2", "v1")
    found, failures = ca.check_channels(store=store, fetch=youtube)
    assert failures == []
    assert [v.headline for v in found] == [
        "New on Rick Steves' Europe: Video v4",
        "New on Rick Steves' Europe: Video v5",
    ]
    assert found[0].url == "https://www.youtube.com/watch?v=v4"
    # Nothing is said twice.
    assert ca.check_channels(store=store, fetch=youtube) == ([], [])


def test_only_the_newest_few_are_asked_for(tmp_path) -> None:
    store = ca.AlertStore(tmp_path)
    store.set_notifying(CHANNEL, True)
    youtube = _YouTube()
    ca.check_channels(store=store, fetch=youtube)
    target, options = youtube.asked[0]
    assert target == f"{CHANNEL}/videos"
    assert options == {"extract_flat": "in_playlist", "playlistend": ca.NEWEST}


def test_the_followed_name_wins_over_youtubes(tmp_path) -> None:
    store = ca.AlertStore(tmp_path)
    store.set_notifying(CHANNEL, True)
    youtube = _YouTube()
    ca.check_channels(store=store, fetch=youtube)
    youtube.answer = _listing("v9", "v3")
    found, _ = ca.check_channels(store=store, fetch=youtube, names={CHANNEL: "Rick"})
    assert found[0].headline == "New on Rick: Video v9"


def test_the_schedule_is_respected_with_a_fake_clock(tmp_path) -> None:
    store = ca.AlertStore(tmp_path)
    store.set_notifying(CHANNEL, True)
    youtube = _YouTube()
    ca.check_channels(store=store, fetch=youtube, now=1000.0, every_minutes=60)
    ca.check_channels(store=store, fetch=youtube, now=1000.0 + 10 * 60, every_minutes=60)
    assert len(youtube.asked) == 1  # ten minutes later: not due
    ca.check_channels(store=store, fetch=youtube, now=1000.0 + 61 * 60, every_minutes=60)
    assert len(youtube.asked) == 2


def test_turning_it_off_stops_the_checks_and_on_again_restarts_the_baseline(tmp_path) -> None:
    store = ca.AlertStore(tmp_path)
    store.set_notifying(CHANNEL, True)
    youtube = _YouTube()
    ca.check_channels(store=store, fetch=youtube)
    store.set_notifying(CHANNEL, False)
    youtube.answer = _listing("v8", "v3")
    assert ca.check_channels(store=store, fetch=youtube) == ([], [])
    store.set_notifying(CHANNEL, True)
    assert ca.check_channels(store=store, fetch=youtube) == ([], [])  # baseline again


def test_a_channel_that_cannot_be_read_is_reported_and_the_rest_checked(tmp_path) -> None:
    store = ca.AlertStore(tmp_path)
    store.set_notifying(CHANNEL, True)
    store.set_notifying("https://www.youtube.com/@Other", True)

    def fetch(target, options):
        if "Other" in target:
            raise RuntimeError("HTTP Error 404: Not Found -- does not exist")
        return _listing("v1")

    found, failures = ca.check_channels(store=store, fetch=fetch)
    assert found == []
    assert failures[0][0] == "https://www.youtube.com/@Other"


def test_safe_mode_asks_nothing(tmp_path) -> None:
    store = ca.AlertStore(tmp_path)
    store.set_notifying(CHANNEL, True)
    youtube = _YouTube()
    assert ca.check_channels(store=store, fetch=youtube, safe_mode=True) == ([], [])
    assert youtube.asked == []


def test_forget_drops_the_bell(tmp_path) -> None:
    store = ca.AlertStore(tmp_path)
    store.set_notifying(CHANNEL, True)
    store.forget(CHANNEL)
    assert store.notifying() == []


def test_notices_carry_a_playable_target_and_one_toast(monkeypatch, quill_data_dir) -> None:
    from quill.core import notification_targets
    from quill.ui.radio import youtube_channel_alerts_ui as ui

    recorded: list[dict] = []
    toasts: list[tuple] = []
    monkeypatch.setattr(
        "quill.core.notifications.add_notice", lambda **kw: recorded.append(kw) or []
    )
    monkeypatch.setattr("quill.ui.toast.show_toast", lambda h, b: toasts.append((h, b)))
    monkeypatch.setattr("quill.ui.quiet_hours_ui.held_back", lambda _k: False)
    monkeypatch.setattr("quill.ui.companion_cues.post_cue", lambda _e: None)
    videos = [
        ca.NewVideo("Rick", "One", "https://www.youtube.com/watch?v=aaaaaaaaaaa"),
        ca.NewVideo("Rick", "Two", "https://www.youtube.com/watch?v=bbbbbbbbbbb"),
    ]
    assert ui.raise_notices(videos) == 2
    assert recorded[0]["title"] == "New on Rick: One"
    kind, url = notification_targets.parse(recorded[0]["target"])
    assert kind == notification_targets.KIND_STREAM and url.endswith("aaaaaaaaaaa")
    assert toasts == [("2 new videos", "Rick")]


def test_opening_a_new_video_notice_plays_it() -> None:
    from types import SimpleNamespace

    from quill.ui.radio import youtube_channel_alerts_ui as ui

    played: list = []
    host = SimpleNamespace(_radio_controller=SimpleNamespace(play_station=played.append))
    assert ui.open_stream_notice(host, "https://www.youtube.com/watch?v=aaaaaaaaaaa")
    assert played[0].stream_url.endswith("aaaaaaaaaaa")
    assert not ui.open_stream_notice(host, "http://example.invalid/stream")
