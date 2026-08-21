"""Analyse Chapters: the explicit, never-automatic request, with progress.

**Nothing here ever runs by itself.** Working chapters out costs real minutes --
it transcribes an hour of audio, or scans a whole file with ffmpeg -- and the
result is a set of claims nobody wrote. Both of those are reasons the listener
asks for it, is told how long it is taking, and is shown what came back before
any of it is adopted.

The shape:

1. The listener asks -- from the Podcasts menu, from the episode context menu, or
   from the command palette.
2. The work happens on the task manager, **off the UI thread**, with spoken
   progress at each stage rather than one long silence.
3. The result opens in :class:`~quill.ui.podcasts.chapter_review_dialog.ChapterReviewDialog`,
   where every mark can be previewed and corrected before it is kept.
4. Only on **Save** is anything stored.

**Progress is spoken, not shown.** A progress bar somebody cannot see is not
progress. Each stage says what it is doing and roughly how long it will take, and
the announcements are throttled so a four-minute transcription does not become
four minutes of chatter -- the rule is that silence longer than about twenty
seconds is indistinguishable from a hang, and anything more often than that is
noise.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from quill.core.podcasts import chapter_edits, inference_budget
from quill.core.podcasts.chapter_scoring import SOURCE_LABELS, ChapterAnswer, describe
from quill.core.podcasts.chapter_sources import MIN_EPISODE_MS, show_identity
from quill.core.podcasts.chapters import PodcastChapter
from quill.core.podcasts.playback_cache import local_audio_path

#: Never speak more often than this while working.
PROGRESS_INTERVAL_SECONDS = 20.0


class SpokenProgress:
    """Say what is happening, often enough to reassure and no more.

    Holds the *last* message rather than dropping it, so the stage a long job is
    actually in is announced once the throttle opens rather than being lost.
    """

    def __init__(self, announce: Any, *, interval: float = PROGRESS_INTERVAL_SECONDS) -> None:
        self._announce = announce
        self._interval = interval
        self._last = 0.0

    def stage(self, message: str, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last < self._interval:
            return
        self._last = now
        try:
            self._announce(message)
        except Exception:  # noqa: BLE001 - progress must never break the work
            return


def _estimate(total_ms: int, budget: inference_budget.InferenceBudget) -> str:
    """How long this is likely to take, in the listener's terms.

    An estimate rather than a percentage, because "about four minutes" tells
    somebody whether to wait and "37%" does not.
    """
    minutes = max(1, total_ms // 60_000)
    if budget.may_transcribe:
        # Vosk on a modern CPU runs at roughly twenty times real time.
        working = max(1, round(minutes / 20))
        return f"about {working} minute{'' if working == 1 else 's'}"
    if budget.may_scan_audio or budget.may_fetch_transcript:
        return "a few seconds"
    return "no time at all"


def analyse_playing_episode(host: Any) -> None:
    """Analyse whatever is loaded in the player.

    The command-palette and menu entry point. Resolving the episode lives here
    rather than on the frame mixin so ``main_frame_podcasts`` stays inside its
    GATE-11 budget -- the mixin's job is to name the command, not to own it.
    """
    state = host._podcast_controller.state
    show = host._podcast_library.find_show(state.show_id or "")
    episode = show.find_episode(state.episode_guid or "") if show is not None else None
    analyse_chapters_for_episode(host, show, episode)


def analyse_chapters_for_episode(host: Any, show: Any, episode: Any) -> None:
    """Command handler. Works chapters out, then opens the review dialog."""
    if show is None or episode is None:
        host._announce("Play or select an episode first.")
        return

    show_id = show_identity(show)
    guid = str(getattr(episode, "guid", ""))
    if not show_id or not guid:
        host._announce("This episode cannot be identified.")
        return

    total_ms = int(getattr(episode, "duration_seconds", 0) or 0) * 1000
    if total_ms and total_ms < MIN_EPISODE_MS:
        host._announce("This episode is too short to need chapters.")
        return

    from quill.ui.podcasts.chapter_inference_ui import _budget_for

    budget = _budget_for(host, show)
    audio_path = local_audio_path(show, episode)
    safe_mode = bool(getattr(host, "_safe_mode", False))
    progress = SpokenProgress(getattr(host, "_announce", lambda _m: None))

    progress.stage(
        f"Analysing this episode for chapters. This will take {_estimate(total_ms, budget)}. "
        "I will say when it is done.",
        force=True,
    )

    def _work(**_kwargs: object) -> ChapterAnswer:
        from quill.core.speech.ffmpeg import find_ffmpeg
        from quill.ui.podcasts.chapter_inference_ui import infer_chapters

        ffmpeg = (find_ffmpeg() or "") if budget.may_scan_audio else ""
        progress.stage("Reading what the publisher provided...", force=True)
        answer = infer_chapters(
            show_id,
            guid,
            total_ms=total_ms,
            audio_path=audio_path,
            ffmpeg=ffmpeg,
            budget=budget,
            show=show,
            episode=episode,
            safe_mode=safe_mode,
            progress=lambda message: progress.stage(message, force=True),
        )
        progress.stage("Working out where the sections are...", force=True)
        return answer

    def _done(_op: str, result: object) -> None:
        answer = result if isinstance(result, ChapterAnswer) else ChapterAnswer()
        host._wx.CallAfter(_review, host, show, episode, show_id, guid, total_ms, answer)

    def _failed(*_args: object) -> None:
        host._wx.CallAfter(host._announce, "Could not analyse this episode for chapters.")

    host._task_manager.submit(
        "podcast-chapter-analysis", _work, on_success=_done, on_failure=_failed
    )


def _review(
    host: Any,
    show: Any,
    episode: Any,
    show_id: str,
    guid: str,
    total_ms: int,
    answer: ChapterAnswer,
) -> None:
    """Show what was found, let it be corrected, and store only on Save."""
    chapters = list(answer.chapters)
    if len(chapters) < 2:
        host._announce(
            "No chapters could be found in this episode. Its publisher did not "
            "provide any, and neither the transcript nor the audio suggested "
            "clear sections."
        )
        return

    audio_path = local_audio_path(show, episode)
    settings = _settings_for(host, show)
    preview_seconds = max(3, int(getattr(settings, "chapters_preview_seconds", 10) or 10))

    from quill.ui.media.chapter_preview import ChapterPreviewPlayer
    from quill.ui.podcasts.chapter_review_dialog import ChapterReviewDialog

    player = ChapterPreviewPlayer(audio_path)
    dialog = ChapterReviewDialog(
        host.frame,
        episode_title=str(getattr(episode, "title", "") or "This episode"),
        chapters=chapters,
        total_ms=total_ms,
        preview_seconds=preview_seconds,
        summary=describe(answer),
        play_range=player.play_range if player.is_available else None,
        stop_preview=player.stop,
        announce_cb=getattr(host, "_announce", None),
    )
    try:
        kept = host._show_modal_dialog(dialog)
    except AttributeError:
        kept = dialog.show()
    finally:
        player.close()

    if not kept:
        host._announce("Chapters were not saved.")
        return
    _store(host, show, episode, show_id, guid, kept, answer.source)


def _settings_for(host: Any, show: Any) -> Any:
    try:
        return host._podcast_library.effective_settings(show)
    except Exception:  # noqa: BLE001 - defaults are a fine answer here
        from quill.core.podcasts.models import PodcastSettings

        return PodcastSettings()


def _store(
    host: Any,
    show: Any,
    episode: Any,
    show_id: str,
    guid: str,
    chapters: list[PodcastChapter],
    source: str,
) -> None:
    """Keep the reviewed list, and adopt it if this episode is playing."""
    from quill.core.podcasts.chapter_inference import save_cached_inference

    save_cached_inference(
        show_id,
        guid,
        chapters,
        source or chapter_edits.SOURCE_EDITED,
        audio_path=local_audio_path(show, episode),
    )
    if getattr(host, "_podcast_chapters_key", None) == (show_id, guid):
        host._podcast_current_chapters = list(chapters)
        host._podcast_chapters_source = SOURCE_LABELS.get(source, source)
    host._announce(f"Saved. {chapter_edits.summarise(chapters)}")


def audio_for(show: Any, episode: Any) -> Path | None:
    """The bytes a preview would play, or ``None`` when nothing is downloaded."""
    return local_audio_path(show, episode)
