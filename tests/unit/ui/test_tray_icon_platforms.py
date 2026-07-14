"""#29: 'Enable system tray mode' was a no-op on macOS. _ensure_tray_icon used
to construct wx.adv.TaskBarIcon() unconditionally, which on macOS produces a
Dock tile rather than the menu-bar item a Mac user expects when toggling a
'tray' setting. We now short-circuit on darwin, surface a one-shot status
message, and let the close handler fall through to a real close."""

from __future__ import annotations

from quill.ui.main_frame import MainFrame


class _Frame:
    pass


class _StubTaskBarIcon:
    def __init__(self) -> None:
        self.icon_set: tuple[object, str] | None = None
        self.bindings: list[tuple[object, object]] = []

    def SetIcon(self, icon: object, tooltip: str) -> None:
        self.icon_set = (icon, tooltip)

    def Bind(self, event: object, handler: object) -> None:
        self.bindings.append((event, handler))


class _StubAdv:
    def __init__(self, sink: list[_StubTaskBarIcon]) -> None:
        self._sink = sink
        # Event-type constants the constructor path binds against.
        self.EVT_TASKBAR_LEFT_DCLICK = object()
        self.EVT_TASKBAR_RIGHT_UP = object()

    def TaskBarIcon(self, *args, **kwargs) -> _StubTaskBarIcon:
        instance = _StubTaskBarIcon()
        self._sink.append(instance)
        return instance


class _StubArtProvider:
    @staticmethod
    def GetIcon(*args, **kwargs) -> object:
        return object()


class _StubWx:
    def __init__(self, sink: list[_StubTaskBarIcon]) -> None:
        self.adv = _StubAdv(sink)
        self.ArtProvider = _StubArtProvider
        self.ART_INFORMATION = object()
        self.ART_OTHER = object()


def _build_frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.frame = _Frame()
    frame._status: list[str] = []
    frame._set_status = lambda message: frame._status.append(message)  # type: ignore[method-assign]
    frame._tray_icon = None
    return frame


def test_ensure_tray_icon_short_circuits_on_macos(monkeypatch) -> None:
    import quill.ui.main_frame as main_frame_module

    frame = _build_frame()
    monkeypatch.setattr(main_frame_module.sys, "platform", "darwin")
    constructed: list[_StubTaskBarIcon] = []
    frame._wx = _StubWx(constructed)

    frame._ensure_tray_icon()

    assert constructed == []
    assert len(frame._status) == 1
    assert "macOS" in frame._status[0]


def test_ensure_tray_icon_status_message_announced_only_once(monkeypatch) -> None:
    import quill.ui.main_frame as main_frame_module

    frame = _build_frame()
    monkeypatch.setattr(main_frame_module.sys, "platform", "darwin")
    constructed: list[_StubTaskBarIcon] = []
    frame._wx = _StubWx(constructed)

    frame._ensure_tray_icon()
    frame._ensure_tray_icon()
    frame._ensure_tray_icon()

    assert len(frame._status) == 1


def test_ensure_tray_icon_constructs_on_windows(monkeypatch) -> None:
    import quill.ui.main_frame as main_frame_module

    frame = _build_frame()
    monkeypatch.setattr(main_frame_module.sys, "platform", "win32")
    constructed: list[_StubTaskBarIcon] = []
    frame._wx = _StubWx(constructed)

    frame._ensure_tray_icon()

    assert len(constructed) == 1
    assert frame._status == []
    # The icon was set and the two mouse handlers were bound — the original
    # Windows/Linux behaviour is preserved.
    assert constructed[0].icon_set is not None
    assert len(constructed[0].bindings) == 2


def test_ensure_tray_icon_constructs_on_linux(monkeypatch) -> None:
    import quill.ui.main_frame as main_frame_module

    frame = _build_frame()
    monkeypatch.setattr(main_frame_module.sys, "platform", "linux")
    constructed: list[_StubTaskBarIcon] = []
    frame._wx = _StubWx(constructed)

    frame._ensure_tray_icon()

    assert len(constructed) == 1
    assert frame._status == []
