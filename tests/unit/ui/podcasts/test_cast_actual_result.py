"""The actual result, once, in Quill Cast (FUX-04, Cast PRD 23.33).

"A save, a change of speed or sound, a download or an import ends by saying
what is now true, in words the listener can check ... It never says 'saved'
while the old value goes on playing."

Each test sets up a state, does the thing, and checks the one sentence said
matches the state it left: the speed the player is really at, the folder a
file went to, and a restore that finished only partly.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


class _Controller:
    """The player, as far as a speed save can see it: what is playing, at what rate."""

    def __init__(self, show_id: str = "", rate: float = 1.0) -> None:
        self.state = SimpleNamespace(
            show_id=show_id or None, episode_guid="e1" if show_id else None
        )
        self.rate = rate
        self.rates: list[float] = []

    def set_rate(self, rate: float) -> None:
        self.rates.append(rate)
        self.rate = rate


def _library(*, local: bool = False) -> tuple[PodcastLibrary, PodcastShow]:
    library = PodcastLibrary()
    show = PodcastShow(id="daily", title="The Daily", feed_url="https://example.invalid/d")
    show.is_local = local
    show.episodes.append(
        PodcastEpisode(guid="e1", title="One", audio_url="https://example.invalid/1.mp3")
    )
    library.add_show(show)
    return library, show


def _manager(library: PodcastLibrary, controller: _Controller) -> Any:
    """The Podcast Manager's half of Change Speed: its library, its player, its voice."""
    said: list[str] = []
    return SimpleNamespace(
        _library=library,
        _controller=controller,
        _announce=said.append,
        _on_library_changed=lambda: None,
        dialog=None,
        said=said,
    )


def _change_speed(monkeypatch: pytest.MonkeyPatch, host: Any, show: PodcastShow, speed: float):
    from quill.ui.podcasts import single_setting_actions

    monkeypatch.setattr(single_setting_actions, "_open", lambda *_a, **_k: speed)
    single_setting_actions.edit_playback_speed(host, show)


def test_a_speed_the_player_took_is_said_once_and_plainly(monkeypatch) -> None:
    library, show = _library()
    host = _manager(library, _Controller("daily", rate=1.5))
    _change_speed(monkeypatch, host, show, 1.5)
    assert host.said == ["This podcast plays at 1.5 times speed."]


def test_chris_a_saved_speed_the_episode_did_not_take_is_not_called_done(monkeypatch) -> None:
    """The 2026-11-19 report: the old speed went on playing under a "saved"."""
    library, show = _library()
    # A scan holds the player at 1x; the save could not push the new speed.
    host = _manager(library, _Controller("daily", rate=1.0))
    _change_speed(monkeypatch, host, show, 1.5)
    assert host.said == ["This podcast plays at 1.5 times speed. The episode playing stays at 1x."]


def test_another_podcast_playing_is_not_reported_on(monkeypatch) -> None:
    library, show = _library()
    other = PodcastShow(id="zebra", title="Zebra", feed_url="https://example.invalid/z")
    library.add_show(other)
    host = _manager(library, _Controller("zebra", rate=1.0))
    _change_speed(monkeypatch, host, show, 1.5)
    assert host.said == ["This podcast plays at 1.5 times speed."]


def test_nothing_playing_claims_nothing_about_playback() -> None:
    from quill.ui.podcasts.speed import speed_not_in_force

    library, show = _library()
    host = SimpleNamespace(_podcast_library=library, _podcast_controller=_Controller())
    assert speed_not_in_force(host, 1.5, show) is None


def test_a_shared_default_does_not_report_on_a_show_with_its_own_speed() -> None:
    from quill.ui.podcasts.speed import speed_not_in_force

    library, show = _library()
    library.apply_show_override(show, speed=1.2)
    library.settings.speed = 1.5
    host = SimpleNamespace(_podcast_library=library, _podcast_controller=_Controller("daily", 1.2))
    assert speed_not_in_force(host, 1.5) is None, "the default was never meant for this show"


def test_the_player_reports_the_rate_it_was_last_set_to(wx_session_app) -> None:
    """``rate`` kept the start-of-episode speed, so every check of it read the old one."""
    import wx

    from quill.ui.podcasts.player_controller import PodcastPlayerController

    frame = wx.Frame(None)
    try:
        controller = PodcastPlayerController(frame)
        controller._engine = SimpleNamespace(set_rate=lambda _rate: None)
        controller.set_rate(1.75)
        assert controller.rate == 1.75
    finally:
        frame.Destroy()


def test_a_restore_that_could_not_refresh_the_view_is_said_not_only_shown(monkeypatch) -> None:
    from quill.ui.podcasts import backup_ui

    said: list[str] = []
    status: list[str] = []

    def reload() -> None:
        raise RuntimeError("tree gone")

    frame = SimpleNamespace(
        _set_status=status.append, _announce=said.append, _reload_library_tree=reload
    )
    from quill.core.podcasts import history, subscriptions

    monkeypatch.setattr(subscriptions, "load_library", lambda _d: object())
    monkeypatch.setattr(history, "load_history", lambda _d: object())
    backup_ui._apply_restore(frame, SimpleNamespace(summary=lambda: "Restored 3 podcasts."))
    assert len(said) == 1 and said == status
    assert said[0].startswith("Restored, but could not refresh the view")


def test_a_restore_that_reloaded_says_so_once(monkeypatch) -> None:
    """The reload step named a module that does not exist, so it raised and said nothing."""
    from quill.core.podcasts import history, subscriptions
    from quill.ui.podcasts import backup_ui

    said: list[str] = []
    library = object()
    frame = SimpleNamespace(
        _set_status=lambda _m: None, _announce=said.append, _reload_library_tree=lambda: None
    )
    monkeypatch.setattr(subscriptions, "load_library", lambda _d: library)
    monkeypatch.setattr(history, "load_history", lambda _d: object())
    backup_ui._apply_restore(frame, SimpleNamespace(summary=lambda: "Restored 3 podcasts."))
    assert frame._podcast_library is library
    assert said == ["Restored 3 podcasts. Your podcasts are back."]


def test_a_saved_transcript_says_its_folder(tmp_path: Path) -> None:
    from quill.ui.podcasts.transcript_actions import _write

    said: list[str] = []
    target = tmp_path / "episode.txt"
    _write(SimpleNamespace(_announce=said.append), str(target), "words")
    assert target.read_text(encoding="utf-8") == "words"
    assert said == [f"Transcript saved to episode.txt in {tmp_path.name}."]
