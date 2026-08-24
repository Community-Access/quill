"""What Quill Radio knows how to try again, from Recent Problems (11.5).

Retry is registered per problem *kind* rather than stored as a closure on the
row (see :mod:`quill.ui.problems_dialog`): the log outlives the session that
wrote it, so a row from last Tuesday has to be retryable from a handler that
exists today. Each handler rebuilds what it needs from the row's ``target``
and returns what to say.

Radio claims two kinds:

* **stream** -- a live station that dropped and could not be reconnected. The
  target is its address, so retrying is simply playing it again.
* **download** -- a file that failed. The target is its address and the
  subject its name, which is all the download queue ever needed.

It does not claim ``feed``: a podcast feed is Cast's to refetch, and Radio's
subscription tree reads the shared library rather than fetching it.
"""

from __future__ import annotations

from typing import Any

from quill.core import problem_log


def _station_from(problem: problem_log.Problem) -> Any:
    """A minimal playable row rebuilt from what the log kept."""
    from quill.core.radio.models import RadioStation

    # The subject carries " -- <group>" for a download row; the name is the
    # part before it, which is what the station was actually called.
    name = problem.subject.split(" -- ", 1)[0].strip() or "That station"
    return RadioStation(name=name, stream_url=problem.target, source="Recent Problems")


def register(host: Any) -> None:
    """Teach Recent Problems what Quill Radio can retry."""
    from quill.ui import problems_dialog

    def _retry_stream(problem: problem_log.Problem) -> str:
        if not problem.target:
            return "That row has no stream address to try again."
        controller = getattr(host, "_radio_controller", None)
        if controller is None:
            return "The player is not available."
        controller.play_station(_station_from(problem))
        return f"Playing {problem.subject or 'that station'} again."

    def _retry_download(problem: problem_log.Problem) -> str:
        if not problem.target:
            return "That row has no address to download from."
        from quill.ui.radio import download_command

        station = _station_from(problem)
        if not download_command.download_station(host, station):
            return f"{station.name} still cannot be downloaded."
        return f"Queued {station.name} again."

    problems_dialog.register_retry(problem_log.KIND_STREAM, _retry_stream)
    problems_dialog.register_retry(problem_log.KIND_DOWNLOAD, _retry_download)
