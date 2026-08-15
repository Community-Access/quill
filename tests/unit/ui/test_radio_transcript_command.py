"""Quill Radio's Transcript command, and the four times it declines.

Every YouTube resolve has always answered with the video's caption track and
Quill Radio has always discarded it. The feature is small; the refusals are the
part worth pinning, because each one has to say *why* rather than doing nothing
-- the rule the rest of the timeline commands already follow.
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio import transcript_command


class _State:
    def __init__(self, name: str = "A Video") -> None:
        self.station = type("_S", (), {"display_name": name})()


class _Controller:
    def __init__(self, *, url: str = "", automatic: bool = False, seekable: bool = True) -> None:
        self._url = url
        self._automatic = automatic
        self._seekable = seekable
        self.state = _State()

    def caption_track(self) -> tuple[str, bool]:
        return self._url, self._automatic

    def is_seekable(self) -> bool:
        return self._seekable

    def position_ms(self) -> int:
        return 0

    def seek_to(self, _ms: int) -> bool:
        return True


class _Tasks:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result if result is not None else []
        self.error = error
        self.submitted: list[str] = []

    def submit(self, name: str, work: Any, *, on_success: Any = None, on_failure: Any = None):
        self.submitted.append(name)
        if self.error is not None:
            if on_failure is not None:
                on_failure(name, self.error)
            return
        if on_success is not None:
            on_success(name, self.result)


class _Wx:
    @staticmethod
    def CallAfter(fn: Any, *args: Any) -> None:  # noqa: N802 - wx's own casing
        fn(*args)


class _Host:
    def __init__(self, controller: Any, *, safe_mode: bool = False, tasks: Any = None) -> None:
        self._radio_controller = controller
        self._safe_mode = safe_mode
        self._task_manager = tasks if tasks is not None else _Tasks()
        self._wx = _Wx()
        self.frame = object()
        self.said: list[str] = []
        self.opened: list[Any] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_a_live_stream_says_it_has_no_transcript() -> None:
    host = _Host(_Controller(url="", seekable=False))
    transcript_command.open_transcript(host)
    assert any("live stream" in m for m in host.said)
    assert host._task_manager.submitted == []


def test_a_video_with_no_captions_says_so_rather_than_failing_quietly() -> None:
    host = _Host(_Controller(url="", seekable=True))
    transcript_command.open_transcript(host)
    assert any("no captions published" in m for m in host.said)
    assert host._task_manager.submitted == []


def test_safe_mode_refuses_out_loud_before_reaching_the_network() -> None:
    host = _Host(_Controller(url="https://example/captions.json3"), safe_mode=True)
    transcript_command.open_transcript(host)
    assert any("Safe Mode" in m for m in host.said)
    assert host._task_manager.submitted == []


def test_a_transcript_that_will_not_parse_is_reported() -> None:
    host = _Host(_Controller(url="https://example/captions.json3"), tasks=_Tasks(result=[]))
    transcript_command.open_transcript(host)
    assert any("could not be read" in m for m in host.said)


def test_a_failed_fetch_is_reported_rather_than_swallowed() -> None:
    host = _Host(
        _Controller(url="https://example/captions.json3"),
        tasks=_Tasks(error=OSError("the server refused")),
    )
    transcript_command.open_transcript(host)
    assert any("could not be fetched" in m for m in host.said)


def test_the_fetch_runs_on_the_task_manager_never_the_ui_thread() -> None:
    host = _Host(_Controller(url="https://example/captions.json3"), tasks=_Tasks(result=[]))
    transcript_command.open_transcript(host)
    assert host._task_manager.submitted == ["radio-transcript"]
    # And it says something first, because a silent pause reads as a dead key.
    assert host.said[0] == "Fetching transcript..."


def test_no_controller_is_not_an_error() -> None:
    host = _Host(_Controller(url=""))
    host._radio_controller = None
    transcript_command.open_transcript(host)
    assert host.said == []
