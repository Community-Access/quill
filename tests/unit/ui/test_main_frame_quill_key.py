from __future__ import annotations

import time
from types import SimpleNamespace

from quill.branding import QUILL_KEY_LABEL
from quill.core.quill_key_help import MODE_BROWSE, MODE_PREFIX
from quill.ui.main_frame import MainFrame


class _Event:
    def __init__(
        self,
        key_code: int,
        *,
        ctrl: bool = False,
        shift: bool = False,
        alt: bool = False,
        raw_ctrl: bool | None = None,
        unicode_key: int | None = None,
    ) -> None:
        self._key_code = key_code
        self._ctrl = ctrl
        self._shift = shift
        self._alt = alt
        self._raw_ctrl = raw_ctrl
        self._unicode_key = unicode_key if unicode_key is not None else key_code
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self._key_code

    def ControlDown(self) -> bool:
        return self._ctrl

    def ShiftDown(self) -> bool:
        return self._shift

    def AltDown(self) -> bool:
        return self._alt

    def GetUnicodeKey(self) -> int:
        return self._unicode_key

    def Skip(self) -> None:
        self.skipped = True


class _MacEvent(_Event):
    """Mimics wx on macOS: ``RawControlDown()`` is the physical Ctrl key.

    ``ControlDown()`` reflects Cmd on macOS, so a real physical Ctrl press
    reports ``ctrl=False`` here, with the physical key visible only via
    ``RawControlDown()``.
    """

    def RawControlDown(self) -> bool:
        return bool(self._raw_ctrl)


_BACKTICK = ord("`")


def _build_frame(
    *,
    binding: str = "Ctrl+Shift+Grave",
    timeout: float = 1.5,
    browse_followon_timeout: str = "unlimited",
    browse_followon_custom_ms: int = 4000,
    announce_mode_changes: bool = True,
    keymap: dict[str, str] | None = None,
) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame._wx = SimpleNamespace(
        WXK_BACKTICK=_BACKTICK,
        WXK_ESCAPE=27,
        ACCEL_CTRL=1,
        ACCEL_SHIFT=2,
        ACCEL_ALT=4,
    )
    frame.settings = SimpleNamespace(
        quill_key_binding=binding,
        quill_key_timeout_seconds=timeout,
        browse_mode_followon_timeout=browse_followon_timeout,
        browse_mode_followon_custom_ms=browse_followon_custom_ms,
        announce_mode_changes=announce_mode_changes,
    )
    frame.keymap = keymap if keymap is not None else {}
    frame._quill_key_mode_active = False
    frame._quill_key_prefix_pending = False
    frame._quill_key_prefix_started_at = 0.0
    frame._quill_key_mode_started_at = 0.0
    frame._quill_key_mode_timeout_seconds = 1.5
    frame._quill_key_mode_sticky = False
    frame._statuses: list[str] = []
    frame._feedback: list[str] = []
    frame._set_status_quiet = frame._statuses.append  # type: ignore[method-assign]
    frame._refresh_statusbar = lambda: None  # type: ignore[method-assign]

    def _feedback(message, *, status_message=None, sound_kind=None):  # type: ignore[no-untyped-def]
        frame._feedback.append(status_message or message)

    frame._quill_feedback = _feedback  # type: ignore[method-assign]
    return frame


def test_default_prefix_press_sets_pending() -> None:
    frame = _build_frame()
    handled = frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    assert handled is True
    assert frame._quill_key_prefix_pending is True


def test_physical_ctrl_on_mac_sets_pending() -> None:
    # #883-follow-up: on macOS, wx's ControlDown() reflects Cmd, not the
    # physical Ctrl key (only RawControlDown() does). A real physical
    # Ctrl+Shift+` press must still trigger the QUILL key prefix there.
    frame = _build_frame()
    event = _MacEvent(_BACKTICK, ctrl=False, shift=True, raw_ctrl=True)
    handled = frame._handle_quill_key_mode_event(event)
    assert handled is True
    assert frame._quill_key_prefix_pending is True


