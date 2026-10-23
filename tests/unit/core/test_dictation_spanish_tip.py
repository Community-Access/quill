"""The one-time Spanish model tip: only when Spanish would go to the built-in
Whisper tiny on a computer whose own Spanish recommendation is a download, said
once across the family, never switching or downloading (spanish_tip.py)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.windows_dictation import model_advice, spanish_tip
from quill.core.windows_dictation.speed_check import SpeedCheck

_EIGHT_GB = SpeedCheck(tiny=0.05, cores=4, memory_gb=7.8)
_FOUR_GB = SpeedCheck(tiny=0.12, cores=2, memory_gb=3.8)


@pytest.fixture
def computer(monkeypatch: pytest.MonkeyPatch):
    """Set which computer the advice is for, and whether Parakeet is here."""
    import quill.core.windows_dictation.model_store as model_store

    state = {"check": _EIGHT_GB, "installed": False}
    monkeypatch.setattr(
        model_advice,
        "for_this_computer",
        lambda language="en", priority=model_advice.PRIORITY_BALANCED: model_advice.recommend(
            state["check"], language, priority=priority
        ),
    )
    monkeypatch.setattr(model_store, "installed", lambda model: state["installed"])
    return state


def test_an_8_gb_computer_dictating_spanish_on_the_built_in_model_hears_it(computer) -> None:
    said = spanish_tip.tip("moonshine", "es")
    assert said.startswith("For Spanish, NVIDIA Parakeet TDT")
    assert "about 6 percent of words wrong, against 29 for the built-in model" in said
    assert said.endswith("download in the model list.")
    assert len(said) < 200  # it is said as the microphone opens


def test_already_downloaded_says_choose_it(computer) -> None:
    computer["installed"] = True
    assert spanish_tip.tip("whisper", "es").endswith(
        "It is already downloaded; choose it in the model list."
    )


def test_an_english_only_download_dictating_spanish_counts(computer) -> None:
    # Parakeet Unified knows no Spanish, so Spanish goes to Whisper tiny too.
    assert spanish_tip.tip("parakeet_unified", "es")


@pytest.mark.parametrize(
    ("engine", "language"),
    [
        ("moonshine", "en"),  # English is not the problem
        ("parakeet", "es"),  # already the good Spanish model
        ("whisper_small", "es"),  # a Spanish model of its own
        ("windows", "es"),  # Windows does the recognising
    ],
)
def test_nothing_when_spanish_is_not_on_whisper_tiny(computer, engine: str, language: str) -> None:
    assert spanish_tip.tip(engine, language) == ""


def test_a_4_gb_computer_is_left_on_the_built_in_model(computer) -> None:
    computer["check"] = _FOUR_GB
    assert spanish_tip.tip("moonshine", "es") == ""


def test_said_once_across_the_family(computer, tmp_path: Path) -> None:
    assert spanish_tip.take_tip("moonshine", "es", folder=tmp_path)
    assert (tmp_path / "spanish-tip.json").is_file()
    assert spanish_tip.take_tip("moonshine", "es", folder=tmp_path) == ""


def test_nothing_recorded_when_nothing_was_said(computer, tmp_path: Path) -> None:
    assert spanish_tip.take_tip("moonshine", "en", folder=tmp_path) == ""
    assert not (tmp_path / "spanish-tip.json").exists()


def test_a_tip_that_cannot_be_recorded_is_still_said(
    computer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.storage as storage

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError("read-only")

    monkeypatch.setattr(storage, "write_json_atomic", refuse)
    assert spanish_tip.take_tip("moonshine", "es", folder=tmp_path)


def test_starting_dictation_in_spanish_says_it_once(
    computer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.windows_dictation import removed_models
    from quill.core.windows_dictation.controller import DictationController
    from quill.core.windows_dictation.preferences import DictationPreferences
    from tests.unit.core.test_dictation_live_controller import Doc, Feedback, Recognizer

    monkeypatch.setattr(spanish_tip, "_tip_path", lambda _folder: tmp_path / "tip.json")
    monkeypatch.setattr(removed_models, "_notices_path", lambda _folder: tmp_path / "n.json")
    feedback = Feedback()
    prefs = DictationPreferences(
        engine="moonshine",
        speech_language="es",
        phrase_feedback="silent",
        cue_sounds=False,
        announce=False,
    )
    controller = DictationController(
        recognizer=lambda _c, _p: Recognizer(),
        document=Doc(),
        feedback=feedback,
        preferences=lambda: prefs,
    )
    controller.start()
    assert any(s.startswith("For Spanish, ") for s in feedback.said)
    controller.stop()
    feedback.said.clear()
    controller.start()
    assert not any(s.startswith("For Spanish, ") for s in feedback.said)
