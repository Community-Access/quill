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

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path

from quill.core.audio.exact_optilab import ExactOptilab
from quill.core.audio.formats import (
    AUDIO_EXTENSIONS,
    AUDIO_OUTPUT_FORMATS,
    FIXED_BITRATE_FORMATS,
    INPUT_EXTENSIONS,
    LOSSLESS_FORMATS,
    MONO_ONLY_FORMATS,
    OUTPUT_ORDER,
    PCM_CODECS,
    VIDEO_EXTENSIONS,
    VIDEO_OUTPUT_FORMATS,
    VideoQuality,
    fit_sample_rate,
    is_video_format,
    output_extension,
    parse_encoder_names,
    required_encoders,
    video_scale_filter,
)
from quill.core.speech.ffmpeg import MP3_VBR_QUALITY, AudioMetadata

# The format matrix -- inputs, outputs, and the constraints each output
# imposes -- lives in quill.core.audio.formats (extracted 2026-09-27, GATE-11)
# and is re-exported here under the names callers have always imported.

# ``sample_fmt`` values offered for FLAC bit depth (§6).
_BIT_DEPTH_SAMPLE_FMT: dict[int, str] = {16: "s16", 24: "s32", 32: "s32"}

#: Every audio output format id (the historical name for the audio table).
ALL_OUTPUT_FORMATS: dict[str, tuple[str, list[str], str]] = AUDIO_OUTPUT_FORMATS


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
    # Optional pass through the *real* OptiLab Core engine instead of an ffmpeg
    # approximation of it (quill/core/audio/exact_optilab.py). ``None`` -- the
    # default -- converts exactly as before. It is not an ``-af`` filter and
    # cannot be one: the engine is a separate process the audio is piped
    # through, so ``build_convert_command`` describes only the encode half and
    # the runner wires up the pipeline.
    exact_optilab: ExactOptilab | None = None
    # Video outputs (formats.VIDEO_OUTPUT_FORMATS): how hard the encode works to
    # keep detail, an optional height cap (720 -> "up to 720p"), and a remux
    # fast path that copies every stream into the new container untouched.
    video_quality: VideoQuality = VideoQuality.HIGH
    video_max_height: int | None = None
    copy_video: bool = False
    video_encoder: str = ""  # a graphics-card encoder (video_accel); "" = the processor
    # Copy caption tracks where the container keeps them (MKV); the runner
    # turns this off and retries when a caption format will not fit.
    keep_subtitles: bool = True
    # An explicit channel count, for sources whose layout FFmpeg cannot name.
    force_channels: int | None = None
    # Keep only part of each file: start at ``start_s`` seconds and stop at
    # ``end_s`` (0 = the end). Both 0 keeps the whole file.
    start_s: float = 0.0
    end_s: float = 0.0
    # Where chapters come from: see quill.core.audio.chapter_plan (keep, list,
    # pauses, every-N, none). The runner resolves it per file.
    chapter_source: str = "keep"

    def output_extension(self) -> str:
        """The file extension (with dot) for this spec's format."""
        return output_extension(self.fmt)

    def is_video(self) -> bool:
        """True when this spec writes a video file."""
        return is_video_format(self.fmt)


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