def test_cmd_alone_without_raw_ctrl_still_matches() -> None:
    # ControlDown()==True (Cmd held) continues to work on its own, e.g. on
    # platforms/configurations where the OS hasn't reserved the chord.
    frame = _build_frame()
    event = _MacEvent(_BACKTICK, ctrl=True, shift=True, raw_ctrl=False)
    handled = frame._handle_quill_key_mode_event(event)
    assert handled is True
    assert frame._quill_key_prefix_pending is True


def test_prefix_then_n_enters_browse_mode() -> None:
    frame = _build_frame()
    frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    handled = frame._handle_quill_key_mode_event(_Event(ord("N")))
    assert handled is True
    assert frame._quill_key_mode_active is True
    assert frame._quill_key_mode_sticky is False


def test_prefix_then_n_honors_sticky_browse_default() -> None:
    # SET-4: when browse_mode_sticky is configured, N enters locked browse mode.
    frame = _build_frame()
    frame.settings.browse_mode_sticky = True
    frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    handled = frame._handle_quill_key_mode_event(_Event(ord("N")))
    assert handled is True
    assert frame._quill_key_mode_active is True
    assert frame._quill_key_mode_sticky is True
    assert any("locked" in message.lower() for message in frame._feedback)


def test_double_press_prefix_enters_sticky_locked_mode() -> None:
    frame = _build_frame()
    frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    handled = frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    assert handled is True
    assert frame._quill_key_mode_active is True
    assert frame._quill_key_mode_sticky is True
    assert any("locked" in message.lower() for message in frame._feedback)


def test_sticky_mode_ignores_timeout() -> None:
    frame = _build_frame(timeout=0.001)
    frame._enter_quill_key_mode(sticky=True)
    frame._quill_key_mode_started_at = time.monotonic() - 10
    assert frame._quill_key_mode_timed_out() is False


def test_zero_timeout_disables_browse_expiry() -> None:
    # #265 follow-up: 'unlimited' disables the timeout entirely.
    frame = _build_frame(timeout=0, browse_followon_timeout="unlimited")
    frame._enter_quill_key_mode()
    frame._quill_key_mode_started_at = time.monotonic() - 10
    assert frame._quill_key_mode_timed_out() is False


def test_positive_timeout_expires_browse_mode() -> None:
    # #265 follow-up: the browse-mode timeout is set via the new chooser
    # tokens; 'fast' (1.5 s) is the shortest preset that still has a
    # positive timeout.
    frame = _build_frame(browse_followon_timeout="fast")
    frame._enter_quill_key_mode()
    frame._quill_key_mode_started_at = time.monotonic() - 10
    assert frame._quill_key_mode_timed_out() is True


def test_remappable_binding_matches_configured_key() -> None:
    frame = _build_frame(binding="Alt+M")
    handled = frame._handle_quill_key_mode_event(_Event(ord("M"), alt=True))
    assert handled is True
    assert frame._quill_key_prefix_pending is True
    # The old default chord no longer triggers the prefix.
    frame2 = _build_frame(binding="Alt+M")
    handled2 = frame2._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    assert handled2 is False
    assert frame2._quill_key_prefix_pending is False


def test_status_bar_reports_quill_key_state() -> None:
    frame = _build_frame()
    assert frame._statusbar_text_for_item("quill_key_mode") == "Off"
    frame._quill_key_prefix_pending = True
    assert frame._statusbar_text_for_item("quill_key_mode") == "Prefix"
    frame._quill_key_prefix_pending = False
    frame._quill_key_mode_active = True
    assert frame._statusbar_text_for_item("quill_key_mode") == "Browse"
    frame._quill_key_mode_sticky = True
    assert frame._statusbar_text_for_item("quill_key_mode") == "Locked"


def test_quill_key_timeout_reads_settings() -> None:
    frame = _build_frame(timeout=3.0)
    assert frame._quill_key_timeout() == 3.0
    frame.settings.quill_key_timeout_seconds = -5
    # Out-of-range values clamp to a non-negative timeout.
    assert frame._quill_key_timeout() == 0.0


def test_prefix_then_a_opens_selection_actions_when_text_selected() -> None:
    # SEL-3: with a selection active, the QUILL key prefix then A opens the
    # scope-aware selection actions surface instead of falling through.
    frame = _build_frame()
    frame.editor = SimpleNamespace(GetSelection=lambda: (0, 5))
    opened: list[str] = []
    frame.quill_key_selection_actions = lambda: opened.append("actions")  # type: ignore[method-assign]

    frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    handled = frame._handle_quill_key_mode_event(_Event(ord("A")))

    assert handled is True
    assert opened == ["actions"]
    assert frame._quill_key_mode_active is False


