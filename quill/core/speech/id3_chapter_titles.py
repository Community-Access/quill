"""Which title a chapter frame really has, and which frames a player lists.

Kept out of the vendored ``audio_tags_core``. ID3 CHAP frames carry their title in
a TIT2 sub-frame, but some tools write a numbered placeholder there and the
real name in TIT3, and a top-level CTOC says which frames are the chapters.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["chapter_frame_title", "listed_frames", "read_podcast_chapters", "top_level_toc_ids"]

_GENERIC_TITLE = re.compile(r"^(chapter|chap|ch|part|section|track)\.?\s*\d+$", re.IGNORECASE)


def chapter_frame_title(frame: Any) -> str:
    """A CHAP frame's title: TIT2, else TIT3 (its description).

    Some tools write a numbered placeholder ("Chapter 3") in TIT2 and the real
    name in TIT3; the real name wins then (Jeff, 2026-11-27: "Chapter 1,
    Chapter 2").
    """

    def first(frame_id: str) -> str:
        sub = frame.sub_frames.get(frame_id)
        return " ".join(str(sub.text[0]).split()) if sub is not None and sub.text else ""

    title, description = first("TIT2"), first("TIT3")
    if description and (not title or _GENERIC_TITLE.match(title)):
        return description
    return title


def top_level_toc_ids(tags: Any) -> set[str]:
    for toc in tags.getall("CTOC"):
        flags = int(getattr(toc, "flags", 0) or 0)
        if flags & 0x01:  # TOP_LEVEL
            return {str(child) for child in getattr(toc, "child_element_ids", []) or []}
    return set()


def listed_frames(tags: Any) -> list[Any]:
    """The CHAP frames a player lists, in time order.

    A top-level table of contents names them; nested tables, and stray CHAP
    frames outside every table, are left out. With no table, every frame.
    """
    frames = sorted(tags.getall("CHAP"), key=lambda frame: frame.start_time)
    listed = top_level_toc_ids(tags)
    kept = [frame for frame in frames if frame.element_id in listed] if listed else []
    return kept or frames


def read_podcast_chapters(path: Any) -> list[tuple[int, int, str]]:
    """``(start_ms, end_ms, title)`` for each listed CHAP frame, in time order.

    QUILL's own reader for a podcast player. ``audio_tags_core`` is vendored
    byte for byte into podHarvest and reads TIT2 only; this one adds TIT3 and
    the table of contents without touching the shared copy.
    """
    from mutagen.id3 import ID3

    return [
        (int(frame.start_time), int(frame.end_time), chapter_frame_title(frame))
        for frame in listed_frames(ID3(str(path)))
    ]
