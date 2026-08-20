"""Seeking, speed, and chapter navigation for a finished video (Quill Radio).

Everything here is refused, out loud, for a live broadcast. That refusal is the
feature as much as the seeking is: a slider that cannot move and a "next
chapter" that silently does nothing are worse than not offering them, because
the listener cannot tell a broken control from a stream that has no timeline.
So every command below says *why* when it declines.

Announcements are spelled out in words ("5 minutes 31 seconds", not "5:31"):
read aloud, a colon-separated time is ambiguous unless you already know it is a
time. Same rule as the playlist picker.

The controller owns the behaviour (:mod:`quill.ui.radio.player_controller`);
this module is the wording and the wx wiring.
"""

from __future__ import annotations

from typing import Any

#: Said whenever a transport command lands on a live stream.
LIVE_REFUSAL = "This is a live stream, so there is no timeline to move along."

#: Said when the video plays but its uploader published no chapters.
NO_CHAPTERS = "This video has no chapters."

CHAPTERS_TITLE = "Chapters"
GO_TO_POSITION_TITLE = "Go to Position"

#: Skip step for the forward/back commands.
SKIP_MS = 30_000

#: The speed steps, so stepping up and down lands on round, speakable values
#: rather than drifting by a multiplier.
SPEED_STEPS: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0)


def spoken_duration(ms: int) -> str:
    """A duration as words: "5 minutes 31 seconds".

    Never "5:31" -- a screen reader reads that as an ambiguous pair of numbers
    unless the listener already knows it is a time.
    """
    total = max(0, int(ms)) // 1000
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'' if hours == 1 else 's'}")
    if minutes:
        parts.append(f"{minutes} minute{'' if minutes == 1 else 's'}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'' if seconds == 1 else 's'}")
    return " ".join(parts)


def describe_chapter(index: int, chapter: Any, *, current: bool = False) -> str:
    """One chapter as a whole sentence, the way the list speaks it.

    Position, title, and start time in one line, so there are no columns to
    arrow across -- the same shape as the playlist picker's rows.
    """
    title = str(getattr(chapter, "title", "") or "").strip() or "Untitled chapter"
    start = spoken_duration(int(getattr(chapter, "start_ms", 0)))
    row = f"{index + 1}. {title}, starts at {start}"
    return f"{row}, playing now" if current else row


def describe_position(controller: Any) -> str:
    """ "3 minutes 10 seconds of 18 minutes 40 seconds", plus the chapter."""
    position = spoken_duration(int(controller._engine.position_ms()))
    total = spoken_duration(controller.duration_ms())
    index = controller.current_chapter_index()
    chapters = controller.chapters()
    if 0 <= index < len(chapters):
        title = str(getattr(chapters[index], "title", "") or "").strip()
        if title:
            return f"{position} of {total}, in {title}"
    return f"{position} of {total}"


def _controller(host: Any) -> Any:
    return host._radio_controller


def _refuse(host: Any) -> bool:
    """Say why a transport command does not apply, and report that it did."""
    controller = _controller(host)
    if controller.is_seekable():
        return False
    host._announce(LIVE_REFUSAL if controller.state.station is not None else "Nothing is playing.")
    return True


# -- seeking -----------------------------------------------------------------


def skip_forward(host: Any) -> None:
    """Jump forward through a finished video."""
    if _refuse(host):
        return
    controller = _controller(host)
    controller.skip_by(SKIP_MS)
    host._announce(describe_position(controller))


def skip_back(host: Any) -> None:
    """Jump back through a finished video."""
    if _refuse(host):
        return
    controller = _controller(host)
    controller.skip_by(-SKIP_MS)
    host._announce(describe_position(controller))


def announce_position(host: Any) -> None:
    """Say where we are, without moving."""
    if _refuse(host):
        return
    host._announce(describe_position(_controller(host)))


