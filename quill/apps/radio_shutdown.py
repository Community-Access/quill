"""Quill Radio's teardown, step by step, with a record of what failed (F-06).

Moved out of ``quill/apps/radio.py`` (GATE-11) when every step started running
through :class:`quill.core.shutdown_report.ShutdownReport`. The order is the
order it always was; what changed is that a failed **must-record** step -- the
"last seen" stamp that lets the next launch report missed recordings, and the
clearing of the active-recording marker that tells a clean close from a crash --
is now written down and said once at the next launch, instead of being
indistinguishable from success.

Also here: the launch side, :func:`radio_launch_notice`, and the Retry that
Recent Problems offers on a "Closing" row -- the same two writes, now.
"""

from __future__ import annotations

from typing import Any

__all__ = ["radio_launch_notice", "retry_radio_final_writes", "run_radio_shutdown"]


def run_radio_shutdown(app: Any) -> None:
    from quill.core.paths import app_data_dir
    from quill.core.shutdown_report import BACKGROUND, BEST_EFFORT, MUST_RECORD, ShutdownReport

    report = ShutdownReport("radio", "Quill Radio")
    # Lambdas, not bound methods: the attribute lookup itself must happen inside
    # the guard, because a frame torn down half-built may not have it.
    report.step("quillins", BEST_EFFORT, lambda: app._app_host.shutdown())
    # The modeless surfaces are parentless peer frames: nothing destroys them
    # with the main window, and any left alive would keep the process running
    # after Exit.
    windows = getattr(app, "_windows", None)
    if windows is not None:
        report.step("peer_windows", BEST_EFFORT, lambda: windows.destroy_all_except(app.frame))
    report.step("last_seen", MUST_RECORD, lambda: app._stamp_radio_last_seen())
    # Stop Weather Guardian's timer without flipping its persisted on state, so
    # a clean exit resumes monitoring on the next launch.
    report.step(
        "weather_monitor",
        BEST_EFFORT,
        lambda: app.stop_weather_monitoring(announce=False, persist=False),
    )
    for timer_attr in ("_radio_last_seen_timer", "_ipc_timer"):
        timer = getattr(app, timer_attr, None)
        if timer is not None:
            report.step(timer_attr.strip("_"), BEST_EFFORT, timer.Stop)
    report.step("recording_marker", MUST_RECORD, lambda: app._clear_radio_recording_marker())
    for name, action in (
        ("player", getattr(getattr(app, "_radio_controller", None), "shutdown", None)),
        ("recorder", getattr(getattr(app, "_radio_recorder", None), "shutdown", None)),
        ("scheduler", getattr(getattr(app, "_radio_scheduler", None), "shutdown", None)),
        # A wx.Timer still running when its frame goes is a timer that can fire
        # into a destroyed window.
        ("feed_monitor", getattr(getattr(app, "_podcast_refresh_monitor", None), "stop", None)),
        ("reminders", getattr(getattr(app, "_reminder_monitor", None), "stop", None)),
    ):
        report.step(name, BEST_EFFORT, action)
    report.step("tasks", BACKGROUND, lambda: app._task_manager.shutdown(wait=False))
    report.step("media_keys", BEST_EFFORT, lambda: app._unregister_media_keys())
    report.step("global_hotkeys", BEST_EFFORT, lambda: app._unregister_global_hotkeys())
    report.step("tray", BEST_EFFORT, lambda: app._remove_tray_icon())
    report.persist(app_data_dir())


def retry_radio_final_writes(app: Any) -> str:
    """Recent Problems' Retry on a "Closing" row: stamp and marker, now.

    The marker is cleared only when nothing is recording: clearing it under a
    live recording would make a crash during that recording look like a clean
    close, which is the one thing the marker exists to tell apart.
    """
    app._stamp_radio_last_seen()
    recorder = getattr(app, "_radio_recorder", None)
    count = getattr(recorder, "active_count", None)
    if callable(count) and count():
        return (
            "Saved when Quill Radio was last open. The recording note stays "
            "while you are recording."
        )
    app._clear_radio_recording_marker()
    return "Saved when Quill Radio was last open, and cleared the recording note, now."


def radio_launch_notice(app: Any) -> None:
    """At launch, deferred: register the Retry, then say the notice if any."""
    from quill.ui.shutdown_notice import register_shutdown_retry, surface_previous_shutdown

    register_shutdown_retry(lambda: retry_radio_final_writes(app))
    surface_previous_shutdown(app, "radio")
