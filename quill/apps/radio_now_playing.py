"""The main window's now-playing readout: what it says, and when it may change.

Split out of :mod:`quill.apps.radio` under GATE-11 (extract, never rebaseline)
when the readout stopped being a one-line ``wx.StaticText`` and became a
read-only ``wx.TextCtrl`` carrying three.

**Why read-only rather than static.** A ``StaticText`` cannot take focus, so it
could not be arrowed through, reviewed word by word, or copied -- and it carries
exactly the text somebody most wants to go back over slowly. The only ways to
read it properly were F6 into the status bar or Ctrl+T for the full window, and
neither should be required to read the line already at the top of the window.

**Why the update is guarded.** A read-only field re-set on a timer re-announces
itself under a screen reader, and rewriting it while somebody is reading it
moves the text out from under them mid-sentence. Two guards, and the module
exists mostly to keep them together: an equality check before writing, and a
pending slot applied when focus leaves.

wx is touched only through the host's own widget; there is no wx import here.
"""

from __future__ import annotations

from typing import Any


def compose(host: Any) -> str:
    """Station and state, the track, and anything else currently true.

    Lines are omitted rather than filled with placeholders: a station with no
    track metadata shows two lines, not a line reading "no track information".
    An absent fact is quieter than a stated absence.

    Slowest-changing fact first, so the start of the field is stable while a
    track name changes underneath it. Elapsed position is deliberately not here
    -- it changes every second, so it would either re-announce constantly or
    have to be exempted from the change check that makes the rest of this safe.
    Ctrl+Shift+W answers it on demand, which is the right shape for a fact you
    want occasionally and never want read at you.
    """
    try:
        headline = host._radio_status_text() or "Radio: stopped"
    except Exception:  # noqa: BLE001 - a readout must never break the window
        headline = "Radio: stopped"
    lines = [headline]

    try:
        track = (host._radio_now_playing_text() or "").strip()
    except Exception:  # noqa: BLE001
        track = ""
    # Not when the headline already carries it: "Playing Jazz24" followed by
    # "Jazz24" is one fact read twice.
    if track and track not in headline:
        lines.append(track)

    recorder = getattr(host, "_radio_recorder", None)
    count = int(getattr(recorder, "active_count", 0) or 0) if recorder is not None else 0
    if count and "recording" not in headline.lower():
        lines.append("Recording" if count == 1 else f"{count} recordings")

    return "\n".join(lines)


def refresh(host: Any) -> None:
    """Recompose and write, obeying both guards."""
    _write(host, compose(host))


def _write(host: Any, text: str) -> None:
    field = getattr(host, "_now_playing_text", None)
    if field is None or field.GetValue() == text:
        return
    wx = getattr(host, "_wx", None)
    focused = wx.Window.FindFocus() if wx is not None else None
    if focused is field:
        # Being read right now. Hold it; on_blur applies it.
        host._pending_now_playing = text
        return
    host._pending_now_playing = None
    field.SetValue(text)


def on_blur(host: Any, event: Any) -> None:
    """Apply whatever arrived while the field was being read."""
    event.Skip()
    pending = getattr(host, "_pending_now_playing", None)
    if pending is None:
        return
    host._pending_now_playing = None
    field = getattr(host, "_now_playing_text", None)
    if field is not None and field.GetValue() != pending:
        field.SetValue(pending)
