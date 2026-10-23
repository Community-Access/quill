"""Models being retired: said once across the family, flagged in every list,
never recommended, never switched (retiring.py; dictation design 32.6, 36)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.windows_dictation import model_advice, retiring
from quill.core.windows_dictation.model_catalog import CATALOGUE, downloadable


def test_every_retiring_model_and_replacement_is_in_the_catalogue() -> None:
    assert retiring.RETIRING, "the 2026-10-22 decisions are recorded"
    for entry in retiring.RETIRING.values():
        assert downloadable(entry.model_id) is not None
        replacement = downloadable(entry.replacement)
        assert replacement is not None
        assert not retiring.is_retiring(entry.replacement)  # never retire to a leaver
        assert entry.evidence.endswith(".")


def test_the_multilingual_whisper_sizes_stay() -> None:
    # The only local models for many languages (design 32.6): never retired.
    for model in CATALOGUE:
        if model.kind == "whisper" and "es" in model.languages:
            assert not retiring.is_retiring(model.id), model.id


def test_a_retiring_model_says_so_first_in_every_list() -> None:
    for model in CATALOGUE:
        if retiring.is_retiring(model.id):
            assert model.good_for.startswith("Being retired, use "), model.id
            assert model.description.startswith("Being retired. In our tests"), model.id
        else:
            assert not model.good_for.startswith("Being retired"), model.id


def test_the_notice_is_said_once_across_the_family(tmp_path: Path) -> None:
    model_id = next(iter(retiring.RETIRING))
    first = retiring.take_notice(model_id, folder=tmp_path)
    # Short, front-loaded: it is said as the microphone opens (a11y review).
    assert first.startswith("Retiring: ")
    assert "nothing changes until you choose another model" in first
    assert len(first) < 160
    # The measured reason is in the details, naming both models.
    assert retiring.reason(model_id).startswith("Being retired. In our tests with real")
    assert "Parakeet Unified got 3.2 percent" in retiring.reason(model_id)
    assert retiring.take_notice(model_id, folder=tmp_path) == ""
    assert (tmp_path / "retiring-notices.json").is_file()


def test_a_model_that_stays_says_nothing(tmp_path: Path) -> None:
    assert retiring.take_notice("moonshine", folder=tmp_path) == ""
    assert retiring.take_notice("parakeet_unified", folder=tmp_path) == ""
    assert not (tmp_path / "retiring-notices.json").exists()


def test_a_notice_that_cannot_be_recorded_is_still_said(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.storage as storage

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError("read-only")

    monkeypatch.setattr(storage, "write_json_atomic", refuse)
    model_id = next(iter(retiring.RETIRING))
    assert retiring.take_notice(model_id, folder=tmp_path)


def test_a_retiring_model_is_never_recommended() -> None:
    from quill.core.windows_dictation.speed_check import SpeedCheck

    machines = (
        SpeedCheck(tiny=0.12, cores=2, memory_gb=3.8),
        SpeedCheck(tiny=0.05, cores=4, memory_gb=7.8),
        SpeedCheck(tiny=0.04, cores=8, memory_gb=31.8),
    )
    for check in machines:
        for language in ("en", "es"):
            for priority, _label in model_advice.PRIORITIES:
                chosen = model_advice.recommend(check, language, priority=priority).model_id
                assert not retiring.is_retiring(chosen), (check, language, priority)


def test_starting_dictation_on_a_retiring_model_says_so_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.windows_dictation.controller import DictationController
    from quill.core.windows_dictation.preferences import DictationPreferences
    from tests.unit.core.test_dictation_live_controller import Doc, Feedback, Recognizer

    monkeypatch.setattr(retiring, "_notices_path", lambda _folder: tmp_path / "said.json")
    model_id = next(iter(retiring.RETIRING))
    feedback = Feedback()
    prefs = DictationPreferences(
        engine=model_id, phrase_feedback="silent", cue_sounds=False, announce=False
    )
    controller = DictationController(
        recognizer=lambda _c, _p: Recognizer(),
        document=Doc(),
        feedback=feedback,
        preferences=lambda: prefs,
    )
    controller.start()
    assert any(s.startswith("Retiring: ") for s in feedback.said)
    controller.stop()
    feedback.said.clear()
    controller.start()
    assert not any(s.startswith("Retiring: ") for s in feedback.said)


def test_transcribe_details_carry_the_measured_reason() -> None:
    from quill.core.transcribe.models import model_rows

    rows = {row.id: row for row in model_rows()}
    for model_id in retiring.RETIRING:
        if model_id in rows:
            note = rows[model_id].note
            assert note.startswith("Being retired, use ")
            assert "In our tests with real recordings, Parakeet Unified got" in note
    assert "In our tests" not in rows["parakeet_unified"].note
