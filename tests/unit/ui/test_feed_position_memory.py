"""Category browsing and feed-list position in the windows (item 43, 2026-10-16).

* Quill Radio's Browse Stations: Escape inside a category goes back to the
  category's row, folded, one level per press, and closes only at the top
  (driven on a real ``wx.TreeCtrl`` built in memory -- no input is sent).
* QUILL's Podcast Manager and QUILL Cast: an opened podcast lands on the
  episode last selected in it, by identity, after a refresh, and after a
  restart; the cross-podcast lists never move a feed's cursor.
* The browse rows say what they cover: a country's chart is not a language.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")


@pytest.fixture
def tree():
    app = shared_wx_app()
    frame = wx.Frame(None)
    control = wx.TreeCtrl(frame, style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT)
    root = control.AddRoot("root")
    countries = control.AppendItem(root, "By Country")
    ireland = control.AppendItem(countries, "Ireland")
    station = control.AppendItem(ireland, "RTE Radio 1")
    control.Expand(countries)
    control.Expand(ireland)
    yield control, countries, ireland, station
    frame.Destroy()
    del app


def test_escape_walks_back_up_the_categories_then_closes(tree) -> None:
    from quill.ui.radio.browse_keys import back_to_category

    control, countries, ireland, station = tree
    control.SelectItem(station)
    assert back_to_category(control) is True
    assert control.GetSelection() == ireland and not control.IsExpanded(ireland)
    assert back_to_category(control) is True
    assert control.GetSelection() == countries
    assert back_to_category(control) is False, "top level: Escape closes, as before"


def test_escape_in_the_tree_is_answered_before_closing(tree) -> None:
    from quill.ui.radio import browse_keys

    control, _countries, ireland, station = tree
    control.SelectItem(station)
    closed: list[bool] = []

    class _Dialog:
        _wx = wx
        _tree = control
        _modeless = True
        _find_ctrl = object()

        class _win:
            @staticmethod
            def FindFocus() -> Any:  # noqa: N802
                return control

            @staticmethod
            def Close() -> None:  # noqa: N802
                closed.append(True)

    class _Escape:
        def GetKeyCode(self) -> int:  # noqa: N802
            return wx.WXK_ESCAPE

        def HasAnyModifiers(self) -> bool:  # noqa: N802
            return False

        def ControlDown(self) -> bool:  # noqa: N802
            return False

        def AltDown(self) -> bool:  # noqa: N802
            return False

        def ShiftDown(self) -> bool:  # noqa: N802
            return False

    assert browse_keys.handle(_Dialog(), _Escape()) is True
    assert control.GetSelection() == ireland and closed == []


def test_rows_disclose_what_a_chart_covers() -> None:
    from quill.core.radio.browse_libraries import STOREFRONT_NOTE

    assert "country" in STOREFRONT_NOTE and "any language" in STOREFRONT_NOTE


# --------------------------------------------------------------------------- #
# Feed position
# --------------------------------------------------------------------------- #


def _ep(guid: str, day: int) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=guid,
        audio_url=f"https://example.invalid/{guid}.mp3",
        published=f"Mon, {day:02d} Jun 2026 08:00:00 +0000",
    )


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    return tmp_path


def test_cast_lands_on_the_remembered_episode_and_only_in_one_feed(data_dir) -> None:
    from quill.ui.podcasts.episode_cursor_ui import flush_cursor, remember_feed_cursor
    from quill.ui.podcasts.main_panel import CastMainPanelMixin
    from quill.ui.podcasts.places_host import CastPlacesHostMixin

    show = PodcastShow(id="s1", title="Talks", feed_url="https://example.invalid/feed")
    episodes = [_ep("c", 3), _ep("b", 2), _ep("a", 1)]

    class _Cast(CastMainPanelMixin, CastPlacesHostMixin):
        def __init__(self) -> None:
            self._current_show = show
            self._current_episodes = list(episodes)
            self._place_opened_show_id = "s1"
            self.selected = 1

        def _selected_episode(self) -> Any:
            return (show, self._current_episodes[self.selected])

    cast = _Cast()
    remember_feed_cursor(cast)
    flush_cursor(cast)
    # A restart, a new episode at the top, and a sort flip later:
    later = _Cast()
    later._current_episodes = [_ep("a", 1), _ep("b", 2), _ep("c", 3), _ep("d", 4)]
    assert later._remembered_episode_row(show) == 1
    # The episode is gone from the feed: its nearest neighbour by date.
    later._current_episodes = [_ep("a", 1), _ep("c", 3)]
    assert later._remembered_episode_row(show) in (0, 1)
    # A cross-podcast list (New Episodes) leaves the feed's cursor alone.
    other = _Cast()
    other._place_opened_show_id = ""
    other.selected = 0
    remember_feed_cursor(other)
    flush_cursor(other)
    again = _Cast()
    again._current_episodes = list(episodes)
    assert again._remembered_episode_row(show) == 1


def test_the_podcast_manager_restores_and_remembers(data_dir) -> None:
    from quill.ui.podcasts.episode_cursor_ui import flush_cursor, remember_episode, remembered_row

    show = PodcastShow(id="s2", title="News", feed_url="https://example.invalid/news")
    episodes = [_ep("n3", 3), _ep("n2", 2), _ep("n1", 1)]

    class _Manager:
        pass

    manager = _Manager()
    assert remembered_row(manager, show, episodes) == 0, "first visit: the top"
    remember_episode(manager, show, episodes[2])
    flush_cursor(manager)
    assert remembered_row(_Manager(), show, episodes) == 2


def test_the_manager_fill_uses_the_cursor(data_dir) -> None:
    """``PodcastManagerDialog._fill_episodes`` selects the remembered row."""
    import inspect

    from quill.ui.podcasts import manager_dialog

    source = inspect.getsource(manager_dialog.PodcastManagerDialog._fill_episodes)
    assert "remembered_row(self, show, self._current_episodes)" in source
    selected = inspect.getsource(manager_dialog.PodcastManagerDialog._on_episode_selected)
    assert "remember_episode(self, self._current_show, episode)" in selected