def test_prefix_then_a_without_selection_does_not_open_actions() -> None:
    frame = _build_frame()
    frame.editor = SimpleNamespace(GetSelection=lambda: (3, 3))
    opened: list[str] = []
    frame.quill_key_selection_actions = lambda: opened.append("actions")  # type: ignore[method-assign]

    frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    frame._handle_quill_key_mode_event(_Event(ord("A")))

    assert opened == []


def _wire_help_stubs(frame: MainFrame) -> MainFrame:
    """Stub the dependencies the cheat sheet needs, leaving the real builder."""
    frame._announcements = []  # type: ignore[attr-defined]
    frame._announce = lambda message, **_kw: frame._announcements.append(message)  # type: ignore[method-assign]
    frame._binding_for = lambda command_id: None  # type: ignore[method-assign]
    frame._help_shown = []  # type: ignore[attr-defined]
    frame._present_quill_key_help = (  # type: ignore[method-assign]
        lambda mode, text: frame._help_shown.append((mode, text))
    )
    frame._browse_navigation_context = lambda: {  # type: ignore[method-assign]
        "headings_by_level": {1: [0], 2: [10, 20]},
        "links": [1, 2, 3],
        "lists": [],
        "list_items": [],
        "tables": [],
        "block_quotes": [],
        "bookmarks": [],
        "code_blocks": [],
        "paragraph_spans": [0],
        "sentence_spans": [0],
    }
    return frame


def test_prefix_then_question_mark_shows_prefix_cheat_sheet() -> None:
    # QK-9: question mark after the prefix opens the prefix cheat sheet.
    frame = _build_frame()
    _wire_help_stubs(frame)
    frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    handled = frame._handle_quill_key_mode_event(_Event(ord("?")))
    assert handled is True
    assert frame._quill_key_prefix_pending is False
    assert len(frame._help_shown) == 1  # type: ignore[attr-defined]
    assert frame._help_shown[0][0] == MODE_PREFIX  # type: ignore[attr-defined]
    assert any(  # type: ignore[attr-defined]
        "QUILL key help" in note for note in frame._announcements
    )


def test_question_mark_via_shift_slash_is_recognized() -> None:
    frame = _build_frame()
    _wire_help_stubs(frame)
    frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    handled = frame._handle_quill_key_mode_event(_Event(ord("/"), shift=True))
    assert handled is True
    assert frame._help_shown[0][0] == MODE_PREFIX  # type: ignore[attr-defined]


def test_bare_shift_keydown_before_question_mark_does_not_clear_prefix() -> None:
    # Regression: wx fires a separate EVT_CHAR_HOOK for the Shift keydown
    # itself, ahead of the "?" character it produces. That bare modifier
    # event was previously read as an unrecognized second key, clearing the
    # pending prefix before the real "?" arrived.
    frame = _build_frame()
    _wire_help_stubs(frame)
    frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    bare_shift_handled = frame._handle_quill_key_mode_event(_Event(-11, shift=True))
    assert bare_shift_handled is True
    assert frame._quill_key_prefix_pending is True
    handled = frame._handle_quill_key_mode_event(_Event(ord("?")))
    assert handled is True
    assert frame._help_shown[0][0] == MODE_PREFIX  # type: ignore[attr-defined]


def test_bare_shift_keydown_in_browse_mode_does_not_exit() -> None:
    # Regression: the same bare-modifier EVT_CHAR_HOOK was misread as "a
    # modified key with no matching browse action" and exited browse mode
    # before e.g. Shift+Tab or Shift+1 ever completed.
    frame = _build_frame()
    _wire_help_stubs(frame)
    frame._enter_quill_key_mode()
    handled = frame._handle_quill_key_mode_event(_Event(-11, shift=True))
    assert handled is True
    assert frame._quill_key_mode_active is True


