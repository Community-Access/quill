"""Quill Converter's Auphonic work: what may be sent, how, and what is remembered.

The planning half of Process with Auphonic
(``docs/planning/QUILL-Converter-Auphonic-Integration-PRD.md``): which queued
files are eligible and why the others are not, the choices a person makes
(separate productions or one multitrack production, a preset, Quick cleanup,
an output format), the JSON body those choices become, the one confirmation
text that names everything before anything is uploaded, and the minimal record
of a production Auphonic has accepted, so it can be resumed after the app
closes. The lifecycle that acts on a plan is :mod:`quill.core.publish.auphonic_run`.

Nothing here touches the network or wx. Pure apart from reading file sizes and
the small pending-work file.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from quill.core.publish.auphonic import OUTPUT_FORMATS

#: The sound files Auphonic takes as input and QUILL can name with confidence.
#: Everything else in the Converter's queue is skipped and named before the
#: confirmation, with a suggestion to convert it to WAV or FLAC first.
ACCEPTED_EXTENSIONS: frozenset[str] = frozenset({
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".oga",
    ".opus",
    ".m4a",
    ".m4b",
    ".aac",
    ".aif",
    ".aiff",
})
#: Auphonic mixes a multitrack production from at least two tracks.
MIN_TRACKS = 2

SEPARATE = "separate"
MULTITRACK = "multitrack"
#: Processing modes: the preset as it is, or Quick cleanup's three switches.
USE_PRESET = "preset"
QUICK_CLEANUP = "cleanup"

#: The pending-work file in the Converter's data folder.
PENDING_FILE = "auphonic_pending.json"
PENDING_SCHEMA = 1


@dataclass(frozen=True, slots=True)
class AuphonicChoices:
    """What the Process with Auphonic window says."""

    mode: str = SEPARATE
    preset_uuid: str = ""  # "" is the account's default preset
    preset_label: str = ""
    processing: str = USE_PRESET
    denoise: bool = False
    output_format: str = ""  # "" keeps the preset's outputs
    title: str = ""  # the multitrack production's title


@dataclass(frozen=True, slots=True)
class Skipped:
    """A queued item that will not be sent, and the reason in words."""

    path: Path
    reason: str


@dataclass(frozen=True, slots=True)
class SourceDetails:
    """What a separate production passes through from its source file."""

    title: str = ""
    artist: str = ""
    album: str = ""
    chapters: tuple[tuple[float, str], ...] = ()


@dataclass(slots=True)
class PendingProduction:
    """The minimum kept about a production Auphonic has accepted.

    Never the token, never the media: the production's id, how it was sent,
    the names to report, the preset's label, and where its results go.
    """

    uuid: str
    mode: str
    title: str
    inputs: list[str]
    preset_label: str
    out_dir: str
    started: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M"))

    def describe(self) -> str:
        count = len(self.inputs)
        what = "multitrack production" if self.mode == MULTITRACK else "production"
        files = f"{count} file" if count == 1 else f"{count} files"
        return f"{self.title}: {what} of {files}, sent {self.started}, saves to {self.out_dir}"


# -- eligibility ----------------------------------------------------------------


def check_inputs(
    paths: Iterable[Path], *, has_video: Callable[[Path], bool] | None = None
) -> tuple[list[Path], list[Skipped]]:
    """Split *paths* into the files that may be sent and the ones that may not.

    Order is kept (it is the multitrack track order) and a repeated file is
    sent once. *has_video* answers whether a file carries a moving picture --
    a cover image is not one -- and is skipped when it cannot be asked.
    """
    from quill.core.audio.formats import VIDEO_EXTENSIONS

    eligible: list[Path] = []
    skipped: list[Skipped] = []
    seen: set[Path] = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        suffix = path.suffix.lower()
        if path.is_dir():
            reason = "it is a folder; add the sound files themselves"
        elif not path.is_file():
            reason = "the file is no longer there"
        elif suffix in VIDEO_EXTENSIONS:
            reason = "it is a video file, and this sends sound only"
        elif suffix not in ACCEPTED_EXTENSIONS:
            kind = f"{suffix} files" if suffix else "files without an extension"
            reason = f"this does not send {kind}; convert it to WAV or FLAC first"
        elif _size(path) == 0:
            reason = "the file is empty"
        elif not _readable(path):
            reason = "the file could not be read"
        elif has_video is not None and has_video(path):
            reason = "it holds a video picture, and this sends sound only"
        else:
            eligible.append(path)
            continue
        skipped.append(Skipped(path, reason))
    return eligible, skipped


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _readable(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            handle.read(1)
    except OSError:
        return False
    return True


def problem(choices: AuphonicChoices, eligible: list[Path]) -> str:
    """Why these choices cannot be sent, in words; ``""`` when they can."""
    if not eligible:
        return "None of the queued files can be sent to Auphonic."
    if choices.mode == MULTITRACK:
        if len(eligible) < MIN_TRACKS:
            return (
                f"A multitrack production needs at least {MIN_TRACKS} sound files, one per "
                f"track, and only {len(eligible)} can be sent."
            )
        if not choices.title.strip():
            return "Give the multitrack production a title."
    if choices.output_format and choices.output_format not in OUTPUT_FORMATS:
        return "Choose an output format from the list."
    return ""


# -- what is sent -----------------------------------------------------------------


def track_ids(paths: list[Path]) -> list[str]:
    """One track name per file: its name without the extension, made unique.

    The name is also the upload's form-field name, so quotes and line breaks
    are taken out.
    """
    ids: list[str] = []
    for path in paths:
        base = re.sub(r'[\r\n"\\]', " ", path.stem).strip() or "Track"
        name, number = base, 2
        while name in ids:
            name, number = f"{base} ({number})", number + 1
        ids.append(name)
    return ids


def _clock(seconds: float) -> str:
    whole = max(0.0, seconds)
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{secs:06.3f}"


def production_body(
    choices: AuphonicChoices,
    *,
    title: str,
    details: SourceDetails | None = None,
    tracks: list[str] | None = None,
) -> dict[str, object]:
    """The JSON API body for one production.

    A separate production carries its source's title, artist, album and
    chapter marks (*details*); a multitrack production carries only its title,
    because tags from separate tracks are never merged.
    """
    metadata: dict[str, str] = {"title": title}
    body: dict[str, object] = {"metadata": metadata}
    if choices.preset_uuid:
        body["preset"] = choices.preset_uuid
    if details is not None and tracks is None:
        if details.artist:
            metadata["artist"] = details.artist
        if details.album:
            metadata["album"] = details.album
        if details.chapters:
            body["chapters"] = [
                {"start": _clock(start), "title": name} for start, name in details.chapters
            ]
    cleanup = choices.processing == QUICK_CLEANUP
    if tracks is None:
        if cleanup:
            body["algorithms"] = {
                "filtering": True,
                "leveler": True,
                "normloudness": True,
                "denoise": bool(choices.denoise),
            }
    else:
        body["is_multitrack"] = True
        entries: list[dict[str, object]] = []
        for track in tracks:
            entry: dict[str, object] = {"type": "multitrack", "id": track}
            if cleanup:
                entry["algorithms"] = {"filtering": True, "denoise": bool(choices.denoise)}
            entries.append(entry)
        body["multi_input_files"] = entries
        if cleanup:
            body["algorithms"] = {"leveler": True, "normloudness": True}
    if choices.output_format:
        body["output_files"] = [{"format": choices.output_format}]
    return body


def folder_name(name: str) -> str:
    """*name* as one safe folder name (never a path, never empty)."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(". ")
    return cleaned[:120] or "Auphonic"


