from __future__ import annotations

import types

import pytest

from quill.platform.windows.prism_bridge import AnnouncementEngine


@pytest.fixture(autouse=True)
def _disable_ao2_fallback(monkeypatch):
    """Disable the accessible_output2 fallback by default.

    Dev machines that actually run a screen reader with accessible_output2
    installed would otherwise satisfy the fallback and change Prism-focused
    assertions. Tests that exercise the fallback override this explicitly.
    """
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge._ao2_live_screen_reader",
        lambda: (None, None),
    )


class _FakeFeatures:
    def __init__(self, *, runtime: bool = True) -> None:
        self.is_supported_at_runtime = runtime


class _FakeBackend:
    def __init__(self, *, runtime: bool = True) -> None:
        self.features = _FakeFeatures(runtime=runtime)
        self.name = "Fake Prism"
        self.messages: list[str] = []
        self.interrupts: list[bool] = []

    def speak(self, message: str, interrupt: bool = False) -> None:
        self.interrupts.append(interrupt)
        self.messages.append(message)


class _FakeContext:
    def __init__(self, backend: _FakeBackend) -> None:
        self._backend = backend

    def acquire_best(self) -> _FakeBackend:
        return self._backend


def test_announcement_engine_uses_prism_backend_when_available(monkeypatch) -> None:
    backend = _FakeBackend(runtime=True)
    prism_module = types.SimpleNamespace(Context=lambda: _FakeContext(backend))
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge.import_module",
        lambda name: prism_module if name == "prism" else None,
    )
    engine = AnnouncementEngine("auto")

    state = engine.state()
    assert state.active_backend == "prism"
    assert state.prism_runtime_ready is True
    assert engine.announce("hello") is None
    assert backend.messages == ["hello"]


def test_announcement_engine_falls_back_to_status_when_prism_missing(monkeypatch) -> None:
    def fail_import(_name: str) -> object:
        raise ImportError

    monkeypatch.setattr("quill.platform.windows.prism_bridge.import_module", fail_import)
    engine = AnnouncementEngine("prism")

    state = engine.state()
    assert state.requested_backend == "prism"
    assert state.active_backend == "status_only"
    assert "not installed" in state.last_error.lower()


