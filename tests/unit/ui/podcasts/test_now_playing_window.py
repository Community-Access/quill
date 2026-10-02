"""Now Playing (qc.md section 5) and the Notes reader (5c), driven with a fake host.

A real ``wx.App`` and real controls, because the promises are about controls:
the slider's keys seek and speak a time, the playing chapter is marked without
moving the cursor, Tab in the notes lands on a link and says its title, the
Copy Notes button copies in the remembered format.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.ui.podcasts.player_controller import PodcastPlaybackState, PodcastPlayerState

NOTES = (
    "<h2>This week</h2>"
    '<p>We talk to <a href="https://example.com/guest">Jane &amp; Co</a> at 0:40.</p>'
    "<h3>Later</h3><p>Nothing more.</p>"
)


class _Controller:
    def __init__(self) -> None:
        self.state = PodcastPlaybackState(
            PodcastPlayerState.PLAYING, "show", "ep", "Thursday's episode"
        )
        self._position = 30_000
        self._length = 1_800_000
        self.volume_percent = 70
        self.muted = False
        self.seeks: list[int] = []

    def position_ms(self) -> int:
        return self._position

    def length_ms(self) -> int:
        return self._length

    def seek(self, ms: int) -> None:
        self.seeks.append(ms)
        self._position = ms

    def set_volume(self, percent: int) -> None:
        self.volume_percent = percent


def _library() -> SimpleNamespace:
    episode = SimpleNamespace(
        guid="ep", title="Thursday's episode", description=NOTES, audio_url=""
    )
    show = SimpleNamespace(
        title="The Daily",
        is_favorite=False,
        find_episode=lambda guid: episode if guid == "ep" else None,
        tags=None,
        feed_url="https://daily.example/feed",
    )
    return SimpleNamespace(
        find_show=lambda show_id: show if show_id == "show" else None,
        queue=[],
        settings=SimpleNamespace(speed=1.0),
        effective_settings=lambda _show: SimpleNamespace(speed=1.0),
    )


@pytest.fixture
def host(wx_app, tmp_path, monkeypatch):
    from quill.core.podcasts import episode_notes as notes

    monkeypatch.setattr(notes, "episode_notes_path", lambda: tmp_path / "notes.json")
    frame = wx.Frame(None, title="QUILL Cast")
    calls: list[str] = []
    said: list[str] = []
    chapters = [
        SimpleNamespace(title="Introduction", start_ms=0),
        SimpleNamespace(title="The main story", start_ms=20_000),
        SimpleNamespace(title="Credits", start_ms=1_700_000),
    ]
    host = SimpleNamespace(
        frame=frame,
        _wx=wx,
        _windows=None,
        _announce=said.append,
        announcements=said,
        calls=calls,
        _podcast_controller=_Controller(),
        _podcast_library=_library(),
        _podcast_current_chapters=chapters,
        _podcast_history=SimpleNamespace(notes_copy_format="plain", switch_to_now_playing=False),
        _save_podcast_history=lambda: calls.append("save_history"),
        _sleep_timer_controller=SimpleNamespace(
            is_active=False, is_end_of_episode=False, remaining_seconds=0
        ),
        _show_modal_dialog=None,
        _keep_menu_ids=lambda *ids: None,
        podcast_toggle_play_pause=lambda: calls.append("play_pause"),
        podcast_stop=lambda: calls.append("stop"),
        podcast_next_chapter=lambda: calls.append("next_chapter"),
        podcast_previous_chapter=lambda: calls.append("previous_chapter"),
        podcast_mute_toggle=lambda: calls.append("mute"),
        open_sleep_timer_dialog=lambda: calls.append("sleep_dialog"),
        sleep_timer_end_of_episode=lambda: calls.append("sleep_end"),
        extend_sleep_timer_command=lambda: calls.append("sleep_extend"),
        _on_favorite_toggle=lambda: calls.append("favorite"),
        podcast_mark_played_and_next=lambda: calls.append("mark_played"),
        open_podcast_episode_extras=lambda: calls.append("about"),
        _refresh_statusbar=lambda: calls.append("statusbar"),
    )
    yield host
    window = getattr(host, "_now_playing_window", None)
    if window is not None:
        window.destroy()
    frame.Destroy()


@pytest.fixture
def wx_app():
    app = wx.GetApp() or wx.App(False)
    yield app


def _open(host: Any):
    from quill.ui.podcasts.now_playing_window import open_now_playing

    return open_now_playing(host, focus=False)


def test_the_window_loads_the_playing_episode_its_chapters_and_its_notes(host) -> None:
    window = _open(host)

    assert window._podcast.GetLabel() == "The Daily"
    assert window._episode.GetLabel() == "Thursday's episode"
    assert window._time.GetLabel() == "0:30 of 30:00"
    assert window._chapters.GetItemCount() == 3
    assert window._chapters_caption.GetLabel() == "&Chapters (3):"
    assert window._chapters.GetItemText(1, 3) == "playing"  # 30 s is in "The main story"
    assert window._chapters.GetFirstSelected() == -1  # the cursor was not moved
    assert window.notes.document.headings[0].text == "This week"
    assert window.notes.links_btn.GetName() == "Links, 1 in these notes"
    assert window._play.GetLabel() == "Pa&use"
    assert window.frame.GetTitle() == "Now Playing"
    assert host.announcements == []  # nothing announced on open (GATE-13)


def test_the_window_is_made_once_and_hidden_on_close_so_its_number_holds(host) -> None:
    first = _open(host)
    first.frame.Close()
    assert not first.frame.IsShown()
    assert first._tick.IsRunning() is False

    second = _open(host)

    assert second is first
    assert second.frame.IsShown()


def test_the_slider_keys_seek_and_say_the_time(host) -> None:
    window = _open(host)
    window._slider.SetFocus()
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(wx.WXK_RIGHT)

    window._on_slider_key(event)

    assert host._podcast_controller.seeks == [35_000]
    assert host.announcements[-1] == "35 seconds"
    event.SetKeyCode(wx.WXK_PAGEUP)
    window._on_slider_key(event)
    assert host._podcast_controller.seeks[-1] == 65_000
    event.SetKeyCode(wx.WXK_END)
    window._on_slider_key(event)
    assert host._podcast_controller.seeks[-1] == 1_799_000


def test_the_transport_buttons_call_the_hosts_verbs(host) -> None:
    window = _open(host)
    for button, verb in (
        (window._play, "play_pause"),
        (window._stop, "stop"),
        (window._prev_chapter, "previous_chapter"),
        (window._next_chapter, "next_chapter"),
        (window._mute, "mute"),
        (window._sleep_set, "sleep_dialog"),
        (window._sleep_end, "sleep_end"),
        (window._sleep_extend, "sleep_extend"),
        (window._played, "mark_played"),
        (window._about, "about"),
    ):
        host.calls.clear()
        event = wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId())
        button.ProcessEvent(event)
        assert verb in host.calls, verb


def test_forward_and_back_skip_thirty_seconds_and_say_where_you_are(host) -> None:
    window = _open(host)

    window._skip(30_000)
    assert host._podcast_controller.seeks[-1] == 60_000
    assert host.announcements[-1] == "1 minute"
    window._skip(-30_000)
    assert host._podcast_controller.seeks[-1] == 30_000


def test_the_playing_chapter_follows_playback_without_moving_the_cursor(host) -> None:
    window = _open(host)
    window._chapters.Select(0)
    host._podcast_controller._position = 1_750_000

    window.refresh()

    assert window._chapters.GetItemText(2, 3) == "playing"
    assert window._chapters.GetItemText(1, 3) == ""
    assert window._chapters.GetFirstSelected() == 0


def test_enter_on_a_chapter_jumps_there_and_says_it(host) -> None:
    window = _open(host)
    window._chapters.Select(2)

    window._jump_to_chapter()

    assert host._podcast_controller.seeks[-1] == 1_700_000
    assert host.announcements[-1] == "Chapter: Credits"


def test_the_paused_state_relabels_the_button_and_the_mute_toggles_its_label(host) -> None:
    window = _open(host)
    host._podcast_controller.state = PodcastPlaybackState(
        PodcastPlayerState.PAUSED, "show", "ep", "Thursday's episode"
    )
    host._podcast_controller.muted = True

    window.refresh()

    assert window._play.GetLabel() == "Res&ume"
    assert window._mute.GetLabel() == "Un&mute"


def test_nothing_playing_says_so_and_dims_the_episode_buttons(host) -> None:
    host._podcast_controller.state = PodcastPlaybackState(
        PodcastPlayerState.STOPPED, None, None, ""
    )
    window = _open(host)

    assert window._podcast.GetLabel() == "Nothing is playing."
    assert not window._played.IsEnabled()
    assert not window._slider.IsEnabled()
    assert window.notes.field.GetValue() == "This episode has no show notes."


def test_the_timestamp_in_the_notes_seeks_the_episode(host) -> None:
    window = _open(host)
    span = window.notes.document.timestamps[0]
    window.notes.field.SetSelection(span.start, span.end)

    assert window.notes._activate_span() is True
    assert host._podcast_controller.seeks[-1] == 40_000
    assert host.announcements[-1] == "At 40 seconds."


def test_your_note_is_saved_on_blur_and_read_back(host) -> None:
    from quill.core.podcasts import episode_notes as notes

    window = _open(host)
    window._note.SetValue("Second half is the good half.")
    event = wx.FocusEvent(wx.wxEVT_KILL_FOCUS)

    window._on_note_blur(event)

    assert host.announcements[-1] == "Note saved."
    kept = notes.episode_level_note(notes.load_episode_notes(), "show", "ep")
    assert kept is not None and kept.text == "Second half is the good half."
    window._on_note_blur(event)  # unchanged: nothing said
    assert host.announcements[-1] == "Note saved."
    window.refresh(full=True)
    assert window._note.GetValue() == "Second half is the good half."


def test_the_copy_format_chosen_from_the_button_menu_is_remembered(host) -> None:
    window = _open(host)

    window.notes._copy_as("markdown")

    assert host._podcast_history.notes_copy_format == "markdown"
    assert "save_history" in host.calls
    assert host.announcements[-1].startswith("Copied the show notes as markdown")


def test_the_sleep_timer_readout_follows_the_controller(host) -> None:
    window = _open(host)
    host._sleep_timer_controller.is_active = True
    host._sleep_timer_controller.remaining_seconds = 125

    window.refresh()

    assert window._sleep.GetLabel() == "Sleep timer: 2:05 left"
    assert window._sleep_extend.IsEnabled()


def test_the_speed_choice_applies_the_speed_through_the_shared_verb(host, monkeypatch) -> None:
    import quill.ui.podcasts.speed as speed

    applied: list[float] = []
    monkeypatch.setattr(speed, "apply_speed", lambda h, value: applied.append(value))
    monkeypatch.setattr(speed, "current_speed", lambda h: 1.0)
    window = _open(host)
    window._speed.SetSelection(4)  # 1.5x

    window._on_speed()

    assert applied == [1.5]


def test_the_volume_slider_sets_the_volume_and_says_it(host) -> None:
    window = _open(host)
    window._volume.SetValue(40)

    window._on_volume()

    assert host._podcast_controller.volume_percent == 40
    assert host.announcements[-1] == "Volume 40"


def test_the_favorite_button_names_its_object_and_toggles(host) -> None:
    window = _open(host)
    assert window._favorite.GetLabel() == "Add to F&avorites"
    show = host._podcast_library.find_show("show")

    def toggle() -> None:
        show.is_favorite = not show.is_favorite

    host._on_favorite_toggle = toggle
    window._on_favorite()

    assert window._favorite.GetLabel() == "Remove from F&avorites"


# -- the Notes reader on its own ------------------------------------------------------


@pytest.fixture
def reader(wx_app):
    from quill.ui.notes_reader import NotesReader

    frame = wx.Frame(None)
    panel = wx.Panel(frame)
    sizer = wx.BoxSizer(wx.VERTICAL)
    said: list[str] = []
    seeks: list[int] = []
    reader = NotesReader(panel, sizer, announce=said.append, on_seek=seeks.append)
    reader.said = said  # type: ignore[attr-defined]
    reader.seeks = seeks  # type: ignore[attr-defined]
    reader.set_notes(NOTES, title="Thursday's episode", podcast="The Daily")
    yield reader
    frame.Destroy()


def test_tab_moves_between_links_and_timestamps_and_says_what_each_is(reader) -> None:
    assert reader._move_span(backwards=False) is True
    assert reader.said[-1] == "Link, Jane & Co."
    start, end = reader.field.GetSelection()
    assert reader.document.text[start:end] == "Jane & Co"
    assert reader._move_span(backwards=False) is True
    assert reader.said[-1] == "Timestamp, 40 seconds. Enter plays from there."
    assert reader._move_span(backwards=False) is True  # wraps to the first
    assert reader.said[-1] == "Link, Jane & Co."


def test_h_and_shift_h_move_between_headings_and_say_the_level(reader) -> None:
    reader.field.SetInsertionPoint(0)
    reader._move_heading(backwards=False)
    assert reader.said[-1] == "Heading level 3, Later"
    reader._move_heading(backwards=True)
    assert reader.said[-1] == "Heading level 2, This week"
    reader._move_heading(backwards=True)
    assert reader.said[-1] == "No previous heading."


def test_find_counts_the_matches_and_f3_moves_on(reader) -> None:
    reader._find_text = "jane"
    reader._find_at = -1
    reader.find_next(say_count=1)
    assert reader.said[-1] == "1 match. Line 2"
    reader.find_next()
    assert reader.said[-1] == "Wrapped to the top. Line 2"


def test_enter_on_a_timestamp_hands_the_milliseconds_to_the_host(reader) -> None:
    span = reader.document.timestamps[0]
    reader.field.SetSelection(span.start, span.end)
    assert reader._activate_span() is True
    assert reader.seeks == [40_000]


def test_the_links_list_is_the_unique_links_with_their_titles(reader) -> None:
    links = reader.links()
    assert [(link.text, link.url) for link in links] == [("Jane & Co", "https://example.com/guest")]
    assert reader.links_btn.IsEnabled()


def test_empty_notes_disable_the_buttons_and_say_so(reader) -> None:
    reader.set_notes("", title="x")
    assert reader.field.GetValue() == "This episode has no show notes."
    assert not reader.links_btn.IsEnabled()
    assert not reader.copy_btn.IsEnabled()
    assert reader._move_span(backwards=False) is False
    assert reader.said[-1] == "No links or timestamps in these notes."
