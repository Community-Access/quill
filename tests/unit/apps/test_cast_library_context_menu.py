"""What each kind of library-tree row offers on its context menu.

The entries builder was split from the wx popup (podcasts_library_actions)
exactly so this is answerable without a frame: an episode row used to fall
into the anything-else branch and offer only "Open Manager..." -- no way to
download the one episode under the cursor (reported 2026-08-17).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("wx")

from quill.apps.podcasts_library_actions import CastLibraryActionsMixin
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


class _Host(CastLibraryActionsMixin):
    """The mixin with just the state the entries builder reads."""

    def __init__(self, library: PodcastLibrary, selected: tuple[str, str] | None) -> None:
        self._podcast_library = library
        self._selected = selected
        self.opened: list[str] = []
        self.said: list[str] = []
        self.changed = 0
        stopped = SimpleNamespace(name="STOPPED")
        self._podcast_controller = SimpleNamespace(
            state=SimpleNamespace(state=stopped, show_id=None, episode_guid=None)
        )

    def _selected_tree_data(self):
        return self._selected

    def _selected_episode(self):
        if self._selected is None or self._selected[0] != "episode":
            return None
        show_id, _, guid = self._selected[1].partition("\x00")
        show = self._podcast_library.find_show(show_id)
        episode = show.find_episode(guid) if show is not None else None
        return None if show is None or episode is None else (show, episode)

    # -- the Manager-shaped names folder_commands reads (CastEpisodeListMixin) --

    @property
    def _library(self) -> PodcastLibrary:
        return self._podcast_library

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _on_library_changed(self) -> None:
        self.changed += 1

    def refresh_tree(self) -> None:
        pass

    def _podcast_open_add_dialog(self) -> None:
        self.opened.append("add")

    def _podcast_open_import_opml(self) -> None:
        self.opened.append("import")


def _library() -> PodcastLibrary:
    library = PodcastLibrary()
    show = PodcastShow(
        id="s1",
        title="Show",
        is_local=True,
        episodes=[PodcastEpisode(guid="e1", title="Pilot", audio_url="https://x/1.mp3")],
    )
    library.add_show(show)
    return library


def _labels(host: _Host) -> list[str]:
    return [label for label, _handler in host._library_context_entries()]


def test_an_episode_row_offers_play_and_download() -> None:
    labels = _labels(_Host(_library(), ("episode", "s1\x00e1")))
    assert "&Play Episode" in labels
    assert "&Download Episode" in labels


def test_a_show_row_offers_custom_order_moves() -> None:
    labels = _labels(_Host(_library(), ("show", "s1")))
    assert any(label.startswith("Move Up in &Custom Order") for label in labels)
    assert any(label.startswith("Move Do&wn in Custom Order") for label in labels)


def test_no_row_offers_open_manager_or_the_view_renames() -> None:
    """Open Manager only led back to the Podcasts place the tree is in, and
    Rename / Reset Name applied to pinned-view rows the tree no longer has."""
    library = _library()
    folder = library.add_folder("News")
    rows = [
        ("show", "s1"),
        ("episode", "s1\x00e1"),
        ("folder", folder.id),
        ("group", ""),
        ("view", "inbox"),
    ]
    for selected in rows:
        labels = _labels(_Host(library, selected))
        assert "Open &Manager..." not in labels, selected
        assert "Reset &Name" not in labels, selected
        assert "&Rename...\tF2" not in labels, selected


def test_a_folder_row_offers_the_folder_verbs_the_guide_teaches() -> None:
    library = _library()
    folder = library.add_folder("News")
    labels = _labels(_Host(library, ("folder", folder.id)))
    assert labels[:5] == [
        "&Play All Unheard",
        "Add All to &Queue",
        "Move &Up",
        "Move Dow&n",
        "&Export This Folder as OPML...",
    ]
    assert "Folder &Settings..." not in labels, "QUILL's Manager only"
    # GATE-14 inside one popup: every access key is claimed once.
    keys = [label.split("&", 1)[1][0].lower() for label in labels if "&" in label]
    assert len(keys) == len(set(keys)), labels


def test_the_folder_verbs_act_on_the_folder() -> None:
    library = _library()
    news = library.add_folder("News")
    library.add_folder("Sport")
    library.find_show("s1").folder_id = news.id
    host = _Host(library, ("folder", news.id))
    entries = dict(host._library_context_entries())

    entries["Add All to &Queue"]()
    assert [item.episode_guid for item in library.queue] == ["e1"]
    assert host.said[-1] == "Added 1 episode to the queue."

    entries["Move Dow&n"]()
    assert host.said[-1] == "News, 2 of 2."
    entries["Move &Up"]()
    assert host.said[-1] == "News, 1 of 2."
    assert host.changed == 3


def test_a_folder_row_advertises_f2_on_rename() -> None:
    library = _library()
    folder = library.add_folder("News")
    labels = _labels(_Host(library, ("folder", folder.id)))
    assert "Rena&me Folder...\tF2" in labels


def test_an_empty_library_action_row_offers_adding_and_importing() -> None:
    host = _Host(PodcastLibrary(), ("action", "search"))
    entries = dict(host._library_context_entries())

    assert list(entries) == ["&Add Podcast...", "&Import Podcasts from OPML..."]
    entries["&Add Podcast..."]()
    entries["&Import Podcasts from OPML..."]()
    assert host.opened == ["add", "import"]


def test_a_downloaded_episode_offers_file_verbs_not_download(tmp_path) -> None:
    """A saved episode is a file: Play/Pause, its own Stop, and Remove Download.

    Offering "Download Episode" on a file already on disk is an offer to do
    nothing, and until this there was no way to take one episode back off the
    disk -- only Remove All Downloads, which empties the whole show.
    """
    library = _library()
    episode = library.find_show("s1").find_episode("e1")
    saved = tmp_path / "Pilot.mp3"
    saved.write_bytes(b"audio")
    episode.downloaded_path = str(saved)

    labels = _labels(_Host(library, ("episode", "s1\x00e1")))

    assert "&Play Episode" in labels
    assert "&Stop" in labels
    assert "Remo&ve Download" in labels
    assert "&Download Episode" not in labels


def test_a_recorded_download_whose_file_is_gone_is_downloadable_again(tmp_path) -> None:
    # Deleted in Explorer: the disk decides, not the record, or the menu would
    # offer to remove a file that is not there and refuse to fetch it again.
    library = _library()
    episode = library.find_show("s1").find_episode("e1")
    episode.downloaded_path = str(tmp_path / "never-written.mp3")

    labels = _labels(_Host(library, ("episode", "s1\x00e1")))

    assert "&Download Episode" in labels
    assert "Remo&ve Download" not in labels
