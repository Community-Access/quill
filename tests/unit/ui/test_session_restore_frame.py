"""Reopening last session in QUILL: the same decisions, the same window.

``SessionRestoreMixin`` is driven with a duck-typed host rather than a real
``MainFrame``, which is how the other mixin tests in this suite work: what is
under test is which files open, what is remembered afterwards, and what is said.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from quill.core.session_restore import (
    ASK_ALWAYS,
    ASK_NEVER,
    ASK_WHEN_IT_MATTERS,
    SessionEntry,
)
from quill.ui.main_frame_session_restore import SessionRestoreMixin
from quill.ui.session_restore_dialog import SessionRestoreAnswer


@dataclass
class _Settings:
    session_files: list[str] = field(default_factory=list)
    session_restore_ask: str = "when_it_matters"
    restore_session: bool = True


class _Host(SessionRestoreMixin):
    def __init__(self, files: list[str]) -> None:
        self.settings = _Settings(session_files=list(files))
        self.frame = object()
        self.opened: list[Path] = []
        self.announced: list[str] = []
        self.status: list[str] = []
        self.saves = 0

    def open_file(self, path: Path, record_recent: bool = True) -> None:
        assert record_recent is False, "a restore is not somebody opening a file"
        self.opened.append(Path(path))

    def _announce(self, text: str) -> None:
        self.announced.append(text)

    def _set_status(self, text: str) -> None:
        self.status.append(text)


@pytest.fixture(autouse=True)
def _no_real_settings_write(monkeypatch):
    """The mixin saves settings; this suite is not testing the settings file."""
    monkeypatch.setattr("quill.core.settings.save_settings", lambda *a, **k: None)


@pytest.fixture
def three(tmp_path: Path) -> list[str]:
    paths = []
    for name in ("one.txt", "two.md", "three.rtf"):
        target = tmp_path / name
        target.write_text("x", encoding="utf-8")
        paths.append(str(target))
    return paths


class _Asked(list):  # type: ignore[type-arg]
    """What the dialog was asked, and the ask mode it was asked in."""

    def __init__(self) -> None:
        super().__init__()
        self.modes: list[str] = []


def _answer(monkeypatch, answer: SessionRestoreAnswer) -> _Asked:
    # A list of what the dialog was shown, carrying the mode it was shown in
    # as an attribute -- a list, because every existing caller compares this
    # against [] or reads its length. The mode decides which half of the
    # Never Ask Again / Ask Me Next Time pair the window offers, so a caller
    # that forgets to pass it greys out the only way back from never.
    asked = _Asked()

    def fake(
        _parent: object,
        entries: tuple[SessionEntry, ...],
        *,
        mode: str = ASK_WHEN_IT_MATTERS,
    ) -> SessionRestoreAnswer:
        asked.append(entries)
        asked.modes.append(mode)
        return answer

    monkeypatch.setattr("quill.ui.session_restore_dialog.ask_session_restore", fake)
    return asked


def test_one_file_reopens_silently_as_it_always_did(monkeypatch, three: list[str]) -> None:
    host = _Host(three[:1])
    asked = _answer(monkeypatch, SessionRestoreAnswer())

    assert host.restore_session() == 1

    assert asked == []
    assert host.opened == [Path(three[0])]


def test_three_files_bring_the_chooser_up(monkeypatch, three: list[str]) -> None:
    host = _Host(three)
    asked = _answer(
        monkeypatch,
        SessionRestoreAnswer(open_paths=(three[1],), remembered=tuple(three)),
    )

    assert host.restore_session() == 1

    assert len(asked) == 1
    assert host.opened == [Path(three[1])]


def test_a_file_that_moved_brings_it_up_on_its_own(monkeypatch, tmp_path: Path) -> None:
    here = tmp_path / "here.txt"
    here.write_text("x", encoding="utf-8")
    host = _Host([str(here), str(tmp_path / "gone.txt")])
    asked = _answer(monkeypatch, SessionRestoreAnswer(remembered=(str(here),)))

    host.restore_session()

    assert len(asked) == 1


def test_restore_session_off_does_nothing_at_all(monkeypatch, three: list[str]) -> None:
    host = _Host(three)
    host.settings.restore_session = False
    asked = _answer(monkeypatch, SessionRestoreAnswer())

    assert host.restore_session() == 0

    assert asked == []
    assert host.opened == []


def test_never_ask_reopens_everything_without_a_question(monkeypatch, three: list[str]) -> None:
    host = _Host(three)
    host.settings.session_restore_ask = ASK_NEVER
    asked = _answer(monkeypatch, SessionRestoreAnswer())

    assert host.restore_session() == 3

    assert asked == []


def test_always_ask_asks_about_a_single_file(monkeypatch, three: list[str]) -> None:
    host = _Host(three[:1])
    host.settings.session_restore_ask = ASK_ALWAYS
    asked = _answer(monkeypatch, SessionRestoreAnswer(remembered=tuple(three[:1])))

    host.restore_session()

    assert len(asked) == 1


def test_forgetting_is_saved_even_when_nothing_opens(monkeypatch, three: list[str]) -> None:
    """The one way a Forget could be lost is a caller that does not save it."""
    host = _Host(three)
    _answer(
        monkeypatch,
        SessionRestoreAnswer(
            remembered=(three[0],),
            forgotten=2,
            spoken="Forgot 2 documents. 1 still remembered. The files themselves are untouched.",
        ),
    )

    host.restore_session()

    assert host.settings.session_files == [three[0]]
    assert host.opened == []
    assert all(Path(path).is_file() for path in three)
    assert any("untouched" in said for said in host.announced)


def test_never_ask_again_writes_the_preference(monkeypatch, three: list[str]) -> None:
    host = _Host(three)
    _answer(
        monkeypatch,
        SessionRestoreAnswer(
            open_paths=tuple(three),
            remembered=tuple(three),
            ask_mode=ASK_NEVER,
            spoken="Last session will reopen without asking from now on.",
        ),
    )

    host.restore_session()

    assert host.settings.session_restore_ask == ASK_NEVER


def test_the_menu_command_says_so_when_nothing_is_remembered(monkeypatch) -> None:
    host = _Host([])
    asked = _answer(monkeypatch, SessionRestoreAnswer())

    assert host.reopen_last_session() == 0

    assert asked == []
    assert "Nothing was open last time" in host.status[0]


def test_the_menu_command_opens_the_same_chooser(monkeypatch, three: list[str]) -> None:
    """What makes Not Now safe: the answer is deferred, not lost."""
    host = _Host(three)
    asked = _answer(
        monkeypatch,
        SessionRestoreAnswer(open_paths=tuple(three), remembered=tuple(three)),
    )

    assert host.reopen_last_session() == 3

    assert len(asked) == 1


def test_one_unreadable_file_never_stops_the_rest(monkeypatch, three: list[str]) -> None:
    host = _Host(three)
    _answer(
        monkeypatch,
        SessionRestoreAnswer(open_paths=tuple(three), remembered=tuple(three)),
    )
    calls: list[Path] = []

    def explode(path: Path, record_recent: bool = True) -> None:
        calls.append(Path(path))
        if len(calls) == 2:
            raise OSError("no")

    host.open_file = explode  # type: ignore[method-assign]

    assert host.restore_session() == 2

    assert len(calls) == 3, "it kept going"


def test_the_list_is_described_in_one_sentence(three: list[str]) -> None:
    host = _Host(three)

    assert host.describe_session_list().startswith("3 documents")
