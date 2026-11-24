"""How Scribe for Documents tells the person about a conversion (2026-11-23).

Jeff: nothing announced in the main window, rich choices (sound, speech,
both, none) for each kind of moment, and different sounds for success and
failure. These are the wx-free rules; the routing through the controller is
``tests/unit/ui/test_scribe_feedback_routing.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.action_feedback import ActionFeedback
from quill.core.scribe import feedback as fb
from quill.core.scribe.feedback import EVERYWHERE, SCRIBE_WINDOWS, FeedbackChoices, Moment
from quill.core.scribe.options import ScribeOptions, load_options, save_options
from quill.core.sound_events import SoundEvent

ALL_SOUNDS = lambda _event: True  # noqa: E731 - a pack that has everything
NO_SOUNDS = lambda _event: False  # noqa: E731


def _plan(choices: FeedbackChoices, moment: Moment, **kw: object) -> fb.Delivery:
    kw.setdefault("has_sound", ALL_SOUNDS)
    kw.setdefault("scribe_window_in_front", False)
    return fb.plan(choices, moment, **kw)  # type: ignore[arg-type]


def test_the_defaults_speak_nothing_and_end_with_a_sound() -> None:
    choices = FeedbackChoices()
    for moment in Moment:
        assert not _plan(choices, moment).speak, moment
        assert not _plan(choices, moment, scribe_window_in_front=True).speak, moment
    assert _plan(choices, Moment.STARTED).sound == ""
    assert _plan(choices, Moment.STAGE, scribe_window_in_front=True).sound == ""
    assert _plan(choices, Moment.FINISHED).sound == SoundEvent.SCRIBE_FINISHED
    assert _plan(choices, Moment.FAILED).sound == SoundEvent.SCRIBE_FAILED


def test_success_and_failure_are_different_sounds() -> None:
    sounds = {fb.sound_for(moment) for moment in (Moment.STARTED, Moment.FINISHED, Moment.FAILED)}
    assert len(sounds) == 3
    assert fb.sound_for(Moment.FINISHED) != fb.sound_for(Moment.FAILED)
    assert fb.sound_for(Moment.FINISHED) != SoundEvent.TASK_COMPLETE
    assert fb.sound_for(Moment.FAILED) != SoundEvent.ERROR


@pytest.mark.parametrize("moment", list(Moment))
@pytest.mark.parametrize(
    ("mode", "sound", "speak"),
    [
        ("sound", True, False),
        ("speech", False, True),
        ("both", True, True),
        ("silent", False, False),
    ],
)
def test_each_moment_in_each_mode(moment: Moment, mode: str, sound: bool, speak: bool) -> None:
    choices = FeedbackChoices(stage_scope=EVERYWHERE)
    choices.set_mode(moment, mode)
    delivery = _plan(choices, moment)
    assert bool(delivery.sound) is sound
    assert delivery.speak is speak
    if sound:
        assert delivery.sound == fb.sound_for(moment)


def test_a_sound_the_pack_lacks_is_said_instead_and_silent_stays_silent() -> None:
    choices = FeedbackChoices()
    assert _plan(choices, Moment.FINISHED, has_sound=NO_SOUNDS) == fb.Delivery("", True)
    choices.finished = "silent"
    assert _plan(choices, Moment.FINISHED, has_sound=NO_SOUNDS) == fb.NOTHING


def test_stage_feedback_follows_its_scope() -> None:
    choices = FeedbackChoices(stage="speech")
    assert _plan(choices, Moment.STAGE) == fb.NOTHING
    assert _plan(choices, Moment.STAGE, scribe_window_in_front=True).speak
    choices.stage_scope = EVERYWHERE
    assert _plan(choices, Moment.STAGE).speak
    # The scope is the stage's alone: the end of a job is heard anywhere.
    choices.stage_scope = SCRIBE_WINDOWS
    assert _plan(choices, Moment.FINISHED).sound


def test_a_stage_sound_is_the_progress_ladder() -> None:
    choices = FeedbackChoices(stage="sound", stage_scope=EVERYWHERE)
    assert _plan(choices, Moment.STAGE, percent=50).sound == "progress_50"
    assert _plan(choices, Moment.STAGE).sound == SoundEvent.PROGRESS_TICK


def test_unknown_values_become_each_fields_default() -> None:
    made = FeedbackChoices.from_mapping({
        "started": "LOUD",
        "finished": "speech",
        "failed": 3,
        "stage_scope": "moon",
    })
    assert made.mode(Moment.STARTED) is ActionFeedback.SILENT
    assert made.mode(Moment.FINISHED) is ActionFeedback.SPEECH
    assert made.mode(Moment.FAILED) is ActionFeedback.SOUND
    assert made.stage_scope == SCRIBE_WINDOWS
    assert FeedbackChoices.from_mapping("nonsense") == FeedbackChoices()


@pytest.mark.parametrize(
    ("old", "expected"),
    [
        # The old default, in every file: the new defaults.
        ("front", FeedbackChoices()),
        (None, FeedbackChoices()),
        # A choice for no stage speech: the new default agrees.
        ("never", FeedbackChoices()),
        # A choice for more speech keeps all of it, and gains the sounds.
        (
            "always",
            FeedbackChoices(
                started="speech",
                stage="speech",
                finished="both",
                failed="both",
                stage_scope=EVERYWHERE,
            ),
        ),
    ],
)
def test_an_older_file_is_migrated(tmp_path: Path, old: str | None, expected: object) -> None:
    path = tmp_path / "options.json"
    data = {"open_results": "offer"}
    if old is not None:
        data["speak_stages"] = old
    path.write_text(json.dumps(data), encoding="utf-8")
    options = load_options(path)
    assert options.feedback == expected
    assert options.open_results == "offer"


def test_choices_persist_and_the_old_field_is_still_written(tmp_path: Path) -> None:
    path = tmp_path / "options.json"
    options = ScribeOptions()
    options.feedback = FeedbackChoices(stage="both", stage_scope=EVERYWHERE, started="speech")
    save_options(options, path)
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["feedback"] == {
        "started": "speech",
        "stage": "both",
        "finished": "sound",
        "failed": "sound",
        "stage_scope": "everywhere",
    }
    assert written["speak_stages"] == "always"  # what an older build reads
    assert load_options(path).feedback == options.feedback
    # A saved file is never migrated again, even with the old field present.
    options.feedback = FeedbackChoices()
    save_options(options, path)
    assert json.loads(path.read_text(encoding="utf-8"))["speak_stages"] == "never"
    assert load_options(path).feedback == FeedbackChoices()


def test_the_old_field_maps_back() -> None:
    assert fb.to_speak_stages(FeedbackChoices()) == "never"
    assert fb.to_speak_stages(FeedbackChoices(stage="sound")) == "front"
    assert fb.to_speak_stages(FeedbackChoices(stage="speech", stage_scope=EVERYWHERE)) == "always"


def test_the_sounds_are_in_the_scheme_with_labels_and_clips() -> None:
    from quill.core.sound_pack import load_sound_pack, resolve_sound_pack_path
    from quill.ui.sound_event_labels import GROUP_FOR, LABELS

    pack = load_sound_pack(resolve_sound_pack_path(""))
    for event in fb.MOMENT_SOUNDS.values():
        assert GROUP_FOR[event] == "Scribe for Documents"
        assert LABELS[event]
        assert event in pack.events, f"the Ink pack has no clip for {event}"
    assert pack.events[SoundEvent.SCRIBE_FINISHED] != pack.events[SoundEvent.SCRIBE_FAILED]


def test_quill_lite_lists_every_scribe_sound() -> None:
    from quill.core.sound_app_events import QUILLLITE_EVENTS

    for event in (*fb.MOMENT_SOUNDS.values(), SoundEvent.PROGRESS_TICK, "progress_25"):
        assert event in QUILLLITE_EVENTS
