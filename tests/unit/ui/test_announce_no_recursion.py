"""Regression tests for the announce -> status -> announce cycle (calculator hang).

The 2026-08-05 thread dump showed MainFrame._announce delivering to the
status sink, whose _set_status called the sr_announce handler, which was
_announce again — infinite recursion until the wx heartbeat declared the UI
dead. Two independent defenses are pinned here:

1. announce_wiring gives the VisualSink the QUIET status setter when the
   host has one, so the service can never re-enter announcement delivery.
2. MainFrame._announce refuses re-entry outright.
"""

from __future__ import annotations

from quill.ui.announce_wiring import _install_optional


class _RecordingService:
    def __init__(self) -> None:
        self.sinks = []

    def add_sink(self, sink) -> None:
        self.sinks.append(sink)


class _HostWithQuiet:
    def __init__(self) -> None:
        self.quiet_calls: list[str] = []
        self.loud_calls: list[str] = []

    def _set_status_quiet(self, message: str) -> None:
        self.quiet_calls.append(message)

    def _set_status(self, message: str) -> None:
        self.loud_calls.append(message)


class _HostWithoutQuiet:
    def __init__(self) -> None:
        self.loud_calls: list[str] = []

    def _set_status(self, message: str) -> None:
        self.loud_calls.append(message)


def _visual_sink(service: _RecordingService):
    for sink in service.sinks:
        if type(sink).__name__ == "VisualSink":
            return sink
    return None


def test_visual_sink_prefers_the_quiet_status_setter() -> None:
    host = _HostWithQuiet()
    service = _RecordingService()
    _install_optional(service, host)
    sink = _visual_sink(service)
    assert sink is not None
    sink._show("hello")
    assert host.quiet_calls == ["hello"]
    assert host.loud_calls == [], "the speaking _set_status must never be the visual sink"


def test_visual_sink_falls_back_to_set_status_for_shells() -> None:
    host = _HostWithoutQuiet()
    service = _RecordingService()
    _install_optional(service, host)
    sink = _visual_sink(service)
    assert sink is not None
    sink._show("hello")
    assert host.loud_calls == ["hello"]


def test_announce_refuses_reentry() -> None:
    """A sink that routes back into _announce must not recurse."""
    from quill.ui.main_frame import MainFrame

    class _Host:
        _announce = MainFrame._announce
        _announce_locked = MainFrame._announce_locked

        def __init__(self) -> None:
            self.delivered: list[str] = []
            self.settings = type("S", (), {"announcement_throttle_ms": 0})()

        def _record_spoken(self, message: object) -> None:
            pass

        def _refresh_statusbar(self) -> None:
            pass

        def _announce_service(self):
            host = self

            class _Service:
                def announce(self, announcement):
                    host.delivered.append(getattr(announcement, "text", str(announcement)))
                    # Simulate the cycle: a sink routing straight back in.
                    host._announce("again")

                    class _Report:
                        failed: dict = {}

                    return _Report()

            return _Service()

    host = _Host()
    host._announce("2")  # without the guard this recurses forever
    assert host.delivered == ["2"]
