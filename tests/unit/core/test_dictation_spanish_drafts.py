"""The drafted Spanish "pule eso" and "sí" / "no" (2026-10-17): off for everybody
until a native speaker has checked them, and working only behind the same
development switch as the rest of the drafted Spanish commands
(``vocabulary_es``). Fakes only: no microphone, no network, no window."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation.speech_language import SPANISH_COMMANDS_VARIABLE
from quill.core.windows_dictation.vocabulary import Command
from quill.core.windows_dictation.vocabulary_es import (
    SPANISH_ANSWERS,
    SPANISH_REVIEW_HELP,
    spanish_answer,
    spanish_review_command,
)
from quill.core.windows_dictation.words_file import load_words
from tests.unit.core.test_dictation_live_controller import _controller, _hear


@pytest.fixture
def drafts_on(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import paths

    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    monkeypatch.setenv(SPANISH_COMMANDS_VARIABLE, "1")


@pytest.fixture
def drafts_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SPANISH_COMMANDS_VARIABLE, raising=False)


# -- the tables ----------------------------------------------------------------- #


def test_the_drafts_are_written_with_their_accents() -> None:
    phrases = [phrase for entry in SPANISH_REVIEW_HELP for phrase in entry.phrases]
    assert "pule eso" in phrases and "púlelo" in phrases and "mejora eso" in phrases
    assert all(entry.command is Command.REVIEW_POLISH for entry in SPANISH_REVIEW_HELP)
    assert SPANISH_ANSWERS == {"yes": ("sí",), "no": ("no",)}


@pytest.mark.usefixtures("drafts_off")
def test_nothing_parses_while_the_switch_is_off() -> None:
    assert spanish_review_command(("pule", "eso"), "es") is None
    assert spanish_review_command(("mejora", "eso"), "es") is None
    assert spanish_answer(("si",), "es") == ""
    assert spanish_answer(("no",), "es") == ""


def test_a_release_build_ignores_the_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import paths

    monkeypatch.setenv(SPANISH_COMMANDS_VARIABLE, "1")
    monkeypatch.setattr(paths, "_DEV_BUILD", False)
    assert spanish_review_command(("pule", "eso"), "es") is None
    assert spanish_answer(("si",), "es") == ""


@pytest.mark.usefixtures("drafts_on")
def test_with_the_switch_on_they_parse_in_spanish_only() -> None:
    assert spanish_review_command(("pule", "eso"), "es") is Command.REVIEW_POLISH
    assert spanish_review_command(("pulelo",), "es") is Command.REVIEW_POLISH  # folded
    assert spanish_review_command(("mejora", "eso"), "es") is Command.REVIEW_POLISH
    assert spanish_review_command(("pule",), "es") is None  # the whole phrase only
    assert spanish_review_command(("pule", "eso"), "en") is None  # English never
    assert spanish_answer(("si",), "es") == "yes"
    assert spanish_answer(("no",), "es") == "no"
    assert spanish_answer(("si", "claro"), "es") == ""
    assert spanish_answer(("si",), "en") == ""


# -- through the controller ----------------------------------------------------- #


def _offer(tmp_path: Path, **preferences: Any) -> tuple[Any, Any, Path]:
    """QUILL Transcribe's shape: no yes/no window, so the offer is spoken."""
    controller, doc, feedback, _r, _clock, _h = _controller(engine="windows", **preferences)
    path = tmp_path / "dictation.md"
    feedback.words_path = lambda: path
    for _round in range(2):
        _hear(controller, "write to Ann", alternatives=("write to Anne",))
        _hear(controller, "correct that")
        _hear(controller, "choose one")
    assert feedback.said[-1].startswith("Add a correction: Ann becomes Anne?")
    return controller, feedback, path


@pytest.mark.usefixtures("drafts_off")
def test_quill_si_is_not_an_answer_while_the_switch_is_off(tmp_path: Path) -> None:
    controller, _feedback, path = _offer(tmp_path, speech_language="es")
    _hear(controller, "quill sí")
    assert not path.exists()
    _hear(controller, "quill yes")  # the English answer works in Spanish dictation
    assert ("Ann", "Anne") in load_words(path).corrections


@pytest.mark.usefixtures("drafts_on")
def test_quill_si_adds_the_correction_with_the_switch_on(tmp_path: Path) -> None:
    controller, _feedback, path = _offer(tmp_path, speech_language="es")
    _hear(controller, "quill sí")
    assert ("Ann", "Anne") in load_words(path).corrections


@pytest.mark.usefixtures("drafts_on")
def test_quill_no_still_declines_in_spanish(tmp_path: Path) -> None:
    controller, feedback, path = _offer(tmp_path, speech_language="es")
    _hear(controller, "quill no")
    assert feedback.said[-1] == "Not added."
    assert not path.exists()


@pytest.mark.usefixtures("drafts_on")
def test_english_dictation_never_takes_si(tmp_path: Path) -> None:
    controller, _feedback, path = _offer(tmp_path)
    _hear(controller, "quill sí")
    assert not path.exists()


def _review(**preferences: Any) -> tuple[Any, Any, Any]:
    from tests.unit.core.test_dictation_review import _controller as review_controller
    from tests.unit.core.test_dictation_review import _say

    controller, document, _feedback, desk = review_controller(polish=True, **preferences)
    assert desk is not None
    _say(controller, "nos vemos el jueves")
    _say(controller, "quill pule eso")
    return document, desk, _say


@pytest.mark.usefixtures("drafts_off")
def test_quill_pule_eso_is_not_a_command_while_the_switch_is_off() -> None:
    _document, desk, _say = _review(speech_language="es")
    assert desk.opened == [] and desk.commands == []


@pytest.mark.usefixtures("drafts_on")
def test_quill_pule_eso_polishes_with_the_switch_on() -> None:
    document, desk, _say = _review(speech_language="es")
    assert desk.opened == ["Nos vemos el jueves"]
    assert desk.commands == [Command.REVIEW_POLISH]
    assert document.text == ""
