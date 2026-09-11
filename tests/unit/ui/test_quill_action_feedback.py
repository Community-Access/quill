"""QUILL's half of the shared feedback rule (``settings.action_feedback``).

QuillLite's half is covered behaviourally in ``tests/unit/apps``; this is the
same four modes exercised against QUILL's three call sites, because "the rule is
shared" is only true while both callers are checked. The rule itself lives in
:mod:`quill.core.action_feedback` and is tested there -- what is tested here is
that QUILL *asks* it, asks it with the right event, and does both halves of the
answer.

Three of the four things below are about a *silence*: a mode that plays no tone,
a status bar written without being spoken, an announcer that is not there. None
of them is visible in a screenshot and none of them raises, which is exactly the
category that shipped broken once already.

No ``MainFrame`` is built. ``CueMixin`` and ``SearchCommandsMixin`` are composed
onto stubs the way wx composes them onto a frame, and ``start_selection`` is
called as an unbound function against the same kind of stub -- so the test
exercises the real code without a real window.
"""

from __future__ import annotations

from typing import Any

import pytest  # type: ignore[import-not-found]

from quill.core.sound_events import SoundEvent
from quill.ui.main_frame_cues import CueMixin
from quill.ui.main_frame_search import SearchCommandsMixin


class _Settings:
    """Only the two fields these paths read. Anything else is not their business."""

    def __init__(self, **values: Any) -> None:
        self.action_feedback = "sound"
        self.find_not_found_feedback = "sound"
        self.wrap_find = True
        self.announce_wrap = True
        for key, value in values.items():
            setattr(self, key, value)


class _Cues(CueMixin):
    """A frame-shaped host: what it heard, and what it was told."""

    def __init__(self, **settings: Any) -> None:
        self.settings = _Settings(**settings)
        self.played: list[str] = []
        self.spoken: list[str] = []

    def cue(self, event: str) -> None:  # the real one reaches the sound manager
        self.played.append(str(event))

    def _announce(self, message: str) -> None:
        self.spoken.append(message)


@pytest.fixture
def clip_for_everything(monkeypatch):
    """A loaded pack that has a clip for whatever it is asked about."""
    import quill.ui.sound_manager as sound_manager

    monkeypatch.setattr(sound_manager, "has_sound_for", lambda _event: True)


@pytest.fixture
def clip_for_nothing(monkeypatch):
    """A pack with no clip for anything -- the fall-through case."""
    import quill.ui.sound_manager as sound_manager

    monkeypatch.setattr(sound_manager, "has_sound_for", lambda _event: False)


# --------------------------------------------------------------------------- #
# CueMixin.action / action_channels
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("sound", (True, False)),
        ("speech", (False, True)),
        ("both", (True, True)),
        ("silent", (False, False)),
    ],
)
def test_action_channels_answers_each_mode(clip_for_everything, mode, expected):
    host = _Cues(action_feedback=mode)
    assert host.action_channels(SoundEvent.TEXT_PASTED) == expected


@pytest.mark.parametrize(
    ("mode", "played", "spoken"),
    [
        ("sound", ["text_pasted"], []),
        ("speech", [], ["Pasted 12 characters"]),
        ("both", ["text_pasted"], ["Pasted 12 characters"]),
        ("silent", [], []),
    ],
)
def test_action_does_both_halves_of_the_answer(clip_for_everything, mode, played, spoken):
    host = _Cues(action_feedback=mode)
    host.action(SoundEvent.TEXT_PASTED, "Pasted 12 characters")
    assert host.played == played
    assert host.spoken == spoken


def test_sound_falls_through_to_words_when_the_pack_has_no_clip(clip_for_nothing):
    """The one rule that stops the default silencing anybody.

    Choosing the mode QUILL has always been in must never make it quieter than
    the day before, so a moment with nothing to play says the words instead.
    """
    host = _Cues(action_feedback="sound")
    host.action(SoundEvent.TEXT_PASTED, "Pasted 12 characters")
    assert host.played == []
    assert host.spoken == ["Pasted 12 characters"]


def test_both_with_no_clip_still_speaks(clip_for_nothing):
    host = _Cues(action_feedback="both")
    host.action(SoundEvent.TEXT_PASTED, "Pasted 12 characters")
    assert (host.played, host.spoken) == ([], ["Pasted 12 characters"])


def test_silent_stays_silent_even_with_no_clip(clip_for_nothing):
    """Silence is a request, not an absence -- the fall-through must not undo it."""
    host = _Cues(action_feedback="silent")
    host.action(SoundEvent.TEXT_PASTED, "Pasted 12 characters")
    assert (host.played, host.spoken) == ([], [])


def test_a_hand_edited_mode_falls_back_to_the_tone(clip_for_everything):
    host = _Cues(action_feedback="loudly")
    host.action(SoundEvent.TEXT_PASTED, "Pasted 12 characters")
    assert (host.played, host.spoken) == (["text_pasted"], [])