def test_browse_mode_question_mark_shows_browse_cheat_sheet_and_stays() -> None:
    # QK-2/QK-9: inside browse mode, question mark shows the browse cheat sheet
    # with live counts and does not leave browse mode.
    frame = _build_frame()
    _wire_help_stubs(frame)
    frame._enter_quill_key_mode()
    handled = frame._handle_quill_key_mode_event(_Event(ord("?")))
    assert handled is True
    assert frame._quill_key_mode_active is True
    assert frame._help_shown[0][0] == MODE_BROWSE  # type: ignore[attr-defined]
    # Three links in the stubbed context surface as a live count.
    assert "(3)" in frame._help_shown[0][1]  # type: ignore[attr-defined]


def test_prefix_then_g_opens_quick_nav() -> None:
    # NAV-4: the QUILL key prefix then G opens Quick Nav / Go to Anything.
    frame = _build_frame()
    opened: list[str] = []
    frame.open_quick_nav = lambda: opened.append("nav")  # type: ignore[method-assign]
    frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    handled = frame._handle_quill_key_mode_event(_Event(ord("G")))
    assert handled is True
    assert opened == ["nav"]
    assert frame._quill_key_mode_active is False


def test_prefix_press_announces_quill_key() -> None:
    # #265: pressing the QUILL key speaks "QUILL key" via _announce when
    # announce_mode_changes is on. Speech fires before the chord sound.
    frame = _build_frame()
    frame._announcements = []  # type: ignore[attr-defined]
    frame._announce = lambda message, **_kw: frame._announcements.append(message)  # type: ignore[method-assign]
    sounds: list[str] = []
    frame._post_sound_stub = sounds.append  # type: ignore[attr-defined]
    handled = frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    assert handled is True
    assert frame._announcements  # type: ignore[attr-defined]
    assert frame._announcements[0] == QUILL_KEY_LABEL  # type: ignore[attr-defined]


def test_prefix_press_silent_when_announce_mode_changes_disabled() -> None:
    # #265: quiet / no-speech profiles keep the prefix silent. Status bar
    # message still appears; only _announce is gated.
    frame = _build_frame(announce_mode_changes=False)
    frame._announcements = []  # type: ignore[attr-defined]
    frame._announce = lambda message, **_kw: frame._announcements.append(message)  # type: ignore[method-assign]
    frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    assert frame._announcements == []  # type: ignore[attr-defined]
    assert frame._quill_key_prefix_pending is True


def test_question_mark_via_unicode_key_is_recognized() -> None:
    # #265: wxPython on some layouts reports neither ord("?") as the keycode
    # nor Shift+"/". GetUnicodeKey is the third detection strategy so the
    # cheat sheet remains reachable on those layouts.
    frame = _build_frame()
    _wire_help_stubs(frame)
    frame._handle_quill_key_mode_event(_Event(_BACKTICK, ctrl=True, shift=True))
    handled = frame._handle_quill_key_mode_event(_Event(ord("/"), shift=True, unicode_key=ord("?")))
    assert handled is True
    assert frame._help_shown[0][0] == MODE_PREFIX  # type: ignore[attr-defined]  # noqa: F821


def test_browse_mode_uses_separate_followon_timeout() -> None:
    # #265 follow-up: the 'slow' preset gives an 8s follow-on window,
    # separate from the 1.5s prefix-decision window.
    frame = _build_frame(timeout=1.5, browse_followon_timeout="slow")
    frame._enter_quill_key_mode()
    frame._quill_key_mode_started_at = time.monotonic() - 7.0
    assert frame._browse_mode_timed_out() is False
    frame._quill_key_mode_started_at = time.monotonic() - 9.0
    assert frame._browse_mode_timed_out() is True


def test_browse_mode_followon_timeout_zero_disables_expiry() -> None:
    # #265 follow-up: the 'unlimited' preset disables the browse-mode
    # timeout entirely.
    frame = _build_frame(browse_followon_timeout="unlimited")
    frame._enter_quill_key_mode()
    frame._quill_key_mode_started_at = time.monotonic() - 60
    assert frame._browse_mode_timed_out() is False


