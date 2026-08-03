"""Tests for recording integrity: joining a dropped recording's parts back
into one file, and the growth-based stall detector that is the recorder's
second liveness signal.

No real ffmpeg is ever launched -- the concat runner is faked -- and no real
clock or process is used by the stall tests.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from quill.core.radio.recording_join import (
    JoinOutcome,
    build_concat_command,
    build_concat_list,
    describe_join,
    describe_reconnect,
    join_recording_parts,
    plan_join,
)
from quill.core.radio.recording_liveness import (
    GrowthTracker,
    is_stalled,
    wait_for_exit,
)

_FFMPEG = "C:/tools/ffmpeg.exe"


def _write(path: Path, size: int = 2048) -> Path:
    path.write_bytes(b"\0" * size)
    return path


def _parts(tmp_path: Path, count: int = 3, *, extension: str = "mp3") -> list[Path]:
    """A base recording plus continuation parts, named as the recorder names
    them (``... (part 2)``), each with real bytes on disk."""
    made = [_write(tmp_path / f"WQXR - 2026-08-02 08-00-00.{extension}")]
    for n in range(2, count + 1):
        made.append(_write(tmp_path / f"WQXR - 2026-08-02 08-00-00 (part {n}).{extension}"))
    return made


class _FakeRunner:
    """Stands in for ``run_subprocess_safely``: records the argv and, when
    *output_size* is given, writes that many bytes to the argv's output path."""

    def __init__(self, *, returncode: int = 0, output_size: int | None = None) -> None:
        self.returncode = returncode
        self.output_size = output_size
        self.calls: list[list[str]] = []

    def __call__(
        self, args: Sequence[str], *, timeout_seconds: float = 30.0
    ) -> subprocess.CompletedProcess[str]:
        argv = list(args)
        self.calls.append(argv)
        if self.output_size is not None:
            Path(argv[-1]).write_bytes(b"\0" * self.output_size)
        return subprocess.CompletedProcess(argv, self.returncode, stdout="", stderr="boom")


# -- plan validation --------------------------------------------------------


def test_plan_join_orders_parts_and_targets_the_base_recording(tmp_path: Path) -> None:
    parts = _parts(tmp_path)
    plan = plan_join(parts)
    assert plan.joinable is True
    assert plan.reason == ""
    assert plan.parts == tuple(parts)  # capture order is preserved
    assert plan.output == parts[0]  # the whole show lands under the expected name
    assert plan.extension == ".mp3"
    assert plan.part_count == 3


def test_plan_join_refuses_a_single_file(tmp_path: Path) -> None:
    plan = plan_join(_parts(tmp_path, 1))
    assert plan.joinable is False
    assert "only one file" in plan.reason


def test_plan_join_collapses_duplicate_paths(tmp_path: Path) -> None:
    parts = _parts(tmp_path, 2)
    plan = plan_join([parts[0], parts[1], parts[1]])
    assert plan.parts == (parts[0], parts[1])


def test_plan_join_refuses_mismatched_extensions(tmp_path: Path) -> None:
    base = _write(tmp_path / "show.mp3")
    other = _write(tmp_path / "show (part 2).aac")
    plan = plan_join([base, other])
    assert plan.joinable is False
    assert "not all the same format" in plan.reason
    assert ".mp3" in plan.reason and ".aac" in plan.reason


def test_plan_join_refuses_a_container_it_cannot_stream_copy(tmp_path: Path) -> None:
    parts = [_write(tmp_path / "show.txt"), _write(tmp_path / "show (part 2).txt")]
    plan = plan_join(parts)
    assert plan.joinable is False
    assert "cannot be joined safely" in plan.reason


def test_plan_join_refuses_when_a_part_is_missing(tmp_path: Path) -> None:
    parts = _parts(tmp_path, 3)
    parts[1].unlink()
    plan = plan_join(parts)
    assert plan.joinable is False
    assert "could not be found" in plan.reason


# -- the concat command -----------------------------------------------------


def test_build_concat_list_uses_forward_slashes_and_escapes_quotes(tmp_path: Path) -> None:
    text = build_concat_list([Path(r"C:\Music\show.mp3"), Path("/music/it's here.mp3")])
    lines = text.splitlines()
    assert lines[0] == "file 'C:/Music/show.mp3'"  # no backslash for the demuxer to eat
    assert lines[1] == "file '/music/it'\\''s here.mp3'"
    assert text.endswith("\n")


