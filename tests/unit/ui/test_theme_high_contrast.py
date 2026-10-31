"""High contrast keeps the person's own theme colours (OSAF testing-4 review).

``_apply_theme("system")`` used to swap in black on white with a yellow frame
whenever Windows high contrast was on. Under high contrast the system colours
already are the person's chosen theme, so forcing a palette replaced, say,
High Contrast Black's white on black with its opposite. The system theme now
always reads the system colours.
"""

from __future__ import annotations

from quill.ui.main_frame import MainFrame


class _Colour:
    def __init__(self, r: int, g: int, b: int) -> None:
        self.rgb = (r, g, b)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Colour) and self.rgb == other.rgb

    def __hash__(self) -> int:
        return hash(self.rgb)


class _Window:
    def __init__(self) -> None:
        self.fg: object = None
        self.bg: object = None

    def SetForegroundColour(self, colour: object) -> bool:  # noqa: N802
        self.fg = colour
        return True

    def SetBackgroundColour(self, colour: object) -> bool:  # noqa: N802
        self.bg = colour
        return True

    def Refresh(self) -> None:  # noqa: N802
        pass


#: A dark high contrast theme: white text on black, cyan frame.
_SYSTEM = {1: _Colour(255, 255, 255), 2: _Colour(0, 0, 0), 3: _Colour(0, 255, 255)}


class _SystemSettings:
    @staticmethod
    def GetColour(index: int) -> _Colour:  # noqa: N802
        return _SYSTEM[index]


class _Wx:
    SYS_COLOUR_WINDOWTEXT = 1
    SYS_COLOUR_WINDOW = 2
    SYS_COLOUR_3DFACE = 3
    Colour = _Colour
    SystemSettings = _SystemSettings

    @staticmethod
    def CallAfter(*_args: object) -> None:  # noqa: N802
        pass


def test_system_theme_uses_the_high_contrast_theme_colours(monkeypatch) -> None:
    monkeypatch.setattr(MainFrame, "apply_editor_font", lambda self: None)
    monkeypatch.setattr(MainFrame, "apply_status_bar_visibility", lambda self: None)
    frame = MainFrame.__new__(MainFrame)
    frame._wx = _Wx()
    frame.frame = _Window()
    frame.statusbar = _Window()
    frame.editor = _Window()

    frame._apply_theme("system")

    assert frame.editor.fg == _SYSTEM[1]
    assert frame.editor.bg == _SYSTEM[2]
    assert frame.frame.bg == _SYSTEM[3]
    assert frame.statusbar.fg == _SYSTEM[1]