class _FakeVoice:
    """Stand-in SAPI SpVoice that records what was spoken."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def Speak(self, message: str, flags: int = 0) -> None:  # noqa: N802 - SAPI API name
        _ = flags
        self.messages.append(message)


def test_announcement_engine_uses_system_speech_when_prism_is_missing(monkeypatch) -> None:
    voice = _FakeVoice()
    build_calls = {"n": 0}

    def _build():
        build_calls["n"] += 1
        return voice

    # The SAPI fallback is the Windows path; on macOS announcements go to
    # VoiceOver instead. Pin a non-darwin platform so this exercises the TTS
    # fallback regardless of the host OS the tests run on.
    monkeypatch.setattr("quill.platform.windows.prism_bridge.sys.platform", "win32")
    monkeypatch.setattr("quill.platform.windows.prism_bridge._build_tts_voice", _build)
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge.import_module",
        lambda _name: (_ for _ in ()).throw(ImportError),
    )
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge._screen_reader_active",
        lambda: False,
    )
    # The SAPI SpVoice is a process-wide singleton built once on the worker
    # thread, so many announcements must build it exactly once after a reset.
    from quill.platform.windows import prism_bridge

    prism_bridge.reset_tts_engine_for_tests()

    engine = AnnouncementEngine("auto")
    assert engine.announce("hello") is None
    assert engine.announce("world") is None
    prism_bridge.flush_tts_for_tests()
    assert voice.messages == ["hello", "world"]
    assert build_calls["n"] == 1
    assert engine.state().active_backend == "speech"


def test_force_speech_bypasses_screen_reader_suppression(monkeypatch) -> None:
    # The QUILL key prefix/browse-mode chord has no focus or control change for
    # a screen reader to pick up on its own, so callers narrating that
    # internal-only state pass force_speech=True to still get spoken even
    # while JAWS/NVDA/Narrator is running and no Prism backend is active.
    voice = _FakeVoice()
    monkeypatch.setattr("quill.platform.windows.prism_bridge.sys.platform", "win32")
    monkeypatch.setattr("quill.platform.windows.prism_bridge._build_tts_voice", lambda: voice)
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge.import_module",
        lambda _name: (_ for _ in ()).throw(ImportError),
    )
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge._screen_reader_active",
        lambda: True,
    )
    from quill.platform.windows import prism_bridge

    prism_bridge.reset_tts_engine_for_tests()

    engine = AnnouncementEngine("auto")
    assert engine.announce("quiet while screen reader runs") is None
    prism_bridge.flush_tts_for_tests()
    assert voice.messages == []

    assert engine.announce("QUILL key", force_speech=True) is None
    prism_bridge.flush_tts_for_tests()
    assert voice.messages == ["QUILL key"]


class _FakeBackendId:
    """Stand-in for prism.BackendId; the probe looks members up by name."""

    JAWS = "JAWS"
    NVDA = "NVDA"


class _NamedBackend(_FakeBackend):
    def __init__(self, name: str, *, runtime: bool) -> None:
        super().__init__(runtime=runtime)
        self.name = name


class _MultiBackendContext:
    """acquire_best() returns an inactive NVDA; acquire(JAWS) returns a live JAWS.

    Mirrors the real bug (#700): acquire_best mis-picks a reader that is not
    running, so the runtime-aware selector must override it.
    """

    def __init__(self) -> None:
        self.jaws = _NamedBackend("JAWS", runtime=True)
        self.nvda = _NamedBackend("NVDA", runtime=False)
        self._by_id = {"JAWS": self.jaws, "NVDA": self.nvda}

    def acquire_best(self) -> _NamedBackend:
        return self.nvda

    def acquire(self, member: str) -> _NamedBackend:
        backend = self._by_id.get(member)
        if backend is None:
            raise RuntimeError("backend not available")
        return backend


def test_selects_live_screen_reader_over_acquire_best(monkeypatch) -> None:
    ctx = _MultiBackendContext()
    prism_module = types.SimpleNamespace(Context=lambda: ctx, BackendId=_FakeBackendId)
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge.import_module",
        lambda name: prism_module if name == "prism" else None,
    )
    monkeypatch.setattr(
        "quill.platform.windows.sr_detect.detect_screen_reader",
        lambda *a, **k: types.SimpleNamespace(detected=True, name="JAWS", source="jfw.exe"),
    )

    engine = AnnouncementEngine("auto")
    state = engine.state()

    assert state.active_backend == "prism"
    assert state.backend_name == "JAWS"  # not the inactive NVDA from acquire_best()

    # Forced announcements interrupt so the reader actually voices them (#700).
    assert engine.announce("Indented lines", force_speech=True) is None
    assert ctx.jaws.messages == ["Indented lines"]
    assert ctx.jaws.interrupts == [True]

    # Routine status does not interrupt the reader's current utterance.
    engine.announce("Saved")
    assert ctx.jaws.interrupts == [True, False]

    # The inactive backend is never spoken through.
    assert ctx.nvda.messages == []


class _FakeAO2Speaker:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.interrupts: list[bool] = []

    def speak(self, message: str, interrupt: bool = False) -> None:
        self.messages.append(message)
        self.interrupts.append(interrupt)


def test_falls_back_to_accessible_output2_when_prism_has_no_live_backend(monkeypatch) -> None:
    # Prism import fails (no live backend); accessible_output2 reports a live JAWS
    # reader, so announcements route through it instead of the SAPI self-voice.
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge.import_module",
        lambda _name: (_ for _ in ()).throw(ImportError),
    )
    speaker = _FakeAO2Speaker()
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge._ao2_live_screen_reader",
        lambda: (speaker, "JAWS"),
    )

    engine = AnnouncementEngine("auto")
    state = engine.state()

    assert state.active_backend == "accessible_output2"
    assert state.backend_name == "JAWS"

    # Forced announcements interrupt so the reader actually voices them.
    assert engine.announce("Indented lines", force_speech=True) is None
    assert speaker.messages == ["Indented lines"]
    assert speaker.interrupts == [True]

    # Routine status does not interrupt the reader.
    engine.announce("Saved")
    assert speaker.interrupts == [True, False]


def test_macos_announce_error_logged(monkeypatch, caplog) -> None:
    """H-4-platform: a VoiceOver announce failure is logged, not silently swallowed."""
    import logging

    monkeypatch.setattr("quill.platform.windows.prism_bridge.sys.platform", "darwin")
    # VoiceOver is running, so the darwin branch routes to the VoiceOver path
    # whose failure is the subject of this test (not the VoiceOver-off self-voice path).
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge._macos_screen_reader_active",
        lambda: True,
        raising=False,
    )
    monkeypatch.setattr(
        "quill.platform.windows.prism_bridge.import_module",
        lambda _name: (_ for _ in ()).throw(ImportError),
    )

    def _boom(_msg: str) -> None:
        raise RuntimeError("VoiceOver not available")

    monkeypatch.setattr(
        "quill.platform.macos.announce.announce",
        _boom,
        raising=False,
    )

    engine = AnnouncementEngine("auto")
    with caplog.at_level(logging.WARNING, logger="quill.platform.windows.prism_bridge"):
        result = engine.announce("test message")

    assert result is None
    assert any("VoiceOver" in r.message for r in caplog.records)
