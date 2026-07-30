"""Quill Radio and QUILL Cast compose the global-hotkeys mixin, and the
transport commands they register are on the allowlist and dispatchable.

Mirrors the ``_Host`` pattern in ``test_global_hotkeys.py``: the dispatch path
is exercised with a tiny stand-in host so no wx frame has to be constructed.
"""

from __future__ import annotations

from quill.apps.podcasts import PodcastsAppFrame
from quill.apps.radio import RadioAppFrame
from quill.core.commands import CommandRegistry
from quill.ui.app_shell import AppShellFrame
from quill.ui.main_frame_hotkeys import GLOBAL_HOTKEY_SAFE_COMMANDS, GlobalHotkeysMixin


def test_app_frames_compose_global_hotkeys_mixin() -> None:
    assert issubclass(RadioAppFrame, GlobalHotkeysMixin)
    assert issubclass(PodcastsAppFrame, GlobalHotkeysMixin)


def test_appshell_toggle_wins_over_mixin_copy() -> None:
    # AppShellFrame is listed before GlobalHotkeysMixin, so its
    # toggle_window_to_tray (frame.Hide(), no send_to_tray which the apps lack)
    # is the one that resolves on the app frames.
    assert RadioAppFrame.toggle_window_to_tray is AppShellFrame.toggle_window_to_tray
    assert PodcastsAppFrame.toggle_window_to_tray is AppShellFrame.toggle_window_to_tray


def test_transport_commands_are_allowlisted() -> None:
    safe = {command_id for command_id, _label, _needs in GLOBAL_HOTKEY_SAFE_COMMANDS}
    for command_id in (
        "radio.play_pause",
        "radio.stop",
        "radio.mute_toggle",
        "radio.volume_up",
        "radio.volume_down",
        "podcasts.play_pause",
        "podcasts.stop",
    ):
        assert command_id in safe, command_id


class _Host(GlobalHotkeysMixin):
    """Just enough host protocol to exercise _on_global_hotkey dispatch."""

    def __init__(self) -> None:
        self.commands = CommandRegistry()
        self.ran: list[str] = []
        self.commands.try_register(
            "radio.play_pause",
            "Radio: Play/Pause",
            lambda: self.ran.append("radio.play_pause"),
        )
        # id 42 is a configured global hotkey; 999 stands in for a media-key id
        # the mixin's catch-all handler must ignore (and Skip) so the id-specific
        # media-key handler still fires.
        self._global_hotkey_map = {42: "radio.play_pause"}

    def _restore_from_tray(self) -> None:  # pragma: no cover - not reached here
        pass

    def _announce(self, message: str) -> None:  # pragma: no cover - error path only
        pass


class _Event:
    def __init__(self, ident: int) -> None:
        self._id = ident
        self.skipped = False

    def GetId(self) -> int:
        return self._id

    def Skip(self) -> None:
        self.skipped = True


def test_on_global_hotkey_dispatches_the_mapped_command() -> None:
    host = _Host()
    host._on_global_hotkey(_Event(42))
    assert host.ran == ["radio.play_pause"]


def test_on_global_hotkey_skips_unmapped_ids() -> None:
    host = _Host()
    event = _Event(999)
    host._on_global_hotkey(event)
    assert host.ran == []
    assert event.skipped is True