def available_output_formats(
    ffmpeg: str | None, runner: Callable[..., object] | None = None
) -> list[str]:
    """Output format ids the resolved ffmpeg can actually encode (§3).

    PCM formats (WAV, AIFF, CAF, AU, Wave64) are always offered. The rest --
    video included, which needs both its video and its audio encoder -- are
    advertised only when every encoder they need appears in
    ``ffmpeg -encoders``, so the UI never offers a format that would fail
    mid-run. Returns ids in :data:`OUTPUT_ORDER`.
    """
    if not ffmpeg:
        return ["wav"]  # no ffmpeg: only the always-present pcm path is offered
    encoders = _probe_encoders(ffmpeg, runner)
    return [fmt for fmt in OUTPUT_ORDER if all(name in encoders for name in required_encoders(fmt))]


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
        if spec.is_video() and src.suffix.lower() in AUDIO_EXTENSIONS:
            # A sound file has no picture to make a video from; it is reported
            # as skipped rather than failing half-way through the encode.
            skipped.append(src)
            continue
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
    ffmpeg: str,
    job: ConversionJob,
    *,
    out_path: Path | None = None,
    pcm_input: tuple[int, int] | None = None,
    chapters_meta: Path | None = None,
) -> list[str]:
    """Compose the ffmpeg argv that converts ``job.source`` -> ``out_path`` (§9.1).

    Audio formats come from :data:`ALL_OUTPUT_FORMATS`, video formats from
    :data:`VIDEO_OUTPUT_FORMATS`; both layer the spec's bitrate / sample-rate /
    channel / bit-depth / DSP options onto the audio. ``out_path`` overrides
    ``job.dest`` so the runner can encode to a temp file and move it into place
    (atomic, never a truncated output). Pure -- safe to hand to a subprocess:
    all paths are controlled and ffmpeg is caller-resolved.

    ``pcm_input`` -- ``(sample_rate, channels)`` -- replaces the file input with
    raw PCM on stdin: this is the *encode half* of an exact-OptiLab pass, where
    the source has already been decoded and processed by another two processes
    (see :mod:`quill.core.audio.exact_optilab`). The source's own ``-af`` filters
    and the video-extraction switch belong to the decode half and are dropped
    here, so nothing is applied twice.
    """
    spec = job.spec
    fmt = spec.fmt.strip().lower()
    video = VIDEO_OUTPUT_FORMATS.get(fmt)
    profile = ALL_OUTPUT_FORMATS.get(fmt)
    if profile is None and video is None:
        raise ValueError(f"Unsupported output format: {spec.fmt!r}")
    target = out_path if out_path is not None else job.dest

    args = [ffmpeg, "-hide_banner", "-loglevel", "error"]
    if pcm_input is not None:
        from quill.core.audio.exact_optilab import build_pcm_input_args

        args += build_pcm_input_args(pcm_input[0], pcm_input[1])
    else:
        args += _clip_args(spec)
        args += ["-i", str(job.source)]
        if chapters_meta is not None:  # chapters made for this file (FFMETADATA)
            args += ["-i", str(chapters_meta), "-map_chapters", "1"]
        elif spec.chapter_source == "none":
            args += ["-map_chapters", "-1"]
        if video is not None:
            # The picture (never an attached cover image, hence capital V),
            # every audio track the container can carry, and captions where
            # the container takes them.
            args += ["-map", "0:V:0"]
            args += ["-map", "0:a?"] if video.all_audio_tracks else ["-map", "0:a:0?"]
            if video.keep_subtitles and spec.keep_subtitles:
                args += ["-map", "0:s?", "-c:s", "copy"]
        else:
            # Select only the audio track (drops any video); for a video source
            # this is the "extract audio" path, for an audio source a no-op.
            # -vn/-sn/-dn as well: with no sound to map, FFmpeg would otherwise
            # fall back to copying whatever it found -- a video inside an .m4a.
            args += (["-map", "0:a:0?"] if spec.extract_from_video else []) + ["-vn", "-sn", "-dn"]

    if video is not None:
        args += _video_args(spec, video)
        if spec.copy_video:
            args += ["-f", video.muxer]
            return _finish(args, spec, target)
        codec, extra, muxer = video.audio_codec, list(video.audio_args), video.muxer
    elif spec.copy_audio:
        # Stream-copy fast path: no codec/filter/rate options apply.
        args += ["-c:a", "copy"]
        return _finish(args, spec, target)
    else:
        assert profile is not None
        codec, extra, muxer = profile
        pcm = PCM_CODECS.get(fmt)
        if pcm is not None:
            codec = pcm.get(spec.bit_depth, pcm[None])
    args += ["-c:a", codec]

    # Quality: explicit CBR bitrate wins where a bit rate means something;
    # else VBR for mp3; else the format's own default extra args.
    if spec.bitrate_kbps and fmt not in LOSSLESS_FORMATS | FIXED_BITRATE_FORMATS:
        args += ["-b:a", f"{int(spec.bitrate_kbps)}k"]
    elif fmt == "mp3":
        args += ["-q:a", str(spec.vbr_quality)]
    else:
        args += extra

    # FLAC bit depth via sample_fmt (the PCM formats chose a codec above).
    if fmt in ("flac", "mka") and spec.bit_depth in _BIT_DEPTH_SAMPLE_FMT:
        args += ["-sample_fmt", _BIT_DEPTH_SAMPLE_FMT[spec.bit_depth]]

    # With a PCM input the spec's own DSP filters have already run, in the
    # decode step, ahead of the OptiLab engine -- the same order the live
    # chain uses (everything else first, broadcast polish last). Only the
    # channel layout is left to do here.
    filters = [] if pcm_input is not None else list(spec.filters)
    channels = (
        Channels.MONO
        if fmt in MONO_ONLY_FORMATS and spec.channels in (Channels.KEEP, Channels.STEREO)
        else spec.channels
    )
    chan = _channel_filter(channels)
    if chan:
        filters.append(chan)
    if filters:
        args += ["-af", ",".join(filters)]

    # -ac only when a fixed count is wanted and no channel filter already set
    # the layout (mono/left/right imply 1 channel via the filter).
    if channels is Channels.STEREO:
        args += ["-ac", "2"]
    elif fmt in MONO_ONLY_FORMATS:
        args += ["-ac", "1"]
    elif spec.force_channels:
        args += ["-ac", str(int(spec.force_channels))]

    # A rate the format cannot take is moved to the nearest one it can; a video
    # format's sound follows the rules of the audio codec it carries.
    rules = _RATE_RULES_FOR_CODEC.get(video.audio_codec, fmt) if video is not None else fmt
    # loudnorm resamples to 192 kHz internally and hands that on; encoders that
    # do not list their rates (WMA) then refuse it, and FLAC would store it.
    wanted = spec.sample_rate or (48000 if any(f.startswith("loudnorm") for f in filters) else None)
    rate = fit_sample_rate(rules, wanted)
    if rate:
        args += ["-ar", str(int(rate))]

    if muxer:
        args += ["-f", muxer]
    return _finish(args, spec, target)


