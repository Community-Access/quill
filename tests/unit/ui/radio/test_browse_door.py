"""Which window "Browse Stations" opens, per app (browse_door, 2026-09-25).

Four doors in the standalone app said "Browse Stations" and opened Search
Stations, because each called ``open_internet_radio`` -- QUILL's spelling --
directly. The standalone app (the one with a WindowManager) opens the tree;
QUILL, which has no tree window, opens the search.
"""

from __future__ import annotations

from quill.ui.radio.browse_door import open_browse


class _Host:
    def __init__(self, *, standalone: bool, tree: bool = True, search: bool = True) -> None:
        self.opened: list[str] = []
        if standalone:
            self._windows = object()
        if tree:
            self.open_browse_stations = lambda: self.opened.append("tree")
        if search:
            self.open_internet_radio = lambda: self.opened.append("search")


def test_the_standalone_app_opens_the_browse_tree() -> None:
    host = _Host(standalone=True)
    open_browse(host)
    assert host.opened == ["tree"]


def test_quill_opens_search_stations_even_when_a_tree_opener_exists() -> None:
    host = _Host(standalone=False)
    open_browse(host)
    assert host.opened == ["search"]


def test_a_host_with_only_the_tree_still_opens_it() -> None:
    host = _Host(standalone=False, search=False)
    open_browse(host)
    assert host.opened == ["tree"]


def test_the_standalone_app_without_a_tree_falls_back_to_search() -> None:
    host = _Host(standalone=True, tree=False)
    open_browse(host)
    assert host.opened == ["search"]


def test_a_host_with_neither_is_a_quiet_no_op() -> None:
    open_browse(object())


def test_the_status_bar_and_tray_browse_row_goes_through_the_door() -> None:
    # The status bar's Play cell and the tray share one menu builder; its
    # "Browse Stations..." row called open_internet_radio directly until
    # 2026-09-25. A source check, because the builder needs a whole frame.
    import inspect

    from quill.ui.main_frame_radio import RadioMixin

    source = inspect.getsource(RadioMixin._build_radio_status_bar_menu)
    assert "browse_door.open_browse(self)" in source
    assert "open_internet_radio" not in source
