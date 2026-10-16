"""QUILL Transcribe's dictation is the editors': keys, settings and commands (D-14).

The sibling of ``test_dictation_parity.py``, which holds QUILL and QUILL Lite
to each other. QUILL Transcribe runs the same controller, so:

* every dictation command the editors have is either on the editors' chord
  here or a row in :data:`quill.core.transcribe.parity.DIVERGENCES` with a
  reason (family rules 2 and 11), and the menu really shows that chord;
* QUILL Transcribe 1.0's own keys still work (rule 5) and claim nothing else;
* its dictation settings are the editors' fields, with a documented subset
  switched off (``PREFERENCES_OFF``);
* every voice command that works in other programs is in its "What can I say"
  list.

The menu is the real one, built over a stand-in host, because that is what a
listener meets.
"""

from __future__ import annotations

import collections
import dataclasses
from typing import Any

import pytest

from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.lite.commands import COMMANDS
from quill.core.lite.parity import COMMAND_EQUIVALENTS
from quill.core.transcribe.parity import (
    ALIASES,
    DIVERGENCES,
    PREFERENCES_OFF,
    SHARED_COMMANDS,
    chord,
)

wx = pytest.importorskip("wx")


def _editor_dictation_commands() -> set[str]:
    """Every dictation command in both editors, by QUILL's id."""
    commands = {
        COMMAND_EQUIVALENTS[row[3]]
        for row in COMMANDS
        if row[3] and ("Dictation" in row[0] or "dictation" in row[3])
    }
    assert commands, "QUILL Lite's command table lost its Dictation rows"
    return commands


def test_every_editor_dictation_command_is_shared_or_has_a_reason() -> None:
    editors = _editor_dictation_commands()
    assert set(SHARED_COMMANDS).isdisjoint(DIVERGENCES)
    assert set(SHARED_COMMANDS) | set(DIVERGENCES) == editors, (
        "missing: "
        + str(sorted(editors - set(SHARED_COMMANDS) - set(DIVERGENCES)))
        + "; not an editor command: "
        + str(sorted((set(SHARED_COMMANDS) | set(DIVERGENCES)) - editors))
    )
    for command, reason in DIVERGENCES.items():
        assert len(reason.split()) >= 12, f"{command}: a reason is a sentence or two"


def test_every_shared_command_has_its_handler_here() -> None:
    from quill.apps.transcribe import QuillTranscribeFrame

    for command, method in SHARED_COMMANDS.items():
        assert callable(getattr(QuillTranscribeFrame, method, None)), (command, method)
        assert chord(command) == DEFAULT_KEYMAP[command]
    assert set(ALIASES) <= set(SHARED_COMMANDS.values())


class _Host:
    """Just enough of QuillTranscribeFrame for the real menu builder."""

    def __init__(self, frame: Any) -> None:
        from quill.core.transcribe.settings import TranscribeSettings
        from quill.ui.window_menu import WindowManager

        self.frame = frame
        self._settings = TranscribeSettings()
        self._windows = WindowManager(wx)
        self._ids: list[Any] = []
        self.ran: list[str] = []

    def _keep_menu_ids(self, *refs: Any) -> None:
        self._ids.extend(refs)

    def dictation_armed(self) -> bool:
        return False

    def dictation_active(self) -> bool:
        return False

    def launch_at_startup_enabled(self) -> bool:
        return False

    def _append_key_items(self, menu: Any) -> None:
        item_id = wx.NewIdRef()
        menu.Append(item_id, "Start and Stop &Key...\tCtrl+Alt+Shift+D")
        self._ids.append(item_id)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *_a, **_k: self.ran.append(name)


@pytest.fixture()
def transcribe_menu(monkeypatch: pytest.MonkeyPatch) -> Any:
    from quill.apps.transcribe_menus import build_menu_bar

    app = wx.App.Get() or wx.App()
    tables: list[list[Any]] = []
    real_table = wx.AcceleratorTable

    def table(entries: list[Any]) -> Any:
        tables.append(list(entries))
        return real_table(entries)

    monkeypatch.setattr(wx, "AcceleratorTable", table)
    frame = wx.Frame(None)
    host = _Host(frame)
    build_menu_bar(host, title="QUILL Transcribe", version="1.0.0")
    yield frame.GetMenuBar(), tables[-1]
    frame.Destroy()
    del app


def _rows(menu_bar: Any) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []

    def walk(menu: Any) -> None:
        for item in menu.GetMenuItems():
            if item.IsSeparator():
                continue
            if item.GetSubMenu() is not None:
                walk(item.GetSubMenu())
                continue
            label = item.GetItemLabel()
            name, _tab, key = label.partition("\t")
            rows.append((name.replace("&", ""), key))

    for index in range(menu_bar.GetMenuCount()):
        walk(menu_bar.GetMenu(index))
    return rows


def test_the_menu_shows_the_editors_chord_for_every_shared_command(transcribe_menu: Any) -> None:
    menu_bar, _table = transcribe_menu
    keys = {key for _name, key in _rows(menu_bar)}
    for command in SHARED_COMMANDS:
        assert chord(command) in keys, (command, chord(command))
    for old in ALIASES.values():
        assert old not in keys, f"{old} should be the second key, not the one shown"


