"""SpotifyWebEngine state machine, driven with a fake WebView (no wx, no SDK)."""

from __future__ import annotations

from quill.ui.spotify.web_player import PlaybackSnapshot, SpotifyWebEngine, parse_snapshot


class FakeView:
    """A stand-in for wx.html2.WebView that only records queued scripts."""

    def __init__(self) -> None:
        self.scripts: list[str] = []

    def RunScriptAsync(self, script: str) -> None:  # noqa: N802 - matches wx API
        self.scripts.append(script)


def _engine(token: str = "tok-123") -> tuple[SpotifyWebEngine, FakeView, dict[str, object]]:
    view = FakeView()
    events: dict[str, object] = {}
    engine = SpotifyWebEngine(
        parent=None,
        token_provider=lambda: token,
        on_ready=lambda device_id: events.__setitem__("ready", device_id),
        on_error=lambda message: events.__setitem__("error", message),
        on_playback=lambda snap: events.__setitem__("playback", snap),
        view=view,
    )
    return engine, view, events


def test_page_ready_provides_token() -> None:
    engine, view, _ = _engine("secret")
    engine.receive_message({"type": "page_ready"})
    assert any("quillSpotifyProvideToken" in s and "secret" in s for s in view.scripts)


def test_missing_token_reports_error() -> None:
    engine, view, events = _engine(token="")
    engine.receive_message({"type": "token_request"})
    assert "error" in events
    assert not view.scripts


def test_device_ready_fires_callback_and_sets_device() -> None:
    engine, _, events = _engine()
    engine.receive_message({"type": "device_ready", "device_id": "dev-9"})
    assert events["ready"] == "dev-9"
    assert engine.device_id == "dev-9"


def test_play_uri_after_ready_queues_play_script() -> None:
    engine, view, _ = _engine()
    engine.receive_message({"type": "device_ready", "device_id": "dev-9"})
    view.scripts.clear()
    engine.play("spotify:episode:abc")
    assert view.scripts == ['window.quillSpotifyPlay("spotify:episode:abc");']


def test_play_uri_before_ready_is_deferred_until_device_ready() -> None:
    engine, view, _ = _engine()
    engine.play("spotify:track:xyz")  # no device yet
    assert view.scripts == []  # nothing queued
    engine.receive_message({"type": "device_ready", "device_id": "dev-1"})
    assert any("quillSpotifyPlay" in s and "xyz" in s for s in view.scripts)


def test_playback_message_updates_snapshot() -> None:
    engine, _, events = _engine()
    engine.receive_message({
        "type": "playback",
        "snapshot": {
            "is_playing": True,
            "position_ms": 12000,
            "duration_ms": 240000,
            "uri": "spotify:track:xyz",
            "name": "A Song",
            "artist": "An Artist",
        },
    })
    assert engine.is_playing() is True
    assert engine.position_ms() == 12000
    assert engine.length_ms() == 240000
    assert engine.snapshot.track_name == "A Song"
    assert isinstance(events["playback"], PlaybackSnapshot)


def test_transport_controls_queue_scripts() -> None:
    engine, view, _ = _engine()
    engine.pause()
    engine.set_volume(55)
    engine.seek(9000)
    joined = " ".join(view.scripts)
    assert "quillSpotifyPause" in joined
    assert "quillSpotifySetVolume(55)" in joined
    assert "quillSpotifySeek(9000)" in joined


def test_error_message_routes_to_callback() -> None:
    engine, _, events = _engine()
    engine.receive_message({"type": "error", "message": "account_error"})
    assert events["error"] == "account_error"


def test_close_is_idempotent_and_stops_scripts() -> None:
    engine, view, _ = _engine()
    engine.close()
    engine.close()  # no raise
    engine.pause()  # closed -> no new scripts
    assert view.scripts == []
    assert engine.is_playing() is False


def test_parse_snapshot_none() -> None:
    assert parse_snapshot(None) is None
    assert parse_snapshot({"is_playing": True}) == PlaybackSnapshot(is_playing=True)