def result_folder(dest: Path, name: str) -> Path:
    """Where one production's results go: a folder named *name* inside *dest*."""
    return dest / folder_name(name)


# -- the confirmation -----------------------------------------------------------------


def describe_processing(choices: AuphonicChoices) -> str:
    """The processing, noise and format choices in one plain sentence."""
    if choices.processing == QUICK_CLEANUP:
        noise = "background noise reduced" if choices.denoise else "background noise left as it is"
        processing = (
            "Quick cleanup, which replaces the preset's own processing: filtering, "
            f"even levels and standard loudness, {noise}"
        )
    else:
        processing = "the preset's own processing, unchanged"
    if choices.output_format:
        label = OUTPUT_FORMATS.get(choices.output_format, choices.output_format)
        output = f"saved as {label} instead of the preset's outputs"
    else:
        output = "saved in the formats the preset chooses"
    return f"Processing: {processing}. Results: {output}."


def confirmation_text(
    choices: AuphonicChoices,
    eligible: list[Path],
    skipped: list[Skipped],
    dest: Path,
    *,
    account: str = "",
) -> str:
    """Everything that will happen, before anything is uploaded."""
    preset = choices.preset_label or "your account's default preset"
    count = len(eligible)
    lines = [
        "These files will be uploaded to Auphonic, an online service, and processed "
        "using your own Auphonic account and its credits"
        + (f" ({account})." if account else ".")
        + " Auphonic's own terms decide how long it keeps them.",
        "",
    ]
    if choices.mode == MULTITRACK:
        lines.append(
            f"One multitrack production called {choices.title.strip()}, "
            f"with {count} tracks in this order:"
        )
        lines += [f"  Track {n}: {name}" for n, name in enumerate(track_ids(eligible), 1)]
        folder = result_folder(dest, choices.title.strip())
        where = f"The final mix is saved in {folder}."
    else:
        noun = "production" if count == 1 else "productions"
        lines.append(f"{count} separate {noun}, one for each file, sent one at a time:")
        lines += [f"  {path.name}" for path in eligible]
        where = f"Each file's results are saved in a folder named after it, inside {dest}."
    lines += ["", f"Preset: {preset}.", describe_processing(choices), where]
    lines.append("Your original files are not changed, and no existing file is replaced.")
    if skipped:
        lines += ["", f"Not sent ({len(skipped)}):"]
        lines += [f"  {item.path.name}: {item.reason}." for item in skipped]
    return "\n".join(lines)


