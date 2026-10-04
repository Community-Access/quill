"""qc.md section 18 in the real QUILL Cast window: the listening keys."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.machine_global


@pytest.fixture
def cast(quill_data_dir: Path):
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.models_episode import PodcastEpisode
    from quill.core.podcasts.subscriptions import PodcastLibrary, save_library

    library = PodcastLibrary()
    for index in (1, 2):
        show = PodcastShow(
            id=f"s{index}", title=f"Show {index}", feed_url=f"http://x.invalid/{index}"
        )
        for ep in (1, 2):
            show.episodes.append(
                PodcastEpisode(
                    guid=f"s{index}e{ep}",
                    title=f"Episode {ep} of {index}",
                    audio_url=f"http://x.invalid/{index}/{ep}.mp3",
                    published=f"2026-09-{ep:02d}T06:00:00+00:00",
                )
            )
        library.add_show(show)
    save_library(quill_data_dir, library)
    app = wx.App()
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = PodcastsAppFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    try:
        yield frame
    finally:
        set_transition_announcement_policy(None)
        try:
            frame.frame.Destroy()
        except Exception:  # noqa: BLE001
            pass
        del app


def _playing(frame, show_id: str, guid: str, position: int, length: int, rate: float = 1.0):
    from quill.ui.podcasts.player_controller import PodcastPlayerState

    state = SimpleNamespace(
        state=PodcastPlayerState.PLAYING, show_id=show_id, episode_guid=guid, title="x"
    )
    real = frame._podcast_controller
    fake = SimpleNamespace(
        state=state,
        position_ms=lambda: position,
        length_ms=lambda: length,
        rate=rate,
    )
    frame._podcast_controller = fake
    return real


def test_ctrl_shift_t_says_time_left(cast) -> None:
    labels = [
        item.GetItemLabel()
        for index in range(cast.frame.GetMenuBar().GetMenuCount())
        for item in cast.frame.GetMenuBar().GetMenu(index).GetMenuItems()
    ]
    assert "Time Remaining\tCtrl+Shift+T" in labels
    cast.say_time_remaining()
    assert cast.said[-1] == "Nothing is playing."
    real = _playing(cast, "s1", "s1e1", 60_000, 600_000)
    try:
        cast.say_time_remaining()
    finally:
        cast._podcast_controller = real
    assert cast.said[-1] == "1:00 of 10:00, 9 minutes left."


def test_up_next_is_said_once_before_the_end(cast, monkeypatch) -> None:
    from quill.core.podcasts.models import QueueItem

    library = cast._podcast_library
    library.queue = [QueueItem("s1", "s1e1", ""), QueueItem("s2", "s2e2", "")]
    spoken: list[str] = []
    monkeypatch.setattr(
        "quill.ui.quiet_hours_ui.speak_background", lambda _h, m, **_k: spoken.append(m)
    )
    real = _playing(cast, "s1", "s1e1", 595_000, 600_000)
    try:
        cast._maybe_say_up_next()
        cast._maybe_say_up_next()
    finally:
        cast._podcast_controller = real
    assert spoken == ["Next: Episode 2 of 2 from Show 2."]


def test_up_next_can_be_switched_off(cast, monkeypatch) -> None:
    from quill.core.podcasts.models import QueueItem

    cast._podcast_library.queue = [QueueItem("s1", "s1e1", ""), QueueItem("s2", "s2e2", "")]
    cast._podcast_history.announce_up_next = False
    spoken: list[str] = []
    monkeypatch.setattr(
        "quill.ui.quiet_hours_ui.speak_background", lambda _h, m, **_k: spoken.append(m)
    )
    real = _playing(cast, "s1", "s1e1", 595_000, 600_000)
    try:
        cast._maybe_say_up_next()
    finally:
        cast._podcast_controller = real
    assert spoken == []


def test_shift_space_plays_this_next_and_ctrl_home_goes_home(cast) -> None:
    cast.show_place("new_episodes", focus=True)
    pair = cast._selected_episode()
    assert pair is not None
    cast.play_this_next()
    assert cast._podcast_library.queue[0].episode_guid == pair[1].guid
    assert cast.said[-1].endswith("plays next, first in the Play Queue.")
    cast.go_home()
    assert cast._current_place in ("podcasts", "inbox", "continue_listening")


def test_ctrl_n_fills_in_the_address_on_the_clipboard(cast, monkeypatch) -> None:
    import quill.ui.podcasts.add_podcast_dialog as add_dialog

    seen: list[str] = []
    monkeypatch.setattr(
        add_dialog.AddPodcastWindow, "prefill_address", lambda self, a: seen.append(a)
    )
    monkeypatch.setattr(
        type(cast), "_clipboard_feed_address", lambda self: "https://feeds.example/rss"
    )
    cast._podcast_open_add_dialog()
    assert seen == ["https://feeds.example/rss"]


def test_the_clipboard_check_takes_only_a_single_web_address(cast, monkeypatch) -> None:
    for text, wanted in (
        ("https://feeds.example/rss", "https://feeds.example/rss"),
        ("hello world", ""),
        ("https://a.example\nhttps://b.example", ""),
        ("ftp://x", ""),
    ):
        monkeypatch.setattr(
            "quill.ui.clipboard_retry.read_clipboard_text", lambda *_a, t=text, **_k: t
        )
        assert cast._clipboard_feed_address() == wanted


def test_global_hotkeys_offer_now_playing_and_only_what_cast_has(cast) -> None:
    offered = {command for command, _label, _needs in cast._global_hotkey_safe_commands()}
    assert {"podcasts.now_playing", "podcasts.time_remaining", "podcasts.play_pause"} <= offered
    assert "radio.play_pause" not in offered
    assert "tools.sticky_note_capture" not in offered


def test_bookmarks_for_one_episode_with_a_note(cast, monkeypatch) -> None:
    from quill.core import bookmark_anchors
    from quill.ui.podcasts import extras_command

    class _Entry:
        def __init__(self, *_a, **_k) -> None: ...
        def __enter__(self):
            return self

        def __exit__(self, *_a) -> None: ...
        def ShowModal(self) -> int:
            return wx.ID_OK

        def GetValue(self) -> str:
            return "the book the guest recommends"

    monkeypatch.setattr(wx, "TextEntryDialog", _Entry)
    anchor = bookmark_anchors.for_episode("s1", "s1e1")
    monkeypatch.setattr(cast, "_bookmark_target", lambda: (anchor, 754_000, "Ep"))
    cast.bookmark_with_note()
    marks = cast._bookmark_store().list(anchor)
    assert [m.note for m in marks] == ["the book the guest recommends"]
    show = cast._podcast_library.find_show("s1")
    section = extras_command._bookmark_section(cast, show, show.find_episode("s1e1"))
    assert section is not None and section.rows[0].label.endswith("the book the guest recommends")
    assert section.rows[0].target == "754000"
    shown: list[str] = []
    monkeypatch.setattr(
        "quill.ui.bookmarks_dialog.show_bookmarks", lambda _h, store, anchor: shown.append(anchor)
    )
    real = _playing(cast, "s1", "s1e1", 1, 10)
    try:
        cast.open_episode_bookmarks()
    finally:
        cast._podcast_controller = real
    assert shown == [anchor]
