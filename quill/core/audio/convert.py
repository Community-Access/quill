"""Universal audio converter core (#1255) — pure, wx-free, unit-tested.

Composes QUILL's bundled ffmpeg into a general audio-conversion engine, kept
UI-free so the Audio Studio dialog and a headless/CLI caller share one path:

    mixed file/folder queue -> plan_jobs -> ConversionJob list
    ConversionJob + ffmpeg  -> build_convert_command -> argv
    jobs                    -> run_conversion_batch  -> multi-worker + progress

This module is the v1 (MVP) foundation from the spec's §14: a mixed file/folder
queue, recursive batch across the encode formats + WAV, CBR bitrate / sample
rate / channels / bit depth, an existing-file policy (skip/overwrite/rename),
a dry-run (``plan_jobs`` itself), and an off-thread, cancellable, multi-worker
runner. Rich DSP, presets and URL import (v2/v3) layer on top of this without
changing the job/plan shape.

Design rules (mirroring the tested ffmpeg wrapper):

- **Pure argv builders.** ``build_convert_command`` takes controlled on-disk
  paths and a validated spec and returns argv; it never touches the network,
  never reads untrusted document text, and only ever names ffmpeg via the
  caller-resolved path (``ffmpeg.find_ffmpeg``).
- **Never destroy originals.** Outputs default to a ``Converted/`` sibling; the
  default conflict policy auto-numbers rather than overwrite; encodes write to a
  temp file that the runner moves into place, so a failed/cancelled encode never
  leaves a truncated output.
- **Degrade, don't crash.** A missing encoder is hidden by the capability probe;
  a corrupt input fails that one job with a readable reason and the batch
  continues.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path

from quill.core.speech.ffmpeg import ENCODE_FORMATS, MP3_VBR_QUALITY, AudioMetadata

# --------------------------------------------------------------------------- #
# Format matrix
# --------------------------------------------------------------------------- #

# Audio containers discovered by extension for a folder add (§3). Each file is
# still probed by the caller, so a mislabeled/corrupt file fails that job alone.
AUDIO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".oga",
    ".opus",
    ".m4a",
    ".m4b",
    ".aac",
    ".wma",
    ".aiff",
    ".aif",
    ".alac",
    ".ape",
    ".wv",
    ".mka",
    ".amr",
    ".3gp",
    ".caf",
})

# Video containers whose audio track can be extracted (-map 0:a). Kept separate
# so the UI can label an "Extract audio from video" path (§3).
VIDEO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp4",
    ".m4v",
    ".mkv",
    ".mov",
    ".webm",
    ".avi",
    ".flv",
    ".wmv",
})

# All input extensions the converter recognizes for a folder scan.
INPUT_EXTENSIONS: frozenset[str] = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

# ``sample_fmt`` values offered for PCM (WAV) / FLAC bit depth (§6).
_BIT_DEPTH_SAMPLE_FMT: dict[int, str] = {16: "s16", 24: "s32", 32: "s32"}
# WAV encodes by bit depth (24-bit PCM WAV is pcm_s24le, not a sample_fmt of a
# generic encoder). FLAC takes -sample_fmt; WAV takes an explicit pcm codec.
_WAV_PCM_CODEC: dict[int, str] = {16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_s32le"}

# Output formats beyond the speech ENCODE_FORMATS (§3 "extensions to add"). Each
# is (codec, default extra args, muxer) like ENCODE_FORMATS. ``wav`` is handled
# specially (bit-depth-driven pcm codec) and is always available (no encoder
# probe needed). The capability probe hides any whose encoder is absent.
_EXTRA_ENCODE_FORMATS: dict[str, tuple[str, list[str], str]] = {
    "wav": ("pcm_s16le", [], ""),
    "aac": ("aac", ["-b:a", "192k"], "adts"),
    "aiff": ("pcm_s16le", [], "aiff"),
    "alac": ("alac", [], "ipod"),
    "wma": ("wmav2", ["-b:a", "192k"], "asf"),
    "caf": ("pcm_s16le", [], "caf"),
}

#: Every output format id the converter knows (subject to the runtime probe).
ALL_OUTPUT_FORMATS: dict[str, tuple[str, list[str], str]] = {
    **ENCODE_FORMATS,
    **_EXTRA_ENCODE_FORMATS,
}

# ffmpeg encoder name that must be present for a format id (probed via
# ``ffmpeg -encoders``). WAV/AIFF/CAF ride on always-present pcm encoders.
_FORMAT_REQUIRED_ENCODER: dict[str, str] = {
    fmt: codec for fmt, (codec, _extra, _mux) in ALL_OUTPUT_FORMATS.items()
}


class OnExisting(StrEnum):
    """What to do when an output path already exists (§4.2)."""

    RENAME = "rename"  # auto-number (default; never destroys an original)
    SKIP = "skip"
    OVERWRITE = "overwrite"


class Channels(StrEnum):
    """Channel layout for the output (§5 Advanced)."""

    KEEP = "keep"
    MONO = "mono"
    STEREO = "stereo"
    LEFT = "left"  # keep only the left channel, as mono
    RIGHT = "right"


# --------------------------------------------------------------------------- #
# Conversion spec + job
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class ConversionSpec:
    """A resolved "how to convert" recipe, independent of any particular file.

    v1 covers format + quality (CBR bitrate or VBR quality / FLAC level), sample
    rate, channels and bit depth, plus a copy/remux fast path and metadata. The
    DSP toggles (v2) are carried as an opaque, ordered list of ``-af`` filter
    strings so the command builder can compose them without this core module
    depending on the individual filter builders.
    """

    fmt: str = "mp3"
    # CBR bitrate in kbps (e.g. 192). None -> use VBR / the format default.
    bitrate_kbps: int | None = None
    # VBR quality for mp3/ogg (ffmpeg -q:a). Ignored when bitrate_kbps is set.
    vbr_quality: str = MP3_VBR_QUALITY
    # Output sample rate (-ar). None -> keep the source rate.
    sample_rate: int | None = None
    channels: Channels = Channels.KEEP
    # 16 / 24 / 32-bit for wav/flac. None -> encoder default.
    bit_depth: int | None = None
    # Stream-copy (no re-encode) into a new container when codecs are compatible.
    copy_audio: bool = False
    # Extract the audio track of a video input (-map 0:a). Auto-set by plan_jobs
    # for video sources; harmless for audio inputs.
    extract_from_video: bool = False
    # Ordered ffmpeg -af filter fragments (v2 DSP); empty in v1.
    filters: tuple[str, ...] = ()
    metadata: AudioMetadata | None = None

    def output_extension(self) -> str:
        """The file extension (with dot) for this spec's format."""
        return _OUTPUT_EXTENSION.get(self.fmt.strip().lower(), "." + self.fmt.strip().lower())


