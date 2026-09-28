"""Progress inside a file, and a Stop that stops the file in progress.

Quill Converter 1.0.0 used to count progress only in finished files -- a
one-file batch of a long audiobook said nothing until it ended -- and Stop
took effect only between files (in a sound batch, never: every file had
already been handed to a worker). These pin the three layers that fixed it:
the FFmpeg runner, the batch runner and the sentence the window shows.
"""

from __future__ import annotations

import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

# ``convert`` before ``convert_runner``: the runner is built on it.
from quill.core.audio import batch_progress, convert, convert_runner, ffmpeg_live
from quill.core.audio.batch_progress import BatchProgress
from quill.core.audio.ffmpeg_live import LiveHooks, parse_out_time, run_ffmpeg_live

cv = convert

# -- FFmpeg's progress lines -------------------------------------------------


@pytest.mark.parametrize(
    ("line", "seconds"),
    [
        ("out_time_us=2500000\n", 2.5),
        ("out_time_ms=2500000", 2.5),  # FFmpeg's "ms" is microseconds too
        ("out_time=01:02:03.500000", 3723.5),
        ("out_time_us=N/A", None),
        ("frame=12", None),
        ("progress=continue", None),
        ("out_time_us=", None),
    ],
)
def test_parse_out_time(line: str, seconds: float | None) -> None:
    assert parse_out_time(line) == seconds


def test_progress_switches_go_straight_after_the_executable() -> None:
    assert ffmpeg_live.with_progress_args(["ffmpeg", "-i", "a.wav", "b.mp3"]) == [
        "ffmpeg",
        "-progress",
        "pipe:1",
        "-nostats",
        "-i",
        "a.wav",
        "b.mp3",
    ]


def _fake_ffmpeg(tmp_path: Path, body: str) -> list[str]:
    script = tmp_path / "fake_ffmpeg.py"
    script.write_text(textwrap.dedent(body), encoding="utf-8")
    return [sys.executable, str(script)]


@pytest.fixture
def no_progress_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    # The fake is Python, which would refuse FFmpeg's switches.
    monkeypatch.setattr(ffmpeg_live, "with_progress_args", list)


@pytest.mark.usefixtures("no_progress_switches")
def test_live_run_reports_rising_fractions_and_never_claims_done(tmp_path: Path) -> None:
    command = _fake_ffmpeg(
        tmp_path,
        """
        import sys
        for us in (0, 1_000_000, 2_000_000, 4_000_000, 5_000_000):
            print(f"out_time_us={us}", flush=True)
            print("progress=continue", flush=True)
        print("out_time_us=N/A", flush=True)
        sys.stderr.write("fine\\n")
        """,
    )
    seen: list[float] = []
    result = run_ffmpeg_live(
        command,
        duration_s=4.0,
        hooks=LiveHooks(on_fraction=seen.append),
        timeout_seconds=60,
    )
    assert result.returncode == 0 and not result.cancelled
    assert "fine" in result.stderr
    assert seen == [0.0, 0.25, 0.5, 0.99]  # rising only, capped below done
    assert all(b > a for a, b in zip(seen, seen[1:], strict=False))


@pytest.mark.usefixtures("no_progress_switches")
def test_stop_kills_the_encode_now(tmp_path: Path) -> None:
    command = _fake_ffmpeg(
        tmp_path,
        """
        import time
        print("out_time_us=1000000", flush=True)
        time.sleep(60)
        """,
    )
    token = cv.CancelToken()
    started = time.monotonic()
    result = run_ffmpeg_live(
        command,
        duration_s=100.0,
        hooks=LiveHooks(on_fraction=lambda _f: token.cancel(), cancel=token),
        timeout_seconds=120,
    )
    assert result.cancelled
    assert result.returncode != 0
    assert time.monotonic() - started < 20  # not the sixty the child wanted


@pytest.mark.usefixtures("no_progress_switches")
def test_a_runaway_encode_is_stopped_at_the_timeout(tmp_path: Path) -> None:
    command = _fake_ffmpeg(tmp_path, "import time\ntime.sleep(60)\n")
    result = run_ffmpeg_live(command, duration_s=0, hooks=LiveHooks(), timeout_seconds=0.5)
    assert result.timed_out and not result.cancelled
    assert "took too long" in result.stderr


# -- the per-file runner ------------------------------------------------------


def test_a_stopped_file_is_skipped_and_leaves_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "book.wav"
    source.write_bytes(b"RIFF")
    out = tmp_path / "out"
    job = cv.ConversionJob(source, out / "book.mp3", cv.ConversionSpec(fmt="mp3"))
    monkeypatch.setattr(convert_runner, "_chapters_for", lambda _job: (None, "", False))

    def fake_live(command, **_kw):
        Path(command[-1]).write_bytes(b"half an encode")
        return ffmpeg_live.LiveResult(returncode=1, stderr="", cancelled=True)

    monkeypatch.setattr(convert_runner, "run_ffmpeg_live", fake_live)
    result = convert_runner._default_single_runner("ffmpeg", job, hooks=LiveHooks())
    assert result.skipped and not result.ok
    assert result.error == convert_runner.STOPPED_NOTE
    assert list(out.iterdir()) == []  # the temp file went with it


