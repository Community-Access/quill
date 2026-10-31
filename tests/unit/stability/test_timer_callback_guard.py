"""O8: a timer callback that raises is logged and reported, never swallowed.

wxPython hands an exception from a ``wx.Timer`` or ``wx.CallLater`` callback
to a console a windowed app does not have, so the callback quietly stops
working (TG Drop Deck's startup announcement raised on every launch for five
releases). Studio's timers go through ``guard_timer_callback``.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from quill.stability.wx_dispatch import call_later_safely, guard_timer_callback

ROOT = Path(__file__).resolve().parents[3]


def _boom(_event=None):
    raise RuntimeError("tick failed")


def test_a_failing_callback_reaches_the_log_and_the_status_bar(caplog):
    shown = []
    guarded = guard_timer_callback(_boom, name="Recording status refresh", report=shown.append)
    with caplog.at_level(logging.ERROR, logger="quill.stability.wx_dispatch"):
        guarded(object())  # a timer event; must not raise
    assert "Recording status refresh" in caplog.text and "tick failed" in caplog.text
    assert shown == ["Recording status refresh failed. The details are in the log."]


def test_a_repeating_failure_is_reported_once_not_every_tick(caplog):
    shown = []
    guarded = guard_timer_callback(_boom, name="Broadcast status refresh", report=shown.append)
    with caplog.at_level(logging.ERROR, logger="quill.stability.wx_dispatch"):
        for _ in range(5):
            guarded()
    assert caplog.text.count("Timer callback failed") == 1 and len(shown) == 1


def test_a_working_callback_runs_with_its_arguments():
    seen = []
    guard_timer_callback(lambda *a, **k: seen.append((a, k)), name="x")(1, two=2)
    assert seen == [((1,), {"two": 2})]


def test_a_broken_report_does_not_escape_either(caplog):
    def bad_report(_text):
        raise RuntimeError("no status bar")

    guard_timer_callback(_boom, name="Camera check", report=bad_report)()
    assert "Could not report" in caplog.text


def test_call_later_safely_wraps_the_callback(monkeypatch):
    import quill.stability.wx_dispatch as dispatch

    made = []

    class FakeCallLater:
        def __init__(self, delay, func, *args, **kwargs):
            made.append(delay)
            self.run = lambda: func(*args, **kwargs)

    monkeypatch.setattr(dispatch.wx, "CallLater", FakeCallLater)
    timer = call_later_safely(5, _boom, name="Voice preview cue")
    timer.run()  # would have raised unguarded
    assert made == [5]


def test_no_studio_timer_is_bound_unguarded():
    """Every wx.Timer and CallLater in Studio's code goes through the guard."""
    files = sorted((ROOT / "quill" / "apps").glob("studio*.py"))
    files += sorted((ROOT / "quill" / "ui").glob("studio_*.py"))
    offenders = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        name = str(path.relative_to(ROOT))
        offenders += [f"{name}: wx.CallLater" for _ in re.finditer(r"\bwx\.CallLater\(", text)]
        guarded = set(re.findall(r"(\w+) = guard_timer_callback\(", text))
        for match in re.finditer(r"Bind\(\s*wx\.EVT_TIMER,\s*([\w.]+)", text):
            handler = match.group(1)
            if handler != "guard_timer_callback" and handler not in guarded:
                offenders.append(f"{name}: EVT_TIMER bound to {handler}")
    assert offenders == []
