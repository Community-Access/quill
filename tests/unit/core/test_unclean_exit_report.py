"""An unclean-exit report has to carry something somebody can act on.

Three of these arrived (#1464, #1466, #1480) and not one could be worked. They
are filed automatically by the Crash Recovery dialog, so nobody wrote a word of
them, and an unclean exit has no traceback by definition -- which left a bounded
tail of the newest log as the entire content. A log tail is mostly five-minute
idle-sweep heartbeats.

What was missing is exactly what a crash *with* a traceback had always filed:
the version, whether the build is portable, the screen reader, the platform, and
the last commands the user ran. That is now built by one shared function so the
two kinds of report cannot describe the same session differently -- and the UI
stall lines, when there are any, are pulled out of the log to the top, because a
six-second freeze buried in a hundred routine lines is a signal nobody finds.
"""

from __future__ import annotations

from quill.core.issue_submit import find_stall_evidence
from quill.stability.crash_submit import build_session_context

STALL = (
    "2026-08-31 14:11:45,655 WARNING quill.stability.wx_heartbeat: "
    "wx UI heartbeat: capturing stacks at 6.1 s stall"
)
BLOCKED = (
    "2026-08-31 14:11:51,755 ERROR quill.stability.wx_heartbeat: "
    "wx UI appears blocked for 10.0 seconds"
)
IDLE = (
    "2026-08-31 14:12:43,070 INFO quill.stability.task_manager: "
    "Task started operation_id=abc name=lifecycle-idle-sweep"
)


def _log(tmp_path, *lines):
    path = tmp_path / "quill.log"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


# --------------------------------------------------------------------- #
# The session context


def test_the_context_carries_what_a_tracebacked_report_carries() -> None:
    """These four facts are the whole difference between the reports that got
    fixed this week and the three that could only be closed."""
    text = build_session_context(
        app_version="1.0.0",
        portable=True,
        screen_reader_name="NVDA",
        recent_commands=["file.open", "file.save"],
        platform_name="Windows-11-10.0.26200",
    )
    assert "1.0.0" in text
    assert "Portable      : True" in text
    assert "NVDA" in text
    assert "Windows-11" in text


def test_the_most_recent_command_is_listed_first() -> None:
    """A reader scanning a report wants the last thing that happened, not the
    first thing in the session."""
    text = build_session_context(
        app_version="1.0.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=["first", "second", "last"],
    )
    body = text.split("Recent commands (most recent first)")[1]
    assert body.index("last") < body.index("second") < body.index("first")


def test_no_command_log_says_so_rather_than_showing_an_empty_heading() -> None:
    """An empty list under a heading reads as "no commands were run", which is a
    different claim from "we do not have the log"."""
    text = build_session_context(
        app_version="1.0.0", portable=False, screen_reader_name=None, recent_commands=[]
    )
    assert "(no recent command log available)" in text


def test_an_absent_screen_reader_is_left_out_rather_than_guessed() -> None:
    text = build_session_context(
        app_version="1.0.0", portable=False, screen_reader_name=None, recent_commands=[]
    )
    assert "Screen reader" not in text


def test_the_command_list_is_bounded() -> None:
    """A report is read by a person. Fifty command ids is not evidence."""
    text = build_session_context(
        app_version="1.0.0",
        portable=False,
        screen_reader_name=None,
        recent_commands=[f"cmd.{n}" for n in range(50)],
    )
    assert text.count("  - ") <= 10


# --------------------------------------------------------------------- #
# Pulling the stall out of the log


def test_a_stall_is_found_among_the_idle_noise(tmp_path) -> None:
    """#1480's log: one real signal, buried in routine logging."""
    logs = _log(tmp_path, IDLE, IDLE, STALL, IDLE, IDLE)
    found = find_stall_evidence(logs)
    assert "6.1 s stall" in found
    assert "idle-sweep" not in found


def test_every_kind_of_stall_line_is_recognised(tmp_path) -> None:
    logs = _log(tmp_path, IDLE, STALL, BLOCKED)
    found = find_stall_evidence(logs)
    assert "capturing stacks" in found
    assert "appears blocked" in found


def test_a_log_with_no_stall_says_nothing_rather_than_quoting_noise(tmp_path) -> None:
    """#1464's log is nothing but idle sweeps. An empty answer is the honest
    one; quoting heartbeats would dress up a report that has no signal."""
    assert find_stall_evidence(_log(tmp_path, IDLE, IDLE, IDLE)) == ""


def test_only_the_last_few_stalls_are_quoted(tmp_path) -> None:
    """A session that stalled forty times does not need forty lines; the recent
    ones are the ones near the exit."""
    logs = _log(tmp_path, *([STALL] * 40))
    assert find_stall_evidence(logs).count("capturing stacks") <= 6


def test_no_log_directory_is_not_an_error(tmp_path) -> None:
    """This runs while filing a crash report. It may not raise, ever."""
    assert find_stall_evidence(tmp_path / "nothing-here") == ""


def test_an_empty_log_directory_is_not_an_error(tmp_path) -> None:
    assert find_stall_evidence(tmp_path) == ""


def test_the_newest_log_is_the_one_read(tmp_path) -> None:
    """A stall in last week's session is not evidence about this one."""
    import os
    import time

    old = tmp_path / "quill.log.1"
    old.write_text(STALL + "\n", encoding="utf-8")
    new = tmp_path / "quill.log"
    new.write_text(IDLE + "\n", encoding="utf-8")
    now = time.time()
    os.utime(old, (now - 10_000, now - 10_000))
    os.utime(new, (now, now))
    assert find_stall_evidence(tmp_path) == ""
