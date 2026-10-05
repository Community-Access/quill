"""Cast's peer windows (qc.md section 6, Phase 4): made once, raised again, and
Escape goes back to whoever opened them.

Against the real QUILL Cast window, because what can go wrong is wiring: a
second window where the first should have been raised, a Window menu that never
learned about it, or focus that lands on the top of the library instead of the
button the listener pressed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

#: Serialized onto one worker under ``-n --dist loadgroup``: this file builds a
#: real QUILL Cast window, which registers the system-wide global hotkeys
#: (RegisterHotKey is per-desktop, not per-process).
#: See ``pytest_collection_modifyitems`` in ``tests/conftest.py``.
pytestmark = pytest.mark.machine_global


@pytest.fixture
def cast(quill_data_dir: Path):
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.models_episode import PodcastEpisode
    from quill.core.podcasts.subscriptions import PodcastLibrary, save_library

    library = PodcastLibrary()
    show = PodcastShow(id="s1", title="Show 1", feed_url="http://x.invalid/1")
    for ep in (1, 2):
        show.episodes.append(
            PodcastEpisode(
                guid=f"s1e{ep}",
                title=f"Episode {ep}",
                audio_url=f"http://x.invalid/1/{ep}.mp3",
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


class _Opener:
    """Stands in for the control that had focus, and records getting it back."""

    def __init__(self) -> None:
        self.focused = 0

    def __bool__(self) -> bool:
        return True

    def GetParent(self):
        return None

    def IsShownOnScreen(self) -> bool:
        return True

    def GetTopLevelParent(self):
        return None

    def SetFocus(self) -> None:
        self.focused += 1


def _escape(frame) -> None:
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(wx.WXK_ESCAPE)
    event.SetEventObject(frame)
    frame.GetEventHandler().ProcessEvent(event)


def _registered(cast, frame) -> bool:
    return cast._windows.key_for(frame) in cast._windows._frames


def _menu_titles(frame) -> list[str]:
    bar = frame.GetMenuBar()
    return [bar.GetMenuLabel(index) for index in range(bar.GetMenuCount())]


def test_statistics_opens_once_and_is_raised_and_refreshed(cast, monkeypatch) -> None:
    from quill.ui.podcasts import stats_dialog

    cast.open_podcast_statistics()
    window = cast._podcast_stats_window
    assert window.frame.IsShown()
    assert _registered(cast, window.frame)
    assert "Statis&tics" in _menu_titles(window.frame)
    assert "&Window" in _menu_titles(window.frame)
    assert window.focus_target() is window._report

    reloads: list[int] = []
    real_load = stats_dialog._load
    monkeypatch.setattr(stats_dialog, "_load", lambda host: reloads.append(1) or real_load(host))
    window.frame.Hide()
    cast.open_podcast_statistics()
    assert cast._podcast_stats_window is window  # raised, never a second copy
    assert window.frame.IsShown()
    assert reloads == [1]  # and read afresh


def test_escape_hides_statistics_says_so_and_restores_focus(cast) -> None:
    from quill.ui.dialog_contract import set_transition_announcement_policy
    from quill.ui.podcasts.stats_dialog import open_statistics_window

    set_transition_announcement_policy(lambda: True)  # the cue is the listener's choice
    opener = _Opener()
    window = open_statistics_window(cast, opener=opener)
    cast.said.clear()
    _escape(window.frame)
    assert not window.frame.IsShown()
    assert window.frame  # hidden, not destroyed: its Window-menu number holds
    assert "Exited Listening Statistics." in cast.said
    assert opener.focused >= 1


def test_ctrl_w_is_the_close_row_of_the_peer_menu(cast) -> None:
    cast.open_podcast_statistics()
    frame = cast._podcast_stats_window.frame
    own = frame.GetMenuBar().GetMenu(0)
    labels = [item.GetItemLabel() for item in own.GetMenuItems()]
    assert "&Close\tCtrl+W" in labels


def test_year_in_review_is_a_peer_opened_from_statistics(cast) -> None:
    from quill.ui.podcasts.year_review_dialog import open_year_in_review

    cast.open_podcast_statistics()
    stats_window = cast._podcast_stats_window
    button = _Opener()
    review = open_year_in_review(stats_window, opener=button)
    assert cast._year_review_window is review
    assert review.frame.IsShown() and _registered(cast, review.frame)
    assert review.focus_target() is review._report
    assert open_year_in_review(stats_window, opener=button) is review
    _escape(review.frame)
    assert not review.frame.IsShown()
    assert button.focused >= 1
    assert stats_window.frame.IsShown()  # closing one peer leaves the other alone


def test_about_this_episode_is_one_window_that_follows_the_episode(cast) -> None:
    from quill.core.podcasts.extras import ACTION_JUMP, Row, Section
    from quill.ui.podcasts import extras_command

    show = cast._podcast_library.find_show("s1")
    first = extras_command.open_episode_extras(cast, show, show.find_episode("s1e1"))
    assert first.frame.IsShown() and _registered(cast, first.frame)
    assert first.frame.GetTitle() == "About This Episode -- Episode 1"
    second = extras_command.open_episode_extras(cast, show, show.find_episode("s1e2"))
    assert second is first
    assert first.frame.GetTitle() == "About This Episode -- Episode 2"

    # The action button simply acts: the window stays open for the next row.
    jumped: list[str] = []
    extras = first._extras
    extras.sections.append(
        Section(
            key="bookmarks",
            title="Bookmarks",
            rows=(Row(label="1 minute", action=ACTION_JUMP, target="60000"),),
            heading="Marks.",
        )
    )
    first.load(extras, episode_title="Episode 2", jump_to=lambda t: jumped.append(t) or True)
    first._notebook.SetSelection(first._notebook.GetPageCount() - 1)
    first._sync_button()
    assert first._action_btn.GetLabel() == "&Go There"
    assert first.activate_selected() is True
    assert jumped == ["60000"]
    assert first.frame.IsShown()


def test_the_contract_works_for_a_host_with_no_window_menu(quill_data_dir: Path) -> None:
    """QUILL's own frame keeps no Window manager; a peer there still closes right."""
    from quill.ui.podcasts.peer_window import open_peer

    app = wx.App()
    owner = wx.Frame(None)
    said: list[str] = []

    class _Host:
        frame = owner

        def _announce(self, message: str, **_kw) -> None:
            said.append(message)

    class _Peer:
        TITLE = "Example"
        MENU_TITLE = "E&xample"

        def __init__(self, host) -> None:
            self.frame = wx.Frame(host.frame, title="Example")
            self.text = wx.TextCtrl(wx.Panel(self.frame))
            self.refreshed = 0

        def focus_target(self):
            return self.text

        def refresh(self) -> None:
            self.refreshed += 1

    host = _Host()
    opener = _Opener()
    try:
        made = open_peer(host, "_example", _Peer, opener=opener)
        assert open_peer(host, "_example", _Peer, opener=opener) is made
        assert made.refreshed == 1
        assert [made.frame.GetMenuBar().GetMenuLabel(0)] == ["E&xample"]
        made.frame.Close()
        assert not made.frame.IsShown()
        assert "Exited Example." in said
        assert opener.focused >= 1
    finally:
        owner.Destroy()
        del app


