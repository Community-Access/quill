"""File > Show and Hide Key...: the picker's loop, driven with stand-ins (no wx
window is shown). A refused key is said in one sentence and the box comes back
holding what was typed; a key Windows will not give leaves the old one."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.show_hide_key_picker import (
    choose_show_hide_key,
    run_show_hide_key_command,
    run_system_key_command,
)


class _Dialog:
    answers: list[tuple[int, str]] = []
    shown: list[str] = []

    def __init__(self, _parent, prompt, _caption, value) -> None:
        self.prompt = prompt
        self.value = value
        _Dialog.shown.append(value)

    def GetValue(self) -> str:
        return self.value

    def Destroy(self) -> None:
        pass


_WX = SimpleNamespace(TextEntryDialog=_Dialog, ID_OK=5100, ID_CANCEL=5101, OK=4, ICON_WARNING=256)


class _Host:
    def __init__(self, *, registers: bool = True) -> None:
        self.frame = object()
        self.boxes: list[str] = []
        self.said: list[str] = []
        self.registered: list[str] = []
        self._registers = registers
        self._show_hide_key = ""

    def _show_modal_dialog(self, dialog, _label) -> int:
        result, typed = _Dialog.answers.pop(0)
        dialog.value = typed
        return result

    def _show_message_box(self, text, *_args) -> int:
        self.boxes.append(text)
        return _WX.OK

    def _announce(self, text, **_kw) -> None:
        self.said.append(text)

    def _replace_tray_hotkey(self, chord: str) -> bool:
        if not self._registers:
            return False
        self.registered.append(chord)
        self._show_hide_key = chord
        return True


def _answers(*pairs: tuple[int, str]) -> None:
    _Dialog.answers = list(pairs)
    _Dialog.shown = []


def test_a_refused_key_is_said_and_the_box_comes_back_with_it() -> None:
    host = _Host()
    _answers((_WX.ID_OK, "Ctrl+Alt+Shift+R"), (_WX.ID_OK, "Ctrl+Alt+Shift+PageUp"))
    chosen = choose_show_hide_key(host, _WX, app_id="weather", current="")
    assert chosen == "Ctrl+Alt+Shift+PageUp"
    assert host.boxes == ["Ctrl+Alt+Shift+R is already Quill Radio's show and hide key."]
    assert _Dialog.shown == ["", "Ctrl+Alt+Shift+R"]


def test_cancel_changes_nothing() -> None:
    host = _Host()
    _answers((_WX.ID_CANCEL, "Ctrl+Alt+Shift+PageUp"))
    assert choose_show_hide_key(host, _WX, app_id="player", current="") is None
    assert host.boxes == []


def test_an_empty_box_means_no_key() -> None:
    host = _Host()
    host._show_hide_key = "Ctrl+Alt+Shift+Left"
    kept: list[str] = []
    _answers((_WX.ID_OK, ""))
    run_show_hide_key_command(host, _WX, app_id="converter", save=kept.append)
    assert kept == [""]
    assert host.registered == [""]
    assert host.said == ["Quill Converter has no show and hide key."]


def test_a_chosen_key_is_registered_kept_and_said() -> None:
    host = _Host()
    kept: list[str] = []
    _answers((_WX.ID_OK, "Ctrl+Alt+Shift+PageDown"))
    run_show_hide_key_command(host, _WX, app_id="inkwell", save=kept.append)
    assert kept == ["Ctrl+Alt+Shift+PageDown"]
    assert host.said == ["Ctrl+Alt+Shift+PageDown now shows and hides Quill Inkwell."]


def test_a_key_windows_will_not_give_is_not_kept() -> None:
    host = _Host(registers=False)
    kept: list[str] = []
    _answers((_WX.ID_OK, "Ctrl+Alt+Shift+PageDown"))
    run_show_hide_key_command(host, _WX, app_id="weather", save=kept.append)
    assert kept == []
    assert host.said == [
        "Another program already uses Ctrl+Alt+Shift+PageDown, so Quill Weather kept its old key."
    ]


class _Keys:
    """Inkwell's Quick Insert key, kept and registered by stand-ins."""

    def __init__(self, *, registers: bool = True) -> None:
        self.kept: list[str] = []
        self.registered: list[str] = []
        self._registers = registers

    def replace(self, chord: str) -> bool:
        if self._registers:
            self.registered.append(chord)
        return self._registers


