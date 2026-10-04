"""Announce Contrast Ratio speaks its answer whatever the startup-tips setting.

It used to speak only when "Speak startup readiness and theme contrast
announcements" was on -- which is off by default -- so pressing the key put the
answer in the status bar and said nothing. That setting is for what QUILL says
on its own at startup; a command somebody pressed always answers out loud.
"""

from __future__ import annotations

import pytest

pytest.importorskip("wx")

from quill.ui.main_frame import MainFrame  # noqa: E402


class _Colour:
    def __init__(self, value: int) -> None:
        self.value = value

    def Red(self) -> int:  # noqa: N802 - wx spelling
        return self.value

    def Green(self) -> int:  # noqa: N802 - wx spelling
        return self.value

    def Blue(self) -> int:  # noqa: N802 - wx spelling
        return self.value


class _Editor:
    def GetForegroundColour(self) -> _Colour:  # noqa: N802 - wx spelling
        return _Colour(0)

    def GetBackgroundColour(self) -> _Colour:  # noqa: N802 - wx spelling
        return _Colour(255)


@pytest.mark.parametrize("startup_tips", [False, True])
def test_the_command_always_speaks(startup_tips: bool) -> None:
    frame = MainFrame.__new__(MainFrame)
    frame.editor = _Editor()
    frame.settings = type("S", (), {"announcement_startup_tips_enabled": startup_tips})()
    spoken: list[str] = []
    frame._announce = lambda message, **_kw: spoken.append(message)  # type: ignore[method-assign]
    frame._set_status_quiet = lambda _message: None  # type: ignore[method-assign]
    frame._set_status = lambda _message: None  # type: ignore[method-assign]

    frame.announce_contrast_ratio()

    assert spoken == ["Contrast ratio: 21.0:1, WCAG grade: AAA (excellent)"]
