"""Unified Browse Stations tree -- row rendering, play routing, favorites.

Drives the wx-heavy dialog against a fake tree (the real one needs a wx.App to
construct). What each *source* produces is tested in
``tests/unit/core/radio/test_browse_sources.py``; what is tested here is the
half that only the dialog can do -- turning BrowseNodes into rows, and routing
an activation to playback, resolution, or expansion.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.radio import browse_sources
from quill.core.radio.browse_nodes import folder, lazy_leaf, leaf
from quill.core.radio.favorites import FavoriteStation, RadioFavoritesStore
from quill.core.radio.models import RadioStation
from quill.ui.radio.browse_tree_dialog import BrowseTreeDialog


class _Node:
    def __init__(self, ok: bool = True) -> None:
        self._ok = ok

    def IsOk(self) -> bool:  # noqa: N802
        return self._ok


class _FakeTree:
    def __init__(self) -> None:
        self._data: dict = {}
        self.children: dict = {}
        self._selection = _Node(False)

    def AppendItem(self, parent, label):  # noqa: N802
        node = _Node()
        self.children.setdefault(parent, []).append((node, label))
        return node

    def SetItemData(self, node, data):  # noqa: N802
        self._data[node] = data

    def GetItemData(self, node):  # noqa: N802
        return self._data.get(node)

    def DeleteChildren(self, node):  # noqa: N802
        self.children[node] = []

    def GetChildrenCount(self, node, recursive=True):  # noqa: N802
        return len(self.children.get(node, []))

    def GetFirstChild(self, node):  # noqa: N802
        kids = self.children.get(node, [])
        return (kids[0][0] if kids else _Node(False)), 0

    def GetNextChild(self, node, cookie):  # noqa: N802
        kids = self.children.get(node, [])
        index = cookie + 1
        return (kids[index][0] if index < len(kids) else _Node(False)), index

    def GetItemText(self, node):  # noqa: N802
        for kids in self.children.values():
            for child, label in kids:
                if child is node:
                    return label
        return ""

    def SelectItem(self, node):  # noqa: N802
        self._selection = node

    def SetFocus(self):  # noqa: N802
        return None

    def GetSelection(self):  # noqa: N802
        return self._selection


def _dialog(*, safe_mode: bool = False) -> Any:
    d = BrowseTreeDialog.__new__(BrowseTreeDialog)
    d._tree = _FakeTree()
    d._announced: list[str] = []
    d._announce = d._announced.append
    d._favorites = RadioFavoritesStore(favorites=[])
    d._safe_mode = safe_mode
    d._details = SimpleNamespace(SetValue=lambda _v: None, ChangeValue=lambda _v: None)
    d._play_btn = SimpleNamespace(Enable=lambda _v: None, SetLabel=lambda _l: None)
    d._favorite_btn = SimpleNamespace(Enable=lambda _v: None, SetLabel=lambda _l: None)
    d._on_favorites_changed = lambda: None
    return d


def _child_data(d, node):
    return [d._tree.GetItemData(n) for n, _label in d._tree.children.get(node, [])]


def _labels(d, node):
    return [label for _n, label in d._tree.children.get(node, [])]


def _station(name: str = "Test FM", url: str = "https://a.example/s") -> RadioStation:
    return RadioStation(name=name, stream_url=url)


# --- rendering rows ------------------------------------------------------------


def test_a_leaf_becomes_a_playable_row() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "acb", "label": "ACB Media"})
    d._add_children(root, [leaf(_station("ACB 1"))])
    data = _child_data(d, root)[0]
    assert data["station"].name == "ACB 1"
    assert not data.get("resolve_lazily")


def test_a_folder_becomes_an_openable_row_with_a_loading_placeholder() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "xiph", "label": "Xiph"})
    d._add_children(root, [folder("xiph:jazz", "Jazz")])
    child_node = d._tree.children[root][0][0]
    assert _child_data(d, root)[0]["node_id"] == "xiph:jazz"
    assert _labels(d, child_node) == ["Loading..."], "a folder must look expandable"


def test_a_child_count_is_shown_before_the_folder_is_opened() -> None:
    # The whole point of child_count: decide whether to spend the wait.
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "iheart", "label": "iHeart"})
    d._add_children(root, [folder("iheart:1310", "Rock", child_count=214)])
    assert "214" in _labels(d, root)[0]


def test_a_note_is_shown_so_nothing_surprises_after_enter() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "tunein", "label": "TuneIn"})
    d._add_children(root, [lazy_leaf("tuneinstation:s1", "BBC", note="resolves when you play it")])
    assert "resolves when you play it" in _labels(d, root)[0]


# --- the empty-branch message --------------------------------------------------


def test_an_empty_internet_branch_says_it_might_be_unreachable() -> None:
    # Reading "could not reach the source" as "this folder is empty" is how a
    # listener concludes a working source is broken, or the reverse.
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "soma", "label": "SomaFM"})
    d._add_children(root, [])
    assert "could not be reached" in d._announced[-1]


def test_an_empty_local_branch_just_says_it_is_empty() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "networks", "label": "Networks"})
    d._add_children(root, [])
    assert "could not be reached" not in d._announced[-1]


def test_safe_mode_says_so_rather_than_showing_an_empty_folder() -> None:
    d = _dialog(safe_mode=True)
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "tunein", "label": "TuneIn"})
    d._add_children(root, [])
    assert "Safe Mode" in d._announced[-1]


def test_a_populated_branch_announces_its_count() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "acb", "label": "ACB Media"})
    d._add_children(root, [leaf(_station("A")), leaf(_station("B", "https://a/2"))])
    assert d._announced[-1] == "2 items."


# --- play routing --------------------------------------------------------------


class _Controller:
    def __init__(self) -> None:
        self.played: list[RadioStation] = []
        self.stopped = 0
        self.state = SimpleNamespace(station=None, state=None, volume_percent=100, muted=False)

    def play_station(self, station):
        self.played.append(station)

    def stop(self):
        self.stopped += 1


def test_activating_a_station_leaf_plays_it() -> None:
    d = _dialog()
    d._controller = _Controller()
    station = _station("Jazz FM")
    d._tree._selection = _Node()
    d._tree.SetItemData(
        d._tree._selection, {"node_id": "x", "label": "Jazz FM", "station": station}
    )
    d._play_selected()
    assert [s.name for s in d._controller.played] == ["Jazz FM"]


def test_activating_a_lazy_leaf_resolves_first_then_plays(monkeypatch) -> None:
    d = _dialog()
    d._controller = _Controller()
    submitted: list = []
    d._task_manager = SimpleNamespace(
        submit=lambda op, work, on_success=None, on_failure=None: submitted.append((
            work,
            on_success,
        ))
    )
    monkeypatch.setattr(
        browse_sources,
        "resolve",
        lambda node_id, **_kw: RadioStation(name="", stream_url="https://cdn/bbc.mp3"),
    )
    d._tree._selection = _Node()
    d._tree.SetItemData(
        d._tree._selection,
        {"node_id": "tuneinstation:s1", "label": "BBC", "station": None, "resolve_lazily": True},
    )
    d._play_selected()
    assert submitted, "a lazy leaf must resolve off the UI thread"
    work, on_success = submitted[0]
    on_success("op", work())
    assert [s.stream_url for s in d._controller.played] == ["https://cdn/bbc.mp3"]
    assert d._controller.played[0].name == "BBC", "the row's label names the resolved station"


def test_a_failed_resolve_says_so_and_plays_nothing(monkeypatch) -> None:
    d = _dialog()
    d._controller = _Controller()
    submitted: list = []
    d._task_manager = SimpleNamespace(
        submit=lambda op, work, on_success=None, on_failure=None: submitted.append((
            work,
            on_success,
        ))
    )
    monkeypatch.setattr(browse_sources, "resolve", lambda node_id, **_kw: None)
    d._tree._selection = _Node()
    d._tree.SetItemData(
        d._tree._selection,
        {"node_id": "tuneinstation:s1", "label": "BBC", "station": None, "resolve_lazily": True},
    )
    d._play_selected()
    work, on_success = submitted[0]
    on_success("op", work())
    assert d._controller.played == []
    assert "Could not play BBC." in d._announced


def test_activating_a_folder_plays_nothing() -> None:
    d = _dialog()
    d._controller = _Controller()
    d._tree._selection = _Node()
    d._tree.SetItemData(d._tree._selection, {"node_id": "xiph", "label": "Xiph", "loaded": False})
    d._play_selected()
    assert d._controller.played == []


# --- favorites -----------------------------------------------------------------


def test_toggle_favorite_adds_and_removes() -> None:
    d = _dialog()
    station = _station("Keeper")
    d._tree._selection = _Node()
    d._tree.SetItemData(d._tree._selection, {"node_id": "x", "label": "Keeper", "station": station})
    d._toggle_favorite()
    assert d._favorites.contains(station)
    d._toggle_favorite()
    assert not d._favorites.contains(station)


def test_favorites_branch_lists_unfiled_stations_then_folders() -> None:
    d = _dialog()
    d._favorites = RadioFavoritesStore(
        favorites=[
            FavoriteStation(station=_station("Unfiled", "https://a/1")),
            FavoriteStation(station=_station("Filed", "https://a/2"), folder="News"),
        ]
    )
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "favorites", "label": "Favorites"})
    d._add_favorites(root)
    labels = _labels(d, root)
    assert labels[0] == "Unfiled"
    assert "News" in labels[-1]


def test_an_empty_favorites_branch_explains_how_to_fill_it() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "favorites", "label": "Favorites"})
    d._add_favorites(root)
    assert "No favorites yet" in _labels(d, root)[0]


def test_favorite_folder_adds_all_loaded_stations() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "acb", "label": "ACB Media"})
    d._add_children(root, [leaf(_station("A")), leaf(_station("B", "https://a/2"))])
    d._favorite_folder(root)
    assert len(d._favorites.favorites) == 2
    assert "Added 2 stations to Favorites." in d._announced


def test_favorite_folder_on_an_unopened_folder_asks_you_to_open_it() -> None:
    d = _dialog()
    root = _Node()
    d._tree.SetItemData(root, {"node_id": "xiph", "label": "Xiph"})
    d._add_children(root, [folder("xiph:jazz", "Jazz")])
    d._favorite_folder(root)
    assert "Open the folder first" in d._announced[-1]


# --- a source switched on from the menu reaches an open tree ------------------
# Reported 2026-08-26: it did not, until the app was restarted.


def test_a_selection_made_outside_the_window_rebuilds_the_roots() -> None:
    from quill.core.radio import browse_visibility

    d = _dialog()
    d._visible_sources = ("favorites",)
    d._favorites_root = None
    rebuilt: list[object] = []
    d._rebuild_sources = lambda: rebuilt.append(d._visible_sources)

    updated = browse_visibility.toggle(("favorites",), "shoutcast")
    assert d.apply_visible_sources(updated) is True

    assert d._visible_sources == updated
    assert rebuilt == [updated]


def test_a_window_that_has_gone_says_so_instead_of_raising() -> None:
    """The shell keeps a reference to the last tree it opened; it may be dead."""
    d = _dialog()
    d._tree = None
    assert d.apply_visible_sources(("favorites",)) is False


def test_choosing_browse_sources_updates_an_open_tree_and_says_so() -> None:
    from quill.ui.radio import settings_commands

    class _Tree:
        def __init__(self) -> None:
            self.applied: list[object] = []

        def apply_visible_sources(self, updated):
            self.applied.append(updated)
            return True

    tree = _Tree()
    host = SimpleNamespace(
        frame=None,
        _radio_history=SimpleNamespace(browse_sources_enabled=("favorites",)),
        _save_radio_history=lambda: None,
        _show_modal_dialog=lambda *a, **k: None,
        _announce=lambda text: said.append(text),
        _radio_browse_dialog=tree,
    )
    said: list[str] = []

    class _Chooser:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def show(self):
            return ("favorites", "shoutcast")

    import quill.ui.radio.browse_sources_dialog as chooser_module

    original = chooser_module.BrowseSourcesDialog
    chooser_module.BrowseSourcesDialog = _Chooser  # type: ignore[misc]
    try:
        settings_commands.browse_sources_visibility(host)
    finally:
        chooser_module.BrowseSourcesDialog = original  # type: ignore[misc]

    assert tree.applied == [("favorites", "shoutcast")]
    assert host._radio_history.browse_sources_enabled == ("favorites", "shoutcast")
    assert said and "Browse Stations has been updated." in said[-1]


def test_with_no_tree_open_nothing_is_claimed_about_one() -> None:
    from quill.ui.radio import settings_commands

    said: list[str] = []
    host = SimpleNamespace(
        frame=None,
        _radio_history=SimpleNamespace(browse_sources_enabled=None),
        _save_radio_history=lambda: None,
        _show_modal_dialog=lambda *a, **k: None,
        _announce=said.append,
        _radio_browse_dialog=None,
    )

    class _Chooser:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def show(self):
            return ("favorites",)

    import quill.ui.radio.browse_sources_dialog as chooser_module

    original = chooser_module.BrowseSourcesDialog
    chooser_module.BrowseSourcesDialog = _Chooser  # type: ignore[misc]
    try:
        settings_commands.browse_sources_visibility(host)
    finally:
        chooser_module.BrowseSourcesDialog = original  # type: ignore[misc]

    assert said and "Browse Stations has been updated." not in said[-1]


# --- closing the Search Results branch (asked for 2026-08-26) -----------------


def test_delete_on_the_search_results_branch_closes_it() -> None:
    from quill.ui.radio import browse_delete, browse_search_all

    d = _dialog()
    cleared: list[bool] = []
    d._node_data = lambda _n: {"node_id": browse_search_all.RESULTS_ID, "label": "Search Results"}
    d._tree.GetSelection = lambda: _Node()
    original = browse_search_all.clear_results
    browse_search_all.clear_results = lambda _host: (cleared.append(True), True)[1]
    try:
        assert browse_delete.delete_selected(d) is True
    finally:
        browse_search_all.clear_results = original

    assert cleared == [True]
    assert d._announced[-1] == "Search results closed."


def test_closing_it_asks_no_question_because_nothing_is_lost() -> None:
    """Every other Delete confirms first; this one owns nothing to confirm."""
    from quill.ui.radio import browse_delete, browse_search_all

    d = _dialog()
    d._node_data = lambda _n: {"node_id": browse_search_all.RESULTS_ID}
    d._tree.GetSelection = lambda: _Node()

    def _no_asking(*_args, **_kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("closing search results must not ask")

    original_confirm = browse_delete.confirm
    original_clear = browse_search_all.clear_results
    browse_delete.confirm = _no_asking
    browse_search_all.clear_results = lambda _host: True
    try:
        assert browse_delete.delete_selected(d) is True
    finally:
        browse_delete.confirm = original_confirm
        browse_search_all.clear_results = original_clear


def test_the_context_menu_offers_the_same_verb() -> None:
    from quill.core.radio import row_actions
    from quill.core.radio.row_state import FolderState

    ids = [a.id for a in row_actions.folder_actions("searchresults", FolderState())]
    assert row_actions.CLOSE_SEARCH_RESULTS in ids


def test_an_ordinary_folder_is_not_offered_it() -> None:
    from quill.core.radio import row_actions
    from quill.core.radio.row_state import FolderState

    ids = [a.id for a in row_actions.folder_actions("rbgenre", FolderState(root_source=True))]
    assert row_actions.CLOSE_SEARCH_RESULTS not in ids


# --- the Find box, standing on the search row, means "search everywhere" ------
# Asked for 2026-08-26: "if you press ctrl+f or shift+tab into the edit field
# and type and press enter it should do the same thing as pressing enter on
# that item ... it should meet people where they are."


def test_typing_in_find_while_on_the_search_row_searches_everything() -> None:
    """It is an ACTION row, not a folder: anchoring walks straight past it."""
    from quill.ui.radio import browse_find, browse_search_all

    d = _dialog()
    d._find_ctrl = SimpleNamespace(GetValue=lambda: "  bluegrass  ")
    d._node_data = lambda _n: {"node_id": "searchall", "label": "Search All Sources..."}
    # No folder anywhere: exactly the shape that used to answer "highlight a
    # source or folder to search in first".
    d._is_folder_data = lambda _data: False
    d._tree.GetItemParent = lambda _n: None
    d._tree.GetSelection = lambda: _Node()
    d._tree.GetItemText = lambda _n: "Search All Sources..."
    asked: list[str] = []
    original = browse_search_all.run
    browse_search_all.run = lambda _host, **kw: asked.append(kw.get("query", ""))
    try:
        browse_find.on_find(d)
    finally:
        browse_search_all.run = original

    assert asked == ["bluegrass"]  # trimmed before it travels


def test_typing_in_find_inside_the_results_starts_a_new_search() -> None:
    from quill.ui.radio import browse_find, browse_search_all

    d = _dialog()
    d._find_ctrl = SimpleNamespace(GetValue=lambda: "jazz")
    d._node_data = lambda _n: {"node_id": "searchresults", "label": "Search Results"}
    d._tree.GetSelection = lambda: _Node()
    d._tree.GetItemText = lambda _n: "Search Results"
    asked: list[str] = []
    original = browse_search_all.run
    browse_search_all.run = lambda _host, **kw: asked.append(kw.get("query", ""))
    try:
        browse_find.on_find(d)
    finally:
        browse_search_all.run = original

    assert asked == ["jazz"]


def test_an_ordinary_folder_still_filters_that_folder() -> None:
    """The change must not turn every Find into a network search."""
    from quill.ui.radio import browse_find, browse_search_all

    d = _dialog()
    d._find_ctrl = SimpleNamespace(GetValue=lambda: "jazz")
    d._node_data = lambda _n: {"node_id": "rbgenre", "label": "By Genre"}
    d._tree.GetSelection = lambda: _Node()
    d._tree.GetItemText = lambda _n: "By Genre"
    d._safe_mode = False
    submitted: list[str] = []
    d._task_manager = SimpleNamespace(
        submit=lambda name, work, on_success=None, on_failure=None: submitted.append(name)
    )
    called: list[str] = []
    original = browse_search_all.run
    browse_search_all.run = lambda *_a, **_kw: called.append("global")
    try:
        browse_find.on_find(d)
    finally:
        browse_search_all.run = original

    assert submitted == ["radio-browse-find"]
    assert called == []


def test_a_query_given_to_the_search_skips_the_prompt() -> None:
    from quill.ui.radio import browse_search_all

    d = _dialog()
    d._safe_mode = False
    d._task_manager = SimpleNamespace(submit=lambda *_a, **_kw: None)
    d._win = None
    started: list[str] = []
    from quill.ui.radio import browse_feedback

    original = browse_feedback.start_search_notice
    browse_feedback.start_search_notice = lambda _h, _what, q: started.append(q)
    try:
        browse_search_all.run(d, query="bluegrass")
    finally:
        browse_feedback.start_search_notice = original

    # No prompt was opened -- the query it was given is the query it used.
    assert started == ["bluegrass"]
    assert any("bluegrass" in said for said in d._announced)


# --- the two-pass search: local first, everything second ---------------------
# Reported 2026-08-26 (third pass): "search is still slow when it is performed".


def test_the_fast_pass_asks_only_what_answers_locally() -> None:
    from quill.core.radio import federated_browse as fb

    fast = {target.seed_id for target in fb.fast_targets()}
    assert fast == fb.FAST_SEED_IDS
    # ...and every one of them is a real target, not a typo in the set.
    assert fast <= {target.seed_id for target in (fb.STATIONS, *fb.TARGETS)}
    # The slow ones are deliberately absent: they are what the second pass is
    # for, and putting them here would make the "fast" pass the whole search.
    assert not fast & {"archive", "tunein", "iheart", "apple", "mixcloud"}


def test_a_narrowed_search_narrows_the_fast_pass_too() -> None:
    from quill.core.radio import federated_browse as fb

    podcasts = fb.targets_of_type("Podcast")
    assert fb.fast_targets(podcasts) == ()


def test_the_search_runs_both_passes() -> None:
    from quill.ui.radio import browse_search_all

    d = _dialog()
    d._safe_mode = False
    submitted: list[str] = []
    d._task_manager = SimpleNamespace(
        submit=lambda name, work, on_success=None, on_failure=None: submitted.append(name)
    )
    d._win = None
    from quill.ui.radio import browse_feedback

    original = browse_feedback.start_search_notice
    browse_feedback.start_search_notice = lambda *_a, **_kw: None
    try:
        browse_search_all.run(d, query="jazz")
    finally:
        browse_feedback.start_search_notice = original

    assert submitted == ["radio-search-all-fast", "radio-search-all"]


class _ResultsTree(_FakeTree):
    """A fake tree with the handful of calls show_results makes."""

    def __init__(self) -> None:
        super().__init__()
        self.root = _Node()
        self.focused = 0
        self.expanded: list = []

    def GetRootItem(self):  # noqa: N802
        return self.root

    def PrependItem(self, parent, label):  # noqa: N802
        node = _Node()
        self.children.setdefault(parent, []).insert(0, (node, label))
        return node

    def InsertItem(self, parent, before, label):  # noqa: N802
        return self.PrependItem(parent, label)

    def Delete(self, node) -> None:  # noqa: N802
        for parent, kids in self.children.items():
            self.children[parent] = [pair for pair in kids if pair[0] is not node]

    def Expand(self, node) -> None:  # noqa: N802
        self.expanded.append(node)

    def SetFocus(self):  # noqa: N802
        self.focused += 1


def _results_dialog():
    d = _dialog()
    d._tree = _ResultsTree()
    d._safe_mode = False
    d._find_active = False
    d._row_label = lambda row: row.label
    d._row_data = lambda row: {"node_id": row.node_id, "label": row.label}
    d._placeholder = lambda: {"placeholder": True}
    d._node_data = lambda node: d._tree.GetItemData(node)
    return d


def test_the_partial_answer_says_it_is_partial() -> None:
    from quill.core.radio.browse_nodes import leaf
    from quill.core.radio.federated_browse import FederatedBrowse
    from quill.ui.radio import browse_search_all

    d = _results_dialog()
    found = FederatedBrowse(rows=[leaf(_station("Jazz FM"))], asked=["Radio Browser"])

    browse_search_all.show_results(d, "jazz", found, partial=True)

    labels = [label for _n, label in d._tree.children.get(d._tree.root, [])]
    assert any("still searching" in label for label in labels)
    assert any("Still searching the rest." in said for said in d._announced)
    # The first pass DOES land the cursor: there was nothing to interrupt.
    assert d._tree.focused == 1


def test_the_full_answer_does_not_move_a_cursor_already_in_the_results() -> None:
    """Being sent back to the top by an arriving source is worse than quiet."""
    from quill.core.radio.browse_nodes import leaf
    from quill.core.radio.federated_browse import FederatedBrowse
    from quill.ui.radio import browse_search_all

    d = _results_dialog()
    browse_search_all.show_results(
        d, "jazz", FederatedBrowse(rows=[leaf(_station("Jazz FM"))]), partial=True
    )
    before = d._tree.focused
    # The listener is now standing on a row inside the results.
    results_node = d._tree.children[d._tree.root][0][0]
    d._tree.SelectItem(d._tree.children[results_node][0][0])
    d._tree.GetItemParent = lambda _n: results_node

    browse_search_all.show_results(
        d, "jazz", FederatedBrowse(rows=[leaf(_station("Jazz FM")), leaf(_station("Blues FM"))])
    )

    assert d._tree.focused == before  # nothing was yanked
    labels = [label for _n, label in d._tree.children.get(d._tree.root, [])]
    assert any("(2)" in label for label in labels)


# --- searching the same thing twice is instant --------------------------------
# Asked for 2026-08-26: "can you look to see if global search can be made even
# faster and lightning fast".


def test_a_repeated_search_renders_the_remembered_answer_instantly() -> None:
    from quill.core.radio.browse_nodes import leaf
    from quill.core.radio.federated_browse import FederatedBrowse
    from quill.ui.radio import browse_feedback, browse_search_all

    browse_search_all._RECENT_RESULTS.clear()
    d = _results_dialog()
    submitted: list[tuple[str, object]] = []
    d._task_manager = SimpleNamespace(
        submit=lambda name, work, on_success=None, on_failure=None: submitted.append((
            name,
            on_success,
        ))
    )
    d._win = None
    original = browse_feedback.start_search_notice
    browse_feedback.start_search_notice = lambda *_a, **_kw: None
    try:
        # First search: both passes run, and the full answer is remembered.
        browse_search_all.run(d, query="jazz")
        assert [name for name, _cb in submitted] == ["radio-search-all-fast", "radio-search-all"]
        full_cb = submitted[-1][1]
        full_cb("radio-search-all", FederatedBrowse(rows=[leaf(_station("Jazz FM"))]))
        submitted.clear()

        # Second search, same query: the remembered answer is on screen before
        # any task runs, and the fast pass is skipped -- it would be a
        # downgrade from an answer that already covers every source.
        d._tree = _ResultsTree()
        browse_search_all.run(d, query="JAZZ")
        labels = [label for _n, label in d._tree.children.get(d._tree.root, [])]
        assert any("Search Results" in label for label in labels)
        assert [name for name, _cb in submitted] == ["radio-search-all"]
    finally:
        browse_feedback.start_search_notice = original
        browse_search_all._RECENT_RESULTS.clear()


def test_a_stale_memory_is_not_offered() -> None:
    import time

    from quill.core.radio.federated_browse import FederatedBrowse
    from quill.ui.radio import browse_feedback, browse_search_all

    browse_search_all._RECENT_RESULTS.clear()
    browse_search_all._RECENT_RESULTS["jazz"] = (
        time.monotonic() - browse_search_all.RECENT_TTL_SECONDS - 1,
        FederatedBrowse(),
    )
    d = _results_dialog()
    submitted: list[str] = []
    d._task_manager = SimpleNamespace(
        submit=lambda name, work, on_success=None, on_failure=None: submitted.append(name)
    )
    d._win = None
    original = browse_feedback.start_search_notice
    browse_feedback.start_search_notice = lambda *_a, **_kw: None
    try:
        browse_search_all.run(d, query="jazz")
        # Too old: the ordinary two passes run, nothing was rendered early.
        assert submitted == ["radio-search-all-fast", "radio-search-all"]
    finally:
        browse_feedback.start_search_notice = original
        browse_search_all._RECENT_RESULTS.clear()


def test_a_narrowed_search_is_never_remembered() -> None:
    """ "Search for a Podcast..." shares run(); its answers must not stand in
    for the everything-search's."""
    from quill.core.radio import federated_browse
    from quill.core.radio.federated_browse import FederatedBrowse
    from quill.ui.radio import browse_feedback, browse_search_all

    browse_search_all._RECENT_RESULTS.clear()
    d = _results_dialog()
    calls: list[tuple[str, object]] = []
    d._task_manager = SimpleNamespace(
        submit=lambda name, work, on_success=None, on_failure=None: calls.append((name, on_success))
    )
    d._win = None
    original = browse_feedback.start_search_notice
    browse_feedback.start_search_notice = lambda *_a, **_kw: None
    try:
        browse_search_all.run(
            d, query="history", targets=federated_browse.targets_of_type("Podcast")
        )
        calls[-1][1]("radio-search-all", FederatedBrowse())
        assert browse_search_all._RECENT_RESULTS == {}
    finally:
        browse_feedback.start_search_notice = original
