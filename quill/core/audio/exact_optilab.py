"""Run the *real* OptiLab Core over a saved file: ffmpeg -> adapter -> ffmpeg.

Attribution
-----------
OptiLab Core is by **Lanes Audio / dgl1984** -- https://github.com/dgl1984/optilab
QUILL vendors its engine unmodified at v1.4.0 under ``quill/native/optilab/upstream/``
(Apache-2.0 WITH the Commons Clause v1.0) and links it into an adapter executable
of QUILL's own (:mod:`quill.core.optilab_adapter` locates it). This module is the
half that actually *runs* it.

Why a three-process pipe
------------------------
The adapter speaks raw interleaved 32-bit float PCM on stdin and stdout -- it has
no idea what an MP3 is, which is exactly right: upstream's API is
``prepare(rate)`` -> ``setParameters(...)`` -> ``processInterleaved(...)`` and
nothing more. So a pass is::

    ffmpeg -i source -f f32le -   |   quill-optilab --mode ...   |   ffmpeg -f f32le -i - out

The three children are wired to **each other's** pipes, never pumped by Python.
That is not a stylistic choice: a parent that reads one child's stdout while
feeding another's stdin deadlocks the moment either OS pipe buffer fills, which
for a three-hour recording is immediately. Here the kernel moves the bytes and
this module only waits.

Both ffmpeg stderrs go to temp files rather than pipes, for the same reason: an
unread stderr pipe is a stall waiting to happen, and a file can be read after the
fact to explain a failure.

Where this is used, and why real time is the hard case
------------------------------------------------------
**Saved files, by default** -- radio recordings and audio conversion. A saved file
is processed once, afterwards, with nothing to protect: no preview to keep
instant, no reconnect to avoid, and time enough to spend.

**Live listening is possible, and it costs something.** The engine cannot be
"applied" to a playing stream the way an equalizer can, and the reason is
structural rather than a missing feature:

* It is a **separate process**. Upstream's own API.md says the C++ API is not a
  stable C ABI and asks consumers to wrap it in an adapter they own, so the audio
  has to physically travel through another program. There is no filter string
  that expresses "someone else's DSP" to mpv or to ffmpeg.
* **Nothing on QUILL's live path ever holds a PCM sample.** mpv is handed a
  filter string (``ui/audio/mpv_engine.py`` sets ``af``) and does everything
  itself. That is the design's central virtue -- it is why enhancements preview
  with no gap and no reconnect -- and it is exactly what an external engine
  cannot join.
* So live processing means **relaying**: decode the stream, pipe it through the
  engine, re-encode it, and hand the player a local URL
  (:meth:`quill.core.audio_enhance.EnhanceRelay.start`). That works -- QUILL does
  it when the listener asks -- but it buys the engine at the price of a slower
  start, a re-encode generation, more CPU, and a reconnect on every settings
  change, because the engine is prepared with a mode and a sample rate when it
  starts and cannot be re-parameterised mid-stream.

Hence the shape of the setting: off, saved files, or saved files *and* listening.
The third option states its own cost, because a listener choosing it is choosing
to give up the instant preview, and that must not be a surprise discovered
afterwards.

**Never both.** When exact processing runs, the caller must build its ffmpeg graph
with the OptiLab *chain* off (EQ, compressor, night mode and the rest still
apply) -- otherwise the adaptation and the real engine both process the same audio
and the result is neither.

**Entirely optional.** No adapter built -> :func:`available` is False and every
caller falls back to the ffmpeg chain exactly as before.

wx-free, strict-typed.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core import optilab_adapter
from quill.core.error_codes import CodedError
from quill.stability.redaction import format_args_for_log

logger = logging.getLogger(__name__)

__all__ = [
    "ExactOptilab",
    "ExactProcessingError",
    "available",
    "build_decode_command",
    "build_pcm_input_args",
    "process_file",
    "process_in_place",
    "unavailable_reason",
]

#: The wire format between the three processes. Fixed and unnegotiated on
#: purpose: the producer is ffmpeg, which is *told* exactly what to emit, so
#: there is no header for anyone to mis-parse. It is also the format upstream's
#: ``processInterleaved`` wants, so nothing converts anything in between.
_PCM_FORMAT = "f32le"

#: OptiLab Core processes mono or stereo. Anything wider is downmixed to stereo
#: *explicitly*, in the decode step, rather than being quietly refused or -- far
#: worse -- handed to the engine as if it were stereo.
_MAX_CHANNELS = 2

#: How long one pass may take before it is abandoned. Generous: a three-hour
#: lossless recording on a slow disk is a legitimate long job. The pass is
#: cancellable, so this is a backstop, not the control.
_DEFAULT_TIMEOUT_SECONDS = 6 * 60 * 60


class ExactProcessingError(CodedError):
    """An exact-OptiLab pass could not be run, or did not finish cleanly."""

    code = "QUILL-AUDIO-OPTILAB-EXACT"


@dataclass(frozen=True, slots=True)
class ExactOptilab:
    """ "Process this file with the real engine, like so" -- or nothing.

    ``mode`` is one of :data:`quill.core.optilab.OPTILAB_MODES` minus ``"off"``;
    ``"off"`` (the default) means *do not run a pass at all*, which is why
    :meth:`active` exists and why every caller may hold one of these
    unconditionally.

    ``input_db`` and ``auto_adapt`` are the same two controls the live chain has,
    so a listener's Sound Enhancements settings carry over unchanged.
    """

    mode: str = "off"
    input_db: float = 0.0
    auto_adapt: int = 0

    @property
    def active(self) -> bool:
        return self.mode in ("podcast", "stream", "limiter")


def available() -> bool:
    """Whether an exact pass can run on this machine at all."""
    return optilab_adapter.available()


def unavailable_reason() -> str:
    """Why it cannot, in words a listener can act on ("" when it can).

    Never returns an empty string while unavailable: an option that is greyed
    out, or a job that failed, with no reason given is worse than one that is
    plainly absent.
    """
    if available():
        return ""
    return optilab_adapter.unavailable_reason() or (
        "Exact OptiLab processing needs the OptiLab component, which this build "
        "does not include. The built-in sound enhancements are unaffected."
    )


# --------------------------------------------------------------------------- #
# Pure argv builders (unit-tested; no process is started here)
# --------------------------------------------------------------------------- #


def build_decode_command(
    ffmpeg: str,
    source: Path | str,
    *,
    sample_rate: int,
    channels: int,
    filter_graph: str = "",
) -> list[str]:
    """ffmpeg argv that decodes *source* to raw PCM on stdout.

    The sample rate is forced to the one the adapter was prepared with -- upstream
    takes the rate at ``prepare()`` and its time constants follow from it, so the
    two must agree. The channel count is capped at stereo (see
    :data:`_MAX_CHANNELS`); a 5.1 source is downmixed here, visibly, by ffmpeg.

    A ``filter_graph`` runs *before* the engine, which is the same order the live
    chain uses: everything else first, broadcast polish last.
    """
    rate = _clamp_rate(sample_rate)
    count = _clamp_channels(channels)
    filter_args = ["-af", filter_graph] if filter_graph else []
    return [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-vn",
        *filter_args,
        "-f",
        _PCM_FORMAT,
        "-ar",
        str(rate),
        "-ac",
        str(count),
        "pipe:1",
    ]


def build_pcm_input_args(sample_rate: int, channels: int) -> list[str]:
    """The ffmpeg input options that read this module's PCM from stdin.

    Shared by every encode step (the recorder's and the converter's) so the
    format contract is written down exactly once.
    """
    return [
        "-f",
        _PCM_FORMAT,
        "-ar",
        str(_clamp_rate(sample_rate)),
        "-ac",
        str(_clamp_channels(channels)),
        "-i",
        "pipe:0",
    ]


def build_encode_command(
    ffmpeg: str,
    dest: Path | str,
    *,
    sample_rate: int,
    channels: int,
    encode_args: list[str],
) -> list[str]:
    """ffmpeg argv that reads PCM on stdin and writes *dest*.

    ``encode_args`` is the caller's own codec/quality choice (the recorder reuses
    its recording format; the converter reuses its spec), so this module never
    guesses at an output format.
    """
    return [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        *build_pcm_input_args(sample_rate, channels),
        *encode_args,
        "-y",
        str(dest),
    ]


def _clamp_rate(sample_rate: int) -> int:
    try:
        rate = int(sample_rate)
    except (TypeError, ValueError):
        return 48_000
    return rate if 8_000 <= rate <= 384_000 else 48_000


def _clamp_channels(channels: int) -> int:
    try:
        count = int(channels)
    except (TypeError, ValueError):
        return _MAX_CHANNELS
    return max(1, min(_MAX_CHANNELS, count))


# --------------------------------------------------------------------------- #
# Probing the source's shape
# --------------------------------------------------------------------------- #


def probe_shape(source: Path | str) -> tuple[int, int]:
    """The source's ``(sample_rate, channels)``, or a safe ``(48000, 2)``.

    Deliberately *not* a resample: the pass keeps the file's own rate so nothing
    about how it sounds changes except the processing. A probe that fails falls
    back to 48 kHz stereo, which is right for every stream QUILL records and
    wrong only in ways ffmpeg then corrects on the decode side anyway.
    """
    from quill.core.speech.ffmpeg import find_ffprobe
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffprobe = find_ffprobe()
    if ffprobe is None:
        return 48_000, _MAX_CHANNELS
    args = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate,channels",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(source),
    ]
    try:
        completed = run_subprocess_safely(args, timeout_seconds=30.0)
    except (OSError, subprocess.SubprocessError):
        return 48_000, _MAX_CHANNELS
    return parse_probe_shape(completed.stdout or "")


def parse_probe_shape(probe_output: str) -> tuple[int, int]:
    """Parse ffprobe's two-line rate/channels output (pure)."""
    rate = 48_000
    channels = _MAX_CHANNELS
    values = [line.strip() for line in probe_output.splitlines() if line.strip()]
    if values:
        try:
            rate = _clamp_rate(int(values[0]))
        except ValueError:
            rate = 48_000
    if len(values) > 1:
        try:
            channels = _clamp_channels(int(values[1]))
        except ValueError:
            channels = _MAX_CHANNELS
    return rate, channels


