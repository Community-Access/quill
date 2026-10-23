"""Models removed from the catalogue: gone from every list, a saved choice moves
to Parakeet Unified only when it is already here, nothing is downloaded or
deleted, and the change is said once across the family (removed_models.py;
dictation design 36, 37)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.windows_dictation import engines, removed_models
from quill.core.windows_dictation.model_catalog import CATALOGUE, downloadable
from quill.core.windows_dictation.model_types import MEASURED

_FIVE = {
    "distil_small_en",
    "whisper_small_en",
    "distil_medium_en",
    "whisper_medium_en",
    "distil_large_v3",
}


@pytest.fixture
def notices(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(removed_models, "_notices_path", lambda _folder: tmp_path / "n.json")
    return tmp_path / "n.json"


def _parakeet_installed(monkeypatch: pytest.MonkeyPatch, here: bool) -> None:
    import quill.core.windows_dictation.model_store as model_store

    monkeypatch.setattr(model_store, "installed", lambda model: here)


def test_the_five_are_recorded_and_gone_from_the_catalogue() -> None:
    assert set(removed_models.REMOVED) == _FIVE
    for model_id in _FIVE:
        assert downloadable(model_id) is None
        assert model_id not in MEASURED
    assert downloadable("parakeet_unified") is not None
    assert downloadable("whisper_base_en") is not None  # base.en stays


def test_the_multilingual_whisper_sizes_stay() -> None:
    sizes = {m.id for m in CATALOGUE if m.kind == "whisper" and "es" in m.languages}
    assert {"whisper_base", "whisper_small", "whisper_medium", "whisper_turbo"} <= sizes


def test_a_saved_removed_model_gives_way_to_the_built_in_one(
    notices: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _parakeet_installed(monkeypatch, False)
    assert engines.coerce_engine("whisper_medium_en") == engines.DEFAULT_ENGINE
    said = removed_models.take_notice()
    assert said.startswith("Whisper medium.en was removed in this release")
    assert "built-in model" in said
    assert "Parakeet Unified" in said
    assert removed_models.take_notice() == ""  # once


def test_it_moves_to_parakeet_unified_only_when_already_downloaded(
    notices: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _parakeet_installed(monkeypatch, True)
    assert engines.coerce_engine("distil_small_en") == "parakeet_unified"
    said = removed_models.take_notice()
    assert said == (
        "Distil-Whisper small.en was removed in this release. Dictation now uses "
        "Parakeet Unified, which you already have."
    )


def test_the_notice_is_said_once_across_the_family(
    notices: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _parakeet_installed(monkeypatch, False)
    engines.coerce_engine("whisper_small_en")
    engines.coerce_engine("whisper_small_en")  # every program that loads it
    assert removed_models.take_notice().count("removed") == 1
    engines.coerce_engine("whisper_small_en")  # a program that had not saved yet
    assert removed_models.take_notice() == ""


def test_an_unknown_engine_records_nothing(notices: Path) -> None:
    assert engines.coerce_engine("no_such_model") == engines.DEFAULT_ENGINE
    assert engines.coerce_engine("parakeet_unified") == "parakeet_unified"
    assert not notices.exists()
    assert removed_models.take_notice() == ""


def test_a_notice_that_cannot_be_recorded_is_still_said(
    notices: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _parakeet_installed(monkeypatch, False)
    removed_models.noticed("distil_large_v3", "")
    import quill.core.storage as storage

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError("read-only")

    monkeypatch.setattr(storage, "write_json_atomic", refuse)
    assert removed_models.take_notice().startswith("Distil-Whisper large-v3 was removed")


def test_starting_dictation_after_a_removal_says_so_once(
    notices: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.windows_dictation.controller import DictationController
    from quill.core.windows_dictation.preferences import DictationPreferences
    from tests.unit.core.test_dictation_live_controller import Doc, Feedback, Recognizer

    _parakeet_installed(monkeypatch, False)
    feedback = Feedback()
    prefs = DictationPreferences(
        engine=engines.coerce_engine("whisper_small_en"),
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
    assert any("was removed in this release" in s for s in feedback.said)
    controller.stop()
    feedback.said.clear()
    controller.start()
    assert not any("was removed" in s for s in feedback.said)
