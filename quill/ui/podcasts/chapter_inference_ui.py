"""Find Chapters: the explicit request that runs the inferred chapter tiers.

The free tiers (feed chapters, ID3 frames, show-note timestamps) run by
themselves whenever an episode loads, because they are instant and their titles
were written by a person. The tiers in
:mod:`quill.core.podcasts.chapter_inference` are neither, so they run only when
the listener asks:

* **Tier 3, the transcript**, is effectively instant -- but only if a transcript
  was already cached, and it never fetches one here.
* **Tier 4, the audio scan**, shells ffmpeg over the whole file. On an hour-long
  episode that is tens of seconds, so it runs on the task manager with a spoken
  start and finish, and it is skipped entirely when tier 3 already answered.

Everything is local: tier 3 reads a cached transcript, tier 4 reads the
downloaded file. Neither reaches the network, so neither is refused in Safe Mode
-- what Safe Mode blocks is *fetching* a transcript, which this never does.

The result is cached against the audio file's size and mtime, so asking twice
costs nothing and replacing the file recomputes rather than showing chapters
that belong to different audio.

Lives outside ``main_frame_podcasts`` so that mixin stays under its GATE-11
budget, the same split the radio mixin uses for quick_play and song_history.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.podcasts.chapter_inference import (
    PODCAST_SILENCE,
    load_cached_inference,
    parse_timed_cues,
    save_cached_inference,
    segment_transcript,
)
from quill.core.podcasts.chapter_sources import MIN_EPISODE_MS, SOURCE_LABELS, show_identity
from quill.core.podcasts.chapters import PodcastChapter
from quill.core.podcasts.playback_cache import local_audio_path


def _episode_total_ms(episode: Any) -> int:
    return int(getattr(episode, "duration_seconds", 0) or 0) * 1000


def infer_chapters(
    show_id: str,
    episode_guid: str,
    *,
    total_ms: int,
    audio_path: Path | None,
    ffmpeg: str = "",
) -> tuple[list[PodcastChapter], str]:
    """Run tier 3, then tier 4. Returns ``(chapters, source)``; never raises.

    Pure orchestration around the two tiers so it can be exercised without wx:
    the caller supplies the ffmpeg path (empty disables the audio tier), and the
    transcript comes from the local cache.
    """
    from quill.core.podcasts.transcripts import load_cached_transcript

    # Tier 3 -- the transcript, if one was cached.
    try:
        raw = load_cached_transcript(show_id, episode_guid)
    except Exception:  # noqa: BLE001 - a missing cache is simply no answer
        raw = ""
    if raw:
        cues = parse_timed_cues(raw)
        chapters = segment_transcript(
            cues, total_ms=total_ms, min_chapter_ms=PODCAST_SILENCE.min_chapter_ms
        )
        if len(chapters) >= 2:
            return chapters, "transcript"

    # Tier 4 -- scan the audio. Only for a downloaded file, and only with ffmpeg.
    # detect_silence_chapters already owns the whole scan (probe the duration,
    # run silencedetect, parse the log, propose boundaries); this supplies the
    # podcast parameters rather than re-implementing any of it.
    if not ffmpeg or audio_path is None or not audio_path.is_file():
        return [], ""
    try:
        from quill.core.speech.silence import detect_silence_chapters

        sections = detect_silence_chapters(
            audio_path,
            noise_db=PODCAST_SILENCE.noise_db,
            min_silence_s=PODCAST_SILENCE.min_silence_s,
            min_chapter_ms=PODCAST_SILENCE.min_chapter_ms,
            title_prefix="Section",
        )
    except Exception:  # noqa: BLE001 - a failed scan is "no chapters", never a crash
        return [], ""
    if len(sections) < 2:
        return [], ""
    chapters = [
        PodcastChapter(start_ms=int(section.start_ms), title=str(section.title))
        for section in sections
    ]
    return chapters, "audio"


def find_chapters_for_episode(host: Any, show: Any, episode: Any) -> None:
    """Command handler: find chapters for *episode*, off the UI thread.

    Announces at every exit, because this is a request whose answer is sometimes
    "there was nothing to find" -- and a command that silently does nothing is
    indistinguishable from one that is broken.
    """
    if show is None or episode is None:
        host._announce("Play or select an episode first.")
        return

    show_id = show_identity(show)
    guid = str(getattr(episode, "guid", ""))
    if not show_id or not guid:
        host._announce("This episode cannot be identified.")
        return

    total_ms = _episode_total_ms(episode)
    if total_ms and total_ms < MIN_EPISODE_MS:
        host._announce("This episode is too short to need chapters.")
        return

    # A streamed episode whose bytes are in the playback cache is scannable
    # exactly like a downloaded one -- that is the whole point of the cache.
    audio_path = local_audio_path(show, episode)

    cached, source = load_cached_inference(show_id, guid, audio_path=audio_path)
    if len(cached) >= 2:
        _apply(host, show_id, guid, cached, source)
        return

    from quill.core.speech.ffmpeg import find_ffmpeg

    ffmpeg = find_ffmpeg() or ""
    scanning = bool(ffmpeg and audio_path is not None and audio_path.is_file())
    host._announce(
        "Looking for chapters. Scanning the audio may take a moment..."
        if scanning
        else "Looking for chapters..."
    )

    def _work(**_kwargs: object) -> tuple[list[PodcastChapter], str]:
        return infer_chapters(
            show_id, guid, total_ms=total_ms, audio_path=audio_path, ffmpeg=ffmpeg
        )

    def _done(_op: str, result: object) -> None:
        chapters, found_source = result if isinstance(result, tuple) else ([], "")
        host._wx.CallAfter(_apply, host, show_id, guid, chapters, found_source)

    def _failed(*_args: object) -> None:
        host._wx.CallAfter(host._announce, "Could not look for chapters in this episode.")

    host._task_manager.submit(
        "podcast-chapter-inference", _work, on_success=_done, on_failure=_failed
    )


def _apply(host: Any, show_id: str, guid: str, chapters: list[PodcastChapter], source: str) -> None:
    """Adopt an inferred list for the playing episode, and say what happened."""
    if len(chapters) < 2:
        host._announce(
            "No chapters could be found in this episode. "
            "Its publisher did not provide any, and neither the transcript nor "
            "the audio suggested clear sections."
        )
        return

    show = host._podcast_library.find_show(show_id)
    episode = show.find_episode(guid) if show is not None else None
    save_cached_inference(
        show_id,
        guid,
        chapters,
        source,
        audio_path=local_audio_path(show, episode) if episode is not None else None,
    )

    # Only adopt into the player when this is still the episode being played.
    if getattr(host, "_podcast_chapters_key", None) == (show_id, guid):
        host._podcast_current_chapters = list(chapters)
        host._podcast_chapters_source = SOURCE_LABELS.get(source, source)

    label = SOURCE_LABELS.get(source, source)
    host._announce(
        f"Found {len(chapters)} sections. {label}. "
        "These were worked out from the episode, not written by its publisher."
    )
