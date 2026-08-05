"""Tests for voice-intent dispatch (quill.ui.media.voice_control)."""

from __future__ import annotations

from quill.core.media.voice import VoiceIntent
from quill.ui.media.voice_control import apply_voice_intent


class FakePlayer:
    def __init__(self, playhead: int = 60_000, length: int = 600_000) -> None:
        self._playhead = playhead
        self._length = length
        self.calls: list[tuple[str, object]] = []
        self._playing = False

    def play(self) -> None:
        self._playing = True
        self.calls.append(("play", None))

    def pause(self) -> None:
        self._playing = False
        self.calls.append(("pause", None))

    def stop(self) -> None:
        self._playing = False
        self.calls.append(("stop", None))

    def toggle(self) -> None:
        self._playing = not self._playing
        self.calls.append(("toggle", None))

    def is_playing(self) -> bool:
        return self._playing

    def playhead_ms(self) -> int:
        return self._playhead

    def length_ms(self) -> int:
        return self._length

    def seek_to(self, ms: int) -> None:
        self._playhead = ms
        self.calls.append(("seek_to", ms))

    def toggle_mute(self) -> None:
        self.calls.append(("toggle_mute", None))


class FakeHost:
    def __init__(self, player: FakePlayer | None = None) -> None:
        self._player = player if player is not None else FakePlayer()
        self.hooks: list[tuple[str, object]] = []

    def voice_next_chapter(self) -> None:
        self.hooks.append(("next", None))

    def voice_prev_chapter(self) -> None:
        self.hooks.append(("prev", None))

    def voice_add_bookmark(self) -> None:
        self.hooks.append(("bookmark", None))

    def voice_where_am_i(self) -> None:
        self.hooks.append(("where", None))

    def voice_summarize(self) -> None:
        self.hooks.append(("summarize", None))

    def voice_recap(self) -> None:
        self.hooks.append(("recap", None))

    def voice_set_sleep(self, minutes: int) -> None:
        self.hooks.append(("sleep", minutes))

    def voice_sleep_eoc(self) -> None:
        self.hooks.append(("sleep_eoc", None))


def test_play_pause_stop() -> None:
    host = FakeHost()
    assert apply_voice_intent(host, VoiceIntent("play")) == "Playing"
    assert apply_voice_intent(host, VoiceIntent("pause")) == "Paused"
    assert apply_voice_intent(host, VoiceIntent("stop")) == "Stopped"
    assert [c[0] for c in host._player.calls] == ["play", "pause", "stop"]


def test_toggle_reflects_state() -> None:
    host = FakeHost()
    assert apply_voice_intent(host, VoiceIntent("toggle")) == "Playing"
    assert apply_voice_intent(host, VoiceIntent("toggle")) == "Paused"


def test_skip_clamps_to_zero() -> None:
    host = FakeHost(FakePlayer(playhead=10_000, length=600_000))
    apply_voice_intent(host, VoiceIntent("skip", -30_000))
    assert host._player.calls[-1] == ("seek_to", 0)


def test_skip_clamps_to_length() -> None:
    host = FakeHost(FakePlayer(playhead=590_000, length=600_000))
    apply_voice_intent(host, VoiceIntent("skip", 30_000))
    assert host._player.calls[-1] == ("seek_to", 600_000)


def test_seek_absolute() -> None:
    host = FakeHost()
    result = apply_voice_intent(host, VoiceIntent("seek", 90_000))
    assert host._player.calls[-1] == ("seek_to", 90_000)
    assert "1:30" in result


def test_hooks_dispatched() -> None:
    host = FakeHost()
    assert apply_voice_intent(host, VoiceIntent("next_chapter")) == "Next chapter"
    assert apply_voice_intent(host, VoiceIntent("bookmark")) == "Bookmark added"
    assert apply_voice_intent(host, VoiceIntent("where_am_i")) == ""
    assert apply_voice_intent(host, VoiceIntent("sleep", 20)) == "Sleep in 20 minutes"
    assert apply_voice_intent(host, VoiceIntent("sleep", 0)) == "Sleep timer off"
    assert apply_voice_intent(host, VoiceIntent("sleep_eoc")) == "Sleep at end of chapter"
    assert [h[0] for h in host.hooks] == [
        "next",
        "bookmark",
        "where",
        "sleep",
        "sleep",
        "sleep_eoc",
    ]


def test_missing_hook_is_graceful() -> None:
    class Bare:
        _player = FakePlayer()

    result = apply_voice_intent(Bare(), VoiceIntent("summarize"))
    assert "isn't available" in result


def test_speed_and_volume_defer_to_ui() -> None:
    host = FakeHost()
    assert "on-screen control" in apply_voice_intent(host, VoiceIntent("faster"))
    assert "on-screen control" in apply_voice_intent(host, VoiceIntent("volume_up"))


def test_none_intent() -> None:
    assert "didn't catch" in apply_voice_intent(FakeHost(), None)
