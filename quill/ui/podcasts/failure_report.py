"""One way for QUILL Cast to say that background work failed (qc.md P4, section 10).

"A background failure is spoken and recorded": a job that failed while the
listener was in another window said its piece to nobody, so every failure is
also written to Recent Problems (Help > Recent Problems), where it can be
found afterwards. An ``on_failure`` that only logs, or does nothing, is a
gate failure (GATE-CAST-SILENT).

Two strengths, chosen at the call site:

* a failure of something the listener asked for is said straight away, with
  the error sound, whatever the feedback setting (``say_failure``);
* a failure of something Cast did on its own (``background=True``) is said
  unless Quiet Hours hold it back, and always recorded -- or only recorded
  (``quiet=True``) when saying it would be noise, such as an optional chapter
  lookup on an episode that simply has none to find.
"""

from __future__ import annotations

from typing import Any

__all__ = ["report_failure"]


def report_failure(
    host: Any,
    sentence: str,
    *,
    subject: str = "",
    kind: str = "",
    target: str = "",
    background: bool = False,
    quiet: bool = False,
) -> None:
    """Say *sentence* (by its strength) and write it to Recent Problems."""
    if not quiet:
        if background:
            from quill.ui.quiet_hours_ui import speak_background

            speak_background(host, sentence)
        else:
            from quill.ui.podcasts.outcome_feedback import say_failure

            say_failure(host, sentence)
    try:
        from quill.core import problem_log
        from quill.core.paths import app_data_dir

        problem_log.record_problem(
            app_data_dir(),
            kind or problem_log.KIND_OTHER,
            subject or "QUILL Cast",
            sentence,
            target=target,
        )
    except Exception:  # noqa: BLE001 - the record is a courtesy, never a second failure
        return