def test_output_length_honours_keep_only_part(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.audio import media_probe

    monkeypatch.setattr(
        media_probe, "probe", lambda _p: media_probe.MediaInfo(path=Path("a"), duration_s=600.0)
    )
    spec = cv.ConversionSpec(fmt="mp3", start_s=60.0, end_s=180.0)
    assert convert_runner._output_seconds(cv.ConversionJob(Path("a"), Path("b"), spec)) == 120
    whole = cv.ConversionJob(Path("a"), Path("b"), cv.ConversionSpec(fmt="mp3"))
    assert convert_runner._output_seconds(whole) == 600


# -- the batch runner ---------------------------------------------------------


def _jobs(n: int) -> list[cv.ConversionJob]:
    return [
        cv.ConversionJob(Path(f"{i}.wav"), Path(f"{i}.mp3"), cv.ConversionSpec(fmt="mp3"))
        for i in range(n)
    ]


def test_a_runner_that_takes_hooks_reports_inside_the_file() -> None:
    heard: list[tuple[str, float]] = []

    def runner(ffmpeg: str, job: cv.ConversionJob, *, hooks: LiveHooks) -> cv.JobResult:
        assert hooks.on_fraction is not None
        hooks.on_fraction(0.5)
        return cv.JobResult(job=job, ok=True)

    result = cv.run_conversion_batch(
        "ffmpeg",
        _jobs(2),
        workers=1,
        on_file_progress=lambda job, f: heard.append((job.source.name, f)),
        single_runner=runner,
    )
    assert result.converted == 2
    assert heard == [("0.wav", 0.5), ("1.wav", 0.5)]


def test_stop_during_a_batch_skips_every_queued_file() -> None:
    token = cv.CancelToken()
    ran: list[str] = []

    def runner(ffmpeg: str, job: cv.ConversionJob) -> cv.JobResult:
        ran.append(job.source.name)
        token.cancel()  # Stop pressed while the first file converts
        return cv.JobResult(job=job, ok=True)

    result = cv.run_conversion_batch(
        "ffmpeg", _jobs(5), workers=1, cancel=token, single_runner=runner
    )
    assert ran == ["0.wav"]
    assert result.converted == 1 and result.skipped == 4
    assert result.cancelled


# -- what the window says -----------------------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_one_file_names_itself_and_estimates_time_left() -> None:
    clock = _Clock()
    progress = BatchProgress(1, clock=clock)
    clock.now = 2.0
    first = progress.file_progress(Path("Book.m4b"), 0.01)
    assert first == ("Converting Book.m4b: 1 percent", 0.01)
    clock.now = 60.0
    text, overall = progress.file_progress(Path("Book.m4b"), 0.25) or ("", 0)
    assert overall == 0.25
    assert text == "Converting Book.m4b: 25 percent, about 3 minutes left"


def test_updates_are_held_to_about_one_a_second() -> None:
    clock = _Clock()
    progress = BatchProgress(3, clock=clock)
    clock.now = 10.0
    assert progress.file_progress(Path("a"), 0.1) is not None
    clock.now = 10.4
    assert progress.file_progress(Path("b"), 0.1) is None  # too soon
    assert progress.file_done(Path("a"))[0].startswith("Converted 1 of 3")  # never held


def test_a_queue_counts_running_files_toward_the_whole() -> None:
    clock = _Clock()
    progress = BatchProgress(4, clock=clock)
    progress.file_done(Path("a"))
    clock.now = 5.0
    update = progress.file_progress(Path("b"), 0.5)
    assert update is not None
    assert update[1] == pytest.approx(0.375)
    assert update[0].startswith("Converted 1 of 4, 37 percent overall")


@pytest.mark.parametrize(
    ("seconds", "said"),
    [
        (30, "less than a minute"),
        (61, "about 1 minute"),
        (600, "about 10 minutes"),
        (3600, "about 1 hour"),
        (4200, "about 1 hour 10 minutes"),
        (7260, "about 2 hours 1 minute"),
    ],
)
def test_time_left_is_said_plainly(seconds: float, said: str) -> None:
    assert batch_progress._say_duration(seconds) == said


def test_the_tracker_is_safe_across_worker_threads() -> None:
    progress = BatchProgress(40)
    threads = [threading.Thread(target=progress.file_done, args=(Path(str(i)),)) for i in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert progress.overall() == 1.0
