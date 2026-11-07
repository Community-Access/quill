"""The WordPress keys: Ctrl+Alt+Shift+Grave, then one letter, in both editors.

wordpress.md 19, option 1. Three things are pinned here: the shared layer's own
answers (a letter, Escape, an unknown key, a timeout), that both editors build
their keys from the one letter table, and that each editor's key hook hands
every letter to the shared command its menu row names -- not to a second copy.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.wordpress import keys
from quill.core.wordpress.menu import LAYER_KEYS, LAYER_PREFIX, all_rows, layer_chord, lite_handler

#: Command id -> the shared WordPressCommands method its menu row names.
_SHARED = {command_id: handler for _path, (command_id, _title, handler) in all_rows()}


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


# --------------------------------------------------------------------------- #
# The shared layer


def test_every_letter_names_a_real_row_and_no_row_has_two_letters() -> None:
    assert set(LAYER_KEYS.values()) <= set(_SHARED)
    assert len(set(LAYER_KEYS.values())) == len(LAYER_KEYS)


def test_the_everyday_six_are_on_the_letters_jeff_chose() -> None:
    assert LAYER_KEYS["O"] == "wordpress.open"
    assert LAYER_KEYS["P"] == "wordpress.publish"
    assert LAYER_KEYS["M"] == "wordpress.media_library"
    assert LAYER_KEYS["S"] == "wordpress.switch_site"
    assert LAYER_KEYS["W"] == "wordpress.open_by_address"
    assert LAYER_KEYS["D"] == "wordpress.save_draft"


def test_a_letter_runs_its_command_and_ends_the_layer() -> None:
    layer = keys.WordPressKeyLayer()
    table = keys.layer_from_bindings(keys.default_bindings())
    assert layer.start() == "WordPress keys"
    assert layer.active
    assert layer.press("O", table) == keys.Outcome(command="wordpress.open")
    assert not layer.active


def test_shift_is_part_of_the_key() -> None:
    layer = keys.WordPressKeyLayer()
    table = keys.layer_from_bindings(keys.default_bindings())
    layer.start()
    assert layer.press("Shift+S", table).command == "wordpress.sites"
    layer.start()
    assert layer.press("S", table).command == "wordpress.switch_site"


def test_escape_leaves_with_a_short_sentence() -> None:
    layer = keys.WordPressKeyLayer()
    layer.start()
    assert layer.press(keys.ESCAPE, {}) == keys.Outcome(message="Left WordPress keys")
    assert not layer.active


def test_an_unknown_letter_says_so_and_is_not_typed() -> None:
    layer = keys.WordPressKeyLayer()
    layer.start()
    outcome = layer.press("Q", keys.layer_from_bindings(keys.default_bindings()))
    assert outcome == keys.Outcome(message="No WordPress command on Q.")
    assert outcome.consumed


def test_after_the_timeout_the_key_is_the_editors_again() -> None:
    clock = _Clock()
    layer = keys.WordPressKeyLayer(clock=clock)
    layer.start()
    clock.now += keys.TIMEOUT_SECONDS + 0.1
    assert layer.press("O", {"O": "wordpress.open"}) == keys.Outcome(consumed=False)


def test_a_moved_key_moves_the_letter() -> None:
    bindings = {"wordpress.open": f"{LAYER_PREFIX}, Shift+Q", "file.save": "Ctrl+S"}
    assert keys.layer_from_bindings(bindings) == {"Shift+Q": "wordpress.open"}


def test_event_key_spells_letters_and_lets_the_rest_through() -> None:
    assert keys.event_key(ord("O"), ctrl=False, alt=False, shift=False) == "O"
    assert keys.event_key(ord("s"), ctrl=False, alt=False, shift=True) == "Shift+S"
    assert keys.event_key(27, ctrl=False, alt=False, shift=False) == keys.ESCAPE
    assert keys.event_key(13, ctrl=False, alt=False, shift=False) == ""
    assert keys.event_key(9, ctrl=False, alt=False, shift=False) == ""


# --------------------------------------------------------------------------- #
# One table, both editors


def test_quill_binds_every_letter_as_a_two_press_key() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP

    for key, command_id in LAYER_KEYS.items():
        assert DEFAULT_KEYMAP[command_id] == f"{LAYER_PREFIX}, {key}"


def test_quill_lite_rows_carry_the_same_keys() -> None:
    from quill.core.lite.commands import COMMANDS

    lite = {handler: key for _menu, _label, key, handler, _kind in COMMANDS}
    for command_id in LAYER_KEYS.values():
        assert lite[lite_handler(command_id)] == layer_chord(command_id)


def test_the_prefix_is_free_everywhere() -> None:
    """No chord in either editor, and no family app's system-wide key, is the prefix."""
    from quill.core.family_chords import SHOW_HIDE_DEFAULTS
    from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS
    from quill.core.lite.keymap import DEFAULT_ALIASES as LITE_ALIASES
    from quill.core.lite.keymap import chord_identity

    prefix = chord_identity(LAYER_PREFIX)
    chords = [
        *DEFAULT_KEYMAP.values(),
        *DEFAULT_ALIASES.values(),
        *(row[2] for row in COMMANDS),
        *LITE_ALIASES.values(),
        *SHOW_HIDE_DEFAULTS.values(),
    ]
    assert [c for c in chords if c and chord_identity(c) == prefix] == []


