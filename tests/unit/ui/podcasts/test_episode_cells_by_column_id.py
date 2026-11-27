"""Cast's episode rows are updated by column id, never by position.

Listeners can reorder and hide the Episodes columns (Subscriptions > Choose
Columns...). A download finishing used to write its status with
``SetItem(row, 3, ...)``: with Time Left moved to position 3 the status landed
in Time Left, and with Published hidden it went into a column that does not
exist. The cross-show views (Inbox, folders, virtual views) wrote every cell by
position. All of them now go through the shared column view.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

from quill.core.media.list_columns import ColumnDef
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.ui.podcasts.manager_row_view import ManagerRowViewMixin

REPO = Path(__file__).resolve().parents[4]


class _FakeList:
    """Enough of wx.ListCtrl to read back what each column holds."""

    def __init__(self, columns: int) -> None:
        self.columns = columns
        self.cells: dict[tuple[int, int], str] = {}
        self.writes: list[tuple[int, int, str]] = []

    def GetItemText(self, row: int, col: int = 0) -> str:
        return self.cells.get((row, col), "")

    def SetItem(self, row: int, col: int, text: str) -> None:
        assert 0 <= col < self.columns, f"wrote column {col} of {self.columns}"
        self.cells[(row, col)] = text
        self.writes.append((row, col, text))


class _Host(ManagerRowViewMixin):
    def __init__(self, columns: list[ColumnDef], *, pair_shows=None, show=None) -> None:
        self._episode_columns = columns
        self._episodes = _FakeList(len(columns))
        self._pair_shows = pair_shows or []
        self._current_show = show
        self._library = SimpleNamespace(settings=SimpleNamespace(announce_show_name_first=False))
        self._download_queue = SimpleNamespace(get=lambda _id: None)

    def _download_item_id(self, episode: PodcastEpisode) -> str:
        return episode.guid

    # The full row builder reads library-wide policy that is not under test.
    def _episode_row_values(self, episode, show):
        return {
            "title": episode.title,
            "published": episode.published[:16],
            "duration": "",
            "status": self._episode_status_text(episode),
            "podcast": show.title if show is not None else "",
            "remaining": "12 min left",
            "downloaded": "Downloaded" if episode.downloaded_path else "Streams",
            "description": "",
        }


def _col(cid: str) -> ColumnDef:
    return ColumnDef(id=cid, label=cid.title())


def _episode(**kw) -> PodcastEpisode:
    return PodcastEpisode(
        guid="g1",
        title="Episode one",
        audio_url="https://example.invalid/1.mp3",
        published="2026-11-20",
        **kw,
    )


def test_status_lands_in_the_status_column_after_reordering() -> None:
    # Time Left moved to where Status used to be (position 3).
    columns = [_col("title"), _col("status"), _col("downloaded"), _col("remaining")]
    host = _Host(columns, show=PodcastShow(id="s1", title="Show"))
    episode = _episode(downloaded_path="C:/x.mp3")
    host._rewrite_episode_row(0, episode)
    assert host._episodes.cells[(0, 1)] == "Downloaded"
    assert host._episodes.cells[(0, 2)] == "Downloaded"
    assert host._episodes.cells[(0, 3)] == "12 min left"


def test_a_layout_with_fewer_than_four_columns_is_not_written_past_its_end() -> None:
    columns = [_col("title"), _col("status")]
    host = _Host(columns, show=PodcastShow(id="s1", title="Show"))
    host._rewrite_episode_row(0, _episode())
    assert host._episodes.cells[(0, 1)] == "Streaming"


def test_an_unchanged_cell_is_not_rewritten() -> None:
    """A status update must not make a screen reader read the whole row again."""
    columns = [_col("title"), _col("status")]
    host = _Host(columns, show=PodcastShow(id="s1", title="Show"))
    episode = _episode()
    host._rewrite_episode_row(0, episode)
    host._episodes.writes.clear()
    host._rewrite_episode_row(0, episode)
    assert host._episodes.writes == []


def test_a_cross_show_row_keeps_its_show_name_in_the_title() -> None:
    columns = [_col("title"), _col("status")]
    show = PodcastShow(id="s2", title="Other show")
    host = _Host(columns, pair_shows=[show])
    host._rewrite_episode_row(0, _episode())
    assert host._episodes.cells[(0, 0)] == "Episode one — Other show"


def test_no_episode_cell_is_written_by_a_fixed_position_any_more() -> None:
    pattern = re.compile(r"_episodes\.SetItem\(\s*\w+\s*,\s*\d")
    for name in ("manager_downloads.py", "manager_phase4.py", "manager_row_view.py"):
        source = (REPO / "quill" / "ui" / "podcasts" / name).read_text(encoding="utf-8")
        assert not pattern.search(source), f"{name} still writes an episode cell by position"
