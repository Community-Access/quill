"""Announcements reach a braille display, not only speech (#1283).

Reported by a braille user: What's Playing, a finished weather refresh, and the
Radio Reading Services update all speak but never appear in braille. The cause
was that QUILL never called either bridge's braille API at all.

A unit test cannot prove a physical display lit up, so these assert the contract
around the call: it happens after speech, on both bridges, with the guards that
keep it from ever costing the user their speech.
"""

from __future__ import annotations

import types

import pytest

from quill.platform.windows import braille_output
from quill.platform.windows.braille_output import (
    braille_via_accessible_output2,
    braille_via_prism,
    prism_supports_braille,
)
from quill.platform.windows.prism_bridge import AnnouncementEngine


@pytest.fixture(autouse=True)
def _clear_duplicate_state():
    braille_output.reset_duplicate_state()
    yield
    braille_output.reset_duplicate_state()


class _PrismBackend:
    def __init__(self, *, supports_braille: bool = True, braille_raises: bool = False) -> None:
        self.features = types.SimpleNamespace(
            is_supported_at_runtime=True, supports_braille=supports_braille
        )
        self.name = "Fake Prism"
        self.spoken: list[str] = []
        self.brailled: list[str] = []
        self._braille_raises = braille_raises

    def speak(self, message: str, interrupt: bool = False) -> None:
        self.spoken.append(message)

    def braille(self, message: str) -> None:
        if self._braille_raises:
            raise RuntimeError("display disconnected")
        self.brailled.append(message)


class _AO2Output:
    def __init__(self, *, braille_raises: bool = False) -> None:
        self.spoken: list[str] = []
        self.brailled: list[str] = []
        self._braille_raises = braille_raises

    def speak(self, message: str, interrupt: bool = False) -> None:
        self.spoken.append(message)

    def braille(self, message: str) -> None:
        if self._braille_raises:
            raise RuntimeError("no display")
        self.brailled.append(message)


def _prism_engine(monkeypatch, backend: _PrismBackend) -> AnnouncementEngine:
    context = types.SimpleNamespace(acquire_best=lambda: backend)
    module = types.SimpleNamespace(Context=lambda: context)
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge.import_module",
        lambda name: module if name == "prism" else None,
    )
    return AnnouncementEngine("auto")


def _ao2_engine(monkeypatch, output: _AO2Output) -> AnnouncementEngine:
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge.import_module",
        lambda _name: (_ for _ in ()).throw(ImportError),
    )
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge._ao2_live_screen_reader",
        lambda: (output, "JAWS", output),
    )
    return AnnouncementEngine("auto")


# -- the dispatch helpers ------------------------------------------------------


def test_prism_braille_requires_the_advertised_capability() -> None:
    unsupported = _PrismBackend(supports_braille=False)
    assert prism_supports_braille(unsupported) is False

    braille_via_prism(unsupported, "Hello")

    # Never probed: an unsupported backend would raise on every announcement.
    assert unsupported.brailled == []


def test_prism_braille_sends_the_message() -> None:
    backend = _PrismBackend()
    assert braille_via_prism(backend, "Now playing: A Song") == ""
    assert backend.brailled == ["Now playing: A Song"]


def test_braille_never_truncates() -> None:
    # A display is narrow, but JAWS and NVDA both let the reader pan; clipping
    # would silently drop the end of a long track title.
    backend = _PrismBackend()
    long_title = "Now playing: " + "a very long track title" * 10
    braille_via_prism(backend, long_title)
    assert backend.brailled == [long_title]
    assert len(backend.brailled[0]) > 200


def test_empty_messages_are_skipped() -> None:
    backend = _PrismBackend()
    braille_via_prism(backend, "   ")
    assert backend.brailled == []


