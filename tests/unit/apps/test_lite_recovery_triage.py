"""QUILL Lite's startup recovery: tidy first, then ask, and never go quiet.

The reported failure in one line: sixty-nine slots, one Yes/No, no way to tell
that sixty-seven of them were the same four characters. These tests drive
``LiteRecoveryMixin`` over a real recovery store in a temporary directory, with
the chooser replaced by a recorder -- the dialog itself is wx and is tested by
being the only thing left out.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest

from quill.apps.lite_recovery import LiteRecoveryMixin
from quill.core.lite import recovery as recovery_mod
from quill.core.lite.settings import Settings
from quill.ui.recovery_dialog import RecoveryAnswer

_DAY = 86400.0


class FakeVoice:
    def __init__(self) -> None:
        self.said: list[str] = []

    def speak(self, message: str) -> None:
        self.said.append(message)


class FakeApp(LiteRecoveryMixin):
    """The shipped mixin, over the few things it reaches for."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.voice = FakeVoice()
        self.shell = None
        self.opened: list[Any] = []
        self.saved = 0

    def new_window(self, mode: str, recovery_slot: Any = None) -> Any:
        self.opened.append(recovery_slot)
        return recovery_slot

    def save_settings(self) -> None:
        self.saved += 1


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real recovery store, somewhere harmless."""
    directory = tmp_path / "recovery"
    directory.mkdir()
    monkeypatch.setattr("quill.core.lite.recovery.recovery_dir", lambda: directory)
    return directory


def _slot(store: Path, text: str, *, path: str = "", age_days: float = 0.0, mode: str = "plain"):
    slot = recovery_mod.new_slot(mode, path)
    slot.content_path.write_text(text, encoding="utf-8")
    recovery_mod.write_meta(slot)
    written = time.time() - age_days * _DAY
    os.utime(slot.content_path, (written, written))
    return slot


@pytest.fixture
def app() -> FakeApp:
    return FakeApp(Settings())


def _answer_with(monkeypatch: pytest.MonkeyPatch, build) -> list[Any]:
    """Replace the chooser with a recorder that answers however *build* says."""
    seen: list[Any] = []

    def fake(_parent, result):
        seen.append(result)
        return build(result)

    monkeypatch.setattr("quill.ui.recovery_dialog.ask_recovery", fake)
    return seen


def test_identical_copies_are_one_row_before_anybody_is_asked(
    store: Path, app: FakeApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reported case, end to end: 67 slots, one question, one row."""
    for _ in range(67):
        _slot(store, "body")
    seen = _answer_with(monkeypatch, lambda _r: RecoveryAnswer())

    app._restore_pending_work()

    assert len(seen) == 1
    assert len(seen[0].offer) == 1
    assert seen[0].copies_of(seen[0].offer[0]) == 67


def test_the_folded_copies_are_deleted_from_the_store(
    store: Path, app: FakeApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Folding that leaves the files behind offers them all again next launch."""
    for _ in range(10):
        _slot(store, "body")
    _answer_with(monkeypatch, lambda _r: RecoveryAnswer())

    app._restore_pending_work()

    assert len(recovery_mod.pending(store)) == 1


def test_expired_copies_are_deleted_and_never_offered(
    store: Path, app: FakeApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    _slot(store, "old", age_days=90)
    seen = _answer_with(monkeypatch, lambda _r: RecoveryAnswer())

    assert app._restore_pending_work() is False

    assert seen == []  # nothing left to ask about
    assert recovery_mod.pending(store) == []


def test_tidying_everything_away_is_said_not_silent(
    store: Path, app: FakeApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Silence here is indistinguishable from work having gone missing."""
    _slot(store, "old", age_days=90)
    _answer_with(monkeypatch, lambda _r: RecoveryAnswer())

    app._restore_pending_work()

    said = " ".join(app.voice.said)
    assert "Tidied up unsaved work" in said
    assert "older than a month" in said


def test_untitled_work_is_dropped_when_the_setting_says_so(
    store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings()
    settings.recover_untitled_documents = False
    app = FakeApp(settings)
    _slot(store, "paste")
    named = _slot(store, "letter", path=str(store / "letter.md"))
    seen = _answer_with(monkeypatch, lambda _r: RecoveryAnswer())

    app._restore_pending_work()

    assert len(seen) == 1
    assert [slot.slot_id for slot in seen[0].offer] == [named.slot_id]


def test_restoring_opens_a_window_per_chosen_slot_and_says_how_many(
    store: Path, app: FakeApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    _slot(store, "one")
    _slot(store, "two")
    _answer_with(monkeypatch, lambda r: RecoveryAnswer(restore=r.offer))

    assert app._restore_pending_work() is True

    assert len(app.opened) == 2
    said = " ".join(app.voice.said)
    assert "Restored 2 unsaved documents" in said
    # Restoring is not saving, and a window that looks like a document is
    # exactly where that gets forgotten.
    assert "Save each one to keep it." in said


def test_declining_keeps_everything_and_says_it_will_be_offered_again(
    store: Path, app: FakeApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ "Not now" must cost nothing, or it is a decision rather than a delay."""
    _slot(store, "work")
    _answer_with(monkeypatch, lambda _r: RecoveryAnswer())

    assert app._restore_pending_work() is False

    assert app.opened == []
    assert len(recovery_mod.pending(store)) == 1
    assert "offered again next time" in " ".join(app.voice.said)


def test_discarding_deletes_the_chosen_slots(
    store: Path, app: FakeApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    _slot(store, "one")
    _slot(store, "two")
    _answer_with(monkeypatch, lambda r: RecoveryAnswer(discard=r.offer))

    app._restore_pending_work()

    assert recovery_mod.pending(store) == []


def test_never_offer_untitled_is_saved_as_a_preference(
    store: Path, app: FakeApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    _slot(store, "paste")
    _answer_with(monkeypatch, lambda _r: RecoveryAnswer(offer_untitled=False))

    app._restore_pending_work()

    assert app.settings.recover_untitled_documents is False
    assert app.saved == 1


def test_an_empty_store_asks_nothing_and_says_nothing(
    store: Path, app: FakeApp, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ordinary launch, which is every launch after a clean exit."""
    seen = _answer_with(monkeypatch, lambda _r: RecoveryAnswer())

    assert app._restore_pending_work() is False

    assert seen == []
    assert app.voice.said == []
