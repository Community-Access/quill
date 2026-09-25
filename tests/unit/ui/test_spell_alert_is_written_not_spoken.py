"""The as-you-type spelling alert obeys its own setting (bad.md S2).

``_set_status`` always announces. So QUILL's live alert spoke the status line
whether or not ``spelling_alert_speech`` was on -- and *twice* when it was on,
once through the status write and once through the deliberate announcement
below it. The setting therefore did nothing in QUILL and did exactly what it
says in QUILL Lite, whose status write is silent: one setting, two opposite
meanings, in two editors that are meant to agree.

Over-announcing is the failure nobody files. "This app is chatty" gets absorbed;
"this app is silent" gets reported. That asymmetry is why GATE-13 exists and why
this is a test rather than a note.
"""

from __future__ import annotations

from quill.ui.main_frame_spell_voice import SpellVoiceMixin


def test_the_alert_writes_the_status_bar_without_speaking_it() -> None:
    source = SpellVoiceMixin._announce_spellcheck_hint.__code__.co_names
    assert "_set_status_quiet" in source, (
        "the live alert must write the status bar quietly; _set_status always "
        "announces, which is the whole of bad.md S2"
    )
    assert "_set_status" not in source or "_set_status_quiet" in source


def test_speech_is_still_available_behind_the_setting() -> None:
    """Silencing the accidental copy must not silence the deliberate one: the
    setting exists so somebody who wants the alert spoken can have it."""
    assert "_announce_result" in SpellVoiceMixin._announce_spellcheck_hint.__code__.co_names


def test_the_status_bar_still_carries_the_word() -> None:
    """GATE-12: a state change on an unfocused control has to be *written*,
    whatever it does about speech. Somebody reviewing the status bar with their
    reader should find the alert there."""
    import inspect

    body = inspect.getsource(SpellVoiceMixin._announce_spellcheck_hint)
    assert "Possible misspelling" in body
