"""Chapters for something Radio is playing, from what already exists.

**Radio has no chapter engine and is not getting one.** It is the lite app: it
streams, it records, and adding a speech model to it would cost 91 MB to answer
a question its sibling has already answered. So this module never *works
anything out*. It looks in the three places an answer may already be sitting:

1. **The file's own chapter frames.** A recording captured from a stream that
   carried them, or an episode downloaded with ID3 chapters in it. Free, exact,
   and written by whoever made the file.
2. **Cast's inference cache.** When Cast has already analysed an episode, the
   result is on this machine, keyed by show and episode. Radio reads it. The two
   apps share a data directory, so the listener who worked chapters out in Cast
   this morning finds them in Radio this evening without doing it twice --
   which is the whole reason for a shared cache rather than a per-app one.
3. **Nothing.** Which is said plainly. Radio declining to guess is not a gap; it
   is the same rule Cast follows when Thorough finds no transcript.

wx-free, strict-typed. Never fetches, never scans, never transcribes.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts.chapters import PodcastChapter

__all__ = ["SOURCE_CACHE", "SOURCE_FILE", "chapters_for_media", "identify_episode"]

#: Where an answer came from, for the sentence the dialog leads with.
SOURCE_FILE = "the file's own chapter marks"
SOURCE_CACHE = "worked out in QUILL Cast earlier"


def identify_episode(data_dir: Path, feed_url: str, audio_url: str) -> tuple[str, str]:
    """``(show_id, episode_guid)`` for a followed episode, or two empty strings.

    Radio knows an episode as a feed address and an audio address, because that
    is what a browse row carries. Cast's cache is keyed by show id and GUID.
    The shared library holds both spellings, so the translation is a lookup
    rather than a second identity scheme -- and Radio already reads that
    library for Follow and Mark Played (:mod:`quill.core.radio.podcast_follow`).
    """
    feed = (feed_url or "").strip()
    audio = (audio_url or "").strip()
    if not feed or not audio:
        return "", ""
    try:
        from quill.core.podcasts.subscriptions import load_library

        library = load_library(data_dir)
    except Exception:  # noqa: BLE001 - a library that will not load is simply no answer
        return "", ""
    show = library.find_show_by_feed_url(feed)
    if show is None:
        return "", ""
    for episode in getattr(show, "episodes", []) or []:
        if str(getattr(episode, "audio_url", "") or "").strip() == audio:
            return str(getattr(show, "id", "") or ""), str(getattr(episode, "guid", "") or "")
    return "", ""


def chapters_for_media(
    audio_path: Path | None, *, show_id: str = "", episode_guid: str = ""
) -> tuple[list[PodcastChapter], str]:
    """``(chapters, where they came from)`` -- never computed, only found.

    *show_id* and *episode_guid* identify a Cast episode; leave them empty for a
    recording, which has no publisher and so no cache entry. An empty list and
    an empty source mean there is no answer, and the caller says so.
    """
    if audio_path is not None and audio_path.is_file():
        from quill.core.podcasts.chapter_sources import read_file_chapters

        try:
            found = read_file_chapters(audio_path)
        except Exception:  # noqa: BLE001 - an unreadable tag is simply no chapters
            found = []
        if len(found) >= 2:
            return found, SOURCE_FILE

    if show_id and episode_guid:
        from quill.core.podcasts.chapter_inference import load_cached_inference

        try:
            cached, _source = load_cached_inference(show_id, episode_guid, audio_path=audio_path)
        except Exception:  # noqa: BLE001 - a cache that cannot be read is not an error
            cached = []
        if len(cached) >= 2:
            return list(cached), SOURCE_CACHE

    return [], ""