# Output file extension per format id (m4b/m4a/alac all ride .m4a-ish containers).
_OUTPUT_EXTENSION: dict[str, str] = {
    "mp3": ".mp3",
    "ogg": ".ogg",
    "opus": ".opus",
    "flac": ".flac",
    "m4a": ".m4a",
    "m4b": ".m4b",
    "wav": ".wav",
    "aac": ".aac",
    "aiff": ".aiff",
    "alac": ".m4a",
    "wma": ".wma",
    "caf": ".caf",
}


@dataclass(frozen=True, slots=True)
class ConversionJob:
    """One planned conversion: read ``source``, write ``dest`` using ``spec``."""

    source: Path
    dest: Path
    spec: ConversionSpec


# --------------------------------------------------------------------------- #
# Capability probe
# --------------------------------------------------------------------------- #

_ENCODER_CACHE: dict[str, frozenset[str]] = {}


def _probe_encoders(ffmpeg: str, runner: Callable[..., object] | None = None) -> frozenset[str]:
    """Return the set of encoder names ``ffmpeg`` reports (cached per binary)."""
    cached = _ENCODER_CACHE.get(ffmpeg)
    if cached is not None:
        return cached
    run = runner if runner is not None else _default_probe_runner
    try:
        result = run([ffmpeg, "-hide_banner", "-encoders"])
        text = str(getattr(result, "stdout", "") or "")
    except Exception:  # noqa: BLE001 - a probe failure means "assume nothing extra"
        text = ""
    names = parse_encoder_names(text)
    _ENCODER_CACHE[ffmpeg] = names
    return names


