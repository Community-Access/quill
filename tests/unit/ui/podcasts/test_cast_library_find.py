"""Find in library: the box above Cast's tree (qc.md 4.2, the interim of P10).

Typing flattens the library tree into matches whose rows are tagged exactly as
the library tags them, so Enter, Play and Shift+F10 work on a result as on the
row it stands for. The count is spoken once, when typing pauses. Escape, or an
empty box, brings the library back with the cursor where it was.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts import library_find
from quill.ui.podcasts.library_find import CastLibraryFindMixin


def _episode(guid: str, title: str, published: str) -> PodcastEpisode:
    return PodcastEpisode(guid=guid, title=title, audio_url="", published=published)


@pytest.fixture
def library() -> PodcastLibrary:
    bristol = PodcastShow(id="b", title="Bristol Stories", feed_url="https://example.invalid/b")
    bristol.episodes = [_episode("b1", "Opening night", "2026-01-01")]
    daily = PodcastShow(id="d", title="The Daily", feed_url="https://example.invalid/d")
    daily.episodes = [
        _episode("d1", "The Bristol bus boycott", "2026-02-01"),
        _episode("d2", "Bristol, again", "2026-03-01"),
        _episode("d3", "Something else", "2026-04-01"),
    ]
    return PodcastLibrary(shows=[bristol, daily])


# -- what is found, and how a row reads ------------------------------------------------ #


def test_podcasts_first_then_episodes_newest_first_each_saying_what_it_is(library) -> None:
    rows = library_find.find_rows(library, "bristol")
    labels = [label for label, _ in rows]
    assert labels[0] == "Bristol Stories -- a podcast (1 unheard)"
    assert labels[1:] == [
        "Bristol, again -- an episode of The Daily",
        "The Bristol bus boycott -- an episode of The Daily",
    ]


def test_rows_carry_the_librarys_own_tags(library) -> None:
    data = [d for _, d in library_find.find_rows(library, "bristol")]
    assert data[0] == ("show", "b")
    assert data[1] == ("episode", "d\x00d2")


def test_a_note_is_found_and_names_its_episode(library) -> None:
    note = SimpleNamespace(show_id="d", episode_guid="d3", text="mentions Bristol harbour\nmore")
    rows = library_find.find_rows(library, "harbour", notes=[note])
    assert rows == [
        ("Note on Something else: mentions Bristol harbour", ("episode", "d\x00d3")),
    ]


def test_the_count_sentence_and_the_way_out_when_there_is_nothing() -> None:
    assert library_find.match_count_sentence(14, " bristol ") == "14 matches for bristol"
    assert library_find.match_count_sentence(1, "x") == "1 match for x"
    assert library_find.match_count_sentence(0, "zzz") == (
        "No matches for zzz. Escape returns to your library."
    )


# -- the box's behaviour ------------------------------------------------------------- #


class _Tree:
    def __init__(self) -> None:
        self.rows: list[tuple[str, Any]] = []
        self.selected: Any = None
        self.focused = 0

    def DeleteAllItems(self) -> None:  # noqa: N802 - wx API shape
        self.rows = []

    def AddRoot(self, _label: str) -> int:  # noqa: N802
        return 0

    def AppendItem(self, _parent: int, label: str) -> int:  # noqa: N802
        self.rows.append((label, None))
        return len(self.rows)

    def SetItemData(self, item: int, data: Any) -> None:  # noqa: N802
        label, _ = self.rows[item - 1]
        self.rows[item - 1] = (label, data)

    def SelectItem(self, item: int) -> None:  # noqa: N802
        self.selected = item

    def SetFocus(self) -> None:  # noqa: N802
        self.focused += 1


class _Box:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def GetValue(self) -> str:  # noqa: N802
        return self.value

    def ChangeValue(self, value: str) -> None:  # noqa: N802
        self.value = value


class _Label:
    def __init__(self) -> None:
        self.text = ""

    def SetLabel(self, text: str) -> None:  # noqa: N802
        self.text = text


class _Host(CastLibraryFindMixin):
    def __init__(self, library: PodcastLibrary) -> None:
        self._podcast_library = library
        self._shows_tree = _Tree()
        self._find_box = _Box()
        self._find_status = _Label()
        self.spoken: list[str] = []
        self.reloaded: list[Any] = []
        self.selected: Any = ("show", "d")

    def _announce(self, message: str) -> None:
        self.spoken.append(message)

    def _selected_tree_data(self) -> Any:
        return self.selected

    def _reload_library_tree(self, *, keep_key: Any = None) -> None:
        self.reloaded.append(keep_key)


@pytest.fixture(autouse=True)
def _no_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.core.podcasts.episode_notes.load_episode_notes", lambda: [])


def test_a_pause_flattens_the_tree_and_says_the_count_once(library) -> None:
    host = _Host(library)
    host._find_box.value = "bristol"
    host._run_library_find()
    assert [label for label, _ in host._shows_tree.rows][
        0
    ] == "Bristol Stories -- a podcast (1 unheard)"
    assert host._shows_tree.selected == 1
    assert host.spoken == ["3 matches for bristol"]
    assert host._find_status.text == "3 matches for bristol"


def test_a_reload_while_finding_refreshes_the_matches_not_the_library(library) -> None:
    host = _Host(library)
    host._find_box.value = "bristol"
    assert host._library_find_active() is True
    said = host._refresh_library_find()
    assert said == "3 matches for bristol"
    assert host.spoken == []  # a refresh is not news; only the pause speaks


def test_escape_brings_the_library_back_with_the_cursor_where_it_was(library) -> None:
    import wx

    host = _Host(library)
    host._find_box.value = "bristol"
    host._run_library_find()
    event = SimpleNamespace(GetKeyCode=lambda: wx.WXK_ESCAPE, Skip=lambda: None)
    host._on_find_key(event)
    assert host._find_box.value == ""
    assert host.reloaded == [("show", "d")]
    assert host._shows_tree.focused == 1
    assert host.spoken[-1] == "Back to your library."
    assert host._find_status.text == ""


def test_down_arrow_moves_into_the_matches(library) -> None:
    import wx

    host = _Host(library)
    host._find_box.value = "bristol"
    skipped: list[bool] = []
    host._on_find_key(
        SimpleNamespace(GetKeyCode=lambda: wx.WXK_DOWN, Skip=lambda: skipped.append(True))
    )
    assert host._shows_tree.focused == 1
    assert skipped == []


def test_a_huge_result_is_capped_with_a_row_that_says_how_many_more(
    library, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [(f"Episode {i} -- an episode of X", ("episode", f"x\x00{i}")) for i in range(205)]
    monkeypatch.setattr(library_find, "find_rows", lambda *_a, **_k: rows)
    host = _Host(library)
    host._find_box.value = "episode"
    host._refresh_library_find()
    assert len(host._shows_tree.rows) == 201
    assert host._shows_tree.rows[-1] == (
        "5 more -- type more of the name to narrow it",
        ("more", ""),
    )


def test_the_box_is_built_above_the_tree_with_its_own_label_and_ctrl_f_reaches_it() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[4]
    panel = (root / "quill" / "ui" / "podcasts" / "main_panel.py").read_text(encoding="utf-8")
    menu = (root / "quill" / "apps" / "podcasts_view_menu.py").read_text(encoding="utf-8")
    # The one window (qc.md 4.2): Find's label, then the box, then the Places
    # list and the content pane below it; View > Find is Ctrl+F.
    assert panel.index('label="Fi&nd:"') < panel.index("self._find_box = wx.TextCtrl(")
    assert panel.index("self._find_box = wx.TextCtrl(") < panel.index("self._places = PlacesList(")
    assert 'view_menu.Append(find_id, "Fi&nd' in menu
    assert "self.focus_library_find()" in menu
