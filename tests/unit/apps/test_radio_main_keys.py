"""The keys Quill Radio's main window answers that no menu item carries.

Alt+1..0 quick-play, Stop and Ctrl+Shift+O mute did nothing on the main window
until 2026-09-25, while the palette, the first-run screen and the tutorials all
taught them (``quill/apps/radio_main_keys.py``). ``chord_of`` and ``resolve``
are pure, so what a press means is pinned here without a wx main loop; the char
hook itself is driven with a fake event.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.apps import radio_main_keys as keys
from quill.core.app_keymaps import APP_KEYMAPS
from quill.core.radio import transport_commands as tc


def _shipped(command_id: str) -> str | None:
    return APP_KEYMAPS["radio"].get(command_id)


def test_chord_of_spells_a_press_the_way_the_keymap_does() -> None:
    assert keys.chord_of(key="1", ctrl=False, alt=True, shift=False) == "Alt+1"
    assert keys.chord_of(key=".", ctrl=True, alt=False, shift=False) == "Ctrl+."
    assert keys.chord_of(key="O", ctrl=True, alt=False, shift=True) == "Ctrl+Shift+O"
    assert keys.chord_of(key="Q", ctrl=True, alt=True, shift=True) == "Ctrl+Alt+Shift+Q"


@pytest.mark.parametrize("slot", range(1, 11))
def test_alt_digit_plays_that_favorite(slot: int) -> None:
    digit = "0" if slot == 10 else str(slot)
    assert keys.resolve(f"Alt+{digit}", _shipped) == ("command", f"radio.play_favorite_{slot}")


def test_ctrl_period_is_the_keymap_stop_on_the_shipped_keys() -> None:
    assert keys.resolve("Ctrl+.", _shipped) == ("command", "radio.stop")


def test_a_rebound_stop_answers_and_the_transport_stop_still_stops() -> None:
    def rebound(command_id: str) -> str | None:
        return "Ctrl+Alt+Q" if command_id == "radio.stop" else _shipped(command_id)

    assert keys.resolve("Ctrl+Alt+Q", rebound) == ("command", "radio.stop")
    assert keys.resolve("Ctrl+.", rebound) == ("transport", tc.STOP)


def test_ctrl_shift_o_is_mute_as_in_every_other_window() -> None:
    assert keys.resolve("Ctrl+Shift+O", _shipped) == ("transport", tc.MUTE)


def test_keys_this_module_does_not_own_are_left_alone() -> None:
    # Ctrl+B is a menu accelerator (Browse Stations); the hook must pass it on.
    assert keys.resolve("Ctrl+B", _shipped) is None
    assert keys.resolve("Alt+1", lambda _cid: None) is None
    assert keys.resolve("", _shipped) is None


class _Event:
    def __init__(
        self, code: int, *, ctrl: bool = False, alt: bool = False, shift: bool = False
    ) -> None:
        self._code, self._ctrl, self._alt, self._shift = code, ctrl, alt, shift
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802
        return self._code

    def ControlDown(self) -> bool:  # noqa: N802
        return self._ctrl

    def AltDown(self) -> bool:  # noqa: N802
        return self._alt

    def ShiftDown(self) -> bool:  # noqa: N802
        return self._shift

    def Skip(self) -> None:  # noqa: N802
        self.skipped = True


class _Registry:
    def __init__(self) -> None:
        self.ran: list[str] = []

    def get(self, command_id: str) -> object:
        return object()

    def run(self, command_id: str) -> None:
        self.ran.append(command_id)


class _App:
    def __init__(self) -> None:
        self.commands = _Registry()

    def _binding_for(self, command_id: str) -> str | None:
        return _shipped(command_id)


class _Wx:
    WXK_SPACE = 32


def test_the_hook_runs_the_favorite_for_alt_digit() -> None:
    app, event = _App(), _Event(ord("3"), alt=True)
    keys._on_key(app, _Wx, event)
    assert app.commands.ran == ["radio.play_favorite_3"]
    assert not event.skipped


def test_the_hook_sends_ctrl_shift_o_to_the_transport(monkeypatch: Any) -> None:
    from quill.ui.radio import transport_keys

    performed: list[str] = []
    monkeypatch.setattr(transport_keys, "perform", lambda _host, cid: performed.append(cid))
    event = _Event(ord("O"), ctrl=True, shift=True)
    keys._on_key(_App(), _Wx, event)
    assert performed == [tc.MUTE]
    assert not event.skipped


def test_the_hook_passes_on_plain_typing_and_unowned_chords() -> None:
    app = _App()
    typed = _Event(ord("A"))
    keys._on_key(app, _Wx, typed)
    unowned = _Event(ord("B"), ctrl=True)
    keys._on_key(app, _Wx, unowned)
    assert typed.skipped and unowned.skipped
    assert app.commands.ran == []
