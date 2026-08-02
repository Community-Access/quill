"""The shells announce through the service (#1298-#1301).

The risk in Phase B is regression, not novelty: every shell's announcement path
moves. So these assert the wiring rather than the mechanisms -- which sinks a
host gets, that a host missing a mechanism simply lacks that channel, and that
the engine stops brailling on its own once the service owns the channel (or the
message would be written to the display twice).
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.announce import Channel
from quill.ui.announce_shim import build_announcement
from quill.ui.announce_wiring import build_announcement_service, policy_modes_from_settings


class _Engine:
    def __init__(self, *, braille: bool = True) -> None:
        self.spoken: list[tuple[str, bool]] = []
        self.brailled: list[str] = []
        self.braille_enabled = True
        self._has_braille = braille

    def announce(self, message: str, *, force_speech: bool = False) -> None:
        self.spoken.append((message, force_speech))
        return None

    def braille(self, message: str) -> str:
        self.brailled.append(message)
        return ""

    def braille_supported(self) -> bool:
        return self._has_braille

    def set_braille_enabled(self, enabled: bool) -> None:
        self.braille_enabled = enabled

    def state(self):
        return SimpleNamespace(active_backend="prism", backend_name="JAWS")


class _Host:
    """A shell with everything wired."""

    def __init__(self, **settings_overrides) -> None:
        defaults = {
            "announcement_braille": True,
            "announcement_braille_style": "speech",
            "announcement_braille_dedupe_seconds": 2.0,
            "announcement_braille_sticky_errors": True,
            "announcement_sounds_in_apps": True,
            "announcement_sound_instead_of_speech_when_quiet": True,
            "sound_events_disabled": "",
        }
        defaults.update(settings_overrides)
        self.settings = SimpleNamespace(**defaults)
        self._announcement_engine = _Engine()
        self.status: list[str] = []
        self.notifications: list[tuple[str, str]] = []
        self.echo: list[str] = []

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _record_notification(self, message: str, category: str = "info") -> None:
        self.notifications.append((message, category))

    def _record_spoken(self, message: str) -> None:
        self.echo.append(message)


class _BareHost:
    """A companion app with only an engine and a status bar."""

    def __init__(self) -> None:
        self.settings = SimpleNamespace()
        self._announcement_engine = _Engine()
        self.status: list[str] = []

    def _set_status(self, message: str) -> None:
        self.status.append(message)


# -- what each host gets -------------------------------------------------------


def test_a_full_shell_gets_every_channel() -> None:
    service = build_announcement_service(_Host())

    channels = service.channels()

    for channel in (
        Channel.SPEECH,
        Channel.BRAILLE,
        Channel.SOUND,
        Channel.VISUAL,
        Channel.NOTIFICATION,
        Channel.ECHO,
        Channel.TRANSCRIPT,
    ):
        assert channel in channels


def test_a_bare_companion_app_gets_what_it_can_serve() -> None:
    # A host without a notification store or echo history should still speak,
    # braille and show -- not fail to build a service.
    service = build_announcement_service(_BareHost())

    channels = service.channels()

    assert Channel.SPEECH in channels
    assert Channel.BRAILLE in channels
    assert Channel.VISUAL in channels
    assert Channel.NOTIFICATION not in channels
    assert Channel.ECHO not in channels


def test_the_probe_names_the_missing_channels_rather_than_hiding_them() -> None:
    service = build_announcement_service(_BareHost())

    statuses = {status.channel: status for status in service.probe()}

    assert statuses[Channel.NOTIFICATION].available is False
    assert "no sink installed" in statuses[Channel.NOTIFICATION].detail


# -- the double-braille hand-off ------------------------------------------------


def test_the_engine_stops_brailling_once_the_service_owns_the_channel() -> None:
    # Otherwise every message would reach the display twice: once from the P0
    # dispatch inside announce(), once from the sink.
    host = _Host()

    build_announcement_service(host)

    assert host._announcement_engine.braille_enabled is False


def test_an_announcement_reaches_speech_braille_and_status() -> None:
    host = _Host()
    service = build_announcement_service(host)

    service.announce(build_announcement("Saved note.md"))

    assert host._announcement_engine.spoken == [("Saved note.md", False)]
    assert host._announcement_engine.brailled == ["Saved note.md"]
    assert host.status == ["Saved note.md"]
    assert host.echo == ["Saved note.md"]


def test_force_interrupts_the_reader() -> None:
    host = _Host()
    service = build_announcement_service(host)

    service.announce(build_announcement("Indented 4 lines", force=True))

    assert host._announcement_engine.spoken == [("Indented 4 lines", True)]


# -- settings (#1301) ----------------------------------------------------------


def test_turning_braille_off_removes_only_that_channel() -> None:
    host = _Host(announcement_braille=False)
    service = build_announcement_service(host)

    service.announce(build_announcement("Saved"))

    assert host._announcement_engine.spoken  # still speaks
    assert host._announcement_engine.brailled == []


def test_the_compact_style_reaches_the_display() -> None:
    from quill.core.announce import Announcement

    host = _Host(announcement_braille_style="compact")
    service = build_announcement_service(host)

    service.announce(
        Announcement(text="Page 7 of 87, line 14", context={"page": 7, "pages": 87, "line": 14})
    )

    assert host._announcement_engine.brailled == ["p7/87 l14"]


def test_settings_map_onto_policy_modes() -> None:
    settings = SimpleNamespace(
        announcement_braille=False,
        announcement_sounds_in_apps=False,
        announcement_sound_instead_of_speech_when_quiet=False,
        announcement_braille_style="compact",
    )

    modes = policy_modes_from_settings(settings)

    assert modes.braille_enabled is False
    assert modes.sound_enabled is False
    assert modes.sound_instead_of_speech_when_quiet is False
    assert modes.braille_style == "compact"


def test_missing_settings_fall_back_to_the_safe_defaults() -> None:
    # A companion app whose settings object predates this block must still get
    # braille -- the whole bug was braille being absent.
    modes = policy_modes_from_settings(SimpleNamespace())

    assert modes.braille_enabled is True
    assert modes.sound_enabled is True


def test_a_disabled_sound_event_is_not_played() -> None:
    from quill.core.announce import Announcement

    host = _Host(sound_events_disabled="document_saved")
    played: list[str] = []
    service = build_announcement_service(host)
    # Replace the sound sink's player with a recorder: the real one needs wx.
    for sink in service._sinks:  # noqa: SLF001 - inspecting wiring is the point
        if sink.channel is Channel.SOUND:
            sink._play = played.append  # noqa: SLF001

    service.announce(Announcement(text="Saved", sound_event="document_saved"))

    assert played == []
