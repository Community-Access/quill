"""Read a spin control the way it reads aloud: by what is typed in it.

Reported by Chris (2026-11-19): typing 1.5 into a speed box and pressing OK
saved the old speed. On Windows ``wx.SpinCtrlDouble`` is wx's generic control,
a text box beside two arrows, and ``GetValue()`` answers with the last value
the control *committed*: the arrows commit at once, but typed text is only
committed when focus leaves the box. Enter and the OK button's access key both
close the dialog without leaving it, so the number the person typed, and heard
read back, was never the number that was saved. Nothing announces the loss.

:func:`spin_value` reads the text instead, in the control's own type, clamped
to its own range, and commits it so the box shows what was used. Where the
text is not a number (half typed, empty) the committed value stands, which is
what the control would have done itself. Every spin read in ``quill/`` and in
Quill Social goes through here; ``tests/unit/ui/test_spin_value.py`` fails on
a new ``.GetValue()`` of a spin control, because the next one would lose a
typed number the same quiet way.

``wx`` is never imported here: the control is enough.
"""

from __future__ import annotations

from typing import Any

__all__ = ["spin_value"]


def spin_value(control: Any) -> Any:
    """What *control* says, from its text when that is a number in range."""
    committed = control.GetValue()
    text_of = getattr(control, "GetTextValue", None)
    if not callable(text_of):
        return committed
    try:
        text = str(text_of()).strip()
    except Exception:  # noqa: BLE001 - a control without text has only its value
        return committed
    if not text:
        return committed
    is_int = isinstance(committed, int) and not isinstance(committed, bool)
    try:
        typed: float | int = (
            int(float(text.replace(",", "."))) if is_int else float(text.replace(",", "."))
        )
    except ValueError:
        return committed
    low, high = _range(control)
    if low is not None and typed < low:
        typed = type(typed)(low)
    if high is not None and typed > high:
        typed = type(typed)(high)
    if typed != committed:
        try:
            control.SetValue(typed)  # commit it, so the box and the setting agree
        except Exception:  # noqa: BLE001 - reading must never fail because writing did
            pass
    return typed


def _range(control: Any) -> tuple[float | None, float | None]:
    try:
        return float(control.GetMin()), float(control.GetMax())
    except Exception:  # noqa: BLE001 - no range: nothing to clamp to
        return None, None
