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

    def open_podcast_manager(self):  # referenced by every menu
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


def test_a_view_row_offers_rename_via_f2_and_reset_only_when_renamed() -> None:
    library = _library()
    plain = _labels(_Host(library, ("view", "inbox")))
    assert "&Rename...\tF2" in plain
    assert "Reset &Name" not in plain
    library.settings.view_names["inbox"] = "Triage"
    renamed = _labels(_Host(library, ("view", "inbox")))
    assert "Reset &Name" in renamed


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