def test_settings_without_the_field_behave_as_the_default(clip_for_everything):
    """A settings object from an older build must not break a copy."""

    class _Bare(CueMixin):
        settings = object()

        def __init__(self) -> None:
            self.played: list[str] = []

        def cue(self, event: str) -> None:
            self.played.append(str(event))

    host = _Bare()
    host.action(SoundEvent.TEXT_PASTED, "Pasted 12 characters")
    assert host.played == ["text_pasted"]


def test_a_missing_announcer_leaves_the_earcon_working(clip_for_everything):
    """The mixin is composed into frames it does not own.

    A host with no announcer must lose the words and keep the tone, rather than
    take the copy down with it.
    """

    class _NoVoice(CueMixin):
        def __init__(self) -> None:
            self.settings = _Settings(action_feedback="both")
            self.played: list[str] = []

        def cue(self, event: str) -> None:
            self.played.append(str(event))

    host = _NoVoice()
    host.action(SoundEvent.TEXT_PASTED, "Pasted 12 characters")  # must not raise
    assert host.played == ["text_pasted"]


def test_an_announcer_that_raises_does_not_take_the_action_with_it(clip_for_everything):
    class _BadVoice(_Cues):
        def _announce(self, message: str) -> None:
            raise RuntimeError("the bridge went away")

    host = _BadVoice(action_feedback="both")
    host.action(SoundEvent.TEXT_PASTED, "Pasted 12 characters")
    assert host.played == ["text_pasted"]


def test_a_broken_sound_manager_falls_back_to_the_old_behaviour(monkeypatch):
    """Feedback must never break the action it is reporting on."""
    import quill.ui.sound_manager as sound_manager

    def _explode(_event: str) -> bool:
        raise RuntimeError("no audio subsystem")

    monkeypatch.setattr(sound_manager, "has_sound_for", _explode)
    host = _Cues(action_feedback="speech")
    assert host.action_channels(SoundEvent.TEXT_PASTED) == (True, False)


# --------------------------------------------------------------------------- #
# SearchCommandsMixin._report_search_missed
# --------------------------------------------------------------------------- #


class _Search(SearchCommandsMixin):
    """A host for the one search method that does not need an editor."""

    def __init__(self, **settings: Any) -> None:
        self.settings = _Settings(**settings)
        self.status: list[str] = []
        self.quiet_status: list[str] = []

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _set_status_quiet(self, message: str) -> None:
        self.quiet_status.append(message)


@pytest.fixture
def recorded_sounds(monkeypatch):
    """Capture ``post_sound`` where the search module reaches for it."""
    import quill.ui.sound_manager as sound_manager

    posted: list[str] = []
    monkeypatch.setattr(sound_manager, "post_sound", lambda event: posted.append(str(event)))
    monkeypatch.setattr(sound_manager, "has_sound_for", lambda _event: True)
    return posted


@pytest.mark.parametrize(
    ("mode", "tone", "loud"),
    [
        ("sound", True, False),
        ("speech", False, True),
        ("both", True, True),
        ("silent", False, False),
    ],
)
def test_a_missed_search_reports_in_the_chosen_channel(recorded_sounds, mode, tone, loud):
    host = _Search(find_not_found_feedback=mode)
    host._report_search_missed("Not found: widget")
    assert bool(recorded_sounds) is tone
    assert host.status == (["Not found: widget"] if loud else [])


@pytest.mark.parametrize("mode", ["sound", "speech", "both", "silent"])
def test_the_status_bar_carries_the_words_in_every_mode(recorded_sounds, mode):
    """The bar is the record, not the feedback.

    ``_set_status`` speaks what it is given, so the quiet modes have to route
    through ``_set_status_quiet`` -- and if they routed nowhere, somebody who
    went and read the bar would find the *previous* search's answer there.
    """
    host = _Search(find_not_found_feedback=mode)
    host._report_search_missed("Not found: widget")
    assert host.status + host.quiet_status == ["Not found: widget"]


def test_speech_off_still_writes_the_bar_quietly(recorded_sounds):
    host = _Search(find_not_found_feedback="sound")
    host._report_search_missed("Not found: widget")
    assert host.quiet_status == ["Not found: widget"]
    assert host.status == []


def test_the_miss_sound_is_the_search_one(recorded_sounds):
    host = _Search(find_not_found_feedback="sound")
    host._report_search_missed("Not found: widget")
    assert recorded_sounds == [str(SoundEvent.SEARCH_NOT_FOUND)]


def test_a_pack_with_no_miss_clip_speaks_instead(monkeypatch):
    import quill.ui.sound_manager as sound_manager

    posted: list[str] = []
    monkeypatch.setattr(sound_manager, "post_sound", lambda event: posted.append(str(event)))
    monkeypatch.setattr(sound_manager, "has_sound_for", lambda _event: False)
    host = _Search(find_not_found_feedback="sound")
    host._report_search_missed("Not found: widget")
    assert posted == []
    assert host.status == ["Not found: widget"]