def parse_encoder_names(encoders_output: str) -> frozenset[str]:
    """Parse ``ffmpeg -encoders`` output into a set of encoder names (pure).

    Each listed line looks like `` A..... libmp3lame  MP3 (MPEG audio layer 3)``:
    a flags column, the encoder name, then a description. We take the second
    whitespace token of any line whose first token is all flag characters.
    """
    names: set[str] = set()
    past_legend = False
    for raw in encoders_output.splitlines():
        line = raw.strip()
        if line and set(line) <= {"-"}:
            # The ``------`` rule separates the flag legend from the real list.
            past_legend = True
            continue
        if not past_legend or not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        flags, name = parts[0], parts[1]
        # A real encoder line: a >=2-char flag column whose first char is the
        # stream type (V/A/S), and an identifier name (skips the '= Audio' legend).
        if len(flags) >= 2 and flags[0] in "VAS" and all(c in ".VASFXBDEILT" for c in flags):
            if name[:1].isalnum():
                names.add(name)
    return frozenset(names)


def available_output_formats(
    ffmpeg: str | None, runner: Callable[..., object] | None = None
) -> list[str]:
    """Output format ids the resolved ffmpeg can actually encode (§3).

    WAV/AIFF/CAF (pcm) are always offered. The rest are advertised only when
    their required encoder appears in ``ffmpeg -encoders`` so the UI never offers
    a format that would fail mid-run. Returns ids in a stable, friendly order.
    """
    order = ["mp3", "m4a", "m4b", "opus", "ogg", "flac", "wav", "aac", "aiff", "alac", "wma", "caf"]
    if not ffmpeg:
        return ["wav"]  # no ffmpeg: only the always-present pcm path is offered
    encoders = _probe_encoders(ffmpeg, runner)
    always = {"wav", "aiff", "caf"}  # pcm muxers/encoders ship with every build
    out: list[str] = []
    for fmt in order:
        if fmt in always or _FORMAT_REQUIRED_ENCODER.get(fmt, "") in encoders:
            out.append(fmt)
    return out


def clear_probe_cache() -> None:
    """Drop the cached encoder probe (e.g. after an ffmpeg update)."""
    _ENCODER_CACHE.clear()


# --------------------------------------------------------------------------- #
# Planning: mixed file/folder queue -> jobs
# --------------------------------------------------------------------------- #


def discover_inputs(
    entry: Path,
    *,
    recurse: bool,
    extensions: frozenset[str] | None = None,
    include_glob: str = "",
    exclude_glob: str = "",
    max_file_bytes: int = 0,
) -> list[Path]:
    """Expand one queue *entry* (a file or a folder) into matching input files.

    A file is returned as-is (extension-filtered); a folder is scanned (recursive
    when *recurse*), honoring the extension set and optional include/exclude
    globs and a per-file size cap. Pure filesystem read; never writes.
    """
    exts = extensions if extensions is not None else INPUT_EXTENSIONS

    def accept(path: Path) -> bool:
        if path.suffix.lower() not in exts:
            return False
        if include_glob and not path.match(include_glob):
            return False
        if exclude_glob and path.match(exclude_glob):
            return False
        if max_file_bytes > 0:
            try:
                if path.stat().st_size > max_file_bytes:
                    return False
            except OSError:
                return False
        return True

    if entry.is_file():
        return [entry] if accept(entry) else []
    if entry.is_dir():
        globber = entry.rglob("*") if recurse else entry.glob("*")
        return sorted(p for p in globber if p.is_file() and accept(p))
    return []


def _output_path(
    source: Path,
    root: Path | None,
    dest_dir: Path,
    spec: ConversionSpec,
    *,
    flatten: bool,
    filename_template: str,
    index0: int,
    total: int,
) -> Path:
    """Compute the destination path for *source* (mirror or flatten under dest)."""
    stem = source.stem
    name = (
        filename_template.format(stem=stem, index=index0 + 1, index0=index0, total=total).strip()
        or stem
    )
    filename = name + spec.output_extension()
    if flatten or root is None:
        return dest_dir / filename
    # Mirror the source tree under dest_dir, relative to the folder that was added.
    try:
        rel_parent = source.parent.relative_to(root)
    except ValueError:
        rel_parent = Path()
    return dest_dir / rel_parent / filename


