"""Convert one file: run FFmpeg, recover from what can be recovered, place the result.

Extracted from :mod:`quill.core.audio.convert` (GATE-11) when the 1.0.0
end-to-end run over real-world files found two failures that are not the
file's fault and have one obvious remedy each:

* **A subtitle the container cannot hold.** MKV keeps every caption track, but
  a DivX file's ``xsub`` bitmaps (or a broadcast recording's teletext) cannot
  be copied into Matroska. Failing the whole film over a caption format is
  wrong; the file is converted again without the subtitles, and says so.
* **A channel layout FFmpeg does not name.** Some Flash-era files declare "1
  channels" with no layout, and the AAC encoder refuses an unnamed layout.
  Giving the count explicitly (``-ac 1``) is all it needs.

Anything else fails that job alone, with the reason in words
(:mod:`quill.core.audio.ffmpeg_errors`). Every encode writes to a temp file
beside the destination and is moved into place only when it succeeded, so a
failed or stopped conversion never leaves a truncated file behind.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

from quill.core.audio.convert import ConversionJob, JobResult, build_convert_command
from quill.core.audio.ffmpeg_live import LiveHooks, run_ffmpeg_live
from quill.core.speech.audio_tags_core import Chapter

_UNNAMED_LAYOUT = re.compile(r'Unsupported channel layout "(\d+) channels"')

#: The report line for a file that was being converted when Stop was pressed.
STOPPED_NOTE = "Stopped part way; the unfinished file was removed."


def _output_seconds(job: ConversionJob) -> float:
    """How long the output should be, for progress -- 0 when it cannot be told."""
    from quill.core.audio.media_probe import probe

    try:
        whole = float(probe(job.source).duration_s or 0.0)
    except Exception:  # noqa: BLE001 - no length means no percentage, not no file
        return 0.0
    start = max(0.0, float(job.spec.start_s or 0.0))
    end = float(job.spec.end_s or 0.0)
    if end > start:
        whole = min(whole, end) if whole else end
    return max(0.0, whole - start)


def _retry_spec(job: ConversionJob, stderr: str) -> tuple[ConversionJob, str] | None:
    """A changed job worth one more attempt, and what changed -- or None."""
    lowered = stderr.lower()
    caption_trouble = any(
        needle in lowered
        for needle in (
            "subtitle",
            "could not find tag for codec",
            "not currently supported in container",
            # Teletext and other captions Matroska cannot describe in its header.
            "could not write header",
        )
    )
    if job.spec.is_video() and job.spec.keep_subtitles and caption_trouble:
        spec = replace(job.spec, keep_subtitles=False)
        return replace(
            job, spec=spec
        ), "Subtitles in a format this container cannot hold were left out."
    found = _UNNAMED_LAYOUT.search(stderr)
    if found and job.spec.force_channels is None:
        spec = replace(job.spec, force_channels=int(found.group(1)))
        return replace(job, spec=spec), ""
    return None


def _default_single_runner(
    ffmpeg: str, job: ConversionJob, *, hooks: LiveHooks | None = None
) -> JobResult:
    """Encode one job to a temp file, then move it into place (atomic, safe).

    With ``hooks`` the encode reports how far it has got and stops the moment
    the batch is stopped; the temp file is removed either way, so a stopped
    file leaves nothing behind.
    """
    if not job.source.is_file():
        return JobResult(job=job, ok=False, error="input file not found")
    from quill.stability.safe_subprocess import run_subprocess_safely

    job.dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".convert-", suffix=job.dest.suffix, dir=str(job.dest.parent)
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    exact = job.spec.exact_optilab
    # A stream copy is never decoded, so it can never be processed and stay a
    # copy. The pair is refused here rather than half-honoured.
    if exact is not None and exact.active and not job.spec.copy_audio:
        return _exact_optilab_runner(ffmpeg, job, tmp_path, hooks=hooks)
    # A feature-length video encode can outlast the hour an audio file gets.
    timeout = 6 * 3600.0 if job.spec.is_video() else 3600.0
    attempt, notes = job, []
    meta = tmp_path.with_suffix(".ffmeta")
    try:
        chapters, chapter_note, write_meta = _chapters_for(job)
        if chapter_note:
            notes.append(chapter_note)
        if write_meta and chapters:
            from quill.core.speech.ffmpeg import build_ffmetadata

            meta.write_text(
                build_ffmetadata([(c.title, c.start_ms, c.end_ms) for c in chapters]),
                encoding="utf-8",
            )
        length = _output_seconds(job) if hooks is not None and hooks.on_fraction else 0.0
        for _try in range(3):
            command = build_convert_command(
                ffmpeg, attempt, out_path=tmp_path, chapters_meta=meta if meta.is_file() else None
            )
            if hooks is None:
                completed: object = run_subprocess_safely(command, timeout_seconds=timeout)
            else:
                completed = run_ffmpeg_live(
                    command, duration_s=length, hooks=hooks, timeout_seconds=timeout
                )
                if getattr(completed, "cancelled", False):
                    tmp_path.unlink(missing_ok=True)
                    return JobResult(job=job, ok=False, skipped=True, error=STOPPED_NOTE)
            if int(getattr(completed, "returncode", 1)) == 0:
                break
            stderr = str(getattr(completed, "stderr", "") or "")
            retry = _retry_spec(attempt, stderr)
            if retry is None:
                from quill.core.audio.ffmpeg_errors import explain_failure

                tmp_path.unlink(missing_ok=True)
                return JobResult(job=job, ok=False, error=explain_failure(stderr))
            attempt, note = retry
            if note:
                notes.append(note)
        else:
            tmp_path.unlink(missing_ok=True)
            return JobResult(job=job, ok=False, error="FFmpeg failed after every retry.")
        if not job.spec.is_video():  # FFmpeg drops most cover art; put it back
            from quill.core.audio.cover_art import carry_cover_art

            carry_cover_art(job.source, tmp_path)
        shutil.move(str(tmp_path), str(job.dest))
        if chapters and not write_meta:  # Ogg/FLAC comments, or a .cue beside it
            from quill.core.audio.chapter_plan import place_chapters

            placed = place_chapters(job.dest, job.spec.fmt, chapters)
            if placed:
                notes.append(placed)
        return JobResult(job=job, ok=True, error=" ".join(notes))
    except Exception as exc:  # noqa: BLE001 - clean up the temp, report the reason
        tmp_path.unlink(missing_ok=True)
        return JobResult(job=job, ok=False, error=str(exc))
    finally:
        meta.unlink(missing_ok=True)


def _chapters_for(job: ConversionJob) -> tuple[list[Chapter] | None, str, bool]:
    """``(chapters, note, write_meta)`` for one job.

    ``chapters`` is None when FFmpeg should simply carry the file's own marks
    (a native format, keeping them). ``write_meta`` is True when the list must
    be handed to FFmpeg as an FFMETADATA input; otherwise any list is placed
    after the encode (Ogg/FLAC comments, or a .cue beside the file).
    """
    from quill.core.audio import chapter_plan as cp

    spec = job.spec
    how = spec.chapter_source or cp.KEEP
    native = cp.chapter_home(spec.fmt) == "native"
    if how == cp.NONE or (how == cp.KEEP and native):
        return None, "", False
    from quill.core.audio.media_probe import probe

    info = probe(job.source)
    own = [
        Chapter(index=i, title=c.title, start_ms=int(c.start_s * 1000), end_ms=int(c.end_s * 1000))
        for i, c in enumerate(info.chapters)
    ]
    chapters, note = cp.resolve_chapters(
        job.source, how, total_ms=int(info.duration_s * 1000), own=own
    )
    if chapters is None:
        return None, note, False
    start_ms, end_ms = int(spec.start_s * 1000), int(spec.end_s * 1000)
    if start_ms or end_ms:
        chapters = cp.clip_chapters(chapters, start_ms, end_ms)
    return chapters, note, native


def _exact_optilab_runner(
    ffmpeg: str, job: ConversionJob, tmp_path: Path, *, hooks: LiveHooks | None = None
) -> JobResult:
    """Convert one job through the real OptiLab engine instead of an ffmpeg
    approximation of it: decode -> ``quill-optilab`` -> encode.

    Falls back to nothing: if the optional component is absent the job fails with
    a reason the batch summary can say out loud, rather than quietly producing a
    file that says "exact" in the log and is not. The caller decides whether to
    offer the option at all (:func:`quill.core.audio.exact_optilab.available`).
    """
    from quill.core.audio import exact_optilab

    spec = job.spec
    exact = spec.exact_optilab
    assert exact is not None  # guarded by the caller
    if not exact_optilab.available():
        tmp_path.unlink(missing_ok=True)
        return JobResult(job=job, ok=False, error=exact_optilab.unavailable_reason())
    rate, channels = exact_optilab.probe_shape(job.source)
    try:
        encode_command = build_convert_command(
            ffmpeg, job, out_path=tmp_path, pcm_input=(rate, channels)
        )
        exact_optilab.process_file(
            job.source,
            tmp_path,
            exact,
            encode_command=encode_command,
            filter_graph=",".join(spec.filters),
            sample_rate=rate,
            channels=channels,
            should_cancel=hooks.cancelled if hooks is not None else None,
        )
        shutil.move(str(tmp_path), str(job.dest))
        return JobResult(job=job, ok=True)
    except Exception as exc:  # noqa: BLE001 - one bad file must never sink the batch
        tmp_path.unlink(missing_ok=True)
        if hooks is not None and hooks.cancelled():
            return JobResult(job=job, ok=False, skipped=True, error=STOPPED_NOTE)
        return JobResult(job=job, ok=False, error=str(exc))