def test_sound_enhancements_is_a_peer_whose_apply_keeps_it_open(cast) -> None:
    cast.open_podcast_sound_enhancements()
    window = cast._sound_enhancements_window
    assert window.frame.IsShown() and _registered(cast, window.frame)
    editor = window._editor
    apply_btn = wx.Window.FindWindowById(wx.ID_OK, editor.dialog)
    close_btn = wx.Window.FindWindowById(wx.ID_CANCEL, editor.dialog)
    assert apply_btn.GetLabel() == "Appl&y"
    assert close_btn.GetLabel() == "Close"
    assert window.focus_target() is editor._preset_choice

    # Nothing is playing, so Apply writes the shared default -- as OK did.
    editor._bass_slider.SetValue(editor._bass_slider.GetValue() + 3)
    editor._compressor_check.SetValue(True)
    expected_bass = editor._current_band_values()[0]
    editor._on_apply(None)
    settings = cast._podcast_library.settings
    assert settings.eq_bass_db == expected_bass
    assert settings.compressor_enabled is True
    assert any(line.startswith("Sound Enhancements for the shared default") for line in cast.said)
    assert window.frame.IsShown()  # Apply acts; it does not close

    cast.open_podcast_sound_enhancements()
    assert cast._sound_enhancements_window is window
    assert window._editor._compressor_check.GetValue() is True  # re-read afresh
    _escape(window.frame)
    assert not window.frame.IsShown()


def test_every_folder_name_is_asked_through_the_one_prompt(cast, monkeypatch) -> None:
    """qc.md section 6: the six raw New Folder / Rename Folder prompts are one."""
    import re

    from quill.ui.podcasts import folder_prompt

    asked: list[str] = []

    def _prompt(_parent, *, current: str = "", announce=None) -> str:
        asked.append(current)
        return "News"

    monkeypatch.setattr(folder_prompt, "folder_name_prompt", _prompt)
    cast._new_library_folder()
    assert asked == [""]
    assert [f.name for f in cast._podcast_library.folders] == ["News"]

    root = Path(__file__).resolve().parents[3] / "quill"
    raw = re.compile(r"TextEntryDialog\([^)]*\"(New Folder|Rename Folder)\"", re.S)
    sources = [*root.glob("ui/podcasts/*.py"), *root.glob("apps/podcasts*.py")]
    offenders = [
        p.name for p in sources if p.name != "folder_prompt.py" and raw.search(p.read_text("utf-8"))
    ]
    assert offenders == []