def _resolve_conflict(path: Path, on_existing: OnExisting, planned: set[Path]) -> Path | None:
    """Apply the existing-file policy; None means "skip this job".

    Collisions are checked against both on-disk files and paths already planned
    in this batch, so two sources that would map to one name never clobber.
    """

    def taken(p: Path) -> bool:
        return p in planned or p.exists()

    if not taken(path):
        return path
    if on_existing is OnExisting.OVERWRITE:
        return path
    if on_existing is OnExisting.SKIP:
        return None
    # RENAME: append " (n)" until free.
    stem, suffix, parent = path.stem, path.suffix, path.parent
    for n in range(1, 10000):
        candidate = parent / f"{stem} ({n}){suffix}"
        if not taken(candidate):
            return candidate
    return None


def plan_jobs(
    queue: Sequence[tuple[Path, Path | None]],
    dest_dir: Path,
    spec: ConversionSpec,
    *,
    recurse: bool = False,
    extensions: frozenset[str] | None = None,
    include_glob: str = "",
    exclude_glob: str = "",
    flatten: bool = False,
    filename_template: str = "{stem}",
    on_existing: OnExisting = OnExisting.RENAME,
    max_file_bytes: int = 0,
) -> tuple[list[ConversionJob], list[Path]]:
    """Plan the full job list from a mixed queue of files and folders (§9.1).

    ``queue`` is a list of ``(entry, root)`` where *entry* is a file or folder
    and *root* is the folder originally added (for source-tree mirroring), or
    ``None`` for an individually-added file. Returns ``(jobs, skipped)`` — jobs
    ready to run and the input paths dropped by the conflict policy. De-duplicates
    inputs so an overlapping folder+file or a file added twice is planned once.
    This is also the dry-run: no bytes are touched.
    """
    # 1. Expand + de-dup inputs, remembering each input's mirror root.
    seen: set[Path] = set()
    inputs: list[tuple[Path, Path | None]] = []
    for entry, root in queue:
        for src in discover_inputs(
            entry,
            recurse=recurse,
            extensions=extensions,
            include_glob=include_glob,
            exclude_glob=exclude_glob,
            max_file_bytes=max_file_bytes,
        ):
            resolved = src.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            inputs.append((src, root))

    # 2. Map each input to an output path under the conflict policy.
    jobs: list[ConversionJob] = []
    skipped: list[Path] = []
    planned: set[Path] = set()
    total = len(inputs)
    for index0, (src, root) in enumerate(inputs):
        job_spec = spec
        if src.suffix.lower() in VIDEO_EXTENSIONS and not spec.extract_from_video:
            job_spec = replace(spec, extract_from_video=True)
        out = _output_path(
            src,
            root,
            dest_dir,
            job_spec,
            flatten=flatten,
            filename_template=filename_template,
            index0=index0,
            total=total,
        )
        resolved_out = _resolve_conflict(out, on_existing, planned)
        if resolved_out is None:
            skipped.append(src)
            continue
        planned.add(resolved_out)
        jobs.append(ConversionJob(source=src, dest=resolved_out, spec=job_spec))
    return jobs, skipped


def default_destination(source_root: Path) -> Path:
    """The default output folder: a ``Converted/`` sibling of the source (§4.2)."""
    base = source_root if source_root.is_dir() else source_root.parent
    return base / "Converted"


# --------------------------------------------------------------------------- #
# Command building
# --------------------------------------------------------------------------- #


