"""GATE-BRAILLE: what QUILL speaks also reaches a braille display.

The static half is ``quill/tools/braille_parity_audit.py`` against its reviewed
snapshot; the behavioural half drives the real wiring with a fake engine, so a
message the service speaks is shown to have been written to braille, and one
the engine speaks on its own is shown to mirror itself.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.tools import braille_parity_audit as audit


# Reading every module under quill/ is I/O-bound; on a busy machine it has
# taken 13 s of the suite's 30 s ceiling.
@pytest.mark.timeout(120)
def test_every_unmirrored_speech_call_is_reviewed() -> None:
    found = audit.problems(audit.scan(), audit.load_snapshot())
    assert not found, "\n".join(found)


def _calls(source: str) -> dict[str, bool]:
    return {c.key.split("::", 1)[1]: c.mirrored for c in audit._calls_in(source, "m.py")}


def test_braille_on_the_same_path_counts_as_mirrored() -> None:
    source = (
        "class E:\n"
        "    def announce(self, m):\n"
        "        try:\n"
        "            self.engine.announce(m, force_speech=True)\n"
        "        except Exception:\n"
        "            return\n"
        "        if m:\n"
        "            self._braille_writer()(m)\n"
    )
    assert _calls(source) == {"E.announce::engine.announce": True}


def test_braille_in_another_branch_does_not_count() -> None:
    """The engine's Narrator fallback returns before the braille line."""
    source = (
        "def announce(self, m):\n"
        "    if self.backend is None:\n"
        "        if narrator_announce.announce(m, important=True):\n"
        "            return None\n"
        "        return None\n"
        "    speak(m, interrupt=False)\n"
        "    self._braille(m)\n"
    )
    assert _calls(source) == {
        "announce::narrator_announce.announce": False,
        "announce::speak(interrupt)": True,
    }


def test_speech_with_no_braille_at_all_is_reported() -> None:
    source = "def say(voice, m):\n    voice.speak(m, interrupt=True)\n"
    calls = audit._calls_in(source, "quill/x.py")
    assert [c.mirrored for c in calls] == [False]
    found = audit.problems(calls, {})
    assert found and "not classified" in found[0]


def test_a_row_needs_a_kind_and_a_reason_and_goes_when_its_call_does() -> None:
    calls = audit._calls_in("def say(v, m):\n    v.speak(m, interrupt=True)\n", "quill/x.py")
    key = calls[0].key
    assert audit.problems(calls, {key: {"kind": "speech_only", "reason": "why"}}) == []
    assert audit.problems(calls, {key: {"kind": "unreviewed", "reason": ""}})
    assert audit.problems(calls, {key: {"kind": "speech_only", "reason": " "}})
    stale = audit.problems([], {key: {"kind": "speech_only", "reason": "why"}})
    assert stale and "remove it" in stale[0]


class _Engine:
    """A Prism-like engine: speech and braille recorded, braille switchable."""

    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.brailled: list[str] = []
        self.inline_braille = True

    def announce(self, message: str, *, force_speech: bool = False) -> None:
        self.spoken.append(message)
        if self.inline_braille:
            self.brailled.append(message)

    def braille(self, message: str) -> str:
        self.brailled.append(message)
        return ""

    def set_braille_enabled(self, enabled: bool) -> None:
        self.inline_braille = enabled

    def braille_supported(self) -> bool:
        return True

    def state(self) -> SimpleNamespace:
        return SimpleNamespace(active_backend="prism", backend_name="NVDA")


def test_the_service_writes_braille_for_what_it_speaks_and_only_once() -> None:
    from quill.core.announce import Announcement, Severity
    from quill.ui.announce_wiring import build_announcement_service

    engine = _Engine()
    host = SimpleNamespace(_announcement_engine=engine, settings=None)
    service = build_announcement_service(host)

    for index, severity in enumerate((Severity.ROUTINE, Severity.WARNING, Severity.ERROR)):
        service.announce(Announcement(text=f"Saved {index}", severity=severity))

    assert engine.spoken == ["Saved 0", "Saved 1", "Saved 2"]
    # Every spoken message reached braille, and none twice: the wiring
    # switched the engine's inline braille off when it installed the sink.
    assert engine.inline_braille is False
    assert sorted(set(engine.brailled)) == engine.spoken
    assert all(engine.brailled.count(text) >= 1 for text in engine.spoken)


def test_the_engine_mirrors_its_own_speech_through_prism(monkeypatch) -> None:
    from quill.platform.windows import prism_bridge

    written: list[str] = []
    monkeypatch.setattr(prism_bridge, "braille_via_prism", lambda _b, m: written.append(m) or "")
    engine = prism_bridge.AnnouncementEngine.__new__(prism_bridge.AnnouncementEngine)
    engine._runtime_backend = SimpleNamespace(speak=lambda m, interrupt=False: None)
    engine._ao2_speaker = None
    engine._braille_enabled = True
    # Built by hand: the real constructor probes for a live screen reader.
    engine._state = prism_bridge.AnnouncementBackendState("auto", "prism", True, True, "NVDA")

    assert engine.announce("Document saved") is None
    assert written == ["Document saved"]