def test_build_concat_command_is_a_stream_copy_through_the_concat_demuxer() -> None:
    args = build_concat_command(_FFMPEG, Path("/tmp/parts.txt"), Path("/out/show.mp3"))
    assert args[0] == _FFMPEG
    # The concat *demuxer* reading a list file -- not the unsafe concat filter
    # or the concat: protocol.
    assert args[args.index("-f") + 1] == "concat"
    assert args[args.index("-safe") + 1] == "0"
    assert args[args.index("-i") + 1] == str(Path("/tmp/parts.txt"))
    # -c copy is what makes the join lossless and fast: no decode, no re-encode.
    assert args[args.index("-c") + 1] == "copy"
    assert "-nostdin" in args
    assert args[-1] == str(Path("/out/show.mp3"))
    assert "-af" not in args and "-b:a" not in args


# -- joining ----------------------------------------------------------------


def test_join_recording_parts_replaces_part_one_and_removes_continuations(
    tmp_path: Path,
) -> None:
    parts = _parts(tmp_path, 3)  # 3 x 2048 bytes
    runner = _FakeRunner(output_size=6144)
    outcome = join_recording_parts(parts, ffmpeg=_FFMPEG, runner=runner)
    assert outcome.joined is True
    assert outcome.path == parts[0]
    assert outcome.part_count == 3
    assert parts[0].stat().st_size == 6144  # the joined audio is under the base name
    assert not parts[1].exists() and not parts[2].exists()
    # No half-written work file is left behind for the folder scan to find.
    assert sorted(p.name for p in tmp_path.iterdir()) == [parts[0].name]
    assert len(runner.calls) == 1


def test_join_recording_parts_keeps_every_part_when_ffmpeg_fails(tmp_path: Path) -> None:
    parts = _parts(tmp_path, 3)
    sizes = [p.stat().st_size for p in parts]
    runner = _FakeRunner(returncode=1, output_size=6144)
    outcome = join_recording_parts(parts, ffmpeg=_FFMPEG, runner=runner)
    assert outcome.joined is False
    assert "error joining" in outcome.reason
    assert outcome.path == parts[0]
    # A failed join must never cost the user their recording.
    assert [p.stat().st_size for p in parts] == sizes
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(p.name for p in parts)


def test_join_recording_parts_keeps_every_part_when_the_output_is_too_small(
    tmp_path: Path,
) -> None:
    parts = _parts(tmp_path, 3)
    # ffmpeg exits 0 but wrote far less than the parts contained: not trustworthy.
    outcome = join_recording_parts(parts, ffmpeg=_FFMPEG, runner=_FakeRunner(output_size=2048))
    assert outcome.joined is False
    assert "smaller than the parts" in outcome.reason
    assert all(p.exists() for p in parts)


def test_join_recording_parts_keeps_every_part_when_nothing_was_written(
    tmp_path: Path,
) -> None:
    parts = _parts(tmp_path, 2)
    outcome = join_recording_parts(parts, ffmpeg=_FFMPEG, runner=_FakeRunner(output_size=None))
    assert outcome.joined is False
    assert "not created" in outcome.reason
    assert all(p.exists() for p in parts)


def test_join_recording_parts_never_runs_ffmpeg_on_mismatched_parts(tmp_path: Path) -> None:
    parts = [_write(tmp_path / "show.mp3"), _write(tmp_path / "show (part 2).ogg")]
    runner = _FakeRunner(output_size=6144)
    outcome = join_recording_parts(parts, ffmpeg=_FFMPEG, runner=runner)
    assert outcome.joined is False
    assert runner.calls == []
    assert all(p.exists() for p in parts)


def test_join_recording_parts_reports_missing_ffmpeg(tmp_path: Path) -> None:
    parts = _parts(tmp_path, 2)
    runner = _FakeRunner(output_size=6144)
    outcome = join_recording_parts(parts, ffmpeg="", runner=runner)
    assert outcome.joined is False
    assert "FFmpeg is not available" in outcome.reason
    assert runner.calls == []
    assert all(p.exists() for p in parts)


def test_join_recording_parts_is_a_no_op_for_one_part(tmp_path: Path) -> None:
    parts = _parts(tmp_path, 1)
    runner = _FakeRunner(output_size=6144)
    outcome = join_recording_parts(parts, ffmpeg=_FFMPEG, runner=runner)
    assert outcome.joined is False
    assert runner.calls == []
    assert parts[0].exists()


# -- what the user is told --------------------------------------------------


def test_describe_join_is_honest_both_ways(tmp_path: Path) -> None:
    parts = tuple(_parts(tmp_path, 3))
    joined = describe_join(JoinOutcome(True, parts[0], parts))
    assert joined.startswith("Joined 3 parts into one recording")
    assert parts[0].name in joined
    kept = describe_join(JoinOutcome(False, parts[0], parts, "FFmpeg is not available"))
    assert kept == "Kept 3 separate parts: FFmpeg is not available."


def test_describe_join_says_nothing_about_a_single_part(tmp_path: Path) -> None:
    only = (_write(tmp_path / "show.mp3"),)
    assert describe_join(JoinOutcome(False, only[0], only, "nothing to join")) == ""