def build_convert_command(
    ffmpeg: str, job: ConversionJob, *, out_path: Path | None = None
) -> list[str]:
    """Compose the ffmpeg argv that converts ``job.source`` -> ``out_path`` (§9.1).

    Reuses :data:`ALL_OUTPUT_FORMATS` for the codec/muxer base and layers the
    converter's own bitrate / sample-rate / channel / bit-depth / DSP options.
    ``out_path`` overrides ``job.dest`` so the runner can encode to a temp file
    and move it into place (atomic, never a truncated output). Pure — safe to
    hand to a subprocess: all paths are controlled and ffmpeg is caller-resolved.
    """
    spec = job.spec
    fmt = spec.fmt.strip().lower()
    profile = ALL_OUTPUT_FORMATS.get(fmt)
    if profile is None:
        raise ValueError(f"Unsupported output format: {spec.fmt!r}")
    target = out_path if out_path is not None else job.dest

    args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(job.source)]

    # Select only the audio track (drops any video); for a video source this is
    # the "extract audio" path, for an audio source it is a harmless no-op.
    args += ["-map", "0:a:0?"] if spec.extract_from_video else ["-vn"]

    if spec.copy_audio:
        # Stream-copy fast path: no codec/filter/rate options apply.
        args += ["-c:a", "copy"]
    else:
        codec, extra, muxer = profile
        # WAV/AIFF/CAF bit depth selects the concrete pcm codec.
        if fmt in ("wav", "aiff", "caf") and spec.bit_depth in _WAV_PCM_CODEC:
            codec = _WAV_PCM_CODEC[spec.bit_depth]
        args += ["-c:a", codec]

        # Quality: explicit CBR bitrate wins; else VBR for mp3/ogg; else the
        # format's own default extra args.
        if spec.bitrate_kbps and fmt not in ("wav", "flac", "aiff", "caf"):
            args += ["-b:a", f"{int(spec.bitrate_kbps)}k"]
        elif fmt == "mp3":
            args += ["-q:a", str(spec.vbr_quality)]
        else:
            args += extra

        # FLAC bit depth via sample_fmt (WAV handled by the pcm codec above).
        if fmt == "flac" and spec.bit_depth in _BIT_DEPTH_SAMPLE_FMT:
            args += ["-sample_fmt", _BIT_DEPTH_SAMPLE_FMT[spec.bit_depth]]

        filters = list(spec.filters)
        chan = _channel_filter(spec.channels)
        if chan:
            filters.append(chan)
        if filters:
            args += ["-af", ",".join(filters)]

        # -ac only when a fixed count is wanted and no channel filter already set
        # the layout (mono/left/right imply 1 channel via the filter).
        if spec.channels is Channels.STEREO:
            args += ["-ac", "2"]

        if spec.sample_rate:
            args += ["-ar", str(int(spec.sample_rate))]

        if muxer:
            args += ["-f", muxer]

    if spec.metadata is not None:
        args += spec.metadata.ffmpeg_args()

    args += ["-y", str(target)]
    return args


def _channel_filter(channels: Channels) -> str:
    """The ``pan``/downmix -af fragment for a channel choice (empty for Keep)."""
    if channels is Channels.MONO:
        return "pan=mono|c0=0.5*c0+0.5*c1"
    if channels is Channels.LEFT:
        return "pan=mono|c0=c0"
    if channels is Channels.RIGHT:
        return "pan=mono|c0=c1"
    return ""  # KEEP / STEREO handled by -ac (or nothing)


# --------------------------------------------------------------------------- #
# Batch runner (multi-worker, cancellable)
# --------------------------------------------------------------------------- #


@dataclass(slots=True)
class JobResult:
    """The outcome of one conversion."""

    job: ConversionJob
    ok: bool
    error: str = ""
    skipped: bool = False


@dataclass(slots=True)
class BatchResult:
    """Aggregate outcome of a conversion batch."""

    results: list[JobResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def converted(self) -> int:
        return sum(1 for r in self.results if r.ok and not r.skipped)

    @property
    def failed(self) -> list[JobResult]:
        return [r for r in self.results if not r.ok and not r.skipped]

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.skipped)

    def summary(self, total: int) -> str:
        """A speakable one-line summary (§10) — names failures, never silent."""
        parts = [f"Converted {self.converted} of {total} files"]
        if self.skipped:
            parts.append(f"{self.skipped} skipped")
        fails = self.failed
        if fails:
            names = ", ".join(r.job.source.name for r in fails[:3])
            more = "" if len(fails) <= 3 else f" (+{len(fails) - 3} more)"
            parts.append(f"{len(fails)} failed: {names}{more}")
        if self.cancelled:
            parts.append("cancelled")
        return ". ".join(parts) + "."


# A single-job runner: (ffmpeg, job) -> JobResult. Injectable for tests; the
# default one shells out through safe_subprocess with a temp-then-move write.
SingleJobRunner = Callable[[str, ConversionJob], JobResult]