# --------------------------------------------------------------------------- #
# The two key hooks


class _Event:
    def __init__(self, code: int, *, ctrl=False, alt=False, shift=False, raw: int = 0) -> None:
        self._code, self._ctrl, self._alt, self._shift, self._raw = code, ctrl, alt, shift, raw

    def GetKeyCode(self) -> int:  # noqa: N802 - wx's name
        return self._code

    def GetRawKeyCode(self) -> int:  # noqa: N802 - wx's name
        return self._raw

    def GetUnicodeKey(self) -> int:  # noqa: N802 - wx's name
        return self._code

    def GetRawKeyFlags(self) -> int:  # noqa: N802 - wx's name
        return 0

    def ControlDown(self) -> bool:  # noqa: N802 - wx's name
        return self._ctrl

    def AltDown(self) -> bool:  # noqa: N802 - wx's name
        return self._alt

    def ShiftDown(self) -> bool:  # noqa: N802 - wx's name
        return self._shift


def _prefix() -> _Event:
    return _Event(0xC0, ctrl=True, alt=True, shift=True, raw=0xC0)


class _Shared:
    """Stands in for WordPressCommands: records which shared method ran."""

    def __init__(self) -> None:
        self.ran: list[str] = []

    def __getattr__(self, name: str):
        if not name.startswith("cmd_"):
            raise AttributeError(name)
        return lambda: self.ran.append(name)


def _quill_frame(*, enabled: bool = True):
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.ui.keybinding_parse import KeybindingParseMixin
    from quill.ui.main_frame_quill_key import QuillKeyMixin
    from quill.ui.main_frame_wordpress import WordPressMenuMixin

    class Frame(WordPressMenuMixin, QuillKeyMixin, KeybindingParseMixin):
        def __init__(self) -> None:
            self._wx = SimpleNamespace(WXK_SHIFT=306, WXK_CONTROL=308, WXK_ALT=307)
            self._wordpress_commands = _Shared()
            self.keymap = dict(DEFAULT_KEYMAP)
            self.settings = SimpleNamespace(quill_key_binding="Ctrl+Shift+Grave")
            self.spoken: list[str] = []

        def _feature_enabled(self, feature: str) -> bool:
            return enabled

        def _announce(self, text: str, **_kw) -> None:
            self.spoken.append(text)

        def _run_command(self, command_id: str) -> None:
            # What the registry holds for a WordPress row (_fill_wordpress_menu).
            getattr(self._wordpress(), _SHARED[command_id])()

    return Frame()


def _lite_window(*, enabled: bool = True):
    from quill.apps.lite_window_wordpress import DocumentWordPressMixin

    class Window(DocumentWordPressMixin):
        def __init__(self) -> None:
            self._wordpress_commands = _Shared()
            self.app = SimpleNamespace(
                feature_enabled=lambda area: enabled or area != "wordpress", keymap=None
            )
            self.spoken: list[str] = []

        def _announce(self, text: str, **_kw) -> None:
            self.spoken.append(text)

        def run_unless_read_only(self, handler: str) -> None:
            getattr(self, handler)()

    return Window()