def _quick_insert(host: _Host, keys: _Keys, current: str = "", own=None) -> None:
    run_system_key_command(
        host,
        _WX,
        app_id="inkwell",
        current=current,
        caption="Quick Insert Key",
        purpose="opens Quill Inkwell's Quick Insert",
        name="Quick Insert",
        replace=keys.replace,
        save=keys.kept.append,
        own=own,
    )


def test_inkwells_quick_insert_key_is_chosen_through_the_same_picker() -> None:
    host, keys = _Host(), _Keys()
    _answers((_WX.ID_OK, "ctrl+shift+alt+pageup"))
    _quick_insert(host, keys)
    assert keys.kept == keys.registered == ["Ctrl+Alt+Shift+PageUp"]
    assert host.said == ["Ctrl+Alt+Shift+PageUp now opens Quill Inkwell's Quick Insert."]


def test_inkwells_old_key_is_refused_with_whose_it_is() -> None:
    host, keys = _Host(), _Keys()
    _answers((_WX.ID_OK, "Ctrl+Alt+Shift+X"), (_WX.ID_CANCEL, ""))
    _quick_insert(host, keys)
    assert len(host.boxes) == 1
    assert host.boxes[0].startswith("Ctrl+Alt+Shift+X is already a shortcut in ")
    assert keys.kept == []


def test_a_key_inkwell_already_uses_for_something_else_is_refused() -> None:
    host, keys = _Host(), _Keys()
    _answers((_WX.ID_OK, "Ctrl+Alt+Shift+PageDown"), (_WX.ID_OK, ""))
    _quick_insert(
        host, keys, current="Ctrl+Alt+PageUp", own={"Expand Word key": "Ctrl+Alt+Shift+PageDown"}
    )
    assert host.boxes == ["Ctrl+Alt+Shift+PageDown is already Quill Inkwell's Expand Word key."]
    assert keys.kept == [""]
    assert host.said == ["Quick Insert has no key."]


def test_a_quick_insert_key_without_ctrl_or_alt_is_refused() -> None:
    host, keys = _Host(), _Keys()
    _answers((_WX.ID_OK, "Shift+F9"), (_WX.ID_CANCEL, ""))
    _quick_insert(host, keys)
    assert host.boxes and "has no Ctrl or Alt" in host.boxes[0]


def test_a_quick_insert_key_windows_will_not_give_is_not_kept() -> None:
    host, keys = _Host(), _Keys(registers=False)
    _answers((_WX.ID_OK, "Ctrl+Alt+Shift+PageUp"))
    _quick_insert(host, keys)
    assert keys.kept == []
    assert host.said == [
        "Another program already uses Ctrl+Alt+Shift+PageUp, so Quick Insert kept its old key."
    ]


def test_the_quick_insert_prompt_says_what_the_key_does() -> None:
    from quill.ui.show_hide_key_picker import _prompt

    said = _prompt("inkwell", "", "opens Quill Inkwell's Quick Insert")
    assert said.startswith("Type the key that opens Quill Inkwell's Quick Insert from any program")


def test_the_prompt_says_what_the_key_is_now_and_offers_a_free_one() -> None:
    from quill.ui.show_hide_key_picker import _prompt

    said = _prompt("weather", "")
    assert "for example Ctrl+Alt+Shift+PageUp" in said
    assert "Leave the box empty for no key." in said
    assert "It has no key now." in said
    assert "It is Ctrl+Alt+Shift+Left now." in _prompt("weather", "Ctrl+Alt+Shift+Left")