# -- the second batch (qc.md section 6 "Peer" rows) ----------------------------


def test_feed_check_is_one_window_that_says_its_summary(cast) -> None:
    from quill.ui.podcasts.feed_check_dialog import open_feed_check

    opener = _Opener()
    window = open_feed_check(cast, opener=opener)
    assert window.frame.IsShown() and _registered(cast, window.frame)
    assert window.focus_target() is window._list
    assert cast.said[-1] == window.summary()
    assert open_feed_check(cast, opener=opener) is window
    _escape(window.frame)
    assert not window.frame.IsShown()
    assert opener.focused >= 1


def test_episode_filters_save_keeps_it_open_and_follows_the_podcast(cast) -> None:
    from quill.core.podcasts.models import PodcastShow

    show = cast._podcast_library.find_show("s1")
    cast._on_episode_filters(show)
    window = cast._episode_filters_window
    assert window.frame.IsShown() and _registered(cast, window.frame)
    assert "&Save\tCtrl+S" in [
        item.GetItemLabel() for item in window.frame.GetMenuBar().GetMenu(0).GetMenuItems()
    ]
    window._enabled.SetValue(False)
    window._on_ok(None)  # nothing switched on: a plain save
    assert window.frame.IsShown()  # Save acts; it does not close
    cast._on_episode_filters(show)
    assert cast._episode_filters_window is window
    other = PodcastShow(id="s2", title="Show 2", feed_url="http://x.invalid/2")
    cast._podcast_library.add_show(other)
    cast._on_episode_filters(other)
    assert cast._episode_filters_window is window
    assert window.frame.GetTitle() == "Episode Filters -- Show 2"


def test_settings_for_this_podcast_saves_and_stays_open(cast) -> None:
    show = cast._podcast_library.find_show("s1")
    cast._on_show_settings(show)
    window = cast._show_settings_window
    assert window.frame.IsShown() and _registered(cast, window.frame)
    assert window.frame.GetTitle() == "Settings for Show 1"
    window._favorite.SetValue(True)
    window._on_ok(None)
    assert show.is_favorite is True
    assert window.frame.IsShown()
    cast._on_show_settings(show)
    assert cast._show_settings_window is window


def test_a_new_smart_playlist_is_made_by_the_first_save_and_edited_after(cast, monkeypatch) -> None:
    monkeypatch.setattr(type(cast), "_prompt_playlist_name", lambda self, *_a, **_k: "Mine")
    cast._on_new_smart_playlist()
    window = cast._playlist_rules_window
    assert window.frame.IsShown() and _registered(cast, window.frame)
    window._on_save(None)
    window._on_save(None)
    names = [p.name for p in cast._podcast_library.playlists]
    assert names == ["Mine"]  # one playlist, made once, then edited
    assert window.frame.IsShown()


def test_add_podcast_is_one_window(cast) -> None:
    cast._podcast_open_add_dialog()
    window = cast._add_podcast_window
    assert window.frame.IsShown() and _registered(cast, window.frame)
    cast._podcast_open_add_dialog()
    assert cast._add_podcast_window is window
    _escape(window.frame)
    assert not window.frame.IsShown()


def test_show_notes_and_transcript_are_one_window_each(cast) -> None:
    from quill.core.podcasts.transcripts import TranscriptCue
    from quill.ui.podcasts import transcript_actions

    show = cast._podcast_library.find_show("s1")
    first, second = show.find_episode("s1e1"), show.find_episode("s1e2")
    first.description = "<p>One</p>"
    second.description = "<p>Two</p>"
    transcript_actions.view_show_notes(cast, first)
    notes = cast._show_notes_window
    transcript_actions.view_show_notes(cast, second)
    assert cast._show_notes_window is notes
    assert notes.frame.GetTitle() == "Show Notes -- Episode 2"

    cues = [TranscriptCue(start_ms=0, end_ms=1000, text="Hello")]
    transcript_actions._open_reader(cast, show, first, cues)
    reader = cast._transcript_window
    assert reader.frame.IsShown() and _registered(cast, reader.frame)
    assert reader.reader._close_btn.GetLabel() == "Close"
    transcript_actions._open_reader(cast, show, second, cues)
    assert cast._transcript_window is reader
    assert reader.frame.GetTitle() == "Transcript: Episode 2"


def test_notifications_and_watched_folders_return_to_their_opener(cast) -> None:
    from quill.ui.podcasts.notifications_window import open_notifications_window
    from quill.ui.podcasts.watched_folders_window import open_watched_folders_window

    for open_it in (open_notifications_window, open_watched_folders_window):
        opener = _Opener()
        window = open_it(cast, opener=opener)
        assert open_it(cast, opener=opener) is window
        _escape(window.frame)
        assert not window.frame.IsShown()
        assert opener.focused >= 1