def test_browse_mode_followon_timeout_returns_configured_value() -> None:
    # #265 follow-up: _browse_mode_timeout() returns the configured preset
    # in seconds, 'unlimited' and unknown tokens resolve to 0.
    frame = _build_frame(browse_followon_timeout="normal")
    assert frame._browse_mode_timeout() == 4.0
    frame.settings.browse_mode_followon_timeout = "fast"
    assert frame._browse_mode_timeout() == 1.5
    frame.settings.browse_mode_followon_timeout = "instant"
    assert frame._browse_mode_timeout() == 0.001
    frame.settings.browse_mode_followon_timeout = "garbage"
    assert frame._browse_mode_timeout() == 0.0


def test_quill_key_cheat_sheet_includes_chord_groups() -> None:
    # #265: the cheat sheet for browse mode surfaces every Ctrl+Shift+Grave
    # chord command grouped by category. The mixin must pass self.keymap
    # and the configured quill_key_binding to build_cheat_sheet.
    frame = _build_frame()
    _wire_help_stubs(frame)
    frame.keymap = {  # type: ignore[attr-defined]
        "navigate.speak_window_title": "Ctrl+Shift+Grave, F",
        "view.send_to_tray": "Ctrl+Shift+Grave, T",
        "file.open_from_remote": "Ctrl+Shift+Grave, Shift+O",
    }
    frame._binding_for = lambda cid: frame.keymap.get(cid)  # type: ignore[method-assign]

    frame._enter_quill_key_mode()
    frame._handle_quill_key_mode_event(_Event(ord("?")))
    mode, text = frame._help_shown[0]  # type: ignore[attr-defined]
    assert mode == MODE_BROWSE
    # The chord groups appear at the end of the cheat sheet text.
    assert "Navigate" in text
    assert "View" in text
    assert "File" in text


def test_browse_mode_unlimited_preset_disables_timeout() -> None:
    # #265 follow-up: 'Unlimited (no timeout)' is the new default; the
    # follow-on timeout is disabled regardless of how long the user pauses.
    frame = _build_frame(browse_followon_timeout="unlimited")
    frame._enter_quill_key_mode()
    frame._quill_key_mode_started_at = time.monotonic() - 60
    assert frame._browse_mode_timed_out() is False


def test_browse_mode_fast_preset_expires_at_1_5s() -> None:
    # #265 follow-up: 'Fast (1500 ms)' preset maps to 1.5s.
    frame = _build_frame(browse_followon_timeout="fast")
    frame._enter_quill_key_mode()
    frame._quill_key_mode_started_at = time.monotonic() - 1.6
    assert frame._browse_mode_timed_out() is True
    frame._quill_key_mode_started_at = time.monotonic() - 1.0
    assert frame._browse_mode_timed_out() is False


def test_browse_mode_slow_preset_expires_at_8s() -> None:
    # #265 follow-up: 'Slow (8000 ms)' preset maps to 8s.
    frame = _build_frame(browse_followon_timeout="slow")
    frame._enter_quill_key_mode()
    frame._quill_key_mode_started_at = time.monotonic() - 7.5
    assert frame._browse_mode_timed_out() is False
    frame._quill_key_mode_started_at = time.monotonic() - 8.5
    assert frame._browse_mode_timed_out() is True


def test_browse_mode_custom_value_used() -> None:
    # #265 follow-up: 'custom' preset reads browse_mode_followon_custom_ms.
    frame = _build_frame(browse_followon_timeout="custom", browse_followon_custom_ms=2500)
    frame._enter_quill_key_mode()
    frame._quill_key_mode_started_at = time.monotonic() - 2.0
    assert frame._browse_mode_timed_out() is False
    frame._quill_key_mode_started_at = time.monotonic() - 3.0
    assert frame._browse_mode_timed_out() is True


def test_browse_mode_unknown_token_disables_timeout() -> None:
    # #265 follow-up: unknown tokens fall through to the unlimited branch
    # so the consumer never crashes on a stale settings file.
    frame = _build_frame(browse_followon_timeout="garbage")
    frame._enter_quill_key_mode()
    frame._quill_key_mode_started_at = time.monotonic() - 60
    assert frame._browse_mode_timed_out() is False


def test_browse_mode_instant_preset_times_out_immediately() -> None:
    # #265 follow-up: 'Instant (0 ms)' is the shortest preset.
    frame = _build_frame(browse_followon_timeout="instant")
    frame._enter_quill_key_mode()
    frame._quill_key_mode_started_at = time.monotonic() - 0.05
    assert frame._browse_mode_timed_out() is True
