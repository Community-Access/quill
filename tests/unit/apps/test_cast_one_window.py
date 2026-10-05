"""The one window, driven as a listener drives it (qc.md Phase 2).

A real ``PodcastsAppFrame`` over an isolated data folder with a small library,
so every place can be shown, every selection helper read, Find flattened and
restored, the Preferences window and the Places chooser built. Marked
``machine_global`` because the frame registers global hotkeys and touches the
clipboard-adjacent speech bridges; one worker at a time.
"""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

#: Serialized onto one worker: building the real frame registers system-wide
#: hotkeys and starts the screen-reader bridges, which race between workers.
pytestmark = pytest.mark.machine_global


def _rows(frame) -> list[str]:
    box = frame._places.box
    return [box.GetString(i) for i in range(box.GetCount())]


@pytest.fixture
def cast_frame(quill_data_dir: Path):
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.models_episode import PodcastEpisode
    from quill.core.podcasts.subscriptions import PodcastLibrary, save_library

    library = PodcastLibrary()
    for index in range(1, 4):
        show = PodcastShow(
            id=f"s{index}", title=f"Show {index}", feed_url=f"http://x.invalid/{index}"
        )
        show.is_favorite = index == 1
        show.route_to_inbox = True
        for ep in range(1, 4):
            show.episodes.append(
                PodcastEpisode(
                    guid=f"s{index}e{ep}",
                    title=f"Episode {ep} of {index}",
                    audio_url=f"http://x.invalid/{index}/{ep}.mp3",
                    published=f"2026-09-{ep:02d}T06:00:00+00:00",
                    duration_seconds=600 * ep,
                    played=ep == 3,
                    position_ms=30_000 if ep == 2 else 0,
                )
            )
        library.add_show(show)
    save_library(quill_data_dir, library)
    app = wx.App()
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = PodcastsAppFrame()
    try:
        yield frame
    finally:
        set_transition_announcement_policy(None)
        try:
            frame.frame.Destroy()
        except Exception:  # noqa: BLE001
            pass
        del app


def test_every_place_shows_names_itself_and_counts(cast_frame) -> None:
    from quill.core.podcasts import places as places_model

    frame = cast_frame
    for place in places_model.PLACES:
        assert frame.show_place(place.id, focus=False), place.id
        assert frame._current_place == place.id
        heading = frame._content.heading.GetLabel()
        assert heading.startswith(places_model.label(frame._podcast_library, place.id)), heading
    # the counts the rows carry
    assert "Inbox (6)" in [
        frame._places.box.GetString(i) for i in range(frame._places.box.GetCount())
    ]
    assert frame._content.showing == frame._content.TREE


def test_the_selection_contract_reads_whichever_pane_is_up(cast_frame) -> None:
    frame = cast_frame
    frame.show_place("inbox", focus=False)
    assert frame._content.showing == frame._content.LIST
    selected = frame._selected_tree_data()
    assert selected is not None and selected[0] == "episode"
    pair = frame._selected_episode()
    assert pair is not None and pair[1].guid.startswith("s")
    assert frame._winamp_rows() and frame._winamp_selected_index() == 0
    frame.show_place("favorites", focus=False)
    selected = frame._selected_tree_data()
    assert selected == ("show", "s1")
    assert frame._selected_show().title == "Show 1"
    frame.show_place("podcasts", focus=False)
    selected = frame._selected_tree_data()
    assert selected is not None and selected[0] in ("show", "folder")


def test_favorites_enter_opens_the_podcast_in_place_and_backspace_returns(cast_frame) -> None:
    frame = cast_frame
    frame.show_place("favorites", focus=False)
    frame._activate_content_row(("show", "s1"))
    assert frame._place_opened_show_id == "s1"
    assert frame._content.heading.GetLabel().startswith("Show 1")
    assert len(frame._current_episodes) == 3
    assert frame._back_from_show_in_place() is True
    assert frame._place_opened_show_id == ""
    assert frame._selected_tree_data() == ("show", "s1")


def test_delete_removes_from_this_place_and_never_the_episode(cast_frame) -> None:
    frame = cast_frame
    frame.show_place("inbox", focus=False)
    before = len(frame._current_episodes)
    frame._remove_from_place(frame._selected_tree_data())
    assert len(frame._current_episodes) == before - 1
    assert sum(len(s.episodes) for s in frame._podcast_library.shows) == 9
    frame.show_place("favorites", focus=False)
    frame._remove_from_place(("show", "s1"))
    assert frame._podcast_library.find_show("s1").is_favorite is False
    assert frame._podcast_library.find_show("s1") is not None