ProgressCallback = Callable[[int, int, ConversionJob], None]  # (done, total, current)


def run_conversion_batch(
    ffmpeg: str,
    jobs: Sequence[ConversionJob],
    *,
    workers: int = 0,
    on_progress: ProgressCallback | None = None,
    cancel: CancelToken | None = None,
    single_runner: SingleJobRunner | None = None,
) -> BatchResult:
    """Convert ``jobs`` across up to ``workers`` threads, reporting progress (§8).

    ``workers`` <= 0 auto-picks ``max(1, cpu-1)``. Cancellation is cooperative:
    ``cancel`` is checked before each job is dispatched, so any in-flight encode
    finishes cleanly and the remainder are marked skipped. Pure of ``wx`` and of
    any UI, so both the dialog and a headless caller reuse it; ``single_runner``
    is injectable so the fan-out is unit-testable without spawning ffmpeg.
    """
    from concurrent.futures import ThreadPoolExecutor

    runner = single_runner if single_runner is not None else _default_single_runner
    token = cancel if cancel is not None else CancelToken()
    n_workers = workers if workers > 0 else max(1, (os.cpu_count() or 2) - 1)
    total = len(jobs)
    result = BatchResult()
    done = 0

    if total == 0:
        return result

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = []
        for job in jobs:
            if token.is_cancelled():
                result.results.append(JobResult(job=job, ok=False, skipped=True))
                continue
            futures.append((job, pool.submit(_guarded_run, runner, ffmpeg, job)))
        for job, fut in futures:
            job_result = fut.result()
            result.results.append(job_result)
            done += 1
            if on_progress is not None:
                on_progress(done, total, job)
    result.cancelled = token.is_cancelled()
    return result


def _guarded_run(runner: SingleJobRunner, ffmpeg: str, job: ConversionJob) -> JobResult:
    try:
        return runner(ffmpeg, job)
    except Exception as exc:  # noqa: BLE001 - one bad file must never sink the batch
        return JobResult(job=job, ok=False, error=str(exc))


class CancelToken:
    """A thread-safe cooperative cancel flag (a thin ``threading.Event`` wrapper)."""

    def __init__(self) -> None:
        import threading

        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


# --------------------------------------------------------------------------- #
# Default runners (thin subprocess shells; not unit-tested directly)
# --------------------------------------------------------------------------- #


def _default_probe_runner(command: Sequence[str]) -> object:
    from quill.stability.safe_subprocess import run_subprocess_safely

    return run_subprocess_safely(list(command), timeout_seconds=30.0)


def _default_single_runner(ffmpeg: str, job: ConversionJob) -> JobResult:
    """Encode one job to a temp file, then move it into place (atomic, safe)."""
    import shutil
    import tempfile

    if not job.source.is_file():
        return JobResult(job=job, ok=False, error="input file not found")
    from quill.stability.safe_subprocess import run_subprocess_safely

    job.dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".convert-", suffix=job.dest.suffix, dir=str(job.dest.parent)
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        command = build_convert_command(ffmpeg, job, out_path=tmp_path)
        completed = run_subprocess_safely(command, timeout_seconds=3600.0)
        if int(getattr(completed, "returncode", 1)) != 0:
            detail = str(getattr(completed, "stderr", "") or "").strip()[-300:]
            tmp_path.unlink(missing_ok=True)
            return JobResult(job=job, ok=False, error=detail or "ffmpeg failed")
        shutil.move(str(tmp_path), str(job.dest))
        return JobResult(job=job, ok=True)
    except Exception as exc:  # noqa: BLE001 - clean up the temp, report the reason
        tmp_path.unlink(missing_ok=True)
        return JobResult(job=job, ok=False, error=str(exc))


def default_worker_count() -> int:
    """A sensible default worker count: one per core, minus one for the UI (§8)."""
    return max(1, (os.cpu_count() or 2) - 1)


def queue_from_paths(paths: Iterable[Path]) -> list[tuple[Path, Path | None]]:
    """Build a plan_jobs queue from bare paths (files as-is, folders as roots)."""
    out: list[tuple[Path, Path | None]] = []
    for p in paths:
        out.append((p, p if p.is_dir() else None))
    return out
