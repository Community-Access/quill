"""Tests for WindowManager's navigation logic (wx calls faked)."""

from __future__ import annotations

from quill.ui.window_menu import WindowManager


class _FakeWx:
    """Just enough wx for WindowManager (ids, menus, accelerators)."""

    def __init__(self) -> None:
        self._n = 1000
        self.ACCEL_CTRL = 1
        self.ACCEL_SHIFT = 2
        self.WXK_TAB = 9
        self.ID_ANY = -1
        self.ITEM_CHECK = 1
        self.EVT_MENU = "EVT_MENU"
        self.EVT_MENU_OPEN = "EVT_MENU_OPEN"

    def NewIdRef(self):  # noqa: N802 - wx shape
        self._n += 1
        return self._n

    def Menu(self):  # noqa: N802
        return _FakeMenu()

    def AcceleratorEntry(self, *args):  # noqa: N802
        return args

    def AcceleratorTable(self, entries):  # noqa: N802
        return entries


class _FakeMenuItem:
    def __init__(self, item_id: int, label: str) -> None:
        self._id = item_id
        self.label = label
        self.checked = False

    def GetId(self) -> int:  # noqa: N802
        return self._id

    def Check(self, value: bool = True) -> None:  # noqa: N802
        self.checked = value


class _FakeMenu:
    """A wx.Menu: popup menus keep the empty default title."""

    def __init__(self, title: str = "") -> None:
        self._title = title
        self._next_item_id = 5000
        self.items: list[_FakeMenuItem] = []

    def GetTitle(self) -> str:  # noqa: N802
        return self._title

    def GetMenuItems(self):  # noqa: N802
        return list(self.items)

    def Delete(self, item: _FakeMenuItem) -> None:  # noqa: N802
        self.items.remove(item)

    def Append(self, _item_id, label, _help="", _kind=None):  # noqa: N802
        self._next_item_id += 1
        item = _FakeMenuItem(self._next_item_id, label)
        self.items.append(item)
        return item


class _FakeMenuBar:
    def __init__(self) -> None:
        self.menus: list[tuple[_FakeMenu, str]] = []

    def Append(self, menu: _FakeMenu, title: str) -> None:  # noqa: N802
        self.menus.append((menu, title))


class _FakeMenuOpenEvent:
    def __init__(self, menu: _FakeMenu) -> None:
        self._menu = menu
        self.skipped = False

    def GetMenu(self) -> _FakeMenu:  # noqa: N802
        return self._menu

    def Skip(self) -> None:  # noqa: N802
        self.skipped = True


class _FakeFrame:
    def __init__(self, frame_id: int) -> None:
        self._id = frame_id
        self.calls: list[str] = []
        self.menu_open_handler = None

    def GetId(self) -> int:  # noqa: N802 - wx shape
        return self._id

    def Show(self) -> None:  # noqa: N802
        self.calls.append("Show")

    def Raise(self) -> None:  # noqa: N802
        self.calls.append("Raise")

    def SetFocus(self) -> None:  # noqa: N802
        self.calls.append("SetFocus")

    def SetAcceleratorTable(self, table) -> None:  # noqa: N802
        pass

    def Bind(self, event, handler, id=None) -> None:  # noqa: N802, A002
        if event == "EVT_MENU_OPEN":
            self.menu_open_handler = handler


def _wm_with(*frames: _FakeFrame) -> WindowManager:
    wm = WindowManager(_FakeWx())
    titles = ["Main", "Browse", "Weather", "Manager"]
    for frame, title in zip(frames, titles, strict=False):
        wm.register(frame, title)
    return wm


def test_register_tracks_and_activates() -> None:
    a, b, c = _FakeFrame(1), _FakeFrame(2), _FakeFrame(3)
    wm = _wm_with(a, b, c)
    assert len(wm) == 3
    assert wm.activate("2") is b
    assert b.calls == ["Show", "Raise", "SetFocus"]  # raised, shown, focused


def test_next_previous_cycle() -> None:
    a, b, c = _FakeFrame(1), _FakeFrame(2), _FakeFrame(3)
    wm = _wm_with(a, b, c)
    assert wm.activate_next(a) is b
    assert wm.activate_next(c) is a  # wraps to the first
    assert wm.activate_previous(a) is c  # wraps to the last
    assert wm.activate_previous(b) is a


def test_activate_number_is_one_based_and_bounded() -> None:
    a, b, c = _FakeFrame(1), _FakeFrame(2), _FakeFrame(3)
    wm = _wm_with(a, b, c)
    assert wm.activate_number(1) is a
    assert wm.activate_number(3) is c
    assert wm.activate_number(0) is None
    assert wm.activate_number(4) is None


def test_unregister_renumbers_and_previous_key_for_close() -> None:
    a, b, c = _FakeFrame(1), _FakeFrame(2), _FakeFrame(3)
    wm = _wm_with(a, b, c)
    # Closing b: the window to fall back to is the one before it (a).
    assert wm.previous_key(b) == "1"
    wm.unregister(b)
    assert len(wm) == 2
    assert wm.activate_number(2) is c  # c renumbered from position 3 to 2
    assert wm.activate("3") is c  # its stable key is unchanged
    assert wm.activate("2") is None  # b's key is gone


def test_activate_unknown_key_is_safe() -> None:
    wm = _wm_with(_FakeFrame(1))
    assert wm.activate("999") is None


def _installed_manager() -> tuple[WindowManager, _FakeFrame, _FakeMenuBar]:
    wm = WindowManager(_FakeWx())
    frame = _FakeFrame(1)
    wm.register(frame, "Quill Radio")
    bar = _FakeMenuBar()
    wm.install(frame, bar)
    assert frame.menu_open_handler is not None
    return wm, frame, bar


def test_menu_open_rebuilds_only_the_window_menu() -> None:
    _wm, frame, bar = _installed_manager()
    window_menu = bar.menus[0][0]
    event = _FakeMenuOpenEvent(window_menu)
    frame.menu_open_handler(event)
    assert [item.label for item in window_menu.items] == ["&1 Quill Radio\tCtrl+1"]
    assert window_menu.items[0].checked  # the current window is ticked
    assert event.skipped


def test_menu_open_leaves_popup_context_menus_alone() -> None:
    # Regression: popup context menus report an empty title, and the old
    # title-based match ("Window" or "") rebuilt them too -- Shift+F10 on the
    # favorites tree showed the numbered window list instead of Play/Remove/....
    _wm, frame, _bar = _installed_manager()
    popup = _FakeMenu()  # a context menu: empty title, its own items
    popup.Append(-1, "&Play")
    popup.Append(-1, "&Remove...\tDelete")
    event = _FakeMenuOpenEvent(popup)
    frame.menu_open_handler(event)
    assert [item.label for item in popup.items] == ["&Play", "&Remove...\tDelete"]
    assert event.skipped
