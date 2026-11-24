"""Scribe for Documents feedback through the controller and in Options (2026-11-23).

Fake speech and sound sinks: the host records what it was asked to say and
which sounds it was asked to play, and claims every sound exists (as the
bundled Ink pack does), so a ``sound`` choice is not turned into words.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.scribe import queue as q
from quill.core.scribe.feedback import EVERYWHERE, FeedbackChoices, Moment
from quill.core.sound_events import SoundEvent
from tests.unit.ui.test_scribe_ui import (  # noqa: F401 - fixtures used by name
    controller,
    isolated,
)

pytestmark = pytest.mark.usefixtures("wx_session_app")

FINISHED = SoundEvent.SCRIBE_FINISHED.value
FAILED = SoundEvent.SCRIBE_FAILED.value


def _sinks(controller: Any) -> Any:  # noqa: F811
    host = controller.host
    host.cues = []
    host.status = []
    host.scribe_cue = host.cues.append
    host.scribe_has_sound = lambda _event: True
    host.scribe_status_text = host.status.append
    controller._service = type("S", (), {"holding": True})()
    options = controller.options()
    options.open_results = "no"  # nothing opens; the result is only said
    controller.save_options(options)
    return host


def _choose(controller: Any, **modes: str) -> None:  # noqa: F811
    options = controller.options()
    options.feedback = FeedbackChoices(stage_scope=EVERYWHERE, **modes)
    controller.save_options(options)


def _job(**kw: Any) -> q.Job:
    kw.setdefault("file_name", "Notes.pdf")
    return q.Job(formats=["docx"], **kw)


def _stage_job() -> q.Job:
    return _job(state=q.CONVERTING, format="docx", stage="add_image_descriptions")


def _failed_job() -> q.Job:
    return _job(state=q.FAILED, message="The file is damaged.", error_code="QUILL-SCRIBE-FAILED")


#: (moment, the runner event that is that moment, its job)
EVENTS = [
    (Moment.STARTED, "started", lambda: _job()),
    (Moment.STAGE, "changed", _stage_job),
    (Moment.FINISHED, "done", lambda: _job(state=q.DONE)),
    (Moment.FAILED, "error", _failed_job),
    (Moment.FAILED, "needs_you", lambda: _job(state=q.NEEDS_SIGNIN)),
]


def _notices() -> list[Any]:
    from quill.core.notifications import load_notifications

    return [n for n in load_notifications() if n.title == "Scribe for Documents"]


def test_by_default_nothing_is_said_and_the_end_of_a_job_is_a_sound(
    controller: Any,  # noqa: F811
) -> None:
    host = _sinks(controller)
    controller._on_event("started", _job())
    controller._on_event("changed", _stage_job())
    controller._on_event("done", _job(state=q.DONE))
    controller._on_event("error", _failed_job())
    assert host.said == []
    assert host.cues == [FINISHED, FAILED]
    # The words are kept where a missed sound can be found again (FUX-04).
    assert any(text.startswith("Scribe for Documents made") for text in host.status)
    assert host.status[-1] == (
        "Scribe for Documents could not convert Notes.pdf: The file is damaged."
    )
    notices = _notices()
    assert [n.category for n in notices] == ["info", "error"]
    assert "could not convert Notes.pdf" in notices[-1].body
    controller.repeat_last()
    assert host.said == [host.status[-1]]


@pytest.mark.parametrize(("moment", "kind", "make"), EVENTS)
@pytest.mark.parametrize(
    ("mode", "sound", "speak"),
    [
        ("sound", True, False),
        ("speech", False, True),
        ("both", True, True),
        ("silent", False, False),
    ],
)
def test_each_event_in_each_mode_routes_to_its_sink(
    controller: Any,  # noqa: F811
    moment: Moment,
    kind: str,
    make: Any,
    mode: str,
    sound: bool,
    speak: bool,
) -> None:
    host = _sinks(controller)
    _choose(controller, **{moment.value: mode})
    controller._on_event(kind, make())
    assert len(host.said) == (1 if speak else 0)
    assert len(host.cues) == (1 if sound else 0)
    if sound:
        from quill.core.scribe.feedback import sound_for

        assert host.cues == [sound_for(moment)]


def test_stage_feedback_by_default_waits_for_a_scribe_window(
    controller: Any,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _sinks(controller)
    options = controller.options()
    options.feedback = FeedbackChoices(stage="speech")  # the scope left at its default
    controller.save_options(options)
    controller._on_event("changed", _stage_job())
    assert host.said == []
    monkeypatch.setattr(controller, "_scribe_window_in_front", lambda: True)
    controller._on_event("changed", _job(state=q.CONVERTING, format="docx", stage="ocr"))
    assert len(host.said) == 1


def test_the_conversions_window_counts_as_a_scribe_window(controller: Any) -> None:  # noqa: F811
    from quill.core.scribe.feedback import SCRIBE_WINDOW_ATTR
    from quill.ui.scribe_conversions_window import ScribeConversionsWindow
    from quill.ui.scribe_documents_dialog import ScribeDocumentsDialog

    assert getattr(ScribeConversionsWindow, SCRIBE_WINDOW_ATTR) is True
    assert getattr(ScribeDocumentsDialog, SCRIBE_WINDOW_ATTR) is True


def test_nothing_is_said_or_played_twice(controller: Any) -> None:  # noqa: F811
    host = _sinks(controller)
    _choose(controller, stage="both", finished="both", failed="both")
    stage = _stage_job()
    controller._on_event("changed", stage)
    controller._on_event("changed", stage)
    assert len(host.said) == 1
    controller._on_event("needs_you", _job(id="j2", state=q.NEEDS_SIGNIN))
    controller._on_event("needs_you", _job(id="j2", state=q.NEEDS_SIGNIN))
    assert len(host.said) == 2
    assert host.cues.count(FAILED) == 1


def test_a_milestone_sound_is_its_step_on_the_progress_ladder(
    controller: Any,  # noqa: F811
) -> None:
    host = _sinks(controller)
    _choose(controller, stage="sound")
    job = _stage_job()
    controller._on_event("changed", job)
    job.progress = 0.55
    controller._on_event("changed", job)
    assert host.cues == [SoundEvent.PROGRESS_TICK.value, "progress_50"]
    assert host.said == []


def test_the_batch_summary_does_not_play_the_sound_again(
    controller: Any,  # noqa: F811
) -> None:
    host = _sinks(controller)
    _choose(controller, finished="both")
    jobs = [
        _job(id="a", file_name="A.pdf", batch="b1", state=q.DONE),
        _job(id="b", file_name="B.pdf", batch="b1", state=q.DONE),
    ]
    controller.queue.add(jobs)
    for job in jobs:
        controller.queue.update(job.id, state=q.DONE)
    controller._on_event("done", controller.queue.get("b"))
    assert host.cues == [FINISHED]
    assert len(host.said) == 2  # the result, then what the batch made


# ------------------------------------------------------------------ Options


def _all_children(window: Any) -> list[Any]:
    found, stack = [], list(window.GetChildren())
    while stack:
        child = stack.pop()
        found.append(child)
        stack.extend(child.GetChildren())
    return found


def test_options_show_the_choices_with_their_defaults(controller: Any) -> None:  # noqa: F811
    from quill.ui.scribe_options_dialog import ScribeOptionsDialog

    dialog = ScribeOptionsDialog(None, controller)
    try:
        section = dialog.feedback
        assert [section.modes[m].GetStringSelection() for m in Moment] == [
            "Neither",
            "Neither",
            "Play a sound",
            "Play a sound",
        ]
        assert section.scope.GetStringSelection().startswith("Only while a Scribe")
        section.modes[Moment.STARTED].SetSelection(1)  # Speak the action
        section.scope.SetSelection(1)
        result = dialog.result()
        assert result.feedback.started == "speech"
        assert result.feedback.stage_scope == EVERYWHERE
        assert result.feedback.finished == "sound"
    finally:
        dialog.Destroy()


def test_options_access_keys_are_unique_in_the_whole_window(
    controller: Any,  # noqa: F811
) -> None:
    """GATE-14 across the dialog and the section it borrows (the gate scopes
    the helper class on its own, so it cannot see the two together)."""
    import re

    from quill.ui.scribe_options_dialog import ScribeOptionsDialog

    dialog = ScribeOptionsDialog(None, controller)
    try:
        keys: list[str] = []
        for child in _all_children(dialog):
            label = child.GetLabel() if hasattr(child, "GetLabel") else ""
            match = re.search(r"&([^&\s])", label or "")
            if match:
                keys.append(match.group(1).lower())
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        assert duplicates == []
    finally:
        dialog.Destroy()


def test_play_previews_each_sound_and_says_why_when_it_cannot(
    controller: Any,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.ui import scribe_feedback_settings, sound_manager
    from quill.ui.scribe_options_dialog import ScribeOptionsDialog

    played: list[str] = []
    monkeypatch.setattr(sound_manager, "is_active", lambda: True)
    monkeypatch.setattr(sound_manager, "has_sound_for", lambda _event: True)
    monkeypatch.setattr(sound_manager, "post_sound", played.append)
    dialog = ScribeOptionsDialog(None, controller)
    try:
        section = dialog.feedback
        section.play(Moment.FINISHED)
        section.play(Moment.FAILED)
        assert played == [FINISHED, FAILED]
        assert controller.host.said == []  # a sound that played needs no words
        monkeypatch.setattr(sound_manager, "is_active", lambda: False)
        section.play(Moment.FINISHED)
        assert controller.host.said == [
            "Sounds are turned off, so nothing played, and a finished conversion is spoken instead."
        ]
        monkeypatch.setattr(sound_manager, "is_active", lambda: True)
        monkeypatch.setattr(sound_manager, "has_sound_for", lambda _event: False)
        assert "no failure sound" in scribe_feedback_settings.preview_sound(Moment.FAILED)
        monkeypatch.setattr(sound_manager, "has_sound_for", lambda _event: True)
        monkeypatch.setattr(sound_manager, "is_event_switched_off", lambda e: e == FINISHED)
        said = scribe_feedback_settings.preview_sound(Moment.FINISHED)
        assert "switched off in Sound Scheme" in said
        assert played == [FINISHED, FAILED]
        labels = {section.play_success.GetLabel(), section.play_failure.GetLabel()}
        assert labels == {"Play Su&ccess Sound", "Play Fai&lure Sound"}
    finally:
        dialog.Destroy()


def test_a_result_is_not_overwritten_by_the_next_file_starting(
    controller: Any,  # noqa: F811
) -> None:
    """In a batch the next file starts as one finishes: an unheard start or
    stage must not replace the result in Repeat Last or the status bar."""
    host = _sinks(controller)
    controller._on_event("done", _job(state=q.DONE))
    result = host.status[-1]
    controller._on_event("started", _job(id="next", file_name="Map.png"))
    controller._on_event("changed", _job(id="next", file_name="Map.png", state=q.UPLOADING))
    assert host.status[-1] == result
    controller.repeat_last()
    assert host.said == [result]


def test_a_delay_is_shown_in_the_status_bar_though_not_said(
    controller: Any,  # noqa: F811
) -> None:
    host = _sinks(controller)
    controller._on_event("busy", _job(state=q.BUSY))
    assert host.said == []
    assert "slow down" in host.status[-1]


def test_with_sounds_off_a_sound_moment_is_spoken_instead(
    controller: Any,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.ui import sound_manager

    host = _sinks(controller)
    del host.scribe_has_sound  # ask the real sound manager
    monkeypatch.setattr(sound_manager, "has_sound_for", lambda _event: True)
    monkeypatch.setattr(sound_manager, "is_active", lambda: False)
    controller._on_event("error", _failed_job())
    assert host.cues == []
    assert host.said == [host.status[-1]]
    monkeypatch.setattr(sound_manager, "is_active", lambda: True)
    controller._on_event("error", _job(id="two", state=q.FAILED, message="Bad."))
    assert host.cues == [FAILED]
    assert len(host.said) == 1
