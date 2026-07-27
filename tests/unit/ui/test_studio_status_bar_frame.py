"""Frame-level logic for the Audio Studio status bar and tray progress.

These drive the ``StudioAppFrame`` accessor/sink methods directly with a fake
``self`` (unbound-method calls), so the pure logic -- the Progress cell text, the
run-progress sink that feeds the tray tooltip, the Sleep timer / Your books cell
text -- is covered without standing up a real wx frame.
"""

from __future__ import annotations

from types import SimpleNamespace


def test_progress_text_idle_and_running() -> None:
    from quill.apps.studio import StudioAppFrame

    frame = SimpleNamespace(_run_progress=None)
    assert StudioAppFrame.studio_progress_text(frame) == "Idle"
    assert StudioAppFrame.studio_progress_details(frame) == "No task is running."

    frame._run_progress = {
        "label": "Narrating documents",
        "current": 5,
        "total": 10,
        "percent": 50,
        "message": "chapter-3.docx",
    }
    assert StudioAppFrame.studio_progress_text(frame) == "50% - Narrating documents"
    details = StudioAppFrame.studio_progress_details(frame)
    assert "5 of 10" in details and "50 percent" in details and "chapter-3.docx" in details


def test_note_progress_records_state_and_drives_status_and_tray() -> None:
    from quill.apps.studio import StudioAppFrame

    seen: dict[str, str] = {}
    frame = SimpleNamespace(
        _run_progress=None,
        _set_status_quiet=lambda m: seen.__setitem__("status", m),
        _update_tray_tooltip=lambda t: seen.__setitem__("tooltip", t),
    )
    StudioAppFrame._note_progress(frame, "Narrating documents", 3, 12, "intro.docx")

    assert frame._run_progress["percent"] == 25
    assert seen["status"] == "Narrating documents: 3/12 - intro.docx"
    # The tray tooltip carries the percent so a run is reviewable while minimized.
    assert "25%" in seen["tooltip"] and "Narrating documents" in seen["tooltip"]


def test_note_progress_handles_zero_total() -> None:
    from quill.apps.studio import StudioAppFrame

    frame = SimpleNamespace(
        _run_progress=None,
        _set_status_quiet=lambda _m: None,
        _update_tray_tooltip=lambda _t: None,
    )
    # total == 0 must not raise (ZeroDivision) -- percent falls back to 0.
    StudioAppFrame._note_progress(frame, "Preparing", 0, 0, "starting")
    assert frame._run_progress["percent"] == 0


def test_sleep_timer_text() -> None:
    from quill.apps.studio import StudioAppFrame

    off = SimpleNamespace(_sleep_setting=None, _sleep_watcher=None)
    assert StudioAppFrame.studio_sleep_timer_text(off) == "Off"

    eoc = SimpleNamespace(
        _sleep_setting=SimpleNamespace(enabled=True, end_of_chapter=True, delay_minutes=30),
        _sleep_watcher=None,
    )
    assert StudioAppFrame.studio_sleep_timer_text(eoc) == "End of chapter"

    delay = SimpleNamespace(
        _sleep_setting=SimpleNamespace(enabled=True, end_of_chapter=False, delay_minutes=30),
        _sleep_watcher=SimpleNamespace(remaining_seconds=lambda: 90),
    )
    # 90 s rounds up to 2 minutes left.
    assert StudioAppFrame.studio_sleep_timer_text(delay) == "2 min left"


def test_library_text_pluralizes() -> None:
    from quill.apps.studio import StudioAppFrame

    none = SimpleNamespace(_recent_books=lambda: [])
    assert StudioAppFrame.studio_library_text(none) == "0 books"
    one = SimpleNamespace(_recent_books=lambda: [object()])
    assert StudioAppFrame.studio_library_text(one) == "1 book"
    many = SimpleNamespace(_recent_books=lambda: [object(), object(), object()])
    assert StudioAppFrame.studio_library_text(many) == "3 books"


def test_activity_text_falls_back_to_ready() -> None:
    from quill.apps.studio import StudioAppFrame

    assert StudioAppFrame.studio_activity_text(SimpleNamespace(_status_message="")) == "Ready"
    assert (
        StudioAppFrame.studio_activity_text(SimpleNamespace(_status_message="Building book"))
        == "Building book"
    )
