"""Watch action: rebuild a folder's audiobook when new audio arrives (WATCH-10).

Drop recordings into a watched folder and the folder's chaptered master is
rebuilt automatically — the ChapterForge watcher idea on QUILL's watch-action
seam. The action runs per arriving audio file but coalesces naturally: it
skips when the folder's master is already newer than the file that triggered
it, so a batch of dropped files produces one rebuild, not one per file.

The chapter plan is the standard scan (one chapter per file, natural order,
filename titles); tags fall back to the folder name. Runs on the watch worker
thread — everything here is wx-free.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from quill.core.watch_actions import WatchActionOutcome, WatchItem, _humanize_action_error

logger = logging.getLogger(__name__)

_FORMATS = ("m4b", "mp3")


def master_path(folder: Path, fmt: str) -> Path:
    """The folder's master file path (``<folder> - Master.<fmt>``)."""
    return folder / f"{folder.name} - Master.{fmt}"


@dataclass
class BuildAudiobookAction:
    """Built-in action: combine the arriving file's folder into one chaptered book."""

    action_id: str = "build_audiobook"
    label: str = "Build audiobook from the folder"
    required_feature_id: str = ""
    requires_consent: bool = False
    description: str = (
        "Rebuild the folder's chaptered audiobook whenever new audio arrives: "
        "each file becomes a chapter, in natural order, titled from its filename."
    )

    def describe(self) -> str:
        return self.description

    def validate(self, options: Mapping[str, object]) -> list[str]:
        fmt = str(options.get("format", "m4b")).strip().lower()
        if fmt not in _FORMATS:
            return [f"Choose an audiobook format of m4b or mp3 (got {fmt!r})."]
        return []

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:
        fmt = str(options.get("format", "m4b")).strip().lower()
        folder = item.source_path.parent
        return f"Rebuild {master_path(folder, fmt).name} from the audio in {folder.name}."

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        from quill.core.speech.audiobook import (
            AUDIO_EXTENSIONS,
            build_audiobook,
            build_chapter_list,
            find_cover,
            is_probable_master,
            scan_audio_folder,
        )
        from quill.core.speech.ffmpeg import AudioMetadata, TranscodeError

        problems = self.validate(options)
        if problems:
            return WatchActionOutcome.failed(problems[0])
        if item.source_path.suffix.lower() not in AUDIO_EXTENSIONS:
            return WatchActionOutcome.skipped(f"{item.source_path.name} is not audio.")
        fmt = str(options.get("format", "m4b")).strip().lower()
        folder = item.source_path.parent
        out = master_path(folder, fmt)
        # Coalesce: a batch of dropped files queues one action each; after the
        # first rebuild the master is newer than the rest, so they skip.
        try:
            if out.is_file() and out.stat().st_mtime >= item.source_path.stat().st_mtime:
                return WatchActionOutcome.skipped("The folder's audiobook is already current.")
        except OSError:
            pass
        sources = [
            p
            for p in scan_audio_folder(folder)
            if not is_probable_master(p.name, folder) and p.resolve() != out.resolve()
        ]
        if not sources:
            return WatchActionOutcome.skipped("No audio files to build from.")
        chapters = build_chapter_list(sources)
        metadata = AudioMetadata(album=folder.name)
        try:
            result = build_audiobook(
                chapters,
                out,
                output_format=fmt,
                metadata=metadata,
                cover=find_cover(folder),
                acx_normalize=bool(options.get("acx_normalize", False)),
            )
        except (TranscodeError, ValueError) as error:
            logger.exception("Watch audiobook build failed for %s", folder)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, error))
        return WatchActionOutcome.done(
            f"Built {out.name} ({result.chapter_count} chapters)", result_path=result.output_path
        )
