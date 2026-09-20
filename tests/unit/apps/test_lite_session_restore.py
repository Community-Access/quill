"""Reopening last session in QuillLite: asked about, and answerable in parts.

It reopened everything silently until 2026-09-19, which is right for one file and
wrong for four. These tests drive the real ``QuillLiteApp`` methods with a
duck-typed ``self`` rather than a wx application, because what is under test is
the decision and the bookkeeping -- which files open, what gets remembered, and
what is said -- and none of that needs a window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from quill.apps.lite import QuillLiteApp
from quill.apps.lite_window_commands import DocumentCommandsMixin
from quill.core.session_restore import ASK_ALWAYS, ASK_NEVER, SessionEntry
from quill.ui.session_restore_dialog import SessionRestoreAnswer


@dataclass
class _Settings:
    session_files: list[str] = field(default_factory=list)
    session_restore_ask: str = "when_it_matters"
    restore_session: bool = True


class _Voice:
    def __init__(self) -> None:
        self.said: list[str] = []

    def speak(self, text: str) -> None:
        self.said.append(text)


class _App:
    """Enough of ``QuillLiteApp`` for the session methods to run."""

    def __init__(self, files: list[str]) -> None:
        self.settings = _Settings(session_files=list(files))
        self.voice = _Voice()
        self.shell = object()
        self.opened: list[Path] = []
        self.saved = 0

    def open_path(self, path: Path) -> bool:
        self.opened.append(Path(path))
        return True

    def save_settings(self) -> None:
        self.saved += 1

    # The three methods under test, taken from the real class.
    choose_session_documents = QuillLiteApp.choose_session_documents
    _open_session_entries = QuillLiteApp._open_session_entries
    _restore_session = QuillLiteApp._restore_session


@pytest.fixture
def three(tmp_path: Path) -> list[str]:
    paths = []
    for name in ("one.txt", "two.md", "three.rtf"):
        target = tmp_path / name
        target.write_text("x", encoding="utf-8")
        paths.append(str(target))
    return paths


def _answer(monkeypatch, answer: SessionRestoreAnswer) -> list[tuple[SessionEntry, ...]]:
    """Patch the dialog where ``lite.py`` imports it, and record what it was asked."""
    asked: list[tuple[SessionEntry, ...]] = []

    def fake(_parent: object, entries: tuple[SessionEntry, ...]) -> SessionRestoreAnswer:
        asked.append(entries)
        return answer

    monkeypatch.setattr("quill.ui.session_restore_dialog.ask_session_restore", fake)
    return asked


# --------------------------------------------------------------------------- #
# The launch decision
# --------------------------------------------------------------------------- #


def test_one_file_still_opens_without_a_question(monkeypatch, three: list[str]) -> None:
    app = _App(three[:1])
    asked = _answer(monkeypatch, SessionRestoreAnswer())

    assert app._restore_session() is True

    assert app.opened == [Path(three[0])]
    assert asked == [], "one file that is still there needs no conversation"


def test_three_files_are_asked_about(monkeypatch, three: list[str]) -> None:
    app = _App(three)
    asked = _answer(
        monkeypatch,
        SessionRestoreAnswer(open_paths=(three[0],), remembered=tuple(three)),
    )

    app._restore_session()

    assert len(asked) == 1
    assert len(asked[0]) == 3
    assert app.opened == [Path(three[0])], "only what was chosen"


def test_a_missing_file_is_asked_about_even_on_its_own(monkeypatch, tmp_path: Path) -> None:
    here = tmp_path / "here.txt"
    here.write_text("x", encoding="utf-8")
    app = _App([str(here), str(tmp_path / "gone.txt")])
    asked = _answer(monkeypatch, SessionRestoreAnswer(remembered=(str(here),)))

    app._restore_session()

    assert len(asked) == 1, "a file that moved is exactly the case silence hides"


def test_never_ask_reopens_without_a_question(monkeypatch, three: list[str]) -> None:
    app = _App(three)
    app.settings.session_restore_ask = ASK_NEVER
    asked = _answer(monkeypatch, SessionRestoreAnswer())

    app._restore_session()

    assert asked == []
    assert len(app.opened) == 3


def test_always_ask_asks_about_one_file(monkeypatch, three: list[str]) -> None:
    app = _App(three[:1])
    app.settings.session_restore_ask = ASK_ALWAYS
    asked = _answer(monkeypatch, SessionRestoreAnswer(remembered=tuple(three[:1])))

    app._restore_session()

    assert len(asked) == 1


# --------------------------------------------------------------------------- #
# The answers
# --------------------------------------------------------------------------- #


def test_opening_two_of_three_says_so(monkeypatch, three: list[str]) -> None:
    app = _App(three)
    _answer(
        monkeypatch,
        SessionRestoreAnswer(open_paths=(three[0], three[2]), remembered=tuple(three)),
    )

    assert app.choose_session_documents() is True

    assert app.opened == [Path(three[0]), Path(three[2])]
    # Counted against what was *chosen*, not against the whole list: the person
    # picked two and got two, and "Reopened 2 of 3" would read as a failure.
    assert any("Reopened all 2 documents" in said for said in app.voice.said)


def test_a_chosen_file_that_will_not_open_is_counted_out_loud(
    monkeypatch, three: list[str], tmp_path: Path
) -> None:
    """The shortfall is the whole reason the sentence carries numbers."""
    gone = str(tmp_path / "gone.txt")
    app = _App(three)
    _answer(
        monkeypatch,
        SessionRestoreAnswer(open_paths=(three[0], gone), remembered=tuple(three)),
    )

    app.choose_session_documents()

    assert app.opened == [Path(three[0])]
    assert any("Reopened 1 of 2" in said for said in app.voice.said)


def test_not_now_opens_nothing_and_keeps_the_list(monkeypatch, three: list[str]) -> None:
    app = _App(three)
    _answer(
        monkeypatch,
        SessionRestoreAnswer(
            remembered=tuple(three),
            spoken="Nothing reopened. The same documents are offered next time.",
        ),
    )

    assert app.choose_session_documents() is False

    assert app.opened == []
    assert app.settings.session_files == three
    assert any("offered next time" in said for said in app.voice.said)


def test_forgetting_shortens_the_list_and_leaves_the_files(monkeypatch, three: list[str]) -> None:
    app = _App(three)
    _answer(
        monkeypatch,
        SessionRestoreAnswer(
            remembered=(three[0],),
            forgotten=2,
            spoken="Forgot 2 documents. 1 still remembered. The files themselves are untouched.",
        ),
    )

    app.choose_session_documents()

    assert app.settings.session_files == [three[0]]
    assert app.saved >= 1, "a Forget that is not saved is a Forget that did not happen"
    assert all(Path(path).is_file() for path in three), "forgetting must not delete"


def test_never_ask_again_writes_the_preference(monkeypatch, three: list[str]) -> None:
    app = _App(three)
    _answer(
        monkeypatch,
        SessionRestoreAnswer(
            open_paths=tuple(three),
            remembered=tuple(three),
            ask_mode=ASK_NEVER,
            spoken="Last session will reopen without asking from now on.",
        ),
    )

    app.choose_session_documents()

    assert app.settings.session_restore_ask == ASK_NEVER


def test_nothing_remembered_says_so_rather_than_opening_an_empty_window(monkeypatch) -> None:
    app = _App([])
    asked = _answer(monkeypatch, SessionRestoreAnswer())

    assert app.choose_session_documents() is False

    assert asked == []
    assert "Nothing was open last time" in app.voice.said[0]


def test_a_remembered_file_that_has_gone_is_not_opened(monkeypatch, tmp_path: Path) -> None:
    gone = str(tmp_path / "gone.txt")
    app = _App([gone])
    _answer(monkeypatch, SessionRestoreAnswer(open_paths=(gone,), remembered=(gone,)))

    app.choose_session_documents()

    assert app.opened == []
    assert any("Opened none" in said for said in app.voice.said)


# --------------------------------------------------------------------------- #
# The command
# --------------------------------------------------------------------------- #


class _Window:
    """The command's way in: a document window that defers to its app."""

    def __init__(self) -> None:
        self.app = _Reached()

    cmd_reopen_last_session = DocumentCommandsMixin.cmd_reopen_last_session


class _Reached:
    def __init__(self) -> None:
        self.calls = 0

    def choose_session_documents(self) -> bool:
        self.calls += 1
        return True


def test_the_command_reaches_the_app() -> None:
    win = _Window()

    win.cmd_reopen_last_session()

    assert win.app.calls == 1