def test_a_broken_resolver_keeps_the_tone(monkeypatch):
    import quill.ui.sound_manager as sound_manager

    posted: list[str] = []
    monkeypatch.setattr(sound_manager, "post_sound", lambda event: posted.append(str(event)))

    def _explode(_event: str) -> bool:
        raise RuntimeError("no audio subsystem")

    monkeypatch.setattr(sound_manager, "has_sound_for", _explode)
    host = _Search(find_not_found_feedback="speech")
    host._report_search_missed("Not found: widget")
    assert posted == [str(SoundEvent.SEARCH_NOT_FOUND)]


# --------------------------------------------------------------------------- #
# MainFrame.start_selection
# --------------------------------------------------------------------------- #


class _Editor:
    def __init__(self, text: str, caret: int) -> None:
        self._text, self._caret = text, caret

    def GetInsertionPoint(self) -> int:  # noqa: N802 - wx's name
        return self._caret

    def GetValue(self) -> str:  # noqa: N802 - wx's name
        return self._text


class _Frame(_Cues):
    """``start_selection`` lives on ``MainFrame`` itself, so it is called unbound."""

    def __init__(self, **settings: Any) -> None:
        super().__init__(**settings)
        self.editor = _Editor("first line\nsecond line", 11)
        self._selection_anchor: int | None = None
        self.status: list[str] = []
        self.quiet_status: list[str] = []

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _set_status_quiet(self, message: str) -> None:
        self.quiet_status.append(message)


@pytest.fixture
def selection_sounds(monkeypatch):
    """Patched where ``start_selection`` looks the name up, not where it used to.

    ``main_frame_selection_span`` imports ``post_sound`` at module scope, so the
    binding this has to replace is that module's -- patching
    ``quill.ui.main_frame`` was correct only while the method lived there, and
    would silently stop capturing rather than fail loudly.
    """
    import quill.ui.main_frame_selection_span as span
    import quill.ui.sound_manager as sound_manager

    posted: list[str] = []
    monkeypatch.setattr(span, "post_sound", lambda event: posted.append(str(event)))
    monkeypatch.setattr(sound_manager, "has_sound_for", lambda _event: True)
    return posted


@pytest.mark.parametrize(
    ("mode", "tone", "loud"),
    [
        ("sound", True, False),
        ("speech", False, True),
        ("both", True, True),
        ("silent", False, False),
    ],
)
def test_start_selection_honours_action_feedback(selection_sounds, mode, tone, loud):
    from quill.ui.main_frame import MainFrame

    host = _Frame(action_feedback=mode)
    MainFrame.start_selection(host)
    assert bool(selection_sounds) is tone
    assert bool(host.status) is loud


def test_start_selection_sets_the_anchor_in_every_mode(selection_sounds):
    """The feedback setting must not be able to break the command it reports on."""
    from quill.ui.main_frame import MainFrame

    for mode in ("sound", "speech", "both", "silent"):
        host = _Frame(action_feedback=mode)
        MainFrame.start_selection(host)
        assert host._selection_anchor == 11
        assert host.status + host.quiet_status == ["Selection started at line 2, column 1."]


# --------------------------------------------------------------------------- #
# power.remove_blank_lines
# --------------------------------------------------------------------------- #


def test_remove_blank_lines_is_declared_as_a_power_tool():
    from quill.ui.main_frame_power_tools_menu import POWER_TOOLS_COMMANDS

    ids = {command.id for command in POWER_TOOLS_COMMANDS}
    assert "power.remove_blank_lines" in ids
    assert "power.trim_blank_lines" in ids, "its companion, and a separate command"


def test_remove_blank_lines_resolves_by_convention_to_its_handler():
    """The id-to-method convention is the only thing wiring these up.

    ``power.remove_blank_lines`` -> ``self.remove_blank_lines``. A command
    declared with no matching method registers fine and raises the first time
    somebody presses it, which is the day after it ships.
    """
    from quill.ui.main_frame_power_tools_menu import PowerToolsMenuMixin

    class _Host(PowerToolsMenuMixin):
        def __init__(self) -> None:
            self.calls: list[str] = []

        def remove_blank_lines(self) -> None:
            self.calls.append("remove")

    host = _Host()
    handler = host._resolve_power_tools_handler("power.remove_blank_lines")
    handler()
    assert host.calls == ["remove"]


def test_every_power_tool_command_resolves_to_something_callable():
    """The ratchet on the convention above, for all of them at once.

    Against ``MainFrame`` rather than the actions mixin, because the convention
    resolves on the composed frame: nine of these live in other mixins
    (``insert_image`` and the clip-library verbs among them), and pinning the
    lookup to one mixin would make adding a command to a *different* mixin fail
    a test that is not about it.
    """
    from quill.ui.main_frame import MainFrame
    from quill.ui.main_frame_power_tools_menu import (
        _MIGRATED_HANDLERS,
        POWER_TOOLS_COMMANDS,
    )

    missing = [
        command.id
        for command in POWER_TOOLS_COMMANDS
        if command.id not in _MIGRATED_HANDLERS
        and not callable(getattr(MainFrame, command.id.partition(".")[2] or command.id, None))
    ]
    assert missing == []
