"""Make Quill Radio My Media Player: the editors' command, with Quill Radio's profile.

What is tested here is that Quill Radio runs the *shared* command (no second
implementation), with its own words, its own keys and its own Default apps
page; and that its doors are Preferences and the Command Palette, with no key.
The system seam is a fake that records registry writes in a dict, so no test
writes a real registry value or opens Settings.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.windows_media import RADIO  # noqa: E402
from quill.ui import text_editor_commands as shared  # noqa: E402
from quill.ui.radio import media_player_registration as media  # noqa: E402
from quill.ui.text_editor_commands import TextEditorCommandsMixin  # noqa: E402

LAUNCHER = r"C:\Users\me\AppData\Local\Programs\Quill Radio\QuillRadio.exe"
ICON = r"C:\Users\me\AppData\Local\Programs\Quill Radio\quill-radio.ico"
REPO = Path(__file__).resolve().parents[4]


class _Reader:
    def __init__(self, keys: dict[str, dict[str, object]] | None = None) -> None:
        self.keys = keys or {}

    def value(self, path: str, name: str) -> object | None:
        return self.keys.get(path, {}).get(name)

    def subkeys(self, path: str) -> list[str]:
        return []


class _System:
    DONE, DECLINED, FAILED = "done", "declined", "failed"

    def __init__(self, reader: _Reader, *, build: int = 22631, opens: bool = True) -> None:
        self.reader = reader
        self.build = build
        self.opens = opens
        self.written: dict[tuple[str, str], str] = {}
        self.opened: list[str] = []

    def CurrentUserWriter(self) -> object:  # noqa: N802 - the class it stands in for
        fake = self

        class _Writer:
            def set_value(self, path: str, name: str, data: str, kind: str) -> None:
                fake.written[(path, name)] = data

        return _Writer()

    def MachineReader(self) -> _Reader:  # noqa: N802 - the class it stands in for
        return self.reader

    def notify_association_change(self) -> None:
        pass

    def open_settings(self, uri: str) -> bool:
        self.opened.append(uri)
        return self.opens

    def windows_build(self) -> int:
        return self.build


class _App:
    def __init__(self) -> None:
        self.frame = SimpleNamespace()
        self.said: list[str] = []

    def _announce(self, text: str, **_kwargs: Any) -> None:
        self.said.append(text)


@pytest.fixture
def answers(monkeypatch):
    state = SimpleNamespace(replies=[], asked=[])

    def fake_box(message, caption, style, parent=None, **_kw):
        state.asked.append((caption, message, parent))
        return state.replies.pop(0)

    monkeypatch.setattr(shared, "show_message_box", fake_box)
    monkeypatch.setattr(shared, "launcher", lambda _profile: ([LAUNCHER], ICON))
    return state


def _system(monkeypatch, reader: _Reader | None = None, **kwargs: Any) -> _System:
    fake = _System(reader or _Reader(), **kwargs)
    monkeypatch.setattr(shared, "system", fake)
    return fake


def test_radio_runs_the_shared_command_rather_than_its_own() -> None:
    assert issubclass(media.RadioMediaPlayer, TextEditorCommandsMixin)
    own = {name for name in vars(media.RadioMediaPlayer) if name.startswith("cmd_")}
    assert own == set(), f"Quill Radio has grown its own registration command: {sorted(own)}"


def test_ok_registers_radio_and_opens_its_default_apps_page(monkeypatch, answers) -> None:
    fake = _system(monkeypatch)
    answers.replies = [wx.OK]
    app = _App()
    assert media.make_media_player(app)
    caption, message, parent = answers.asked[0]
    assert parent is app.frame, "with no window active, the main window owns the question"
    assert caption == "Make Quill Radio My Media Player"
    assert "only you can choose" in message
    assert "choose .mp3, pick Quill Radio" in message
    assert "music, audiobooks, video and playlists" in message
    command = rf"Software\Classes\{RADIO.progid}\shell\open\command"
    assert fake.written[(command, "")] == f'"{LAUNCHER}" "%1"'
    assert fake.written[(r"Software\RegisteredApplications", "Quill Radio")] == (
        RADIO.capabilities_key
    )
    assert fake.opened == ["ms-settings:defaultapps?registeredAppUser=Quill%20Radio"]
    assert app.said == [
        "Quill Radio is ready in Default apps. Choose it for .mp3 and any other type."
    ]


def test_cancel_writes_nothing(monkeypatch, answers) -> None:
    fake = _system(monkeypatch)
    answers.replies = [wx.CANCEL]
    app = _App()
    assert not media.make_media_player(app)
    assert fake.written == {} and fake.opened == [] and app.said == []


def test_an_installed_copy_for_everyone_is_not_copied(monkeypatch, answers) -> None:
    reader = _Reader({
        rf"Software\Classes\{RADIO.progid}\shell\open\command": {"": f'"{LAUNCHER}" "%1"'},
        r"Software\RegisteredApplications": {"Quill Radio": RADIO.capabilities_key},
    })
    fake = _system(monkeypatch, reader)
    answers.replies = [wx.OK]
    media.make_media_player(_App())
    assert fake.written == {}
    assert fake.opened == ["ms-settings:defaultapps?registeredAppMachine=Quill%20Radio"]


def test_when_settings_will_not_open_the_way_there_is_said(monkeypatch, answers) -> None:
    _system(monkeypatch, opens=False)
    answers.replies = [wx.OK]
    app = _App()
    media.make_media_player(app)
    assert app.said == [
        "Quill Radio is registered. Open Settings, then Apps, then Default apps, "
        "and choose Quill Radio for .mp3 and any other type."
    ]


def test_the_palette_has_it_and_no_key_does() -> None:
    from quill.core.app_keymaps import APP_KEYMAPS
    from quill.core.keymap import DEFAULT_KEYMAP

    registered: list[tuple[str, str]] = []
    app = SimpleNamespace(
        commands=SimpleNamespace(
            try_register=lambda cid, title, _h, _b, **_k: registered.append((cid, title))
        ),
        _binding_for=lambda _cid: None,
    )
    media.register(app)
    assert registered == [(media.COMMAND_ID, media.COMMAND_TITLE)]
    assert media.COMMAND_ID not in DEFAULT_KEYMAP
    assert media.COMMAND_ID not in APP_KEYMAPS.get("radio", {})


def test_preferences_carry_the_button_in_windows_and_your_files() -> None:
    from quill.ui.text_editor_prefs import GROUP_TITLE

    assert media.GROUP_TITLE == GROUP_TITLE
    source = (REPO / "quill" / "apps" / "radio_preferences.py").read_text(encoding="utf-8")
    assert "media_player.BUTTON_LABEL" in source
    assert "group=media_player.GROUP_TITLE" in source
    assert "&Q" in media.BUTTON_LABEL


def test_only_standalone_radio_registers_it() -> None:
    """Embedded QUILL is a different program; registering it as Radio would lie."""
    launch = (REPO / "quill" / "apps" / "radio_launch_tasks.py").read_text(encoding="utf-8")
    assert "media_player_registration.register(app)" in launch
    palette = (REPO / "quill" / "ui" / "radio" / "palette_commands.py").read_text(encoding="utf-8")
    assert "media_player" not in palette
