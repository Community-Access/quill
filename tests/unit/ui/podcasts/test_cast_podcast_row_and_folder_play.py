"""A podcast row's menu offers one refresh, and Play All Unheard plays.

Check Now and Refresh Feed on the same podcast menu ran the same handler, so
Cast keeps the one that is a Quick Action (Refresh Feed). Play All Unheard
called a play verb the one window does not have -- and the Manager's needs a
resume point it was never given -- so it queued and then stopped, or raised;
it now starts through the one shared starter.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


class _Menu:
    def __init__(self) -> None:
        self.labels: list[str] = []

    def Append(self, _id, label):  # noqa: N802 - wx's name
        self.labels.append(label)
        return SimpleNamespace(Enable=lambda _on: None, SetHelp=lambda _t: None)

    def AppendSeparator(self) -> None:  # noqa: N802
        self.labels.append("")

    def Bind(self, *_a, **_k) -> None:  # noqa: N802
        pass

    def Destroy(self) -> None:  # noqa: N802
        pass


def _library() -> tuple[PodcastLibrary, PodcastShow]:
    library = PodcastLibrary()
    show = PodcastShow(
        id="s1",
        title="Show",
        feed_url="https://example.test/feed.xml",
        episodes=[PodcastEpisode(guid="e1", title="Pilot", audio_url="https://x/1.mp3")],
    )
    library.add_show(show)
    return library, show


def test_a_podcast_row_offers_refresh_feed_once_and_no_check_now() -> None:
    from quill.core.podcasts.quick_actions import QuickActionOrders
    from quill.ui.podcasts import context_menus

    library, show = _library()
    menu = _Menu()
    host = SimpleNamespace(
        _wx=SimpleNamespace(Menu=lambda: menu, ID_ANY=-1, EVT_MENU=object()),
        _selected_show=lambda: show,
        _content=SimpleNamespace(control=SimpleNamespace(PopupMenu=lambda _m: None)),
        _library=library,
        _safe_mode=False,
        _quick_actions=QuickActionOrders(),
    )
    context_menus.podcast_row_menu(host)
    assert "Chec&k Now" not in menu.labels
    refresh = [label for label in menu.labels if label.startswith("&Refresh Feed")]
    assert len(refresh) == 1, menu.labels


def test_play_all_unheard_queues_one_each_and_starts_the_first(monkeypatch) -> None:
    from quill.core.podcasts import folder_actions
    from quill.ui.podcasts import folder_commands, show_actions

    library, show = _library()
    folder = library.add_folder("News")
    show.folder_id = folder.id
    started: list[str] = []
    monkeypatch.setattr(
        show_actions,
        "start_episode_playback",
        lambda _c, _l, _s, episode, **_k: started.append(episode.guid) or True,
    )
    said: list[str] = []
    host = SimpleNamespace(
        _library=library,
        _controller=object(),
        _announce=said.append,
        _on_library_changed=lambda: None,
    )
    assert folder_actions.latest_unplayed_per_show(library, folder.id)
    folder_commands.play_folder(host, folder.id)
    assert started == ["e1"]
    assert [item.episode_guid for item in library.queue] == ["e1"]
    assert said == ["Queued 1 episode, one from each podcast. Playing Pilot from Show."]