# -- pending work ------------------------------------------------------------------------


def pending_path(data_dir: Path | None = None) -> Path:
    if data_dir is None:
        from quill.core.paths import app_data_dir

        data_dir = app_data_dir()
    return data_dir / "converter" / PENDING_FILE


def load_pending(path: Path) -> list[PendingProduction]:
    """The productions waiting to be fetched (read forgivingly; never the network)."""
    from quill.core.storage import read_json

    data = read_json(path, {})
    rows = data.get("pending") if isinstance(data, dict) else None
    records: list[PendingProduction] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not isinstance(row.get("uuid"), str):
            continue
        inputs = row.get("inputs")
        records.append(
            PendingProduction(
                uuid=str(row["uuid"]),
                mode=str(row.get("mode", SEPARATE)),
                title=str(row.get("title", "")),
                inputs=[str(x) for x in inputs] if isinstance(inputs, list) else [],
                preset_label=str(row.get("preset_label", "")),
                out_dir=str(row.get("out_dir", "")),
                started=str(row.get("started", "")),
            )
        )
    return records


def save_pending(path: Path, records: list[PendingProduction]) -> None:
    """Write the pending list atomically; with nothing pending, remove the file."""
    from quill.core.storage import write_json_atomic

    if not records:
        path.unlink(missing_ok=True)
        return
    write_json_atomic(
        path, {"schema": PENDING_SCHEMA, "pending": [asdict(record) for record in records]}
    )


def add_pending(path: Path, record: PendingProduction) -> None:
    records = [r for r in load_pending(path) if r.uuid != record.uuid]
    save_pending(path, [*records, record])


def remove_pending(path: Path, production_uuid: str) -> None:
    records = load_pending(path)
    kept = [r for r in records if r.uuid != production_uuid]
    if len(kept) != len(records):
        save_pending(path, kept)
