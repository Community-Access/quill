"""The rule for "a tone, words, both, or neither", which both editors share.

Small enough to read in one go and worth its own file because it is the one place
the rule lives: QUILL asks it in :meth:`CueMixin.action_channels` and QuillLite in
``DocumentFrame._action``, and if either had its own copy the two products would
answer the same setting differently -- which is exactly the divergence the shared
package exists to prevent.

Two properties matter more than the four obvious cases:

**The default must be what the app already did.** A setting that changed behaviour
for somebody who has never opened it is a regression wearing a feature's clothes.

**No mode may leave a moment with no feedback at all.** ``sound`` on an event the
pack cannot play has to fall through to the words. Otherwise turning the setting
to its own default would make the app quieter than the day before -- silently, and
only for the events whose clips happen to be missing.
"""

from __future__ import annotations

import pytest

from quill.core.action_feedback import (
    ACTION_FEEDBACK_LABELS,
    ActionFeedback,
    coerce,
    resolve,
)


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("sound", (True, False)),
        ("speech", (False, True)),
        ("both", (True, True)),
        ("silent", (False, False)),
    ],
)
def test_each_mode_reaches_the_channels_it_names(mode: str, expected: tuple[bool, bool]) -> None:
    assert resolve(mode, has_sound=True) == expected


def test_the_default_is_the_tone_alone() -> None:
    assert coerce("nonsense") is ActionFeedback.SOUND
    assert resolve("nonsense", has_sound=True) == (True, False)


@pytest.mark.parametrize("mode", ["sound", "both"])
def test_a_mode_wanting_a_tone_speaks_when_there_is_no_clip(mode: str) -> None:
    """The choice is between two kinds of feedback, never a route to none."""
    play, speak = resolve(mode, has_sound=False)
    assert play is False
    assert speak is True


def test_silent_stays_silent_even_with_no_clip() -> None:
    """The fall-through is a repair for an absent clip, not an override of a
    deliberate request for quiet."""
    assert resolve("silent", has_sound=False) == (False, False)


def test_speech_is_unaffected_by_whether_a_clip_exists() -> None:
    assert resolve("speech", has_sound=False) == (False, True)
    assert resolve("speech", has_sound=True) == (False, True)


def test_a_settings_file_edited_by_hand_cannot_break_the_rule() -> None:
    """Whitespace, case, ``None`` and a number all land on the default."""
    for value in (" BOTH ", "Sound", None, 7, "", "  "):
        resolved = coerce(value)
        assert isinstance(resolved, ActionFeedback)
    assert coerce(" BOTH ") is ActionFeedback.BOTH
    assert coerce("Sound") is ActionFeedback.SOUND
    assert coerce(None) is ActionFeedback.SOUND


def test_every_mode_has_a_label_for_a_chooser() -> None:
    """A mode with no wording would be a radio button nobody could name.

    The labels live beside the rule so both editors' preference panes read from
    one list; two panes that drifted would offer one setting under two names,
    which reads as two settings.
    """
    labelled = {mode for mode, _text in ACTION_FEEDBACK_LABELS}
    assert labelled == set(ActionFeedback)
    assert all(text and text[0].isupper() for _mode, text in ACTION_FEEDBACK_LABELS)


def test_the_labels_lead_with_the_default() -> None:
    """First in the list is first in the chooser, and it should be the default."""
    assert ACTION_FEEDBACK_LABELS[0][0] is ActionFeedback.SOUND


def test_both_settings_that_use_the_rule_default_to_a_tone() -> None:
    """``action_feedback`` and ``find_not_found_feedback`` are separate settings on
    purpose -- somebody may well want successes spoken and the failure a tone --
    but both start where the app already was."""
    from quill.core.settings import Settings

    settings = Settings()
    assert settings.action_feedback == "sound"
    assert settings.find_not_found_feedback == "sound"