def test_space_queues_and_the_queue_place_lists_it(cast_frame) -> None:
    frame = cast_frame
    frame.show_place("new_episodes", focus=False)
    frame._queue_selected_episode()
    assert len(frame._podcast_library.queue) == 1
    frame.show_place("queue", focus=False)
    assert len(frame._current_episodes) == 1


def test_the_places_list_is_the_listeners(cast_frame) -> None:
    frame = cast_frame
    frame.show_place("inbox", focus=False)
    frame._move_place("inbox", 1)
    rows = _rows(frame)
    assert rows[1].startswith("Inbox")
    assert frame._podcast_library.settings.places_layout
    frame._on_place_hide("downloads")
    assert "downloads" in frame._places_layout().hidden
    assert not any(
        row.startswith("Downloads")
        for row in [frame._places.box.GetString(i) for i in range(frame._places.box.GetCount())]
    )
    frame._on_place_show("downloads")
    assert "downloads" not in frame._places_layout().hidden


def test_find_flattens_the_pane_and_escape_restores_the_place(cast_frame) -> None:
    frame = cast_frame
    frame.show_place("inbox", focus=False)
    frame._find_box.ChangeValue("Show 2")
    frame._run_library_find()
    assert frame._content.showing == frame._content.TREE
    assert frame._content.heading.GetLabel() == "Matches"
    assert frame._library_find_active()
    frame._find_box.ChangeValue("")
    frame._end_library_find(announce=False)
    assert frame._current_place == "inbox"
    assert frame._content.showing == frame._content.LIST


def test_the_doors_of_the_old_windows_lead_to_places(cast_frame) -> None:
    frame = cast_frame
    frame.open_podcast_manager()
    assert frame._current_place == "podcasts"
    frame._open_play_queue()
    assert frame._current_place == "queue"
    frame.open_podcast_downloads()
    assert frame._current_place == "downloads"
    frame.open_continue_listening()
    assert frame._current_place == "continue_listening"
    frame.open_cast_notifications()
    assert frame._current_place == "notifications"


def test_the_menu_bar_has_the_places_and_no_manager(cast_frame) -> None:
    bar = cast_frame.frame.GetMenuBar()
    labels: list[str] = []

    def walk(menu) -> None:
        for item in menu.GetMenuItems():
            labels.append(item.GetItemLabelText())
            if item.GetSubMenu() is not None:
                walk(item.GetSubMenu())

    for index in range(bar.GetMenuCount()):
        walk(bar.GetMenu(index))
    assert "Open Podcast Manager..." not in labels
    assert "Podcast Settings..." not in labels
    assert "Skip Settings..." not in labels
    wanted_rows = (
        "Inbox",
        "New Episodes",
        "Continue Listening",
        "Favorites",
        "Play Queue",
        "Downloads",
        "Notifications",
        "Podcasts",
        "Places...",
        "Show",
        "Sort Episodes",
        "Settings for This Podcast...",
        "Refresh All Now",
    )
    for wanted in wanted_rows:
        assert wanted in labels, wanted


def test_a_feature_switched_off_is_absent(cast_frame) -> None:
    frame = cast_frame
    frame._cast_app_features().set_enabled("queue", False)
    frame._build_menu_bar()
    frame._rebuild_places()
    rows = _rows(frame)
    assert not any(row.startswith("Play Queue") for row in rows)
    probe = frame._cast_command_unavailable_reason
    assert probe("podcasts.open_queue") == "off in Customize Features"
    assert probe("podcasts.play_pause") == ""
    assert frame.commands.unavailable_reason("podcasts.open_queue") == "off in Customize Features"
    frame._cast_app_features().set_enabled("queue", True)


def test_preferences_and_the_places_chooser_build(cast_frame) -> None:
    from quill.apps.podcasts_preferences import app_rows
    from quill.ui.podcasts.places_chooser import PlacesChooser
    from quill.ui.podcasts.preferences_window import CastPreferencesWindow

    frame = cast_frame
    window = CastPreferencesWindow(
        frame.frame,
        library=frame._podcast_library,
        history=frame._podcast_history,
        app_rows=app_rows(frame),
        announce=lambda _m: None,
        summary=lambda: "summary",
    )
    for index in range(window._section.GetCount()):
        window._section.SetSelection(index)
        window._on_section()
        assert window._built or index in (4,), (
            index
        )  # every section has rows (Chapters may be defs only)
    window.dialog.Destroy()
    chooser = PlacesChooser(
        frame.frame,
        layout=frame._places_layout(),
        label_for=lambda place_id: place_id,
        enabled=frame._cast_area_enabled,
        announce=lambda _m: None,
    )
    assert chooser._list.GetCount() == 11
    chooser.dialog.Destroy()