#: A video format's audio codec -> the audio format whose rate rules it obeys.
_RATE_RULES_FOR_CODEC: dict[str, str] = {"mp2": "mp2", "libopus": "opus"}


def _clip_args(spec: ConversionSpec) -> list[str]:
    """Input-side seek and length for "keep only part of each file"."""
    args: list[str] = []
    start = max(0.0, float(spec.start_s or 0.0))
    end = max(0.0, float(spec.end_s or 0.0))
    if start:
        args += ["-ss", f"{start:g}"]
    if end and end > start:
        args += ["-t", f"{end - start:g}"]
    return args


def _video_args(spec: ConversionSpec, video: object) -> list[str]:
    """The video-stream half of a video conversion (pure)."""
    from quill.core.audio.formats import VideoProfile
    from quill.core.audio.video_accel import video_codec_args

    assert isinstance(video, VideoProfile)
    if spec.copy_video:
        return ["-c", "copy"]
    encoder = spec.video_encoder or video.video_codec
    args = video_codec_args(video, spec.video_quality, encoder)
    scale = video_scale_filter(video.video_codec, spec.video_max_height)
    if scale:
        args += ["-vf", scale]
    return args


def _finish(args: list[str], spec: ConversionSpec, target: Path) -> list[str]:
    """Metadata, overwrite, and the output path: the end of every command."""
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


# --------------------------------------------------------------------------- #
# Default runners (thin subprocess shells; not unit-tested directly)
# --------------------------------------------------------------------------- #


def _default_probe_runner(command: Sequence[str]) -> object:
    from quill.stability.safe_subprocess import run_subprocess_safely

    return run_subprocess_safely(list(command), timeout_seconds=30.0)


def queue_from_paths(paths: Iterable[Path]) -> list[tuple[Path, Path | None]]:
    """Build a plan_jobs queue from bare paths (files as-is, folders as roots)."""
    out: list[tuple[Path, Path | None]] = []
    for p in paths:
        out.append((p, p if p.is_dir() else None))
    return out


# The batch runner (convert_batch, extracted 2026-09-28) and the per-file
# runners (convert_runner, 2026-09-27) left this module under GATE-11; they are
# imported last because they are built on it, and re-exported so callers keep
# importing from here.
from quill.core.audio.convert_batch import (  # noqa: E402
    CancelToken as CancelToken,
)
from quill.core.audio.convert_batch import (  # noqa: E402
    FileProgressCallback as FileProgressCallback,
)
from quill.core.audio.convert_batch import (  # noqa: E402
    ProgressCallback as ProgressCallback,
)
from quill.core.audio.convert_batch import (  # noqa: E402
    SingleJobRunner as SingleJobRunner,
)
from quill.core.audio.convert_batch import (  # noqa: E402
    default_worker_count as default_worker_count,
)
from quill.core.audio.convert_batch import (  # noqa: E402
    run_conversion_batch as run_conversion_batch,
)
from quill.core.audio.convert_runner import (  # noqa: E402
    _default_single_runner as _default_single_runner,
)
from quill.core.audio.convert_runner import (  # noqa: E402
    _exact_optilab_runner as _exact_optilab_runner,
)