def test_an_identical_message_does_not_steal_the_display_twice() -> None:
    # A braille flash replaces whatever is under the reader's fingers, and the
    # radio now-playing poller can re-announce the same title.
    backend = _PrismBackend()
    braille_via_prism(backend, "Now playing: A Song", now=100.0)
    braille_via_prism(backend, "Now playing: A Song", now=100.5)
    assert backend.brailled == ["Now playing: A Song"]

    # Outside the window the same text is legitimate again.
    braille_via_prism(backend, "Now playing: A Song", now=200.0)
    assert len(backend.brailled) == 2


def test_a_different_message_always_gets_through() -> None:
    backend = _PrismBackend()
    braille_via_prism(backend, "First", now=100.0)
    braille_via_prism(backend, "Second", now=100.1)
    assert backend.brailled == ["First", "Second"]


def test_a_braille_failure_is_reported_not_raised() -> None:
    backend = _PrismBackend(braille_raises=True)
    error = braille_via_prism(backend, "Hello")
    assert "Braille output failed" in error


def test_accessible_output2_braille_goes_to_the_concrete_output() -> None:
    output = _AO2Output()
    assert braille_via_accessible_output2(output, "Saved") == ""
    assert output.brailled == ["Saved"]


# -- the engine ----------------------------------------------------------------


def test_prism_announcements_speak_and_braille(monkeypatch) -> None:
    backend = _PrismBackend()
    engine = _prism_engine(monkeypatch, backend)

    assert engine.announce("Now playing: A Song") is None

    assert backend.spoken == ["Now playing: A Song"]
    assert backend.brailled == ["Now playing: A Song"]


def test_accessible_output2_announcements_speak_and_braille(monkeypatch) -> None:
    output = _AO2Output()
    engine = _ao2_engine(monkeypatch, output)

    assert engine.announce("Weather updated") is None

    assert output.spoken == ["Weather updated"]
    assert output.brailled == ["Weather updated"]


def test_speech_still_happens_when_braille_fails(monkeypatch) -> None:
    # The whole point of routing braille separately: an unplugged display must
    # never cost the user their speech.
    backend = _PrismBackend(braille_raises=True)
    engine = _prism_engine(monkeypatch, backend)

    assert engine.announce("Recording started") is None

    assert backend.spoken == ["Recording started"]
    assert backend.brailled == []
    assert "Braille output failed" in engine.state().last_error


def test_a_backend_without_braille_support_still_speaks(monkeypatch) -> None:
    backend = _PrismBackend(supports_braille=False)
    engine = _prism_engine(monkeypatch, backend)

    engine.announce("Saved")

    assert backend.spoken == ["Saved"]
    assert backend.brailled == []


def test_turning_the_setting_off_stops_braille_but_not_speech(monkeypatch) -> None:
    backend = _PrismBackend()
    engine = _prism_engine(monkeypatch, backend)
    engine.set_braille_enabled(False)

    engine.announce("Saved")

    assert backend.spoken == ["Saved"]
    assert backend.brailled == []


def test_diagnostics_report_whether_braille_is_live(monkeypatch) -> None:
    backend = _PrismBackend()
    engine = _prism_engine(monkeypatch, backend)

    diagnostics = engine.diagnostics_environment()

    assert diagnostics["announcement_braille_enabled"] is True
    assert diagnostics["announcement_braille_supported"] is True
    assert diagnostics["announcement_braille_active"] is True

    engine.set_braille_enabled(False)
    assert engine.diagnostics_environment()["announcement_braille_active"] is False


# -- the verbosity braille channel ---------------------------------------------


def test_the_verbosity_outcome_now_carries_braille() -> None:
    """#425/#498 rendered a braille channel and threw it away; #1283 keeps it."""
    from quill.core.verbosity.controller import VerbosityController

    controller = VerbosityController()
    outcome = controller.process("Saved note.md")

    assert outcome.braille == outcome.visual


def test_a_suppressed_announcement_brailles_nothing() -> None:
    # Quiet mode should not flash the display either -- suppression means
    # suppressed on every channel, not just speech.
    from quill.core.verbosity.controller import VerbosityController

    controller = VerbosityController()
    controller.quiet.toggle()
    outcome = controller.process("Saved note.md")

    assert outcome.speech == ""
    assert outcome.braille == ""