def test_cast_never_takes_ctrl_alt_shift_q_system_wide(cast_frame) -> None:
    """qc.md C2-01: Ctrl+Alt+Shift+Q is QUILL's show/hide key. Cast must not
    claim it as a second show/hide while it runs, even when Windows refuses
    Cast's own chord."""
    from quill.apps.podcasts_routes import CAST_TRAY_HOTKEY

    assert cast_frame._own_tray_hotkey == CAST_TRAY_HOTKEY
    cast_frame._tray_hotkey_registered = False  # as if Windows refused it
    assert "Ctrl+Alt+Shift+Q" not in cast_frame._global_hotkey_bindings().values()


def test_mark_as_played_and_next_shows_its_own_key(cast_frame) -> None:
    """It was Ctrl+Alt+Shift+Q, QUILL's show/hide key, and never fired while
    QUILL ran. It now follows Next in Queue's key, through the app keymap."""
    labels = []
    bar = cast_frame.frame.GetMenuBar()
    for index in range(bar.GetMenuCount()):
        for item in bar.GetMenu(index).GetMenuItems():
            if item.GetSubMenu() is not None:
                labels += [sub.GetItemLabel() for sub in item.GetSubMenu().GetMenuItems()]
    assert "Mark as Played and Ne&xt\tCtrl+Alt+Shift+Down" in labels


def test_player_information_and_carry_my_place_have_menu_rows(cast_frame) -> None:
    """qc.md C2-03: both were reachable only through the Command Palette."""
    labels = []
    bar = cast_frame.frame.GetMenuBar()
    for index in range(bar.GetMenuCount()):
        labels += [item.GetItemLabel() for item in bar.GetMenu(index).GetMenuItems()]
    assert any(label.startswith("Player Information...\tCtrl+I") for label in labels)
    assert any("Carry My Place Between Mac&hines..." in label for label in labels)


def test_delete_lands_on_the_row_that_moved_into_its_place(cast_frame) -> None:
    """qc.md F-10: after a row leaves, the cursor is on its neighbour, not the top."""
    frame = cast_frame
    frame.show_place("inbox", focus=False)
    frame._select_list_row(2)
    assert frame._episodes.GetFirstSelected() == 2, frame._list_rows
    following = frame._list_rows[3]
    removed = frame._selected_tree_data()
    frame._remove_from_place(removed)
    assert removed not in frame._list_rows, (removed, frame._list_rows)
    assert frame._episodes.GetFirstSelected() == 2
    assert frame._list_rows[2] == following


def test_dismissing_from_the_inbox_deletes_the_download_when_done_means_deleted(
    cast_frame, tmp_path
) -> None:
    """Earshot R4: with Delete downloads when done on, Delete in the Inbox frees the file."""
    frame = cast_frame
    frame._podcast_library.settings.delete_after_play = True
    frame.show_place("inbox", focus=False)
    pair = frame._selected_episode()
    assert pair is not None
    _show, episode = pair
    copy = tmp_path / "episode.mp3"
    copy.write_bytes(b"audio")
    episode.downloaded_path = str(copy)
    frame._remove_from_place(frame._selected_tree_data())
    assert episode.downloaded_path == ""
    assert not copy.exists()


def test_the_palette_says_casts_menu_names_not_quills(cast_frame) -> None:
    """The shared mixin registers QUILL's titles; Cast speaks its own words and
    has no Open Manager (it only led back to the Podcasts place)."""
    commands = cast_frame.commands
    assert commands.get("podcasts.open_manager") is None
    expected = {
        "podcasts.acb_media": "Podcasts: Follow ACB Media Podcasts",
        "podcasts.add_local": "Podcasts: Add Personal Audio...",
        "podcasts.settings": "Podcasts: Fetching Preferences...",
        "podcasts.skip_settings": "Podcasts: Playing Preferences...",
    }
    for command_id, title in expected.items():
        command = commands.get(command_id)
        assert command is not None, command_id
        assert command.title == title


def test_play_next_episode_from_the_managers_verbs_plays_in_the_one_window(
    cast_frame, monkeypatch
) -> None:
    """The Manager's play verb was never defined on the one window, so its
    Play Next Episode (and chapter jump) raised there."""
    from quill.ui.podcasts import show_actions

    started: list[tuple[str, int | None]] = []
    monkeypatch.setattr(
        show_actions,
        "start_episode_playback",
        lambda _c, _l, show, episode, *, resume_ms=None, announce=None: (
            started.append((episode.guid, resume_ms)) or True
        ),
    )
    frame = cast_frame
    show = frame._podcast_library.find_show("s2")
    frame._play_next_unplayed(show)
    assert started and started[0][0].startswith("s2e")
