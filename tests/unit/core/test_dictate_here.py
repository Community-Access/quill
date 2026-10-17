"""Dictate Here in Quill Cast and Quill Radio, through QUILL Transcribe (dict.md D-16).

``quill/core/windows_dictation/dictate_here.py`` decides; the request file in
``quill/core/dictation_owner.py`` carries it. Fakes only: nothing is launched
and no real window is touched.
"""

from __future__ import annotations

import pytest

from quill.core import dictation_owner
from quill.core.windows_dictation.dictate_here import LAUNCH_ARGS, dictate_here


def _never_launch() -> bool:
    raise AssertionError("must not launch")


def test_a_running_transcribe_is_asked_to_start_and_this_app_says_nothing() -> None:
    sent: list[tuple[str, str]] = []
    outcome = dictate_here(
        "cast",
        owner=lambda: "transcribe",
        send=lambda command, sender: sent.append((command, sender)) or True,
        launch=_never_launch,
    )
    assert sent == [("start", "cast")]
    assert outcome.kind == "asked" and outcome.sentence == ""  # QUILL Transcribe says it


def test_a_request_that_cannot_be_written_is_said() -> None:
    outcome = dictate_here(
        "radio", owner=lambda: "transcribe", send=lambda *_a: False, launch=_never_launch
    )
    assert outcome.kind == "unreachable"
    assert outcome.sentence == "QUILL Transcribe is running, and could not be reached."


def test_inkwell_dictating_is_named_and_nothing_is_sent() -> None:
    def no_send(*_args: object) -> bool:
        raise AssertionError("must not send")

    outcome = dictate_here("cast", owner=lambda: "inkwell", send=no_send, launch=_never_launch)
    assert outcome.kind == "busy"
    assert outcome.sentence == "Quill Inkwell is dictating. Stop it there, then try again."


def test_nobody_running_launches_transcribe() -> None:
    launched: list[bool] = []
    outcome = dictate_here(
        "radio",
        owner=lambda: "",
        send=lambda *_a: True,
        launch=lambda: launched.append(True) or True,
    )
    assert launched == [True]
    assert outcome.kind == "launching"
    assert outcome.sentence == "Starting QUILL Transcribe. Dictation starts here when it is ready."
    assert LAUNCH_ARGS == ("--tray", "--dictate-here")  # in the tray, so the field keeps focus


def test_no_transcribe_to_launch_is_said() -> None:
    outcome = dictate_here("cast", owner=lambda: "", send=lambda *_a: True, launch=lambda: False)
    assert outcome.kind == "missing"
    assert "not installed" in outcome.sentence


def test_the_default_launcher_respects_the_release_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import app_launcher
    from quill.core.windows_dictation import dictate_here as module

    calls: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(app_launcher, "is_app_released", lambda _app: False)
    monkeypatch.setattr(
        app_launcher,
        "launch_app",
        lambda app, extra_args=(): calls.append((app, extra_args)) or True,
    )
    assert module._launch_transcribe() is False and calls == []
    monkeypatch.setattr(app_launcher, "is_app_released", lambda _app: True)
    assert module._launch_transcribe() is True
    assert calls == [("transcribe", LAUNCH_ARGS)]


def test_cast_and_radio_may_send_a_request_and_strangers_may_not() -> None:
    assert dictation_owner.send_request("start", sender="cast") is True
    assert dictation_owner.send_request("start", sender="radio") is True
    assert dictation_owner.send_request("start", sender="weather") is False
    taken = dictation_owner.take_requests()
    assert [(r.command, r.sender) for r in taken] == [("start", "cast"), ("start", "radio")]
    # Only the two that type into other programs may *own* Dictate Anywhere.
    assert "cast" not in dictation_owner.APPS and "radio" not in dictation_owner.APPS