def _press(target, event: _Event) -> bool:
    hook = getattr(target, "_wordpress_key_event", None) or target._wordpress_key_down
    return bool(hook(event))


_EDITORS = {"quill": _quill_frame, "lite": _lite_window}


def _letter_event(key: str) -> _Event:
    shift = key.startswith("Shift+")
    return _Event(ord(key[-1]), shift=shift)


@pytest.mark.parametrize("editor", sorted(_EDITORS))
@pytest.mark.parametrize(("key", "command_id"), sorted(LAYER_KEYS.items()))
def test_each_letter_reaches_the_shared_command(editor: str, key: str, command_id: str) -> None:
    pytest.importorskip("wx")
    target = _EDITORS[editor]()
    assert _press(target, _prefix())
    assert target.spoken == ["WordPress keys"]
    assert _press(target, _letter_event(key))
    assert target._wordpress_commands.ran == [_SHARED[command_id]]
    assert target.spoken == ["WordPress keys"]  # the command speaks for itself


@pytest.mark.parametrize("editor", sorted(_EDITORS))
def test_escape_and_an_unknown_letter_in_each_editor(editor: str) -> None:
    pytest.importorskip("wx")
    target = _EDITORS[editor]()
    _press(target, _prefix())
    assert _press(target, _Event(27))
    _press(target, _prefix())
    assert _press(target, _Event(ord("Q")))
    assert target.spoken[1::2] == ["Left WordPress keys", "No WordPress command on Q."]
    assert target._wordpress_commands.ran == []
    assert not _press(target, _Event(ord("O")))  # the layer is over: O is typing again


@pytest.mark.parametrize("editor", sorted(_EDITORS))
def test_shift_going_down_does_not_end_the_layer(editor: str) -> None:
    pytest.importorskip("wx")
    import wx

    target = _EDITORS[editor]()
    if editor == "quill":
        target._wx = wx
    _press(target, _prefix())
    assert _press(target, _Event(wx.WXK_SHIFT, shift=True))
    assert _press(target, _Event(ord("S"), shift=True))
    assert target._wordpress_commands.ran == ["cmd_sites"]


@pytest.mark.parametrize("editor", sorted(_EDITORS))
def test_with_wordpress_off_the_prefix_is_not_claimed(editor: str) -> None:
    pytest.importorskip("wx")
    target = _EDITORS[editor](enabled=False)
    assert not _press(target, _prefix())
    assert target.spoken == []


def test_quill_leaves_the_prefix_to_a_quill_key_moved_onto_it() -> None:
    target = _quill_frame()
    target.settings.quill_key_binding = "Ctrl+Alt+Shift+Grave"
    assert not _press(target, _prefix())


@pytest.mark.parametrize("editor", sorted(_EDITORS))
@pytest.mark.parametrize(
    ("platform", "code", "raw"),
    [
        ("darwin", ord("^"), 0x0A),  # German Mac, ISO key above Tab
        ("darwin", ord("<"), 0x32),  # German Mac, ISO key beside left Shift
        ("darwin", 0, 0x32),  # US Mac, no character reported
    ],
)
def test_the_prefix_is_found_by_position_on_any_layout(
    editor: str, platform: str, code: int, raw: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #1753: on a German layout the grave key types "^", not a back-tick.
    pytest.importorskip("wx")
    import quill.core.grave_key as grave_key

    monkeypatch.setattr(grave_key, "_current_platform", lambda: platform)
    target = _EDITORS[editor]()
    assert _press(target, _Event(code, ctrl=True, alt=True, shift=True, raw=raw))
    assert target.spoken == ["WordPress keys"]


@pytest.mark.parametrize("editor", sorted(_EDITORS))
def test_windows_ctrl_alt_shift_2_is_not_the_prefix(
    editor: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 0x32 is the Mac back-tick code but the Windows virtual key for "2".
    pytest.importorskip("wx")
    import quill.core.grave_key as grave_key

    monkeypatch.setattr(grave_key, "_current_platform", lambda: "win32")
    target = _EDITORS[editor]()
    assert not _press(target, _Event(ord("2"), ctrl=True, alt=True, shift=True, raw=0x32))