# --------------------------------------------------------------------------- #
# The pass itself
# --------------------------------------------------------------------------- #


def process_file(
    source: Path,
    dest: Path,
    spec: ExactOptilab,
    *,
    encode_args: list[str] | None = None,
    encode_command: list[str] | None = None,
    filter_graph: str = "",
    sample_rate: int = 0,
    channels: int = 0,
    should_cancel: Callable[[], bool] | None = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Process *source* into *dest* with the real engine.

    Give either ``encode_args`` (codec/quality options; this module builds the
    rest of the encode argv) or a whole ``encode_command`` built elsewhere -- the
    converter has a command builder of its own and reuses it, so its exact pass
    and its ordinary pass cannot drift apart. A command must read PCM on stdin;
    see :func:`build_pcm_input_args`.

    Raises :class:`ExactProcessingError` when the pass cannot be run (no adapter,
    no ffmpeg, an inactive mode) or did not finish cleanly. A caller that can
    carry on without it should catch that and keep the unprocessed file: this
    never deletes or replaces anything itself.

    ``should_cancel`` is polled while waiting; a cancel terminates all three
    children and raises, leaving *dest* to the caller to clean up.
    """
    if not spec.active:
        raise ExactProcessingError("No OptiLab mode is selected, so there is nothing to apply.")
    adapter = optilab_adapter.find_adapter()
    if adapter is None:
        raise ExactProcessingError(optilab_adapter.unavailable_reason())
    from quill.core.speech.ffmpeg import INSTALL_HINT, find_ffmpeg

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise ExactProcessingError(f"ffmpeg is not installed. {INSTALL_HINT}")
    if not Path(source).is_file():
        raise ExactProcessingError(f"{Path(source).name} could not be found.")

    rate, count = (sample_rate, channels)
    if rate <= 0 or count <= 0:
        probed_rate, probed_channels = probe_shape(source)
        rate = rate if rate > 0 else probed_rate
        count = count if count > 0 else probed_channels
    rate, count = _clamp_rate(rate), _clamp_channels(count)

    decode = build_decode_command(
        ffmpeg, source, sample_rate=rate, channels=count, filter_graph=filter_graph
    )
    process = optilab_adapter.adapter_command(
        adapter,
        mode=spec.mode,
        sample_rate=rate,
        channels=count,
        input_db=spec.input_db,
        auto_adapt=spec.auto_adapt,
    )
    if encode_command is not None:
        encode = list(encode_command)
    else:
        encode = build_encode_command(
            ffmpeg, dest, sample_rate=rate, channels=count, encode_args=list(encode_args or [])
        )
    logger.info(
        "Exact OptiLab pass: %s | %s | %s",
        format_args_for_log(decode),
        format_args_for_log(process),
        format_args_for_log(encode),
    )
    _run_pipeline(
        decode,
        process,
        encode,
        should_cancel=should_cancel,
        timeout_seconds=timeout_seconds,
    )


def process_in_place(
    path: Path,
    spec: ExactOptilab,
    *,
    encode_args: list[str],
    should_cancel: Callable[[], bool] | None = None,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Replace *path* with its processed self, or leave it exactly as it was.

    The pass writes a sibling temp file and only then replaces the original, in
    one ``os.replace``. A failure anywhere -- a missing adapter, a crash, a
    cancel, a full disk -- deletes the temp and leaves the original untouched.
    Losing somebody's recording to a post-process is the one outcome this whole
    feature must never produce, so the original is never opened for writing.
    """
    source = Path(path)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".optilab-", suffix=source.suffix or ".tmp", dir=str(source.parent)
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        process_file(
            source,
            tmp_path,
            spec,
            encode_args=encode_args,
            should_cancel=should_cancel,
            timeout_seconds=timeout_seconds,
        )
        if not tmp_path.is_file() or tmp_path.stat().st_size <= 0:
            raise ExactProcessingError("the processed file came out empty")
        os.replace(tmp_path, source)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def _run_pipeline(
    decode: list[str],
    process: list[str],
    encode: list[str],
    *,
    should_cancel: Callable[[], bool] | None,
    timeout_seconds: float,
) -> None:
    """Start the three children wired to each other and wait for the last one."""
    # No console window on Windows, exactly as every other QUILL subprocess.
    creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    decode_err: Any = tempfile.TemporaryFile()
    encode_err: Any = tempfile.TemporaryFile()
    adapter_err: Any = tempfile.TemporaryFile()
    children: list[subprocess.Popen[bytes]] = []
    try:
        try:
            p_decode = subprocess.Popen(
                decode,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=decode_err,
                creationflags=creationflags,
            )
            children.append(p_decode)
            p_adapter = subprocess.Popen(
                process,
                stdin=p_decode.stdout,
                stdout=subprocess.PIPE,
                stderr=adapter_err,
                creationflags=creationflags,
            )
            children.append(p_adapter)
            p_encode = subprocess.Popen(
                encode,
                stdin=p_adapter.stdout,
                stdout=subprocess.DEVNULL,
                stderr=encode_err,
                creationflags=creationflags,
            )
            children.append(p_encode)
        except OSError as exc:
            _terminate(children)
            raise ExactProcessingError(f"Could not start exact OptiLab processing: {exc}") from exc
        # The parent must drop its own copies of the middle pipes, or the reader
        # never sees EOF and the pipeline hangs at the end of the file.
        for handle in (p_decode.stdout, p_adapter.stdout):
            if handle is not None:
                handle.close()
        _wait(p_encode, should_cancel=should_cancel, timeout_seconds=timeout_seconds)
        for child in (p_adapter, p_decode):
            try:
                child.wait(timeout=30.0)
            except subprocess.TimeoutExpired:
                child.kill()
        failures = [
            (name, child.returncode, err)
            for name, child, err in (
                ("ffmpeg (decode)", p_decode, decode_err),
                ("the OptiLab adapter", p_adapter, adapter_err),
                ("ffmpeg (encode)", p_encode, encode_err),
            )
            if child.returncode not in (0, None)
        ]
        if failures:
            name, code, err = failures[0]
            raise ExactProcessingError(f"{name} failed ({code}): {_tail(err)}")
    finally:
        _terminate(children)
        for handle in (decode_err, adapter_err, encode_err):
            try:
                handle.close()
            except OSError:
                pass


def _wait(
    child: subprocess.Popen[bytes],
    *,
    should_cancel: Callable[[], bool] | None,
    timeout_seconds: float,
) -> None:
    """Wait for *child*, checking for cancellation as we go."""
    if should_cancel is None:
        try:
            child.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            raise ExactProcessingError(
                "Exact OptiLab processing took too long and was stopped."
            ) from exc
        return
    waited = 0.0
    while True:
        try:
            child.wait(timeout=0.5)
            return
        except subprocess.TimeoutExpired:
            waited += 0.5
            if should_cancel():
                raise ExactProcessingError("Exact OptiLab processing was cancelled.") from None
            if waited >= timeout_seconds:
                raise ExactProcessingError(
                    "Exact OptiLab processing took too long and was stopped."
                ) from None


def _terminate(children: list[subprocess.Popen[bytes]]) -> None:
    for child in children:
        if child.poll() is None:
            try:
                child.terminate()
            except OSError:
                pass


def _tail(handle: object, limit: int = 300) -> str:
    """The last of a child's stderr, for a message somebody can act on."""
    try:
        handle.seek(0)  # type: ignore[attr-defined]
        raw = handle.read()  # type: ignore[attr-defined]
    except (OSError, ValueError):
        return "no further detail"
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
    text = " ".join(text.split())
    return text[-limit:] if text else "no further detail"
