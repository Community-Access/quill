"""Two Preferences rows from the FreeRadio round: time-shift length, AcoustID key.

Its own module because ``radio_preferences`` is near its GATE-11 ceiling, and
because the two rows share a shape the rest of that dialog does not: both
change something the *engine* or the *credential store* holds rather than a
field ``RadioHistory`` simply keeps.

* **Time-shift buffer** -- how far back live radio can be paused and rewound,
  kept on disk (``quill.core.radio.timeshift``). Applied to the running engine
  at once; it takes hold at the next station change.
* **AcoustID key** -- the application key Identify This Song needs. Empty by
  default; saved to the Windows credential store, never to a settings file, and
  blanking the box removes it.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import acoustid, timeshift

#: No access key on either row: this dialog has no letter left that is not
#: already taken, and a duplicate would be worse than none (GATE-14).
TIMESHIFT_LABEL = "Time-shift buffer:"
TIMESHIFT_HELP = (
    "How far back you can pause and rewind a live station. Kept on disk in this "
    "computer's cache folder, never in a synced data folder, capped in size and "
    "deleted when Quill Radio closes. In memory only keeps the old buffer of "
    "about 45 minutes and writes nothing to disk. Needs the mpv playback engine; "
    "a change takes effect at the next station you play."
)

ACOUSTID_LABEL = "AcoustID key for song recognition:"
ACOUSTID_HELP = (
    "The free application key Identify This Song needs to ask AcoustID what is "
    f"playing. Register one at {acoustid.REGISTER_URL} and paste it here. Kept in "
    "the Windows credential store, not in a settings file; clear the box to "
    "remove it. Nothing is sent anywhere until you choose Identify This Song."
)


def rows(app: Any) -> tuple[Any, Any]:
    """``(time-shift choice, AcoustID key text)`` for the Preferences dialog."""
    from quill.ui.app_preferences_dialog import PreferenceChoice, PreferenceText

    history = app._radio_history
    choice = PreferenceChoice(
        TIMESHIFT_LABEL,
        TIMESHIFT_HELP,
        [label for _minutes, label in timeshift.CHOICES],
        timeshift.choice_index(int(getattr(history, "timeshift_minutes", 60))),
    )
    key_text = PreferenceText(ACOUSTID_LABEL, ACOUSTID_HELP, acoustid.stored_key())
    return choice, key_text


def apply(app: Any, choice_index: int, key_value: str) -> str:
    """Apply both rows. Returns a sentence to add to "Preferences saved", or ""."""
    said: list[str] = []
    history = app._radio_history
    index = min(max(0, int(choice_index)), len(timeshift.CHOICES) - 1)
    minutes = timeshift.CHOICES[index][0]
    if minutes != history.timeshift_minutes:
        history.timeshift_minutes = minutes
        engine = getattr(getattr(app, "_radio_controller", None), "_mpv_engine", None)
        configure = getattr(engine, "configure_timeshift", None)
        if callable(configure):
            configure(minutes)
        said.append("The new time-shift buffer starts with the next station you play.")
    new_key = key_value.strip()
    if new_key != acoustid.stored_key():
        if not acoustid.save_key(new_key):
            said.append("The AcoustID key could not be saved on this computer.")
        elif new_key:
            said.append("AcoustID key saved.")
        else:
            said.append("AcoustID key removed.")
    return " ".join(said)
