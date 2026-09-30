"""QUILL Cast's playback speed scale: its bounds, its step, and one clamp.

One module for one scale, because the alternative had already failed. The bounds
lived in ``models_settings`` and the step lived in
``quill/ui/main_frame_podcast_session.py``, so ``quill/ui/podcasts/speed.py``
imported ``SPEED_STEP`` from the module that held the other two and got an
ImportError -- Speed Up, Speed Down, Reset Speed and their three palette rows
all raised on use. A crash on a keypress, and nothing in the suite imported the
module to find out.

Splitting a step from the range it has to stay inside is what let one half go
missing, so they are together here and nowhere else. ``models_settings``
re-exports all four names, which is why no caller had to change: this module is
where they are decided, not a new place to import them from.

A separate module rather than more lines in ``models_settings``, which is 23
lines under GATE-11's 600-line default and is the wrong place for anything that
can live elsewhere.

wx-free.
"""

from __future__ import annotations

__all__ = ["SPEED_MAX", "SPEED_MIN", "SPEED_STEP", "clamp_speed", "speed_label"]

#: The slowest and fastest Cast will play, matching Earshot's range.
SPEED_MIN = 0.5
SPEED_MAX = 5.0

#: What one press of Speed Up or Speed Down moves the speed by.
#:
#: 0.05 rather than 0.1, matching Earshot: fine enough to find the speed that
#: suits one narrator, and small enough that holding the key is a reasonable way
#: to get there.
SPEED_STEP = 0.05


def clamp_speed(value: float) -> float:
    """*value* as a speed this scale actually has: bounded, and on the step.

    Rounded to :data:`SPEED_STEP` as well as bounded, so every speed is one the
    keys can return to. Without it floating-point addition drifts -- ten presses
    of Speed Up from 1.0 arrive at 1.5000000000000002, which reads back as
    "1.5x" and then fails to match the 1.5 in a settings list or a preset, and
    gets reported as "the speed list forgets my choice".

    Rounded twice on purpose: 0.05 has no exact binary form, so the multiply
    carries its own error and 2.85 comes back as 2.8500000000000005.
    """
    stepped = round(float(value) / SPEED_STEP) * SPEED_STEP
    return round(max(SPEED_MIN, min(SPEED_MAX, stepped)), 2)


def speed_label(value: float) -> str:
    """A speed as a listener hears it: ``1.5x``, ``1x``, ``0.95x``.

    ``:g`` rather than a fixed number of decimals, so 1.0 is "1x" and not
    "1.00x" -- the announcements read the value aloud and a trailing zero is a
    syllable that carries nothing.
    """
    return f"{clamp_speed(value):g}x"