def go_to_position(host: Any) -> None:
    """Jump to an absolute position in a finished video.

    Reuses the Media Player's Go to Position dialog rather than growing a
    second prompt: it is already built to the desktop accessibility checklist
    (labelled Hours/Minutes/Seconds spin controls as the primary input, an
    optional timecode field for power users, OK as the default button) and
    already clamps with the tested :func:`quill.core.media.clamp_position`.

    Relative skipping gets you somewhere near; this is how you get somewhere
    exact, which is the other half of what a timeline is for.
    """
    if _refuse(host):
        return
    from quill.ui.media.go_to_position_dialog import GoToPositionDialog

    controller = _controller(host)
    dialog = GoToPositionDialog(
        host.frame,
        duration_ms=controller.duration_ms(),
        current_ms=controller.position_ms(),
        announce=host._announce,
    )
    try:
        import wx

        if host._show_modal_dialog(dialog, GO_TO_POSITION_TITLE) != wx.ID_OK:
            return
        target = dialog.get_target_ms()
        clamped = dialog.clamped_message()
    finally:
        dialog.Destroy()
    controller.seek_to(target)
    host._announce(clamped or describe_position(controller))


# -- speed -------------------------------------------------------------------


def _step_speed(host: Any, direction: int) -> None:
    controller = _controller(host)
    current = controller.playback_rate()
    # Land on the neighbouring step rather than multiplying, so the spoken
    # value stays a round number the listener can predict.
    candidates = [s for s in SPEED_STEPS if (s > current if direction > 0 else s < current)]
    if not candidates:
        host._announce(f"Already at {current:g} times speed.")
        return
    target = min(candidates) if direction > 0 else max(candidates)
    applied = controller.set_playback_rate(target)
    if controller.is_seekable():
        # A podcast episode's chosen speed is remembered per show (Radio-side
        # store; see episode_profile). "" for everything else, so ordinary
        # videos and recordings speak exactly as before.
        from quill.ui.radio import episode_profile

        # announce-punctuation: exempt -- the sentence ends before the suffix,
        # and remember_speed_choice returns either "" or its own full sentence.
        host._announce(
            f"{applied:g} times speed.{episode_profile.remember_speed_choice(controller)}"
        )
    else:
        # Still remembered for the next video -- say so, rather than looking
        # like the key did nothing.
        host._announce(f"{applied:g} times speed, for videos. Live radio plays at normal speed.")


def speed_up(host: Any) -> None:
    """Next speed step up (0.25x-4x)."""
    _step_speed(host, 1)


def slow_down(host: Any) -> None:
    """Next speed step down (0.25x-4x)."""
    _step_speed(host, -1)


def reset_speed(host: Any) -> None:
    """Back to normal speed."""
    controller = _controller(host)
    controller.set_playback_rate(1.0)
    from quill.ui.radio import episode_profile

    # announce-punctuation: exempt -- see _step_speed.
    host._announce(f"Normal speed.{episode_profile.remember_speed_choice(controller)}")


# -- chapters ----------------------------------------------------------------


def _announce_chapter(host: Any, index: int) -> None:
    controller = _controller(host)
    chapters = controller.chapters()
    if 0 <= index < len(chapters):
        title = str(getattr(chapters[index], "title", "") or "").strip() or "Untitled chapter"
        host._announce(f"{title}, chapter {index + 1} of {len(chapters)}.")


def next_chapter(host: Any) -> None:
    """Jump to the next published chapter."""
    if _refuse(host):
        return
    controller = _controller(host)
    if not controller.chapters():
        host._announce(NO_CHAPTERS)
        return
    index = controller.go_to_adjacent_chapter(1)
    if index < 0:
        host._announce(NO_CHAPTERS)
        return
    _announce_chapter(host, index)


def previous_chapter(host: Any) -> None:
    """Jump to the previous chapter, or restart this one."""
    if _refuse(host):
        return
    controller = _controller(host)
    if not controller.chapters():
        host._announce(NO_CHAPTERS)
        return
    index = controller.go_to_adjacent_chapter(-1)
    if index < 0:
        host._announce(NO_CHAPTERS)
        return
    _announce_chapter(host, index)


def open_chapters(host: Any) -> None:
    """A list of the video's chapters; Enter jumps to the chosen one."""
    if _refuse(host):
        return
    controller = _controller(host)
    chapters = controller.chapters()
    if not chapters:
        host._announce(NO_CHAPTERS)
        return
    from quill.ui.radio.chapter_list_dialog import ChapterListDialog

    dialog = ChapterListDialog(
        host.frame,
        chapters=chapters,
        current_index=controller.current_chapter_index(),
        show_modal_dialog=host._show_modal_dialog,
        announce=host._announce,
        go_to_chapter=controller.go_to_chapter,
        transport_host=host,
    )
    dialog.show()