def test_describe_reconnect_promises_the_stitch() -> None:
    text = describe_reconnect(2, 5)
    assert "attempt 2 of 5" in text
    assert "part file" in text
    assert "joined back" in text


# -- growth-based stall detection -------------------------------------------


def test_stall_needs_a_full_run_of_non_growing_checks() -> None:
    # The first sample is only a baseline; every later one is a check. N-1
    # non-growing checks leave the recording alive, the Nth declares a stall.
    tracker = GrowthTracker(stall_checks=4, interval_seconds=15.0)
    assert tracker.sample(1000, 0.0) is False  # baseline
    assert tracker.sample(1000, 15.0) is False  # check 1
    assert tracker.sample(1000, 30.0) is False  # check 2
    assert tracker.sample(1000, 45.0) is False  # check 3 -- N-1, still alive
    assert tracker.non_growing_checks == 3
    assert tracker.stalled is False
    assert tracker.sample(1000, 60.0) is True  # check 4 -- N, stalled
    assert tracker.stalled is True


def test_any_growth_resets_the_run() -> None:
    tracker = GrowthTracker(stall_checks=3, interval_seconds=10.0)
    tracker.sample(1000, 0.0)
    tracker.sample(1000, 10.0)
    tracker.sample(1000, 20.0)
    assert tracker.non_growing_checks == 2
    assert tracker.sample(1001, 30.0) is False  # one byte is progress
    assert tracker.non_growing_checks == 0
    assert tracker.sample(1001, 40.0) is False
    assert tracker.sample(1001, 50.0) is False
    assert tracker.sample(1001, 60.0) is True


def test_samples_taken_too_soon_are_not_counted_as_checks() -> None:
    # A caller polling in a tight loop must not be able to declare a healthy
    # recording dead between two muxer flushes.
    tracker = GrowthTracker(stall_checks=2, interval_seconds=15.0)
    tracker.sample(1000, 0.0)
    for tick in range(1, 20):
        assert tracker.sample(1000, tick * 0.1) is False
    assert tracker.non_growing_checks == 0


def test_is_stalled_reads_a_whole_series() -> None:
    flat = [(500, float(n * 15)) for n in range(5)]
    assert is_stalled(flat, stall_checks=4, interval_seconds=15.0) is True
    assert is_stalled(flat[:4], stall_checks=4, interval_seconds=15.0) is False
    growing = [(500 * n, float(n * 15)) for n in range(1, 6)]
    assert is_stalled(growing, stall_checks=4, interval_seconds=15.0) is False


class _FakeProcess:
    """A Popen stand-in: never exits on its own until it is terminated."""

    def __init__(self, *, exits_after_waits: int | None = None) -> None:
        self.stdin = None
        self.terminated = False
        self._waits = 0
        self._exits_after = exits_after_waits

    def wait(self, timeout: float | None = None) -> int:
        self._waits += 1
        if self.terminated or (self._exits_after is not None and self._waits >= self._exits_after):
            return 0
        raise subprocess.TimeoutExpired("ffmpeg", timeout or 0)

    def poll(self) -> int | None:
        return 0 if self.terminated else None

    def terminate(self) -> None:
        self.terminated = True


def test_wait_for_exit_reports_a_clean_exit_without_touching_the_file(tmp_path: Path) -> None:
    process = _FakeProcess(exits_after_waits=2)
    stalled = wait_for_exit(
        process,  # type: ignore[arg-type]
        tmp_path / "never-created.mp3",
        interval_seconds=0.01,
        stall_checks=4,
        clock=lambda: 0.0,
    )
    assert stalled is False
    assert process.terminated is False


def test_wait_for_exit_stops_a_stalled_recording(tmp_path: Path) -> None:
    output = _write(tmp_path / "show.mp3", 4096)  # never grows again
    ticks = iter([0.0, 10.0, 20.0, 30.0, 40.0, 50.0])
    process = _FakeProcess()
    stalled = wait_for_exit(
        process,  # type: ignore[arg-type]
        output,
        interval_seconds=10.0,
        stall_checks=2,
        clock=lambda: next(ticks),
    )
    assert stalled is True
    # The stalled ffmpeg is stopped so the recorder's ordinary drop path -- the
    # existing reconnect/finalize handling -- takes over.
    assert process.terminated is True


def test_wait_for_exit_never_judges_a_recording_the_user_stopped(tmp_path: Path) -> None:
    output = _write(tmp_path / "show.mp3", 4096)
    process = _FakeProcess(exits_after_waits=6)
    stalled = wait_for_exit(
        process,  # type: ignore[arg-type]
        output,
        is_stopped=lambda: True,
        interval_seconds=0.01,
        stall_checks=1,
        clock=lambda: 0.0,
    )
    assert stalled is False
    assert process.terminated is False