def test_no_key_is_claimed_twice_and_the_1_0_keys_still_work(transcribe_menu: Any) -> None:
    from quill.core.keymap_query import canonical_binding

    menu_bar, table = transcribe_menu
    claimed: dict[str, list[str]] = collections.defaultdict(list)
    for name, key in _rows(menu_bar):
        assert key, f"{name} shows no key"
        claimed[canonical_binding(key) or key].append(name)
    for method, key in ALIASES.items():
        claimed[canonical_binding(key) or key].append(f"alias for {method}")
    assert {key: who for key, who in claimed.items() if len(who) > 1} == {}
    by_id = {int(item.GetId()): item.GetItemLabel() for item in _items(menu_bar)}
    aliased = {}
    for entry in table:
        command = int(entry.GetCommand())
        if command in by_id:
            aliased[entry.ToString()] = by_id[command].partition("\t")[2]
    expected = {key: chord(_command_for(method)) for method, key in ALIASES.items()}
    assert {canonical_binding(k): v for k, v in aliased.items()} == {
        canonical_binding(k): v for k, v in expected.items()
    }


def _items(menu_bar: Any) -> list[Any]:
    found: list[Any] = []

    def walk(menu: Any) -> None:
        for item in menu.GetMenuItems():
            if item.GetSubMenu() is not None:
                walk(item.GetSubMenu())
            elif not item.IsSeparator():
                found.append(item)

    for index in range(menu_bar.GetMenuCount()):
        walk(menu_bar.GetMenu(index))
    return found


def _command_for(method: str) -> str:
    return next(command for command, name in SHARED_COMMANDS.items() if name == method)


def test_the_settings_are_the_editors_with_a_documented_subset_off() -> None:
    """The same fields, loaded by the same loader; only PREFERENCES_OFF differs."""
    from quill.apps.transcribe_dictation import TranscribeDictationMixin
    from quill.core.transcribe.settings import TRANSCRIBE_DICTATION_DEFAULTS, TranscribeSettings
    from quill.core.windows_dictation.anywhere import settings_from
    from quill.core.windows_dictation.preferences import DictationPreferences
    from quill.core.windows_dictation.settings_fields import DictationSettings

    names = {field.name for field in dataclasses.fields(DictationSettings)}
    assert {field.name for field in dataclasses.fields(settings_from({}))} == names
    assert set(TRANSCRIBE_DICTATION_DEFAULTS) <= names
    for reason in PREFERENCES_OFF.values():
        assert len(reason.split()) >= 12

    stored = {
        "windows_dictation_wake_enabled": True,
        "windows_dictation_hold_to_talk": True,
        "windows_dictation_pause": "long",
        "windows_dictation_speech_language": "es",
    }

    class _Host(TranscribeDictationMixin):
        _settings = TranscribeSettings(dictation=dict(stored))
        _engine_override = ""

    transcribe = _Host()._dictation_preferences()
    editors = DictationPreferences.from_settings(
        settings_from({**TRANSCRIBE_DICTATION_DEFAULTS, **stored}), rewrite=None
    )
    differ = {
        field.name
        for field in dataclasses.fields(DictationPreferences)
        if field.compare
        and field.name != "rewrite"
        and getattr(transcribe, field.name) != getattr(editors, field.name)
    }
    assert differ == set(PREFERENCES_OFF)
    assert all(getattr(transcribe, name) is False for name in PREFERENCES_OFF)
    # D-9: the wake phrase and holding the key to talk are the editors' again.
    assert PREFERENCES_OFF == {}
    assert transcribe.wake_enabled is True and transcribe.hold_to_talk is True


def test_wake_and_hold_default_off_in_all_three() -> None:
    """D-9's acceptance: both off until the person turns them on, everywhere."""
    from quill.apps.transcribe_dictation import TranscribeDictationMixin
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings
    from quill.core.transcribe.settings import TranscribeSettings

    class _Host(TranscribeDictationMixin):
        _settings = TranscribeSettings()
        _engine_override = ""

    transcribe = _Host()._dictation_preferences()
    assert transcribe.wake_enabled is False and transcribe.hold_to_talk is False
    for editor in (Settings(), LiteSettings()):
        assert editor.windows_dictation_wake_enabled is False
        assert editor.windows_dictation_hold_to_talk is False


def test_every_command_that_works_in_other_programs_is_in_what_can_i_say() -> None:
    """QUILL Transcribe's Dictation Commands window shows only what works in
    another program (commands_reference(external=True), D-7), and all of it."""
    from quill.core.windows_dictation.anywhere import EXTERNAL_COMMANDS
    from quill.core.windows_dictation.reference import commands_reference
    from quill.core.windows_dictation.vocabulary import COMMAND_HELP, PREFIX_HELP
    from quill.core.windows_dictation.vocabulary_types import Command
    from quill.core.windows_dictation.wake import DEFAULT_STOP_PHRASE

    reference = commands_reference(external=True).lower()
    said: dict[Any, list[str]] = collections.defaultdict(list)
    for entry in COMMAND_HELP:
        said[entry.command].extend(entry.phrases)
    for prefix in PREFIX_HELP:
        said[prefix.command].extend(prefix.prefixes)
    for command in EXTERNAL_COMMANDS:
        if command is Command.STOP and command not in said:
            assert DEFAULT_STOP_PHRASE.lower() in reference
            continue
        assert said[command], f"{command} works in other programs and is in no list"
        assert any(phrase.lower() in reference for phrase in said[command]), command
